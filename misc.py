import discord
import sqlite3
from datetime import datetime
import pytz
import time
from discord.ui import View, Button, Select

def get_dt_now():
    """
    RETURNS CURRENT DATE-TIME IN PHILIPPINE TIMEZONE
    """
    utc_now = pytz.utc.localize(datetime.utcnow())
    return utc_now.astimezone(pytz.timezone('Asia/Manila'))

def create_embed(title,body,field_titles:list=None,field_values:list=None,author:discord.Member=None):
    db = sqlite3.connect('main.sqlite')
    cursor = db.cursor()
    """
    CREATES AN EMBED FOR ANNOUNCEMENTS AND REMINDERS
    """
    embed = discord.Embed(title=title,description=body,color=discord.Colour.red())
    if author:
        embed.set_author(name=author.display_name,icon_url=author.avatar.url)
        if cursor.execute(f"SELECT * FROM names WHERE id={author.id}").fetchone():
            author_name = ' '.join(cursor.execute(f"SELECT name,surname FROM names WHERE id={author.id}").fetchone())
            embed.set_author(name=author_name,icon_url=author.avatar.url)
    if field_titles is None:
        return embed
    for n in range(len(field_titles)):
        embed.add_field(inline=False,name=field_titles[n],value=field_values[n])
    return embed

def convert_time(date_time):
### converts YYYY-MM-DD HH:MM<AM/PM> to iso datetime format ###
    time = date_time.split(' ')[1]
    if time[5:] == 'AM':
        if int(time[0:2])==12:
            # 12:00AM in military time is 00:00
            return str(f"{date_time.split(' ')[0]} 00:{time[3:5]}")
        return str(f"{date_time.split(' ')[0]} {time[:5]}")
    else:
        if int(time[0:2])==12:
            return str(f"{date_time.split(' ')[0]} {time[:5]}")
        # 1:00PM in military time is 13:00
        return str(f"{date_time.split(' ')[0]} {str(int(time[0:2])+12)}:{time[3:5]}")

def get_id(table):
    db = sqlite3.connect('main.sqlite')
    cursor = db.cursor()
    temp_id=cursor.execute(f'SELECT id FROM {table}').fetchall()
    if len(temp_id) == 0:
        return 1
    else:
        return int(temp_id[len(temp_id)-1][0])+1

