import discord
from discord.ext import commands
import datetime
from datetime import timedelta
from datetime import date
from misc import *
import asyncio
import sqlite3
from discord import Option,OptionChoice
from discord.ui import View, Button, Select
from discord.commands import slash_command
# from discord_slash import SlashCommand, SlashContext, cog_ext
import os
from discord.ext.commands import has_permissions
import time

class Attendance(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')
        self.bot.loop.create_task(self.check_attendance())

    async def check_attendance(self):
        # to check if the attendance is already overdue
        start_time = time.time()
        # load the database
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        while 1:
            dt_now = get_dt_now().replace(tzinfo=None)
            attendances = cursor.execute(f"SELECT * FROM attendance WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={dt_now.year}").fetchall()
            for details in attendances:
                att_id, guild, message_id, channel_id, iso, participants = details[0], discord.utils.get(self.bot.guilds,id=details[1]), details[2], details[3], details[4], details[5]
                channel = discord.utils.get(guild.channels,id=channel_id)
                # the attendance is already overdue
                if (dt_now-datetime.fromisoformat(iso)).seconds <= 1:
                    # creaate attendance lock embed
                    lock_embed = discord.Embed(title='Attendance Closed',description=f"The attendance for {datetime.fromisoformat(str(iso)).strftime('%B %d, %Y')} has been closed.\n\nUse `/listattendance` to get a list of the participants and `/checkattendance` for individual records.")
                    lock_embed.set_footer(text=f'ID: {str(att_id).zfill(3)}')

                    # update embed in message to locked
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=lock_embed)
                    await message.clear_reactions()

                    # update attendance status to 0 (off)
                    cursor.execute(f'UPDATE attendance SET status=? WHERE message_id=?',(0,message_id))
                    db.commit()
                    print(f'{self.__class__.__name__} - close  | {time.time()-start_time} s')
            await asyncio.sleep(1)

    def attendance_embed(self,date,emoji,iso):
        attendance_datetime = datetime.fromisoformat(iso)
        return discord.Embed(color=0xfcc48f,title=f"[{date}] Attendance",description=f"Please react with {emoji} to record your attendance.\n\nFor admins, react with 🔒 to stop accepting attendances.\n\n**Up until**\n{attendance_datetime.strftime('%B %d, %Y @ %I:%M %p')}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        # check if a new attendance is to be recorded
        start_time = time.time()
        # load database
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        # check if there's an attendance associated with the message ID of reaction
        if payload.member == self.bot.user:
            return
        if cursor.execute(f'SELECT * FROM attendance WHERE message_id={payload.message_id}').fetchone() != None:
            details = cursor.execute(f'SELECT * FROM attendance WHERE message_id={payload.message_id}').fetchone()
            att_id, guild, channel_id, iso, participants = details[0], discord.utils.get(self.bot.guilds,id=details[1]), details[3], details[4], details[5]
            if participants:
                participants = participants.split(';')
            else:
                participants = []
            print(participants)
            channel = discord.utils.get(guild.channels,id=channel_id)
            message = await channel.fetch_message(payload.message_id)
            # check if reaction emoji is the same as assigned emoji for attendance
            if cursor.execute(f'SELECT emoji FROM attendance WHERE message_id={payload.message_id}').fetchone()[0] in [payload.emoji.name,str(payload.emoji)]:
                # check if attendance is still active (status = 1)
                if cursor.execute(f'SELECT status FROM attendance WHERE message_id={payload.message_id}').fetchone()[0] == 1:
                    record_embed = discord.Embed(title='Receipt of Attendance',color=discord.Colour.green(),description=f"Your attendance in `{guild.name}` has been recorded.\n\nDate: `{datetime.fromisoformat(str(iso)).strftime('%B %d, %Y')}`\nID: `{str(att_id).zfill(3)}`")
                    if cursor.execute(f"SELECT * FROM names WHERE id={payload.member.id}").fetchone():
                        name = cursor.execute(f"SELECT surname,name FROM names WHERE id={payload.member.id}").fetchone()
                        record_embed.set_author(name=f'{name[0]}, {name[1]}',icon_url=payload.member.avatar.url)
                    else:
                        record_embed.set_author(name=payload.member.display_name,icon_url=payload.member.avatar.url)
                    record_embed.set_footer(text='This is an automated message. Do not reply.')

                    # send receipt to member
                    owner_dm = await payload.member.create_dm()
                    if str(payload.member.id) in participants:
                        return await owner_dm.send('Attendance already recorded.')
                    await owner_dm.send(embed=record_embed)

                    # add member to participants
                    participants.append(str(payload.member.id))
                    await message.remove_reaction(payload.emoji,payload.member)
                    cursor.execute(f'UPDATE attendance SET participants=? WHERE message_id=?',(str(';'.join(participants)),payload.message_id))
                    db.commit()
                    return print(f'{self.__class__.__name__} - record | {time.time()-start_time} s')
            # check if reaction emoji is lock and member has admin permissions
            elif payload.emoji.name == '🔒':
                print(payload.member.top_role.permissions.administrator)
                # update embed to locked
                lock_embed = discord.Embed(title='Attendance Closed',description=f"The attendance for {datetime.fromisoformat(str(iso)).strftime('%B %d, %Y')} has been closed.\n\nUse `/listattendance` to get a list of the participants and `/checkattendance` for individual records.")
                lock_embed.set_footer(text=f'ID: {str(att_id).zfill(3)}')

                await message.edit(embed=lock_embed)
                await message.clear_reactions()

                cursor.execute(f'UPDATE attendance SET status=? WHERE message_id=?',(0,payload.message_id))
                db.commit()
                return print(f'{self.__class__.__name__} - close | {time.time()-start_time} s')
            else:
                return await message.remove_reaction(payload.emoji,payload.member)

    @commands.group(invoke_without_command=True)
    async def attendance(self,ctx):
        start_time = time.time()
        await ctx.send(embed=get_attendance(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    # create_options = [
    #     Option(discord.TextChannel,description='Where the attendance will take place'),
    #     Option(str,description='Users will react with this emoji to record their attendance'),
    #     Option(int,description='Duration (in hours of the attendance)'),
    #     Option(discord.Role,description='Role to be mentioned')
    # ]

    #@cog_ext.cog_slash(name='newattendance',description='This command will create a new attendance',options=create_options)
    @slash_command(name='newattendance',description='This command will create a new attendance')
    async def create(
        self,ctx,
        channel:Option(discord.TextChannel,description='Where the attendance will take place'),
        emoji:Option(str,description='Users will react with this emoji to record their attendance'),
        duration:Option(int,description='Duration (in hours of the attendance)'),
        role:Option(discord.Role,description='Role to be mentioned')=None
    ):
        await ctx.defer()
        start_time = time.time()

        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.send('❌ | You don\'t have permissions to do that.')

        if duration <= 0:
            return await ctx.send('❌ | Duration can only be greater than zero.')
        if emoji == '🔒':
            return await ctx.send('❌ | Please use another emoji. The emoji 🔒 is used to close attendances.')

        dt_now = get_dt_now()
        set_dt = (get_dt_now().replace(tzinfo=None) + timedelta(hours=int(duration)))
        iso = set_dt.isoformat(' ')[:16]
        att_id = get_id('attendance') # get last attendance ID in database

        # create attendance embed
        embed = self.attendance_embed(dt_now.strftime('%m/%d/%Y'),emoji,iso)
        embed.set_footer(text=f'ID: {str(att_id).zfill(3)}')

        async with ctx.channel.typing():
            message = await ctx.respond('The attendance is being created...')
            await asyncio.sleep(3)
            if role:
                role = role.mention
            role_message = await channel.send(role,embed=embed)
            await role_message.add_reaction(str(emoji))
            await role_message.add_reaction('🔒')
        # DATABASE
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        cursor.execute('INSERT INTO attendance(id,message_id,guild_id,channel_id,iso,participants,emoji,status,month,day,year,created_at,create_month,create_day,create_year) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (att_id,role_message.id,ctx.guild.id,channel.id,iso,'',str(emoji),1,set_dt.strftime('%b'),set_dt.day,set_dt.year,dt_now.isoformat(' ')[:16],dt_now.strftime('%b'),dt_now.day,dt_now.year))
        db.commit()

        await ctx.respond('Attendance created successfully.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        pass

    @attendance.command()
    @has_permissions(manage_guild=True)
    async def extend(self,ctx,duration:int=None):
        # extend the attendance duration by hour/s
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if duration is None:
            return await ctx.send('❌ | `Duration` is a required argument.')
        if duration < 1:
            return await ctx.message.reply('❌ | Please enter a valid duration.')
        try:
            ctx.message.reference.message_id
        except:
            return await ctx.message.reply('❌ | Please reply to a message that has an existing attendance.')
        else:
            if cursor.execute(f'SELECT * FROM attendance WHERE message_id={ctx.message.reference.message_id}').fetchone():
                # get attendance details
                details = cursor.execute(f'SELECT * FROM attendance WHERE message_id={ctx.message.reference.message_id}').fetchone()
                att_id, guild, message_id, channel_id, iso, participants, emoji, created_at = details[0], ctx.guild, details[2], details[3], details[4], details[5], details[6], details[11]
                # add hour/s to supposed end time of attendance
                iso = (datetime.fromisoformat(iso) + timedelta(hours=int(duration))).isoformat(' ')[:16]

                # update embed details

                embed = self.attendance_embed(datetime.fromisoformat(created_at).strftime('%m/%d/%Y'),emoji,iso)
                embed.set_footer(text=f'ID: {str(att_id).zfill(3)}')
                channel = discord.utils.get(guild.channels,id=channel_id)
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)

                # update database
                cursor.execute('UPDATE attendance SET iso=? WHERE message_id=?',(iso,ctx.message.reference.message_id))
                db.commit()

                # confirmation message
                if duration>1:
                    await message.reply(f'Attendance has been extended for {duration} hours.',delete_after=5)
                else:
                    await message.reply(f'Attendance has been extended for an hour.',delete_after=5)
                return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
            return await ctx.send('❌ | No attendance found in the message.',delete_after=5)


    options = [
        {
        'name':'month',
        'description':'Month of the attendance you want to obtain',
        'required':True,
        'type':3,
        'choices':[
            {
                'name':'January',
                'value':'Jan'
            },
            {
                'name':'February',
                'value':'Feb'
            },
            {
                'name':'March',
                'value':'Mar'
            },
            {
                'name':'April',
                'value':'Apr'
            },
            {
                'name':'May',
                'value':'May'
            },
            {
                'name':'June',
                'value':'Jun'
            },
            {
                'name':'July',
                'value':'Jul'
            },
            {
                'name':'August',
                'value':'Aug'
            },
            {
                'name':'September',
                'value':'Sep'
            },
            {
                'name':'October',
                'value':'Oct'
            },
            {
                'name':'November',
                'value':'Nov'
            },
            {
                'name':'December',
                'value':'Dec'
            }
            ]
        },
        {
        'name':'day',
        'description':'Day of the attendance you want to obtain',
        'required':True,
        'type':3
        },
        {
        'name':'year',
        'description':'Year of the attendance you want to obtain',
        'required':True,
        'type':3
        }
    ]

    @slash_command(name='checkattendance',description='Users can check their attendance record on specific dates')
    async def check(self,ctx,
        month:Option(str,description='Month of the attendance you want to obtain',choices=[
                    OptionChoice(name=date(2022,n,1).strftime('%B'),value=date(2022,n,1).strftime('%b')) for n in range (1,13)]),
        day:Option(int,description='Day of the attendance you want to obtain'),
        year:Option(int,description='Year of the attendance you want to obtain')
    ):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        await ctx.defer()
        #datetime.date(year,datetime.strptime(month,'%b').month,day)
        try:
            date(year,datetime.strptime(month,'%b').month,day)
        except:
            return await ctx.respond('❌ | Please enter a valid date.')

        details = cursor.execute(f"SELECT id,participants,iso,status,channel_id,message_id FROM attendance WHERE create_month='{month}' AND create_day={day} AND create_year={year} AND guild_id={ctx.guild.id}").fetchall()
        if details:
            description, att_legend = '',{True:'✅',False:'🅾'}
            for att in details:
                channel = discord.utils.get(ctx.guild.channels,id=int(att[4]))
                id, is_present, att_time, message = att[0], str(ctx.author.id) in att[1].split(';'), datetime.fromisoformat(att[2]).strftime('%m/%d/%Y @ %I:%M %p'), await channel.fetch_message(att[5])
                if att[3] == 1:
                    description += f"{att_legend[is_present]} | [ID:{str(id).zfill(2)}]({message.jump_url}) Closes at `{att_time}` 🆙" + '\n'
                else:
                    description += f"{att_legend[is_present]} | [ID:{str(id).zfill(2)}]({message.jump_url}) Closed at `{att_time}`" + '\n'
            embed=discord.Embed(color=0x583D73,title='My Record',description=f'Attendance\nGuild: `{ctx.guild.name}`\nDate: `{month} {day}, {year}`\n\n{description}')
            name = cursor.execute(f'SELECT surname,name FROM names WHERE id={ctx.author.id}').fetchone()
            if name:
                embed.set_author(icon_url=ctx.author.avatar.url,name=f'{name[0]}, {name[1]}')
            else:
                embed.set_author(icon_url=ctx.author.avatar.url,name=f'{ctx.author.display_name}')

            await ctx.respond(embed=embed)
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        return await ctx.respond('❌ | No attendance found in specified date.')

    @slash_command(name='attendancelist',description='Users can get a record of attendances in a day')
    async def list(self,ctx,
        month:Option(str,description='Month of the attendance you want to obtain',choices=[
                    OptionChoice(name=date(2022,n,1).strftime('%B'),value=date(2022,n,1).strftime('%b')) for n in range (1,13)]),
        day:Option(int,description='Day of the attendance you want to obtain'),
        year:Option(int,description='Year of the attendance you want to obtain')
    ):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        await ctx.defer()
        try:
            date(year,datetime.strptime(month,'%b').month,day)
        except:
            return await ctx.respond('❌ | Please enter a valid date.')

        details = cursor.execute(f"SELECT id,participants,iso,status,channel_id,message_id FROM attendance WHERE create_month='{month}' AND create_day={day} AND create_year={year} AND guild_id={ctx.guild.id}").fetchall()
        if details:
            if len(details) == 1:
                participants, iso = details[0][1].split(';'), datetime.fromisoformat(details[0][2])
                participants.sort()
            if len(details) > 1:
                emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                                 14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}
                description = ''
                for n in range(len(details)):
                    if details[n][3] == 1:
                        description += f"{emojis[n]} Closes at {datetime.fromisoformat(details[n][2]).strftime('%I:%M %p')} 🆙\n"
                    else:
                        description += f"{emojis[n]} Closed at {datetime.fromisoformat(details[n][2]).strftime('%I:%M %p')}\n"
                embed = discord.Embed(description=f'{description}')
                message = await ctx.send('It looks like the server has multiple records of attendance for this day. Which of the following would you like to obtain?',embed=embed)
                for n in range(len(details)):
                    await message.add_reaction(emojis[n])
                try:
                    reaction = await self.bot.wait_for('reaction_add',timeout=60,check=lambda reaction,user: str(reaction.emoji) in emojis.values() and user == ctx.author)
                except TimeoutError:
                    return await ctx.respond('❌ | Process terminated. [Timeout Error]')
                else:
                    for index,emoji in emojis.items():
                        if str(reaction[0].emoji) == emoji:
                            details = details[index]
                            break
                participants, iso = details[1].split(';'), datetime.fromisoformat(details[2])
                participants.sort()
            await message.delete()
            if '' in participants:
                participants.remove('')
            pages = []

            if len(participants) == 0:
                return await ctx.respond('No recorded attendance.',delete_after=5)
            attendees = []
            for person in participants:
                if cursor.execute(f'SELECT surname,name FROM names WHERE id={int(person)}').fetchone():
                    name = cursor.execute(f'SELECT surname,name FROM names WHERE id={int(person)}').fetchone()
                    attendees.append(f'{name[0]}, {name[1]} | ID: {person}')
                else:
                    try:
                        attendees.append(f'[Server Nickname] {discord.utils.get(ctx.guild.members,id=int(person)).display_name} | ID: {person}')
                    except:
                        attendees.append(f'[User Not Found] | ID: {person}')
            attendees.sort()
            f = open(f"[{iso.strftime('%d%m%y')}] {ctx.guild.name}.txt","w+")
            f.write(f"Attendance List | ID: {str(details[0]).zfill(3)}\nDate: {iso.strftime('%B %d, %Y')}\nGuild: {ctx.guild.name}\nID: {ctx.guild.id}\n\n")
            f.write('\n'.join(attendees))
            f.close()
            await ctx.respond(file=discord.File(f"[{iso.strftime('%d%m%y')}] {ctx.guild.name}.txt"))
            os.remove(f"[{iso.strftime('%d%m%y')}] {ctx.guild.name}.txt")
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

        return await ctx.send('❌ | No attendance found in specified date.')

def setup(bot):
    bot.add_cog(Attendance(bot))
