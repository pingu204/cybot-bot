import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
import sqlite3
from datetime import timedelta
from datetime import datetime
from dateutil import relativedelta
import math
import asyncio
from misc import *
import time

class Announcements(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    ######################
    ### MISC FUNCTIONS ###
    ######################

    async def check_schedule(self):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        while 1:
            dt_now = get_dt_now().replace(tzinfo=None)
            announcements = cursor.execute(f"SELECT id,type,guild_id,channel_id,iso,title,body,field_titles,field_values,author_id FROM announcements WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={dt_now.year}").fetchall()
            # announcements = [id,type,guild_id,channel_id,iso,title,body,field_titles,field_values]
            for element in announcements:
                time_diff = dt_now-datetime.fromisoformat(element[4])
                if time_diff.seconds <= 1:
                    start_time = time.time()
                    # announcement is scheduled NOW
                    guild = self.bot.get_guild(element[2])
                    if element[1] == 'text':
                        # send title + body to destination channel
                        await discord.utils.get(guild.channels,id=int(element[3])).send(f'**{element[5]}**\n\n{element[6]}')
                    else:
                        # send embed in message object  to destination channel
                        channel = discord.utils.get(guild.channels,id=int(element[3]))
                        author = discord.utils.get(guild.members,id=int(element[9]))
                        if element[7]:
                            await channel.send(embed=create_embed(element[5],element[6],element[7].split(';'),element[8].split(';'),author))
                        else:
                            await channel.send(embed=create_embed(element[5],element[6],None,None,author))
                    cursor.execute(f"DELETE FROM announcements WHERE id={int(element[0])}")
                    db.commit()
                    print(f'{self.__class__.__name__} - Send scheduled announcement | {time.time()-start_time} s')
            await asyncio.sleep(1)

    async def add_fields(self,ctx):
        ### returns string of field titles and values ###
        titles,values = [],[]
        while 1:
            field_response = await ctx.send('Do you want to add a new field?')
            await field_response.add_reaction('👍')
            await field_response.add_reaction('👎')
            try:
                reaction = await self.bot.wait_for('reaction_add',timeout=30,check=lambda reaction,user: user == ctx.author and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'))
            except:
                await field_response.delete()
                if len(titles)==0:
                    return None,None
                return ';'.join(titles),';'.join(values)
            else:
                if str(reaction[0]) == '👍':
                    # field details
                    for key in ['title','description']:
                        message = await ctx.send(f'Enter the {key} of the field')
                        value = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
                        if key == 'title':
                            titles.append(value.content)
                        else:
                            values.append(value.content)
                        await value.add_reaction('✅')
                        await message.delete()
                else:
                    await field_response.delete()
                    if len(titles)==0:
                        return None,None
                    return ';'.join(titles),';'.join(values)

    async def ask_details(self,ctx):
        field_dict = {'title':None,'description':None}
        to_delete = []
        for key in field_dict.keys():
            message = await ctx.send(f'Enter the {key} of the announcement.')
            try:
                value = await self.bot.wait_for('message',timeout=240,check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
                field_dict.update({key:value})
            except:
                break
            else:
                await value.add_reaction('✅')
                await message.delete()
                to_delete.append(value)
        await ctx.channel.delete_messages(to_delete)
        return field_dict['title'],field_dict['description']

    async def edit_datetime(self,ctx,table,id):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        to_delete = []

        # ask new value for date
        message=await ctx.send('Please enter a send date in the format `<month> <day> <year>`')
        user_response = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
        await user_response.add_reaction('✅')
        await message.delete()
        to_delete.append(user_response)
        date = user_response.content.split(' ')

        # ask new value for time
        message = await ctx.send('Please enter a send time in the format `HH:MM<AM/PM>`')
        user_response = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
        await user_response.add_reaction('✅')
        await message.delete()
        to_delete.append(user_response)
        temp_time = user_response.content.split(':')
        convert_datetime = f"{date[2]}-{str(datetime.strptime(date[0][:3].capitalize(),'%b').month).zfill(2)}-{str(date[1]).zfill(2)} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"

        try:
            if datetime.fromisoformat(convert_time(convert_datetime)) < get_dt_now().replace(tzinfo=None):
                return await ctx.send('❌ | New date-time is already overdue.',delete_after=3)
        except:
            return await ctx.send('❌ | Invalid date-time.')
        else:
            new_datetime = datetime.fromisoformat(convert_time(convert_datetime))

        month, day, year = new_datetime.strftime('%b'), new_datetime.day, new_datetime.year
        cursor.execute(f'UPDATE {table} SET year=?,month=?,day=?,iso=? WHERE id=? AND guild_id = ?',(year,month, day,new_datetime.isoformat(' '),id,ctx.guild.id))
        await ctx.channel.delete_messages(to_delete)
        await ctx.send(f'✅ Date-time has been updated to `{new_datetime.strftime("%B %d, %Y @ %I:%M %p")}`',delete_after=5)
        db.commit()


    ######################
    ### MISC FUNCTIONS ###
    ######################

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')
        self.bot.loop.create_task(self.check_schedule())

    @commands.group(invoke_without_command=True, aliases=['announcement'])
    async def announce(self,ctx):
        ### SEND GUIDE IN USING THE ANNOUNCEMENT FEATURE ###
        await ctx.send(embed=get_announcements(ctx))

    @announce.command(aliases=['new','+'])
    @has_permissions(manage_guild=True)
    async def create(self,ctx,channel:discord.TextChannel=None,type:str='text'):
        ### CREATES A NEW ANNOUNCEMENT ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        to_delete = []

        if channel is None:
            return await ctx.send('❌ | Channel is a required parameter.')
        if type.lower() not in ['text','embed']:
            return await ctx.send('❌ | Announcement type must be `text` or `embed` only.')
        title,description = await self.ask_details(ctx)
        if title is None or description is None:
            return await ctx.send('❌ | Failed to obtain needed information. Please try again.',delete_after=2.0)

        if(type == 'text'):
            # SEND TITLE AND BODY OF TEXT ANNOUNCEMENT
            confirm_msg = await ctx.send(f'React with 👍 to confirm announcement\n\nTitle: ```\n{title.content}```\n\nDescription:```\n{description.content}```')
            field_titles,field_values=None,None # NO FIELDS IN TEXT ANNOUNCEMENTS
        else:
            # CREATE AN EMBED OBJECT
            field_titles,field_values=await self.add_fields(ctx)
            # SEND TITLE AND BODY OF TEXT ANNOUNCEMENT
            if field_titles:
                embed = create_embed(title.content,description.content,field_titles.split(';'),field_values.split(';'),ctx.author)
            else:
                embed = create_embed(title.content,description.content,field_titles,field_values,ctx.author)
            confirm_msg = await ctx.send(f'React with 👍 to confirm announcement',embed=embed)

        await confirm_msg.add_reaction('👍')
        try:
            reaction = await self.bot.wait_for('reaction_add',timeout=30,check=lambda reaction,user: user == ctx.author and str(reaction.emoji) == '👍')
            await confirm_msg.delete()
        except:
            return await ctx.send('❌ | Timeout error. Please try again.', delete_after=2.0)
        else:
            # ASK WHEN TO SEND THE ANNOUNCEMENT
            confirm_date = await ctx.send('Send now? React with ⏰ to schedule send.')
            await confirm_date.add_reaction('👍')
            await confirm_date.add_reaction('⏰')
            try:
                reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and reaction.message == confirm_date and str(reaction.emoji) in ['👍','⏰'])
                await confirm_date.delete()
            except:
                return await ctx.send('❌ | Timeout error. Please try again.', delete_after=4.0)
            else:
                if str(reaction[0]) == '👍':
                    # SEND ANNOUNCEMENT TO DESTINATION CHANNEL
                    if type=='text':
                        await channel.send(f'**{title.content}**\n\n{description.content}')
                    else:
                        await channel.send(embed=embed)
                    await ctx.message.reply(f'✅ Announcement has been sent to {channel.mention}.')
                    return print(f'{self.__class__.__name__} - {ctx.command.name} {type} | {time.time()-start_time} s')

                to_delete = []
                # ASK DATE
                ask_date = await ctx.send('Please enter a send date in the format `<month> <day> <year>`')
                user_response = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
                await ask_date.delete()
                date = user_response.content.split(' ')
                await user_response.add_reaction('✅')
                to_delete.append(user_response)
                # ASK TIME
                ask_time = await ctx.send('Please enter a send time in the format `HH:MM<AM/PM>`')
                user_response = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
                user_response.content = ''.join(user_response.content.split(' '))
                await ask_time.delete()
                temp_time = user_response.content.split(':')
                await user_response.add_reaction('✅')
                to_delete.append(user_response)
                # CONVERT TO ISO FORMAT
                convert_datetime = f"{date[2]}-{str(datetime.strptime(date[0][:3].capitalize(),'%b').month).zfill(2)}-{str(date[1]).zfill(2)} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"
                ann_id = get_id('announcements')
                await ctx.channel.delete_messages(to_delete)

                try:
                    if datetime.fromisoformat(convert_time(convert_datetime)) < get_dt_now().replace(tzinfo=None):
                        return await ctx.send('❌ | Entered datetime is already overdue.',delete_after=5)
                except:
                    return await ctx.send('❌ | Invalid date-time.', delete_after=5)
                else:
                    announcement_datetime = datetime.fromisoformat(convert_time(convert_datetime))
                month, day, year = announcement_datetime.strftime('%b'), announcement_datetime.day, announcement_datetime.year
                cursor.execute('INSERT INTO announcements(\
                                            id, type, guild_id, channel_id, month, day, year, iso,\
                                            title, body, field_titles, field_values, author_id)\
                                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                            (ann_id,type,ctx.guild.id,channel.id,month,day,year,convert_time(convert_datetime),
                                            title.content,description.content,field_titles,field_values,ctx.author.id))
                db.commit()
                await ctx.send(f'✅ Announcement `[ID: {str(ann_id).zfill(2)}]` added to server\'s schedule.')

                return print(f'{self.__class__.__name__} - {ctx.command.name} scheduled {type} | {time.time()-start_time} s')

    @announce.command(aliases=['-','remove'])
    @has_permissions(manage_guild=True)
    async def delete(self,ctx,id:int=None):
        ### DELETE A SCHEDULED ANNOUNCEMENT BY ID ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if id is None:
            return await ctx.send('❌ | Announcement `ID` is a required parameter', delete_after=5)
        if db.cursor().execute(f'SELECT title,iso FROM announcements WHERE guild_id={ctx.guild.id} and id={id}').fetchone() is None:
            return await ctx.send(f'❌ | Announcement `ID:{id}` does not exist.', delete_after=5)

        announcement = db.cursor().execute(f'SELECT title,iso FROM announcements WHERE guild_id={ctx.guild.id} and id={id}').fetchone()
        message = await ctx.send(f'Title:  `{announcement[0]}`\nDate-time: `{announcement[1]}`\n\nDelete this announcement?')
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        try:
            reaction = await self.bot.wait_for('reaction_add',timeout=10,check=lambda reaction,user: user == ctx.author and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'))
        except:
            return await ctx.send('❌ | Timeout error. Please try again.')
        else:
            if str(reaction[0]) == '👍':
                # DELETE ANNOUNCEMENT FROM DATABASE
                row_id = cursor.execute(f"SELECT rowid FROM announcements WHERE guild_id={ctx.guild.id} and id={int(id)}").fetchone()[0]
                cursor.execute(f'DELETE FROM announcements WHERE rowid={row_id}')
                confirm = await ctx.send(f'Announcement `[ID: {str(id).zfill(2)}]` has been deleted.')
            else:
                return await ctx.send('❌ | Process terminated.')
        await message.delete()
        await confirm.delete()
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')

    @announce.command()
    @has_permissions(manage_guild=True)
    async def edit(self,ctx,id:int=None):
        ### EDIT A SCHEDULED ANNOUNCEMENT BY ID ###
        db = sqlite3.connect('main.sqlite')
        if id is None:
            return await ctx.send('❌ | Announcement `ID` is a required parameter.',delete_after=5)
        if db.cursor().execute(f"SELECT * FROM announcements WHERE guild_id={ctx.guild.id} AND id={int(id)}").fetchone() is None:
            return await ctx.send(f'❌ | Announcement `ID: {id}` does not exist.', delete_after=5)

        while 1:
            start_time = time.time()
            announcement = db.cursor().execute(f"SELECT * FROM announcements WHERE guild_id={ctx.guild.id} AND id={int(id)}").fetchone()
            if announcement[1] == 'text':
                # GET CURRENT ANNOUNCEMENT DETAILS
                embed = discord.Embed(title='Edit Announcement', description='Which of the following information do you want to change?')
                embed.add_field(inline=False,name='1️⃣ Title',value=announcement[8])
                embed.add_field(inline=False,name='2️⃣ Body',value=announcement[9])
                embed.add_field(inline=False,name='3️⃣ Destination Channel',value=discord.utils.get(ctx.guild.channels,id=int(announcement[3])).mention)
                embed.add_field(inline=False,name='4️⃣ Date-time',value=datetime.fromisoformat(announcement[7]).strftime("%B %d, %Y @ %I:%M %p"))

                text_details = await ctx.send(embed=embed)
                for emoji in ['1️⃣','2️⃣','3️⃣','4️⃣','❌']:
                    await text_details.add_reaction(emoji)
                reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in ['1️⃣','2️⃣','3️⃣','4️⃣','❌'])

                # EMOJI EQUIVALENTS
                equivalent = {'1️⃣':'title','2️⃣':'body','3️⃣':'channel'}
                if str(reaction[0]) == '❌':
                    # NO CHANGE
                    await text_details.delete()
                    return await ctx.send('Process terminated.', delete_after=2.0)
                await text_details.clear_reactions()
                if str(reaction[0]) in equivalent.keys():
                    # CHANGE TITLE,BODY,OR CHANNEL
                    # ASK NEW VALUE FOR ANNOUNCEMENT DETAIL
                    message = await ctx.send(f'Please enter a new {equivalent[str(reaction[0])]}.')
                    text = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
                    await text.add_reaction('✅')
                    await message.delete()
                    if str(reaction[0]) == '1️⃣':
                        db.cursor().execute(f'UPDATE announcements SET title = ? WHERE id=? AND guild_id = ?',(text.content,id,ctx.guild.id))
                        await text.delete()
                        await ctx.send(f'✅ Announcement title changed to: ```\n{text.content}```',delete_after=3)
                    elif str(reaction[0]) == '2️⃣':
                        db.cursor().execute(f'UPDATE announcements SET body = ? WHERE id=? AND guild_id = ?',(text.content,id,ctx.guild.id))
                        await text.delete()
                        await ctx.send(f'✅ Announcement body changed to: ```\n{text.content}```',delete_after=3)
                    else:
                        try:
                            db.cursor().execute(f'UPDATE announcements SET channel_id = ? WHERE id=? AND guild_id = ?',(int(text.content[2:-1]),id,ctx.guild.id))
                        except:
                            await ctx.channel.delete_messages([text_details,text])
                            return await ctx.send('❌ | Please **mention** a valid channel.')
                        else:
                            await text.delete()
                            await ctx.send(f'✅ Announcement will now be sent to {discord.utils.get(ctx.guild.text_channels,id=int(text.content[2:-1])).mention}',delete_after=5)
                else:
                    # CHANGE DATE-TIME
                    await self.edit_datetime(ctx,'announcements',id)
                await text_details.delete()
            else: # EMBED
                # EMBED FIELDS
                titles,values=[],[]
                if announcement[10] is not None:
                    titles,values=announcement[10].split(';'),announcement[11].split(';')
                author = discord.utils.get(ctx.guild.members,id=int(announcement[12]))
                embed = discord.Embed(title='Edit Announcement', description='Which of the following information do you want to change?')
                embed.add_field(inline=False,name='1️⃣ Destination Channel',value=discord.utils.get(ctx.guild.channels,id=int(announcement[3])).mention)
                embed.add_field(inline=False,name='2️⃣ Date-time',value=datetime.fromisoformat(announcement[7]).strftime("%B %d, %Y @ %I:%M %p"))
                embed.add_field(inline=False,name='3️⃣ Embed',value='Details below:')
                ask_embed = await ctx.send(embed=embed)
                embed_details = await ctx.send(embed=create_embed(announcement[8],announcement[9],titles,values,author))
                for emoji in ['1️⃣','2️⃣','3️⃣','❌']:
                    await embed_details.add_reaction(emoji)
                reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in ['1️⃣','2️⃣','3️⃣','❌'])
                if (str(reaction[0])) == '❌':
                    # NO CHANGE
                    await ctx.channel.delete_messages([ask_embed,embed_details])
                    return await ctx.send('Process terminated.', delete_after=5)
                if str(reaction[0])=='1️⃣':
                    # CHANGE CHANNEL
                    message=await ctx.send(f'Please enter a new channel.')
                    text = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
                    await message.delete()
                    await text.add_reaction('✅')
                    try:
                        db.cursor().execute(f'UPDATE announcements SET channel_id = ? WHERE id=? AND guild_id = ?',(int(text.content[2:-1]),id,ctx.guild.id))
                    except:
                        await ctx.channel.delete_messages([ask_embed,embed_details,text])
                        return await ctx.send('❌ | Please **mention** a valid channel.')
                    else:
                        await text.delete()
                        await ctx.send(f'✅ Announcement will now be sent to {discord.utils.get(ctx.guild.text_channels,id=int(text.content[2:-1])).mention}',delete_after=3)
                elif str(reaction[0])=='2️⃣':
                    # CHANGE DATETIME
                    await self.edit_datetime(ctx,'announcements',id)
                else:
                    # CHANGE EMBED
                    title,description = await self.ask_details(ctx)
                    field_titles,field_values=await self.add_fields(ctx)
                    if field_titles:
                        embed = create_embed(title.content,description.content,field_titles.split(';'),field_values.split(';'),author)
                    else:
                        embed = create_embed(title.content,description.content,field_titles,field_values,author)
                    message = await ctx.send(f'React with 👍 to confirm announcement',embed=embed)
                    await message.add_reaction('👍')
                    try:
                        reaction = await self.bot.wait_for('reaction_add',timeout=30,check=lambda reaction,user: user == ctx.author and str(reaction.emoji) == '👍')
                    except:
                        await message.delete()
                        await ctx.channel.delete_messages([ask_embed,embed_details])
                        return await ctx.send('❌ | Timeout error. Please try again.', delete_after=2.0)
                    else:
                        await message.delete()
                        db.cursor().execute(f'UPDATE announcements SET title=?,body=?,field_titles=?,field_values=? WHERE id=? AND guild_id = ?',
                                            (title.content,description.content,field_titles,field_values,id,ctx.guild.id))
                        await ctx.send('✅ Embed has been updated',delete_after=3)
                await ctx.channel.delete_messages([ask_embed,embed_details])
            db.commit()
            print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')

    @announce.command()
    @has_permissions(manage_guild=True)
    async def list(self,ctx):
        ### LISTS ALL SCHEDULED ANNOUNCEMENT FOR THE SERVER ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        announcements = db.cursor().execute(f"SELECT id,type,title,channel_id,iso,month,day,year FROM announcements WHERE guild_id={ctx.guild.id}").fetchall()
        field_value = ''
        pages = []
        if len(announcements)==0:
            return await ctx.send('No scheduled announcements for now...',delete_after=3.0)
        while len(announcements) > 10:
            field_value, embed = '', discord.Embed(title='Scheduled Announcements',description='Here are the pending scheduled announcements for the server.',color=0x03f0fc)
            temp_announcements = announcements[:10]
            del announcements[:10]
            for element in temp_announcements:
                field_value += f"`[ID: {str(element[0]).zfill(2)}]` {element[1].capitalize()} announcement in {discord.utils.get(ctx.guild.channels,id=element[3]).mention} `<in {time_diff(element[4])[:-1]}>`\n"
            embed.add_field(inline=False,name='Announcements',value=field_value)
            pages.append(embed)
        #print(announcements)
        field_value, embed = '', discord.Embed(title='Scheduled Announcements',description='Here are the pending scheduled announcements for the server.',color=0x03f0fc)
        for element in announcements:
            field_value += f"`[ID: {str(element[0]).zfill(2)}]` {element[1].capitalize()} announcement in {discord.utils.get(ctx.guild.channels,id=element[3]).mention} `<in {time_diff(element[4])[:-1]}>`\n"
        embed.add_field(name='Announcements',value=field_value)
        pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
            print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')
        else:
            for n in range(1,len(pages)+1):
                pages[n-1].set_author(name=f'Page {n}/{len(pages)}')
            message = await ctx.send(embed=pages[0])
            print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')
            for reaction in ['⏪','◀️','▶️','⏩']:
                await message.add_reaction(reaction)
            i = 0
            while(1):
                try:
                    reaction = await self.bot.wait_for('reaction_add',timeout=240,check=lambda reaction,user: str(reaction.emoji) in ['⏪','◀️','▶️','⏩'] and reaction.message == message and user != self.bot.user)
                except:
                    lock_embed = discord.Embed(description='This embed has been locked [Reason: Timeout]')
                    await message.edit(embed = lock_embed)
                    return await message.clear_reactions()
                else:
                    if str(reaction[0].emoji) == '⏪':
                        await message.edit(embed=pages[0])
                    elif str(reaction[0].emoji) == '◀️':
                        if i>0:
                            i-=1
                            await message.edit(embed=pages[i])
                    elif str(reaction[0].emoji) == '▶️':
                        if i<len(pages)-1:
                            i+=1
                            await message.edit(embed=pages[i])
                    else:
                        i=len(pages)-1
                        await message.edit(embed=pages[i])
                    await message.remove_reaction(reaction[0].emoji,reaction[1])
        db.commit()

