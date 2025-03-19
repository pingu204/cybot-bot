import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import calendar
import asyncio
from misc import *
import time
import sys
from .announcements import Announcements

class Requirements(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    ######################
    ### MISC FUNCTIONS ###
    ######################

    def sort(self,reqList):
        temp = []
        temp.append(reqList[0])
        for i in range(1,len(reqList)):
            temp.append(reqList[i])
            for j in range(i-1,-1,-1):
                if int(temp[i][0]) < int(temp[j][0]):
                    temp[i],temp[j] = temp[j],temp[i] #continue
        return temp

    def generateList(self,type,guild_id,month,year):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        reqList = cursor.execute(f"SELECT day,req,id,iso FROM reqs WHERE guild_id={int(guild_id)} and month LIKE '{month}' and year={year}").fetchall() #list of reqs
        if len(reqList)>0:
            ### sort reqs by ascending day ###
            if(len(reqList)>1): #more than 1 requirements
                reqList = self.sort(reqList)
                reqs,ids='',''
                for i in reqList:
                    reqs+=f"`[{i[3][5:10].replace('-','/')} {i[3][11:16]}]` {i[1].capitalize()} `<in {time_diff(str(i[3]))[:-1]}>`\n"
                    ids+=f'`[ID: {str(i[2]).zfill(2)}]` {i[1].capitalize()} `<{i[3]}>`\n'
                if type == 'reqs':
                    return reqs
                return ids
            else: #1 requirement
                if type == 'reqs':
                    return f'`{str(reqList[0][0]).zfill(2)}` {reqList[0][1].capitalize()} `<in {time_diff(str(reqList[0][3]))[:-1]}>`'
                return f'`[ID: {str(reqList[0][2]).zfill(2)}]` {reqList[0][1].capitalize()} `<{reqList[0][3]}>`\n'
        else:
            return None
        db.commit()

    ######################
    ### MISC FUNCTIONS ###
    ######################

    async def check_overdue(self):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        while 1:
            dt_now = get_dt_now().replace(tzinfo=None)
            requirements = cursor.execute(f"SELECT id,iso FROM reqs").fetchall()
            if len(requirements) == 0:
                pass
            n = 0
            for iso in requirements:
                if datetime.fromisoformat(iso[1])<dt_now:
                    start_time = time.time()
                    cursor.execute(f"DELETE FROM reqs WHERE id={iso[0]}")
                    db.commit()
                    n+=1
            if n > 0:
                print(f'Deleted {n} schedules.')
                print(f'{self.__class__.__name__} - delete overdue | {time.time()-start_time} s')
            await asyncio.sleep(1)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')
        self.bot.loop.create_task(self.check_overdue())

    @commands.group(invoke_without_command=True,aliases=['req','reqs','sched'])
    async def schedule(self,ctx,year:int=None):
        start_time = time.time()
        ### displays requirements list for the year ###
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        month = get_dt_now().replace(tzinfo=None).month
        if year is None:
            year = get_dt_now().replace(tzinfo=None).year
        if (year - get_dt_now().replace(tzinfo=None).year) >= 1: # if not current year, start with January (1st month)
            month=1
        pages = []
        for month_index in range(month,13):
            embed = discord.Embed(color=discord.Colour.blue(),description=f'**Schedules List** [{year}]')
            reqs_string= self.generateList('reqs',ctx.guild.id,str(calendar.month_abbr[month_index]),year)
            if reqs_string is None:
                embed.add_field(inline=True,name=str(calendar.month_name[month_index]),value='nothing here...for now')
            else:
                embed.add_field(inline=True,name=str(calendar.month_name[month_index]),value=str(reqs_string))
            embed.set_footer(text=f'Type {ctx.prefix}sched <year> to view schedules for that year.')
            pages.append(embed)
        # display embed
        # for page in pages:
        #     await ctx.send(embed=page)
        message = await ctx.send(embed=pages[0])
        print(f'{self.__class__.__name__} - {ctx.command.name} | {time.time()-start_time} s')
        for reaction in ['⏪','◀️','▶️','⏩']:
            await message.add_reaction(reaction)
        # pages navigation
        i = 0
        while(1):
            reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: str(reaction.emoji) in ['⏪','◀️','▶️','⏩'] and reaction.message == message and user == ctx.author)
            if str(reaction[0].emoji) == '⏪':
                await message.edit(embed=pages[0])
            elif str(reaction[0].emoji) == '◀️':
                    i-=1
                    await message.edit(embed=pages[i])
            elif str(reaction[0].emoji) == '▶️':
                if i<len(pages)-1:
                    i+=1
                    await message.edit(embed=pages[i])
            else:
                await message.edit(embed=pages[len(pages)-1])
            await message.remove_reaction(reaction[0].emoji,reaction[1])
        db.commit()


    @schedule.command()
    @has_permissions(manage_guild=True)
    async def id(self,ctx,year:int=None):
        start_time = time.time()
        ### displays requirements list by ID (for administrators) ###
        month = get_dt_now().replace(tzinfo=None).month
        if year is None:
            year = get_dt_now().replace(tzinfo=None).year
        if (year - get_dt_now().replace(tzinfo=None).year) >= 1: # if not current year, start with January (1st month)
            month=1
        pages = []
        for month_index in range(month,13):
            embed = discord.Embed(color=0x811596,description=f'**Schedules List by ID** [{year}]')
            id_string = self.generateList('id',ctx.guild.id,str(calendar.month_abbr[month_index]),year)
            if id_string is None:
                embed.add_field(inline=True,name=str(calendar.month_name[month_index]),value='nothing here...for now')
            else:
                embed.add_field(inline=True,name=str(calendar.month_name[month_index]),value=str(id_string))
            embed.set_footer(text=f'Type {ctx.prefix}sched edit/delete <ID> to modify a requirement.')
            pages.append(embed)
        ## display embed ##
        message = await ctx.send(embed=pages[0])
        for reaction in ['⏪','◀️','▶️','⏩']:
            await message.add_reaction(reaction)
        ## pages navigation ##
        print(f'{self.__class__.__name__} - sched {ctx.command} | {time.time()-start_time} s')
        i = 0 # first counter
        while(1):
            reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user:str(reaction.emoji) in ['⏪','◀️','▶️','⏩'] and reaction.message.id == message.id and user == ctx.author)
            if str(reaction[0].emoji) == '⏪': # back to first page
                await message.edit(embed=pages[0])
            elif str(reaction[0].emoji) == '◀️': # backward one page
                if i>0:
                    i-=1
                    await message.edit(embed=pages[i])
            elif str(reaction[0].emoji) == '▶️': # forward one page
                if i<len(pages)-1:
                    i+=1
                    await message.edit(embed=pages[i])
            else: # forward to last page
                await message.edit(embed=pages[len(pages)-1])
            await message.remove_reaction(reaction[0].emoji,reaction[1])


    @schedule.command(aliases=['+','new'])
    @has_permissions(manage_guild=True)
    async def add(self,ctx,month,day,year=None,time_input=None,*,reqt=None):
        ### adds a new requirement to server's reqs list ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        reqt_id = get_id('reqs')
        if not month.isnumeric():
            try:
                datetime.strptime(month[:3].capitalize(),'%b')
            except:
                days,hours,mins = 0,0,0
                time_codes = list(month)
                if time_codes and 'd' in time_codes:
                    temp = list(str(''.join(time_codes)).rpartition('d'))
                    days = int(temp[0])
                    del(time_codes[:len(temp[0])+len(temp[1])])
                if time_codes and 'h' in time_codes:
                    temp = list(str(''.join(time_codes)).rpartition('h'))
                    hours = int(temp[0])
                    del(time_codes[:len(temp[0])+len(temp[1])])
                if time_codes and 'm' in time_codes:
                    temp = list(str(''.join(time_codes)).rpartition('m'))
                    mins = int(temp[0])
                    del(time_codes[:len(temp[0])+len(temp[1])])
                if time_codes:
                    return await ctx.send('❌ | Invalid date-time format. Make sure to follow either:\n`month name` `DD` `YYYY` `HH:MM<AM/PM>` OR\n`month name` `day` `year` `HH:MM` - military time OR\n`00d00h00m` - until due date')
                sched_datetime = (get_dt_now().replace(tzinfo=None) + timedelta(days=days,hours=hours,minutes=mins))
                reqt = f'{day} {year} {time_input} {reqt}'.replace('None','').rstrip()
            else:
                temp_time = time_input.split(':')
                print(temp_time)
                if 'am' not in temp_time[1].lower() and 'pm' not in temp_time[1].lower():
                    if int(temp_time[0]) == 0 or int(temp_time[0])==24:
                        time_input = f'12:{temp_time[1]}AM'
                    elif int(temp_time[0]) < 12:
                        time_input = f'{temp_time[0].zfill(2)}:{temp_time[1]}AM'
                    elif int(temp_time[0]) == 12:
                        time_input = f'{temp_time[0].zfill(2)}:{temp_time[1]}PM'
                    else:
                        time_input = f'{str(int(temp_time[0])-12).zfill(2)}:{temp_time[1]}PM'
                else:
                    time_input = f'{temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}'

                try:
                    convert_datetime = f"{year}-{str(datetime.strptime(month[:3].capitalize(),'%b').month).zfill(2)}-{str(day).zfill(2)} {time_input}"
                    sched_datetime = datetime.fromisoformat(convert_time(convert_datetime))
                except:
                    return await ctx.send('❌ | Invalid date-time format. Make sure to follow either:\n`month name` `DD` `YYYY` `HH:MM<AM/PM>` OR\n`month name` `day` `HH:MM` - military time OR\n`00d00h00m` - until due date')

            if sched_datetime<get_dt_now().replace(tzinfo=None):
                return await ctx.send('❌ | Cannot add overdue requirements.')
            #print(sched_datetime)
            month = sched_datetime.strftime('%b')
            day = int(sched_datetime.strftime('%d'))
            year = int(sched_datetime.strftime('%Y'))
            cursor.execute('INSERT INTO reqs(id,guild_id,month,day,year,req,iso) VALUES(?,?,?,?,?,?,?)',(reqt_id,ctx.guild.id,month,day,year,reqt,sched_datetime.isoformat(' ')[:16]))
            await ctx.send(f'✅ Requirement `{reqt} [ID: {str(reqt_id).zfill(2)}]` added to server\'s list.')
            db.commit()
            return print(f'{self.__class__.__name__} - sched {ctx.command} | {time.time()-start_time} s')
        else:
            return await ctx.send('❌ | Please input month names (e.g. `January`, `Jan`).')


    @schedule.command(aliases=['-','remove'])
    @has_permissions(manage_guild=True)
    async def delete(self,ctx,id:int):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f"SELECT * FROM reqs WHERE guild_id={ctx.guild.id} and id={int(id)}").fetchone() is None:
            return await ctx.send('❌ | Requirement ID does not exist.', delete_after=2.0)
        row_id = cursor.execute(f"SELECT rowid FROM reqs WHERE guild_id={ctx.guild.id} and id={int(id)}").fetchone()[0]
        reqt = cursor.execute(f'SELECT req,iso FROM reqs WHERE guild_id={ctx.guild.id} and id={id}').fetchone()
        message = await ctx.send(f'Requirement:  `{reqt[0]}`\nDate-time: `{reqt[1]}`\n\nDelete this requirement?')
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        try:
            reaction = await self.bot.wait_for('reaction_add',timeout=10,check=lambda reaction,user: user == ctx.author and (str(reaction.emoji) == '👍' or str(reaction.emoji) == '👎'))
        except:
            return await ctx.send('❌ | Timeout error. Please try again.',delete_after=2)
        else:
            if str(reaction[0]) == '👍':
                print(row_id)
                cursor.execute(f'DELETE FROM reqs WHERE rowid={int(row_id)}')
                confirm = await ctx.send(f'Requirement `[ID: {str(id).zfill(2)}]` has been deleted.')
            else:
                return await ctx.send('*Process terminated.*',delete_after=2)
        await message.delete()
        await confirm.delete()
        db.commit()
        return print(f'{self.__class__.__name__} - sched {ctx.command} | {time.time()-start_time} s')

    @schedule.command()
    @has_permissions(manage_guild=True)
    async def edit(self,ctx,id:int):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        if db.cursor().execute(f"SELECT * FROM reqs WHERE guild_id={ctx.guild.id} and id={int(id)}").fetchone() is None:
            return await ctx.send('❌ | Requirement ID does not exist.', delete_after=2.0)
        reqt = db.cursor().execute(f'SELECT req,iso FROM reqs WHERE guild_id={ctx.guild.id} and id={id}').fetchone()
        reqt_details = await ctx.send(f'Requirement:  `{reqt[0]}`\nDue date: `{reqt[1]}`\n\nWhich of the following information do you want to change?\n\n1️⃣ - Requirement Name\n2️⃣ - Due date\n❌ - None')
        for emoji in ['1️⃣','2️⃣','❌']:
            await reqt_details.add_reaction(emoji)
        reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in ['1️⃣','2️⃣','❌'])
        if str(reaction[0]) == '❌':
            # no change
            await reqt_details.delete()
            return await ctx.send('*Process terminated.*', delete_after=2.0)
        if str(reaction[0]) == '1️⃣':
            message = await ctx.send(f'Please enter a new requirement name.')
            text = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
            await text.add_reaction('✅')
            db.cursor().execute(f"UPDATE reqs SET req = ? WHERE id=? AND guild_id = ?",(text.content,id,ctx.guild.id))
            await ctx.send(f'Name of requirement `[ID: {str(id).zfill(2)}]` has been set to ```{text.content}```',delete_after=5)
            await message.delete()
        else:
            await Announcements.edit_datetime(self,ctx,'reqs',id)
        db.commit()
        return print(f'{self.__class__.__name__} - sched {ctx.command} | {time.time()-start_time} s')