def time_diff(iso):
    if iso is None:
        return None
    else:
        time_diff, string = (datetime.fromisoformat(iso))-get_dt_now().replace(tzinfo=None),''
        time_units = ['d','h','m']
        time_input = [time_diff.days,time_diff.seconds//3600,(time_diff.seconds-(time_diff.seconds//3600*3600))//60]
        if time_diff.seconds < 60:
            return f'{time_diff.seconds}s '
        for n in range(len(time_input)):
            if time_input[n] != 0:
                string+=f'{time_input[n]}{time_units[n]} '
        return string

def is_setup(guild,bot):
    return guild.roles[len(guild.roles)-1].name == bot.user.name

####################
### GUIDE EMBEDS ###
####################

class DocumentationButton(Button):
    def __init__(self):
        super().__init__(label = 'View Full Documentation',row=1, url='https://docs.google.com/document/d/1jMqrCvDmOKzdc6_e7TRP0IrzIgxR5a3A0l2yUgKZHQw/edit?usp=sharing',style = discord.ButtonStyle.link)

    async def callback(self,interaction:discord.Interaction):
        view = self.view
        self.disabled = True
        await interaction.response.edit_message(view=view)


async def get_help(ctx,bot):
    start_time = time.time()
    """
    1 - Intro
    2 - Features
    3 - Moderation
    4 - Announcements
    5 - Reminders
    6 - Consultation
    7 - Attendance
    8 - Roles
    9 - Scheduling/Requirements
    10 - Logs
    11 - Math
    12 - Grades Computation
    13 - Polls
    14 - Forums
    15 - Utility
    16 - Bot info
    """
    page_one = discord.Embed(title=f'Cybot Guide | $help',description='Hey there, I am Cybot, specifically designed to accomodate the needs of academic servers! You can visit my [documentation guide](https://docs.google.com/document/d/1jMqrCvDmOKzdc6_e7TRP0IrzIgxR5a3A0l2yUgKZHQw/edit?usp=sharing) or use this embed to help you guide your way in using my features.',color=0xA3C1BC)
    page_one.add_field(inline=False,name=f'$features',value='Lists the features of the bot')
    page_one.add_field(inline=False,name=f'$commands',value='Lists the commands of the bot\n\nSome commands require specific permissions (👥) to perform the action')
    page_one.add_field(inline=False,name=f'$setup',value='Initializes the bot for smoother use')
    page_one.add_field(inline=False,name=f'$bot',value='Learn more about the bot\'s creation')
    pages = [page_one,get_features(ctx)]
    pages.extend(get_moderation(ctx))
    pages.extend([get_announcements(ctx),
            get_bulletin(ctx),
            get_reminders(ctx),
            get_consultation(ctx),
            get_attendance(ctx),
            get_roles(ctx),
            get_sched(ctx),
            get_todolist(ctx),
            get_logs(ctx),
            get_math(ctx),
            get_polls(ctx),
            get_forum(ctx),
            get_utility(ctx),
            get_info(ctx)])

    for n in range(1,len(pages)+1):
        pages[n-1].set_author(name=f'Page {n}/{len(pages)}')
    message = await ctx.channel.send(embed=pages[0],view=View(DocumentationButton()))
    for reaction in ['⏪','◀️','▶️','⏩']:
        await message.add_reaction(reaction)
    print(f'Help - $help | {time.time()-start_time} s')
    i = 0
    while(1):
        try:
            reaction = await bot.wait_for('reaction_add',timeout=240,check=lambda reaction,user: str(reaction.emoji) in ['⏪','◀️','▶️','⏩'] and reaction.message.id == message.id and user != bot.user)
        except:
            lock_embed = discord.Embed(description='This embed has been locked [Reason: Timeout]')
            await message.edit(embed = lock_embed)
            return await message.clear_reactions()
        else:
            if str(reaction[0].emoji) == '⏪':
                await message.edit(embed=pages[0],view=View(DocumentationButton()))
                i=0
            elif str(reaction[0].emoji) == '◀️':
                if i>0:
                    i-=1
                    await message.edit(embed=pages[i],view=View(DocumentationButton()))
            elif str(reaction[0].emoji) == '▶️':
                if i<len(pages)-1:
                    i+=1
                    await message.edit(embed=pages[i],view=View(DocumentationButton()))
            else:
                i=len(pages)-1
                await message.edit(embed=pages[i],view=View(DocumentationButton()))
            await message.remove_reaction(reaction[0].emoji,reaction[1])

def get_features(ctx):
    features = discord.Embed(title=f'Features | $features',description='Here are the things that I can do in the server!\nThe features are divided into the following categories:',color=0xA3C1BC)
    features.add_field(inline=False,name=f'🛎 Management',value='`moderation` `logs` `roles`\n`information` `utility` `help`')
    features.add_field(inline=False,name=f'🏫 Digital Classroom',value='`scheduling` `announcements` `reminders`\n`consultation` `attendance`')
    features.add_field(inline=False,name=f'💡 Extras',value='`forum` `polls` `bulletin`\n`information` `utility` `help`')
    features.set_footer(text=f'For more information regarding a feature, use $help <feature>')
    return features

def get_moderation(ctx):
    server_moderation = discord.Embed(color=0xA3C1BC,title=f'Server Moderation | $mod',description='👥 `Manage Server`\nAdministrators can use this feature to control what\'s happening in the server')
    server_moderation.add_field(inline=False,name='/mod `logs` `channel` `maxwarns` `warnpunishment` `censor` `censorpunishment`',value='Configures the moderation settings in the server')
    server_moderation.add_field(inline=False,name=f'$modsettings',value='Returns the moderation settings for the server')
    server_moderation.add_field(inline=False,name='/censor `prompts`',value='Adds prompts that are to be filtered in the server')
    server_moderation.add_field(inline=False,name='/lockdown `channel`',value='Disallows *everyone* from sending messages to the server')
    server_moderation.add_field(inline=False,name='/unlock `channel`',value='Unlocks a previously locked channel')
    server_moderation.set_footer(text=f'Example: /warn user:@user')

    member_moderation = discord.Embed(color=0xA3C1BC,title=f'Member Moderation | $mod',description='👥 `Manage Server`\nAdministrators can use this feature to control the actions of certain users')
    member_moderation.add_field(inline=False,name='/mute `user` `reason:Optional`',value='Disallows a user from sending messages to the server')
    member_moderation.add_field(inline=False,name='/tempmute `user` `duration` `reason:Optional`',value='Temporarily mutes a user for a given number of hour/s')
    member_moderation.add_field(inline=False,name='/unmute `user`',value='Unmutes a previously muted user')
    member_moderation.add_field(inline=False,name='/kick `user` `reason:Optional`',value='Evicts a user from the server')
    member_moderation.add_field(inline=False,name='/ban `user` `reason:Optional`',value='Bans a user from the server')
    member_moderation.add_field(inline=False,name='/softban `user` `duration` `reason:Optional`',value='Temporarily bans a user for a given number of hour/s')
    member_moderation.add_field(inline=False,name='/unban `user ID`',value='Unbans a previously banned user')
    member_moderation.add_field(inline=False,name='/warn `user` `reason:Optional`',value='Warns a user in the server')
    member_moderation.add_field(inline=False,name='/removewarn `user` `number`',value='Removes a number of warnings from the member\'s record')
    member_moderation.add_field(inline=False,name='/clearwarns `user`',value='Clears the warning record of a user in the server')
    return [server_moderation,member_moderation]

def get_bulletin(ctx):
    bulletin = discord.Embed(color=0xA3C1BC,title=f'Bulletin | $bulletin',description='Using this feature, members can freely express their thoughts on a designated channel')
    bulletin.add_field(inline=False,name='$setbulletin `channel`',value='Sets channel as the destination of all bulletin posts')
    bulletin.add_field(inline=False,name='/post `category` `message` `attachment:Optional`',value='Creates a new bulletin entry in the server')
    bulletin.add_field(inline=False,name='/deletepost `post number`',value='Deletes an existing post\nUsers can only delete their own posts')
    bulletin.add_field(inline=False,name='/warnpost `post number` `reason`',value='👥 `Manage Server`\nWarns the author of a post given a reason\n*Note: this is different from `/warn` in server moderation*')
    bulletin.add_field(inline=False,name='/mutepost `post number` `reason`',value='👥 `Manage Server`\nProhibits the user from posting bulletin entries in the server\n*Note: this is different from `/mute` in server moderation*')
    bulletin.add_field(inline=False,name='/unmutepost `post number`',value='👥 `Manage Server`\nRemoves restriction from previously muted member')
    bulletin.set_footer(text=f'Example: /post category:Feeback message:Add more channels')
    return bulletin

def get_announcements(ctx):
    announcements = discord.Embed(color=0xA3C1BC,title=f'Announcements | $announce',description='👥 `Manage Server`\nAnnouncements can be used by administrators, teachers, and instructors to relay messages to the members of the server. Through the following commands, you can create both text and embed `($help embed)` announcements that can be sent right away or can be scheduled for another day/time.')
    announcements.add_field(name='_create  `#channel` `type`',value='Creates a new announcement posted in a specific channel',inline=False)
    announcements.add_field(name='_edit `ID`',value=f'Edit the details of a scheduled announcement by its ID ($announce list)',inline=False)
    announcements.add_field(name='_delete `ID`',value=f'Deletes a scheduled announcement by its ID ($announce list)',inline=False)
    announcements.add_field(name='_list',value='Lists all pending announcements for the server',inline=False)
    announcements.set_footer(text=f'Example: $announce create #channel embed')
    return announcements

def get_reminders(ctx):
    reminders = discord.Embed(color=0xA3C1BC,title=f'Reminders | $remind',description='👥 `Manage Server`\nReminders are quick announcements that can be sent once, daily, weekly, and monthly. This feature is essential for noting weekly meetings or monthly activities.')
    reminders.add_field(name='_create `#channel` `repeat:Optional`',value='Creates a new reminder in a specific channel\n\nRepeat options:\n*once*\n*daily*\n*weekly*\n*monthly*\n*never [leave empty]*',inline=False)
    reminders.add_field(name='_edit `ID`',value=f'Edit the details of a scheduled reminder by its ID ($remind list)',inline=False)
    reminders.add_field(name='_list',value='Lists all scheduled reminders for the server',inline=False)
    reminders.add_field(name=f'$stop `ID`',value=f'Deletes a scheduled reminder by its ID ($remind list)',inline=False)
    reminders.set_footer(text=f'Example: $remind create #channel weekly')
    return reminders

def get_attendance(ctx):
    attendance = discord.Embed(color=0xA3C1BC,title=f'Attendance | $attend',description='Attendances allow the administrators to check the present people at a specific time')
    attendance.add_field(inline=False,name='/newattendance `channel` `emoji` `duration` `role`',value='👥 `Manage Server`\nCreates a new attendance instance')
    attendance.add_field(inline=False,name=f'$extend `duration`',value='👥 `Manage Server`\nExtends the duration of an active attendance by a given number of hours\nCalled by replying to the attendance message')
    attendance.add_field(inline=False,name='/checkattendance `month` `day` `year`',value='Checks the user\'s attendance in a specific date')
    attendance.add_field(inline=False,name='/listattendance `month` `day` `year`',value='👥 `Manage Server`\nLists all the present people in a specific attendance date')
    attendance.set_footer(text=f'Example: /listattendance month:May day:15 year:2022')
    return attendance

def get_consultation(ctx):
    consultation = discord.Embed(color=0xA3C1BC,title=f'Consultation | $consult',description='The consultation feature of the bot allows users to ask queries to the administrators of the server without having to DM them personally. Rest assured, all outgoing messages will remain anonymous.')
    consultation.add_field(inline=False,name=f'DM @Cybot#2586 (`$consult test`)',value='Interacts with the bot to initialize a new conversation, to reply to an existing ticket, or to adjourn a consultation\n\nFormat:\n`message` - create a new consultation ticket\n`@XXXX <message>` - reply to an existing ticket with its assigned *four-digit* ID\n`close @XXXX` - close an existing consultation ticket using its assigned ID')
    consultation.add_field(inline=False,name=f'$admin',value='Lists the administrators for the server')
    consultation.add_field(inline=False,name=f'_set `@mention/ID`',value='👥 `Manage Server`\nSet a user as a server admin')
    consultation.add_field(inline=False,name=f'_remove `@mention/ID`',value='👥 `Manage Server`\nRemove a user from the server\'s admin list')
    consultation.set_footer(text=f'Example: $admin set @user | $admin remove @user')
    return consultation

def get_roles(ctx):
    roles = discord.Embed(color=0xA3C1BC,title=f'Roles Management | $roles',description='👥 `Manage Roles`\nThis feature allows you to create and modify roles, as well as make a reaction role system that allows the members to obtain the role they want.')
    roles.add_field(inline=False,name=f'_create `name`',value='Creates a new role')
    roles.add_field(inline=False,name=f'_edit `role name/mention`',value='Modifies the attributes of an existing role')
    roles.add_field(inline=False,name=f'_delete `role`',value='Deletes an existing role')
    roles.add_field(inline=False,name=f'_assign `role`',value='Assigns an existing role')
    roles.add_field(inline=False,name=f'_unassign `role`',value='Unassigns an existing role')
    roles.add_field(inline=False,name=f'$rr',value='Creates a new reaction role instance')
    roles.set_footer(text=f'Example: $role assign student @user')
    return roles

def get_sched(ctx):
    schedule = discord.Embed(color=0xA3C1BC,title=f'Scheduling/Requirements | $sched/reqs',description='Tracking upcoming deadlines and appointments is one of the essential features of the bot. It allows users to browse through schedules duly consolidated by the server administrators.')
    schedule.add_field(inline=False,name=f'$sched `year:Optional`',value='Displays schedules list for the year (current year if no argument passed)')
    schedule.add_field(inline=False,name='_id `year:Optional`',value='👥 `Manage Server`\nDisplays schedules list for the year by ID')
    schedule.add_field(inline=False,name='_add `month` `day` `year` `time` `name`',value='👥 `Manage Server`\nAdds a new schedule instance to the server\'s database')
    schedule.add_field(inline=False,name='_delete `ID`',value='👥 `Manage Server`\nDeletes a schedule by its ID')
    schedule.add_field(inline=False,name='_edit `ID`',value='👥 `Manage Server`\nModifies a schedule by its ID')
    schedule.set_footer(text=f'Example: $sched add March 20 2021 10:00AM reflection paper')
    return schedule

def get_todolist(ctx):
    schedule = discord.Embed(color=0xA3C1BC,title=f'To-do Lists | $td',description='To-do lists allow users to track their own progress in their tasks')
    schedule.add_field(inline=False,name=f'_setchannel `channel`',value='👥 `Manage Server`\nSets channel as the destination of server to-do lists')
    schedule.add_field(inline=False,name='_new `channel` `tasks`',value='Creates a new to-do list instance\nChannel can be *DM* or *default*\nMultiple tasks are separated by line breaks\n*Note: Private to-do lists cannot be modified*')
    schedule.add_field(inline=False,name='_add `tasks`',value='Adds new task/s to a to-do list\nCalled by replying to the message containing the list')
    schedule.add_field(inline=False,name='_remove `emoji`',value='Removes the task that corresponds to the emoji\nCalled by replying to the message containing the list')
    schedule.set_footer(text=f'Example: $td new DM eat chocolate | $td add eat strawberry')
    return schedule

def get_logs(ctx):
    db = sqlite3.connect('main.sqlite')
    cursor = db.cursor()
    logs_status,status_emoji = cursor.execute(f"SELECT mlog,schedlog,serverlog FROM logs_status WHERE guild_id={ctx.guild.id}").fetchone(),{1:'✅',0:'❌',None:'❌'}
    logs_status = [logs_status[0],logs_status[1],logs_status[2]]
    logs_description = {'mlog':'Logs who goes in and out of the server',
                        'schedlog':'Updates the server regarding upcoming events and tasks in the server daily, weekly, or monthly',
                        'serverlog':'Logs all actions happening in the server'}
    logs_embed = discord.Embed(color=0xA3C1BC,title=f'Logs | $logs',description='👥 `Manage Server`\nLogs the activities and changes inside the server.')
    n = 0
    for log,description in logs_description.items():
        logs_embed.add_field(inline=False,name=f'${log}',value=f'{description}\nStatus: {status_emoji[logs_status[n]]}')
        n+=1
    logs_embed.set_footer(text=f'Example: $mlog')
    return logs_embed

def get_math(ctx):
    math_bot = discord.Embed(color=0xA3C1BC,title=f'Math | $math',description='The bot\'s unit conversion feature allows users to easily convert a measurement into another unit')
    math_bot.add_field(inline=False,name=f'$convert `unit_a>unit_b` `value`',value='Converts a measurement from one unit to another')
    math_bot.add_field(inline=False,name=f'$units `category`',value=f'Lists the valid units for measurement conversion (`$convert`)')
    math_bot.set_footer(text=f'Example: $convert rad>deg 3.14 | $units energy')
    return math_bot

# def get_grades(ctx):
#     grades = discord.Embed(color=0xA3C1BC,title=f'Grades | $grades',description='')
#     grades.add_field(inline=False,name=f'$grade `raw_grade`',value='- Transmutes a given raw grade into its equivalent numeric grade\n- Requires parameter **raw_grade [integer/decimal]**')
#     grades.add_field(inline=False,name=f'$gwa `grade_level:Optional`',value='- Computes the general weighted average of given grades\n- Accepts parameter **grade_level [integer]**')
#     grades.set_footer(text=f'Example: $grade 87.41')
#     return grades

def get_polls(ctx):
    polls = discord.Embed(color=0xA3C1BC,title=f'Polls | $poll',description='Polls allow the members to participate in decision-making')
    polls.add_field(inline=False,name=f'$create `channel`',value='Creates a new poll instance in a channel\nUp to 18 choices')
    polls.add_field(inline=False,name=f'$add `choice/s`',value='Adds choice/s to an existing poll\nMultiple choices are allowed, separated by line breaks')
    polls.add_field(inline=False,name=f'$remove `emoji`',value='Removes a choice that corresponds to the emoji in an existing poll')
    polls.set_footer(text=f'Example: $<command> <argument>')
    return polls

def get_forum(ctx):
    forum = discord.Embed(color=0xA3C1BC,title=f'Forum Threads | $forum',description='Forums allow members to answer questions set by admins')
    forum.add_field(inline=False,name=f'$setforum `channel`',value='Sets the channel as the destination of all forum-related interactions')
    forum.add_field(inline=False,name='/ask `question` `details` `anonymity` `votingsystem`',value='Creates a new question in the forum channel\nResponses can be kept anonymous\nAn upvote-downvote system can be applied to the question')
    forum.add_field(inline=False,name='/answer `forumnumber` `answer` `details`',value='Answers a forum question')
    forum.set_footer(text=f'Example: /ask question:What is love? details:Explain in 10 words anonymity:Enabled votingsystem:Disabled')
    return forum

def get_utility(ctx):
    utility = discord.Embed(color=0xA3C1BC,title=f'Utility Commands | $utility')
    utility.add_field(inline=False,name=f'$prune `n` `user:Optional`',value='👥 `Manage Messages`\n- Deletes **n** number of messages\n- Accepts parameter **user** for user-specific deletion of messages\n- **user** can be a member\'s name, member mention, or `bot`')
    utility.add_field(inline=False,name=f'$prefix `new prefix`',value='👥 `Manage Server`\n- Sets the server prefix to `new prefix`')
    utility.add_field(inline=False,name=f'$rules',value='Displays the rules set for the server')
    utility.add_field(inline=False,name=f'_add `rule`',value='👥 `Manage Server`\nAdds the rule to the server\'s rulebook')
    utility.add_field(inline=False,name=f'_remove `rulenumber`',value='👥 `Manage Server`\nRemoves the rule that corresponds to the rule number in the server')
    utility.set_footer(text=f'Example: $prune 100 @user | $rules add No Profanity!')
    return utility

def get_info(ctx):
    info = discord.Embed(color=0xA3C1BC,title=f'Info | $info',description='Allows users to obtain info about the members, the server, as well as the bot')
    info.add_field(inline=False,name=f'$member `member`',value='Displays info about the member\nIf no member is passed, own info will be sent instead')
    info.add_field(inline=False,name=f'$avatar `member`',value='Displays the avatar of the member\nIf no member is passed, own avatar will be sent instead')
    info.add_field(inline=False,name=f'$server',value='Displays info about the server')
    info.add_field(inline=False,name=f'_meet `url`',value='👥 `Manage Server`\nSets the meeting link for the server')
    info.add_field(inline=False,name=f'_subject `topic`',value='👥 `Manage Server`\nSets the topic of the server')
    info.add_field(inline=False,name=f'_reset',value='👥 `Manage Server`\nResets all information (i.e. meet link, subject) for the server')
    info.add_field(inline=False,name=f'$bot',value='Displays information about Cybot')
    info.set_footer(text=f'Example: $bot | $server meet https://meet.google.com')
    return info