class Reminders(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    async def check_schedule(self):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        while 1:
            dt_now = get_dt_now().replace(tzinfo=None)
            reminders = cursor.execute(f"SELECT id,guild_id,channel_id,body,role_id,repeat,iso FROM reminders WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={dt_now.year}").fetchall()
            if len(reminders)==0: # NO ANNOUNCEMENT
                pass
            else:
                for element in reminders:
                    time_diff = dt_now-datetime.fromisoformat(element[6])
                    if time_diff.seconds <= 1:
                        start_time = time.time()
                        # reminder is scheduled NOW
                        guild = self.bot.get_guild(element[1])
                        role = ''
                        if element[4] is not None:
                            role = discord.utils.get(guild.roles,id=int(element[4])).mention
                        embed = create_embed('Reminder',element[3])
                        if element[5] is not None:
                            embed.set_footer(text=f'{element[5].capitalize()} reminder | To stop, enter $stop {element[0]}')
                        await discord.utils.get(guild.channels,id=int(element[2])).send(role,embed=embed)
                        if element[5] is None:
                            cursor.execute(f"DELETE FROM reminders WHERE id={int(element[0])} AND guild_id={int(element[1])}")
                        else:
                            # UPDATE ISO DEPENDING ON REPEAT
                            repeat = element[5]
                            if repeat == 'once':
                                new_iso,repeat = (datetime.fromisoformat(element[6]) + timedelta(days=1)).isoformat(' '),None
                            elif repeat == 'daily':
                                new_iso = (datetime.fromisoformat(element[6]) + timedelta(days=1)).isoformat(' ')
                            elif repeat == 'weekly':
                                new_iso = (datetime.fromisoformat(element[6]) + timedelta(days=7)).isoformat(' ')
                            else:
                                new_iso = (datetime.fromisoformat(element[6]) + relativedelta(months=1)).isoformat(' ')
                            new_datetime = datetime.fromisoformat(new_iso)
                            month,day,year = new_datetime.strftime('%b'),new_datetime.day,new_datetime.year
                            cursor.execute(f"UPDATE reminders SET iso=?,repeat=?,month=?,day=?,year=? WHERE id=? AND guild_id=?",
                                            (new_iso,repeat,month,day,year,int(element[0]),int(element[1])))
                        db.commit()
                        print(f'{self.__class__.__name__} - Send scheduled reminder | {time.time()-start_time} s')
            await asyncio.sleep(1)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')
        self.bot.loop.create_task(self.check_schedule())

    @commands.group(invoke_without_command=True,aliases=['reminder'])
    async def remind(self,ctx):
        await ctx.send(embed=get_reminders(ctx))

    @remind.command()
    @has_permissions(manage_guild=True)
    async def create(self,ctx,channel:discord.TextChannel=None,repeat=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        to_delete = []
        if channel is None:
            return await ctx.send('❌ | Channel is a required parameter.',delete_after=5)
        if repeat is None:
            pass
        elif ''.join(repeat.split(' ')).lower() not in ['once','1','daily','everyday','d','everyweek','week','weekly','w','monthly','everymonth','month','m','mon']:
            return await ctx.send('❌ | Invalid `repeat` argument!\n\n`Reminders can only be repeated once, daily, weekly, and monthly.`',delete_after=2.0)
        else:
            repeat = ''.join(repeat.split(' ')).lower()
            if repeat in ['once','1']:
                repeat = 'once'
            elif repeat in ['daily','everyday','d']:
                repeat = 'daily'
            elif repeat in ['everyweek','week','weekly','w']:
                repeat = 'weekly'
            elif repeat in ['monthly','everymonth','month','m','mon']:
                repeat = 'monthly'
        message = await ctx.send('Please enter the body of reminder.\n\n*Example: Attend check-in @ [link]*')
        body = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
        reminder_body = body.content
        await body.add_reaction('✅')
        to_delete.append(body)
        await message.delete()
        message = await ctx.send('Do you want to mention any role for the reminder?')
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'))
        await message.delete()
        role_id=None
        if str(reaction[0]) == '👍':
            message = await ctx.send('Please enter the role to be mentioned. Enter `none` to skip this process.')
            while 1:
                role_msg = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
                if 'none' in role_msg.content.lower():
                    to_delete.append(role_msg)
                    break
                if role_msg.content[0] == '<': # mentioned role
                    if discord.utils.get(ctx.guild.roles,id=int(role_msg.content[3:role_msg.content.index('>')])) is None:
                        await role_msg.add_reaction('❌')
                        await ctx.send(f'Invalid role. Please try again.',delete_after=2)
                    else:
                        role_id = int(role_msg.content[3:role_msg.content.index('>')])
                        await role_msg.add_reaction('✅')
                        to_delete.append(role_msg)
                        break
                elif role_msg.content.isnumeric():
                    try:
                        int(discord.utils.get(ctx.guild.roles,id=int(role_msg.content)).id)
                    except:
                        await role_msg.add_reaction('❌')
                        await ctx.send(f'Role {role} not found. Please try again.',delete_after=2)
                    else:
                        await role_msg.add_reaction('✅')
                        role_id = int(role_msg.content)
                        to_delete.append(role_msg)
                        break
                else: # role name
                    role = role_msg.content
                    for name in [role.lower(),role.capitalize(),role.title()]:
                        try:
                            int(discord.utils.get(ctx.guild.roles,name=name).id)
                        except:
                            pass
                        else:
                            role_id = int(discord.utils.get(ctx.guild.roles,name=name).id)
                            await role_msg.add_reaction('✅')
                            break
                    if role_id is None:
                        await role_msg.add_reaction('❌')
                        await ctx.send(f'Role {role} not found. Please try again.',delete_after=2)
                    else:
                        to_delete.append(role_msg)
                        break
                to_delete.append(role_msg)
            await message.delete()
        if role_id is None:
            role = ''
        else:
            role = discord.utils.get(ctx.guild.roles,id=role_id).mention

        # DATETIME
        message = await ctx.send('Please enter a starting send date in the format `<month> <day> <year>`')
        send_date = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
        date = send_date.content.split(' ')
        await send_date.add_reaction('✅')
        await message.delete()
        to_delete.append(send_date)
        message = await ctx.send('Please enter the send time of the reminder in the format `HH:MM<AM/PM>`')
        send_time = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
        send_time.content = ''.join(send_time.content.split(' '))
        temp_time = send_time.content.split(':')
        await send_time.add_reaction('✅')
        await message.delete()
        to_delete.append(send_time)

        convert_datetime = f"{date[2]}-{str(datetime.strptime(date[0][:3].capitalize(),'%b').month).zfill(2)}-{str(date[1]).zfill(2)} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"

        # VALIDATE IF CURRENT DATETIME PRECEDES TARGET
        if get_dt_now().replace(tzinfo=None) > datetime.fromisoformat(convert_time(convert_datetime)):
            return await ctx.send('❌ | Cannot send reminders to the past.',delete_after=3)

        ann_id = get_id('reminders')
        embed = create_embed('Reminder',body.content)
        confirm_msg = await ctx.send(content=f'React with 👍 to confirm reminder\n\n{role}',embed=embed)
        await confirm_msg.add_reaction('👍')
        try:
            reaction = await self.bot.wait_for('reaction_add',timeout=30,check=lambda reaction,user: user == ctx.author and (str(reaction.emoji) == '👍'))
        except:
            await confirm_msg.delete()
            return await ctx.send('❌ | Timeout error. Please try again.', delete_after=2.0)
        else:
            await confirm_msg.delete()
            iso = convert_time(convert_datetime)
            temp_datetime = datetime.fromisoformat(iso)
            month, day, year = temp_datetime.strftime('%b'),temp_datetime.day,temp_datetime.year
            cursor.execute('INSERT INTO reminders(id,guild_id,channel_id,body,role_id,repeat,iso,month,day,year) VALUES(?,?,?,?,?,?,?,?,?,?)',
                            (ann_id,ctx.guild.id,channel.id,reminder_body,role_id,repeat,iso,month,day,year))
            await ctx.channel.delete_messages(to_delete)
            await ctx.send(f'✅ Reminder `[ID: {str(ann_id).zfill(2)}]` added to server\'s schedule.')
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')

    @remind.command()
    @has_permissions(manage_guild=True)
    async def list(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        reminders = db.cursor().execute(f"SELECT id,channel_id,body,repeat,iso FROM reminders WHERE guild_id={ctx.guild.id}").fetchall()
        # [[id,channel_id,body,repeatiso FROM reminders]]
        pages = []
        field_value = ''
        if len(reminders)==0:
            return await ctx.send('No scheduled reminders for now...',delete_after=3.0)
        while len(reminders) > 10:
            field_value, embed = '', discord.Embed(title='Scheduled Reminders',description='Here are the pending scheduled reminders for the server.',color=0x03f0fc)
            temp_reminders = reminders[:10]
            del reminders[:10]
            for element in temp_reminders:
                repeat = ''
                if element[3] is not None:
                    repeat = element[3].capitalize()
                field_value += f"`[ID: {str(element[0]).zfill(2)}]` {repeat} reminder in {discord.utils.get(ctx.guild.channels,id=element[1]).mention} `<in {time_diff(element[4])[:-1]}>`\n"
            embed.add_field(name='Reminders',value=field_value)
            pages.append(embed)

        field_value, embed = '', discord.Embed(title='Scheduled Reminders',description='Here are the pending scheduled reminders for the server.',color=0x03f0fc)
        for element in reminders:
            repeat = ''
            if element[3] is not None:
                repeat = element[3].capitalize()
            field_value += f"`[ID: {str(element[0]).zfill(2)}]` {repeat} reminder in {discord.utils.get(ctx.guild.channels,id=element[1]).mention} `<in {time_diff(element[4])[:-1]}>`\n"
        embed.add_field(name='reminders',value=field_value)
        pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
            print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')
        else:
            for n in range(1,len(pages)+1):
                pages[n-1].set_author(name=f'Page {n}/{len(pages)}')
            message = await ctx.send(embed=pages[0])
            print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')
            for reaction in ['⏪','◀️','▶️','⏩']:
                await message.add_reaction(reaction)
            i = 0
            while(1):
                try:
                    reaction = await self.bot.wait_for('reaction_add',timeout=240,check=lambda reaction,user: str(reaction.emoji) in ['⏪','◀️','▶️','⏩'] and reaction.message == message and user != self.bot.user)
                except TimeoutError:
                    lock_embed = discord.Embed(description='This embed has been locked [Reason: Timeout]')
                    await message.edit(embed = lock_embed)
                    return await message.clear_reactions()
                else:
                    if str(reaction[0].emoji) == '⏪':
                        await message.edit(embed=pages[0])
                    elif str(reaction[0].emoji) == '◀️':
                        if i>0:
                            i-=1
                            await message.edit(embed=pages[i])
                    elif str(reaction[0].emoji) == '▶️':
                        if i<len(pages)-1:
                            i+=1
                            await message.edit(embed=pages[i])
                    else:
                        i=len(pages)-1
                        await message.edit(embed=pages[i])
                    await message.remove_reaction(reaction[0].emoji,reaction[1])
        db.commit()

    @commands.command(aliases=['-','delete','remove'])
    @has_permissions(manage_guild=True)
    async def stop(self,ctx,id:int):
        ### delete a scheduled announcement by ID ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        if db.cursor().execute(f'SELECT * FROM reminders WHERE guild_id={ctx.guild.id} and id={id}').fetchone() is None:
            return await ctx.send('❌ Reminder ID does not exist.', delete_after=2.0)
        reminder = db.cursor().execute(f'SELECT body,repeat,iso FROM reminders WHERE guild_id={ctx.guild.id} and id={id}').fetchone()
        repeat = 'Never'
        if reminder[1] is not None:
            repeat = f'{reminder[1].capitalize()} every {reminder[2][11:16]}'
        message = await ctx.send(f'Reminder:  ```{reminder[0]}```\nRepeat: `{repeat}`\n\nStop this reminder?')
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        try:
            reaction = await self.bot.wait_for('reaction_add',timeout=10,check=lambda reaction,user: user == ctx.author and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'))
        except:
            return await ctx.send('❌ | Timeout error. Please try again.')
        else:
            if str(reaction[0]) == '👍':
                db.cursor().execute(f'DELETE FROM reminders WHERE id={id} AND guild_id={ctx.guild.id}')
                confirm = await ctx.send(f'Reminder `[ID: {str(id).zfill(2)}]` has been deleted.')
            else:
                return await ctx.send('❌ | Process terminated.')
        await message.delete()
        await confirm.delete()
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')

def setup(bot):
    bot.add_cog(Announcements(bot))
    bot.add_cog(Reminders(bot))