class SchedLog(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    async def send_schedlog(self):
        """
        Send list of requirements for the day/week/month
        """
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        while 1:
            dt_now = get_dt_now().replace(tzinfo=None) # Current date-time

            # Get all guilds with enabled schedule logs
            guilds = cursor.execute(f"SELECT guild_id FROM logs_status WHERE schedlog=1").fetchall()

            for id in guilds:
                # Get details of sched logs per server
                element = cursor.execute(f"SELECT month,channel_id,role_id,type,iso FROM schedlog WHERE guild_id={id[0]} AND month='{dt_now.strftime('%b')}' AND day={int(dt_now.day)} AND year={int(dt_now.year)}").fetchone()
                if element:
                    if (dt_now-datetime.fromisoformat(element[4])).seconds <= 1:
                        """
                        Log is scheduled to be sent NOW

                        For daily logs, generate list of requirements for the day; add 1 day to date-time
                        For weekly logs, generate list of requirements for 7 days; add 1 week to date-time
                        For monthly logs, generate list of requirements for the whole month; add 1 month to datet-time
                        """
                        start_time = time.time()
                        guild = self.bot.get_guild(id[0])
                        role = None
                        if element[2] is not None:
                            role = discord.utils.get(guild.roles,id=int(element[2])).mention

                        # Generate list of requirements
                        if element[3] == 'd': # daily logs
                            requirements = cursor.execute(f"SELECT day,req,iso FROM reqs WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={dt_now.year}").fetchall()
                            new_iso = (datetime.fromisoformat(element[4]) + timedelta(days=1)).isoformat(' ')
                            title = f"**Daily Schedule** [{dt_now.strftime('%m/%d/%Y')}]"
                        elif element[3] == 'w': # weekly logs
                            requirements = cursor.execute(f"SELECT day,req,iso FROM reqs WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={int(dt_now.year)}").fetchall()
                            for n in range(1,7):
                                dt_now += timedelta(days=1)
                                requirements.extend(cursor.execute(f"SELECT day,req,iso FROM reqs WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={int(dt_now.year)}").fetchall())
                            dt_now -= timedelta(days=6)
                            new_iso = (datetime.fromisoformat(element[4]) + timedelta(days=7)).isoformat(' ')
                            title = f"**Weekly Schedule** [{dt_now.strftime('%m/%d')} - {(dt_now+timedelta(days=6)).strftime('%m/%d')}]"
                        else: # monthly logs
                            requirements = cursor.execute(f"SELECT day,req,iso FROM reqs WHERE month='{dt_now.strftime('%b')}' AND year={int(dt_now.year)}").fetchall()
                            new_iso = (datetime.fromisoformat(element[4]) + relativedelta.relativedelta(months=1)).isoformat(' ')
                            title = f"**Monthly Schedule** [{dt_now.strftime('%B')}]"

                        if(len(requirements)>1): #more than 1 requirement
                            reqList = Requirements.sort(self,requirements)
                            reqs=''
                            for i in reqList:
                                reqs+=f"`[{i[2][5:10].replace('-','/')} {i[2][11:16]}]` {i[1].capitalize()} `<in {time_diff(str(i[2]))[:-1]}>`\n"
                        elif len(requirements) == 1:
                            requirements = requirements[0]
                            reqs = f'`{str(requirements[0]).zfill(2)}` {requirements[1].capitalize()} `<in {time_diff(str(requirements[2]))[:-1]}>`'
                        else:
                            reqs = 'nothing here...for now'

                        embed = discord.Embed(color=discord.Colour.blue(),description=title)
                        embed.add_field(name='Tasks',value=reqs)
                        await discord.utils.get(guild.channels,id=element[1]).send(role,embed=embed)
                        new_datetime = datetime.fromisoformat(new_iso)
                        month,day,year = new_datetime.strftime('%b'),new_datetime.strftime('%d'),int(new_datetime.strftime('%Y'))
                        cursor.execute(f"UPDATE schedlog SET iso=?,month=?,day=?,year=? WHERE guild_id=?",
                                        (new_iso,month,int(day),int(year),id[0]))
                        db.commit()
                        print(f'{self.__class__.__name__} - send schedlog | {time.time()-start_time} s')
                    #print('Failed to obtain sched log details')
            await asyncio.sleep(1)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')
        self.bot.loop.create_task(self.send_schedlog())

    @commands.group(invoke_without_command=True)
    async def schedlog(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f"SELECT schedlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone() is None or cursor.execute(f"SELECT schedlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone()[0] == 0:
            schedlog_status, schedlog_channel, schedlog_type, schedlog_time = '❌','','',''
        else:
            schedlog_status = '✅'
            types = {'w':'every week','d':'everyday','m':'every month'}
            details = cursor.execute(f"SELECT channel_id,type,iso FROM schedlog WHERE guild_id = {ctx.guild.id}").fetchone()
            schedlog_channel, schedlog_type, schedlog_time = ('in ' + discord.utils.get(ctx.guild.channels,id=int(details[0])).mention), types[details[1]], ('@ ' + details[2][11:])

        ## EMBED ##
        embed = discord.Embed(color=discord.Colour.blue(),title=f'Schedule Log | {ctx.prefix}schedlog',description=f'Logs upcoming events and tasks in the server daily, weekly, or monthly\nStatus: {schedlog_status} {schedlog_type} {schedlog_time} {schedlog_channel}')
        embed.set_author(name=self.bot.user.display_name,icon_url=self.bot.user.avatar.url)
        embed.add_field(name='_enable `channel` `repeat`',value=f'Enable schedule logs for this server',inline=False)
        embed.add_field(name='_disable',value=f'Disable schedule logs for this server\n\nFor weekly logs, the list will be sent every Sunday, while the first day of a month will be utilized for monthly logs.',inline=False)
        embed.set_footer(text=f'Example: {ctx.prefix}schedlog enable #channel-name weekly | {ctx.prefix}schedlog channel #channel-name')
        await ctx.send(embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @schedlog.command()
    @has_permissions(manage_guild=True)
    async def enable(self,ctx,channel:discord.TextChannel,*,type:str=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if type is None or ''.join(type.split(' ')).lower() not in ['daily','everyday','d','everyweek','week','weekly','w','monthly','everymonth','month','m','mon']:
            return await ctx.send('❌ | Requirements can only be logged daily, weekly, or monthly.',delete_after=5)
        type = ''.join(type.split(' ')).lower()
        if type in ['daily','everyday','d']:
            type = 'd'
        elif type in ['everyweek','week','weekly','w']:
            type = 'w'
        else:
            type = 'm'
        types = {'w':'every week','d':'everyday','m':'every month'}

        # MENTIONING ROLE
        message = await ctx.send('Do you want to mention any role for scheduling logs?')
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
                    break
                if role_msg.content[0] == '<': # mentioned role
                    if discord.utils.get(ctx.guild.roles,id=int(role_msg.content[3:role_msg.content.index('>')])) is None:
                        await role_msg.add_reaction('❌')
                        await ctx.send(f'Invalid role. Please try again.',delete_after=2)
                    else:
                        role_id = int(role_msg.content[3:role_msg.content.index('>')])
                        await role_msg.add_reaction('✅')
                        break
                else: # role name
                    role,id = role_msg.content,None
                    for name in [role.lower(),role.capitalize(),role.title()]:
                        try:
                            id = (discord.utils.get(ctx.guild.roles,name=name).id)
                        except:
                            print(name)
                        else:
                            if id != None:
                                role_id = int(id)
                                await role_msg.add_reaction('✅')
                                break
                    if id is None:
                        await role_msg.add_reaction('❌')
                        await ctx.send(f'Role {role} not found. Please try again.',delete_after=2)
                    else:
                        break
            await message.delete()
        # if role_id is None:
        #     role = ''
        # else:
        #     role = discord.utils.get(ctx.guild.roles,id=role_id).mention

        # SEND TIME
        message = await ctx.send('Please enter the send time of the logs in the format `HH:MM<AM/PM>`')
        send_time = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
        send_time.content = ''.join(send_time.content.split(' '))
        temp_time = send_time.content.split(':')


        # DATETIME
        """
        IF current datetime precedes target datetime:
        retain datetime

        ELSE:
        daily: add one day to current datetime
        weekly: add days to current datetime until weekday = Sunday (6)
        monthly: add one month to current datetime; set day to 01 (first day)

        FINALLY:
        iso = <date of current datetime> + <input time>
        """

        dt_now = get_dt_now().replace(tzinfo=None)
        if type == 'd': # DAILY LOGS
            if dt_now<datetime.fromisoformat(convert_time(f"{dt_now.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}")):
                convert_datetime = f"{dt_now.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"
            else:
                tomorrow = dt_now + timedelta(days=1)
                convert_datetime = f"{tomorrow.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"
        elif type == 'w': # WEEKLY LOGS
            if dt_now.weekday() == 6 and dt_now<datetime.fromisoformat(convert_time(f"{dt_now.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}")):
                convert_datetime = f"{dt_now.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"
            else:
                if dt_now.weekday() == 6: # Sunday
                    dt_now += timedelta(days=1)
                while dt_now.weekday() != 6:
                    dt_now += timedelta(days=1)
                convert_datetime = f"{dt_now.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"
        else: # MONTHLY LOGS
            if dt_now.day == 1 and dt_now<datetime.fromisoformat(convert_time(f"{dt_now.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}")):
                convert_datetime = f"{dt_now.strftime('%Y-%m-%d')} {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"
            else:
                dt_now += relativedelta.relativedelta(months=1)
                convert_datetime = f"{dt_now.strftime('%Y-%m')}-01 {temp_time[0].zfill(2)}:{temp_time[1][:2]}{temp_time[1][2:].upper()}"
        iso = convert_time(convert_datetime)
        temp_datetime = datetime.fromisoformat(iso)
        month, day, year = temp_datetime.strftime('%b'),int(temp_datetime.day),int(temp_datetime.year)

        await send_time.add_reaction('✅')
        await message.delete()

        # DATABASE
        if cursor.execute(f'SELECT * FROM schedlog WHERE guild_id={ctx.guild.id}').fetchone() is None:
            cursor.execute('INSERT INTO schedlog(guild_id,role_id,channel_id,type,iso,month,day,year) VALUES(?,?,?,?,?,?,?,?)',
                            (ctx.guild.id,role_id,channel.id,type,iso,month,day,year))
        else:
            cursor.execute('UPDATE schedlog SET channel_id=?, role_id=?, type=?, iso=?, month=?, day=?, year=?',
                            (channel.id,role_id,type,iso,month,day,year))
        db.commit()

        if cursor.execute(f'SELECT schedlog FROM logs_status WHERE guild_id={ctx.guild.id}').fetchone() is None:
            cursor.execute(f"INSERT INTO logs_status(schedlog,guild_id) VALUES(?,?)",(1,ctx.guild.id))
        else:
            cursor.execute(f"UPDATE logs_status SET schedlog = ? WHERE guild_id = ?",(1,ctx.guild.id))

        # CONFIRMATION MESSAGE
        await ctx.send(f"✅ Schedules will be logged {types[type]} at {datetime.fromisoformat(iso).strftime('%I:%M %p')}")
        db.commit()
        return print(f'{self.__class__.__name__} - schedlog {ctx.command} | {time.time()-start_time} s')

    @schedlog.command()
    @has_permissions(manage_guild=True)
    async def disable(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f"SELECT schedlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone() is None or cursor.execute(f"SELECT schedlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone()[0] == 0:
            return await ctx.send('❌ | Scheduling logs are already disabled.')
        else:
            cursor.execute(f"UPDATE logs_status SET schedlog = ? WHERE guild_id = ?",(0,ctx.guild.id))
        await ctx.send(f'✅ Schedule logs have been disabled.')
        db.commit()
        return print(f'{self.__class__.__name__} - schedlog {ctx.command} | {time.time()-start_time} s')

class ToDoList(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    @commands.group(aliases=['td'],invoke_without_command=True)
    async def todolist(self,ctx):
        await ctx.send(embed=get_todolist(ctx))

    @todolist.command()
    @has_permissions(manage_guild=True)
    async def setchannel(self,ctx,channel:discord.TextChannel):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        if cursor.execute(f'SELECT todolist FROM info WHERE guild_id={ctx.guild.id}').fetchone() is None:
            cursor.execute(f'INSERT INTO info(guild_id,todolist) VALUES(?,?)',(ctx.guild.id,channel.id))
        else:
            cursor.execute(f'UPDATE info SET todolist=? WHERE guild_id=?',(channel.id,ctx.guild.id))
        await ctx.send(f'{channel.mention} has been set as the channel for to-do lists.',delete_after=5)
        db.commit()
        return print(f'{self.__class__.__name__} - td {ctx.command} | {time.time()-start_time} s')

    async def update_td(self,message,tasklist,letter_emojis):
        description = ''
        for n in range(len(tasklist)):
            if tasklist[n].split('%')[1]=='1':
                description += f"~~*{letter_emojis[n]} {tasklist[n].split('%')[0]}*~~\n"
            else:
                description += f"{letter_emojis[n]} {tasklist[n].split('%')[0]}\n"
        embed=discord.Embed(description=f'{description}')
        embed.set_footer(text='React with 🏁 to close the to-do list.')
        await message.edit(embed=embed)
        await message.clear_reactions()
        for n in range(len(tasklist)):
            await message.add_reaction(letter_emojis[n])
        await message.add_reaction('🏁')

    @todolist.command(aliases=['create'])
    async def new(self,ctx,channel,*,tasks=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if channel.lower() not in ['default','dm']:
            await ctx.send('❌ | To-do lists can only be sent to `default` set channel or your `dm`.',delete_after=5)
            return await ctx.message.delete()
        elif cursor.execute(f'SELECT todolist FROM info WHERE guild_id={ctx.guild.id}').fetchone()[0] is None:
            await ctx.message.reply(f'❌ | No default channel has been set for to-do lists. Use `{ctx.prefix}td setchannel #channel` to set one.',delete_after=5)
            return await ctx.message.delete()
        elif tasks==None:
            return await ctx.message.reply(f'❌ | No tasks found.')
            #return await ctx.message.delete()

        tasklist = [f'{task}%0' for task in tasks.split('\n')]
        if len(tasklist)>18:
            tasklist = tasklist[:18]
            await ctx.send('Only a maximum of 18 tasks are allowed so other tasks were removed from the list.',delete_after=5)
        emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                         14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}
        description=''
        for n in range(len(tasklist)):
            if tasklist[n].split('%')[1]==1:
                description += f"~~*{emojis[n]} {tasklist[n].split('%')[0]}*~~\n"
            else:
                description += f"{emojis[n]} {tasklist[n].split('%')[0]}\n"
        embed=discord.Embed(description=f'{description}')
        embed.set_footer(text='React with 🏁 to close the to-do list.')
        send_channel = discord.utils.get(ctx.guild.channels,id=cursor.execute(f'SELECT todolist FROM info WHERE guild_id={ctx.guild.id}').fetchone()[0])
        if channel == 'dm':
            send_channel = await ctx.author.create_dm()
        message = await send_channel.send(f'{ctx.author.mention}, here is your to-do list.',embed=embed)
        for n in range(len(tasklist)):
            await message.add_reaction(emojis[n])
        await message.add_reaction('🏁')

        cursor.execute('INSERT INTO td(guild_id,channel_type,channel_id,message_id,author_id,tasks,counter) VALUES(?,?,?,?,?,?,?)',(ctx.guild.id,channel,send_channel.id,message.id,ctx.author.id,';'.join(tasklist),0))
        await ctx.send('To-do list has been created.',delete_after=5)
        await ctx.message.delete()
        db.commit()
        return print(f'{self.__class__.__name__} - td {ctx.command} | {time.time()-start_time} s')

    @todolist.command()
    async def add(self,ctx,*,tasks=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        letter_emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                         14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}
        #print(tasks)
        #print(ctx.message.reference.message_id)

        if tasks is None:
            return await ctx.message.reply('❌ | Tasks are a required parameter!',delete_after=5)
        try:
            ctx.message.reference.message_id
        except:
            return await ctx.message.reply('❌ | Please reply to a message that has an existing to-do list.',delete_after=5)
        else:
            tasks, added_tasks = tasks.split('\n'), []
            if cursor.execute(f'SELECT * FROM td WHERE message_id={ctx.message.reference.message_id} AND author_id={ctx.author.id}').fetchone():
                details = cursor.execute(f'SELECT * FROM td WHERE message_id={ctx.message.reference.message_id}').fetchone()
                channel_type, tasklist, description = details[1], details[5].split(';'), ''
                if channel_type == 'dm':
                    return await ctx.message.reply('❌ | New tasks cannot be appended to a private to-do list.',delete_after=5)
                message = await ctx.channel.fetch_message(ctx.message.reference.message_id)

                if len(tasklist) > 18:
                    await ctx.send('Appending the tasks exceed the limit for the list. Only 18 tasks will be displayed.',delete_after=3)
                    for task in tasks:
                        tasklist.append(f'{task}%0')
                        added_tasks.append(task)
                        if len(tasklist) == 18:
                            break
                else:
                    for task in tasks:
                        tasklist.append(f'{task}%0')
                        added_tasks.append(task)

                await self.update_td(message,tasklist,letter_emojis)
                await ctx.message.delete()
                cursor.execute('UPDATE td SET tasks=? WHERE message_id=?',(';'.join(tasklist),message.id))
                db.commit()
                await message.reply("Added the following:\n```{}```".format('\n'.join(added_tasks)),delete_after=5)
                return print(f'{self.__class__.__name__} - td {ctx.command} | {time.time()-start_time} s')
            return await ctx.message.reply('❌ | No to-do list found in the message.',delete_after=5)

    @todolist.command()
    async def remove(self,ctx,*,emoji:str=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        letter_emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                         14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}
        if emoji is None:
            return await ctx.message.reply('❌ | Emoji representing the task to be removed is a required parameter!',delete_after=5)
        elif len(emoji.split(' '))>1:
            return await ctx.message.reply('❌ | Tasks can only be removed one-by-one',delete_after=5)
        try:
            ctx.message.reference.message_id
        except:
            return await ctx.message.reply('❌ | Please reply to a message that has an existing to-do list.')
        else:
            if cursor.execute(f'SELECT * FROM td WHERE message_id={ctx.message.reference.message_id} AND author_id={ctx.author.id}').fetchone():
                details = cursor.execute(f'SELECT * FROM td WHERE message_id={ctx.message.reference.message_id}').fetchone()
                channel_type, tasklist, description = details[1], details[5].split(';'), ''
                if channel_type == 'dm':
                    return await ctx.message.reply('❌ | Tasks cannot be removed from a private to-do list.',delete_after=5)
                message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if emoji in list(letter_emojis.values())[:len(tasklist)]:
                    for key,value in letter_emojis.items():
                        if value == emoji:
                            removed_task=tasklist.pop(key).split('%')[0]
                            break
                else:
                    return await ctx.message.reply(f'❌ | Emoji {emoji} not found in the choices.',delete_after=5)

                await self.update_td(message,tasklist,letter_emojis)
                await ctx.message.delete()
                cursor.execute('UPDATE td SET tasks=? WHERE message_id=?',(';'.join(tasklist),message.id))
                db.commit()
                await message.reply(f'Removed task `{removed_task}`',delete_after=5)
                return print(f'{self.__class__.__name__} - td {ctx.command} | {time.time()-start_time} s')
            return await ctx.message.reply('❌ | No to-do list found in the message.')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        letter_emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                         14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}

        if (payload.emoji.name in letter_emojis.values() or payload.emoji.name=='🏁') and payload.member != self.bot.user and cursor.execute(f'SELECT * FROM td WHERE message_id={payload.message_id}').fetchone() != None:
            #print('new interaction')
            details = cursor.execute(f'SELECT * FROM td WHERE message_id={payload.message_id}').fetchone()
            guild,channel_type,channel_id,message_id,author_id,tasklist,counter=discord.utils.get(self.bot.guilds,id=details[0]),details[1],details[2],details[3],details[4],details[5].split(';'),details[6]
            channel, description = discord.utils.get(guild.channels,id=channel_id), ''
            try:
                author_dm = await payload.member.create_dm()
            except: # DM todolist
                member = discord.utils.get(guild.members,id=author_id)
                author_dm = await member.create_dm()
                channel = author_dm
            else:
                if payload.member.id != author_id:
                    return
                member = payload.member
            message = await channel.fetch_message(message_id)
            if payload.emoji.name == '🏁':
                if counter != len(tasklist):
                    for n in range(len(tasklist)):
                        if tasklist[n].split('%')[1]=='1':
                            description += f"~~*{letter_emojis[n]} {tasklist[n].split('%')[0]}*~~\n"
                        else:
                            description += f"{letter_emojis[n]} {tasklist[n].split('%')[0]}\n"
                    embed=discord.Embed(description=f'{description}',timestamp=get_dt_now())
                    embed.set_footer(text='Archived')
                    await message.delete()
                    await author_dm.send(embed=embed)
                    cursor.execute(f'DELETE FROM td WHERE message_id={payload.message_id}')
                    db.commit()
                    return print(f'{self.__class__.__name__} - archive td | {time.time()-start_time} s')
            else:
                for index,emoji in letter_emojis.items():
                    if payload.emoji.name == emoji:
                        try:
                            await message.remove_reaction(emoji,member)
                        except:
                            pass
                        task = tasklist.pop(index).split('%')
                        if task[1] == '0':
                            task[1] = '1'
                            counter+=1
                        else:
                            task[1] = '0'
                            counter-=1
                        tasklist.insert(index,'%'.join(task))
                        for n in range(len(tasklist)):
                            if tasklist[n].split('%')[1]=='1':
                                description += f"~~*{letter_emojis[n]} {tasklist[n].split('%')[0]}*~~\n"
                            else:
                                description += f"{letter_emojis[n]} {tasklist[n].split('%')[0]}\n"
                        break
            if counter == len(tasklist):
                embed=discord.Embed(color=0xFFFFFF,title='Tasks Completed',description=f'{description}',timestamp=get_dt_now())
                embed.set_footer(text='Finished all tasks')
                await author_dm.send('🎉 Keep up the good work!',embed=embed)
                await message.delete()
                print(f'{self.__class__.__name__} - finished td | {time.time()-start_time} s')
            else:
                embed=discord.Embed(description=f'{description}')
                embed.set_footer(text='React with 🏁 to close the to-do list.')
                await message.edit(embed=embed)
                cursor.execute('UPDATE td SET tasks=?,counter=? WHERE message_id=?',(';'.join(tasklist),counter,payload.message_id))
                print(f'{self.__class__.__name__} - update td | {time.time()-start_time} s')
        db.commit()

def setup(bot):
    bot.add_cog(Requirements(bot))
    bot.add_cog(SchedLog(bot))
    bot.add_cog(ToDoList(bot))
