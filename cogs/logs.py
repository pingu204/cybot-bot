import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
import datetime
from misc import *
import time
from discord import Option,OptionChoice
from discord.ui import View, Button, Select
from discord.commands import slash_command

class Logs(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    @commands.command()
    async def logs(self,ctx):
        start_time = time.time()
        await ctx.send(embed=get_logs(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

class ServerLog(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    # RETURNS STATUS OF LOGS IN THE SERVER
    @commands.group()
    async def serverlog(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        embed = discord.Embed(color=discord.Colour.blue(),title=f'Server Log | {ctx.prefix}serverlog',description=f"Logs activities inside the server")
        if cursor.execute(f'SELECT serverlog FROM logs_status WHERE guild_id={ctx.guild.id}').fetchone()[0] in [None,0]:
            embed.add_field(name='Status',value=f'Disabled')
        else:
            settings = cursor.execute(f'SELECT * FROM serverlog WHERE guild_id={ctx.guild.id}').fetchone()
            channel,server,role,emoji,invite,msg_delete,track_description = discord.utils.get(ctx.guild.channels,id=settings[1]), settings[2], settings[3], settings[4], settings[5], settings[6],''
            embed.add_field(name='Status',value=f'Enabled in {channel.mention}')
            for change,status in [['Server Changes',server],['Role Changes',role],['Emoji Changes',emoji],['Invite Changes',invite],['Deleted Messages',msg_delete]]:
                if status == 0:
                    track_description += f'❌ {change}\n'
                else:
                    track_description += f'✅ {change}\n'
            embed.add_field(inline=False,name='Track',value=track_description)
        embed.set_footer(text='Use /logs for configuration')
        await ctx.send(embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    # OPTIONS FOR THE SLASH COMMAND
    settings = [
        {
        'name':'status',
        'description':'Whether you want to allow server logs in the server',
        'required':True,
        'type':4,
        'choices':[{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'channel',
        'description':'Channel where to send server logs (if enabled)',
        'required':True,
        'type':7
        },
        {
        'name':'serverchanges',
        'description':'Whether you want to track changes in the server',
        'required':True,
        'type':4,
        'choices':[{'name':'Skipped [Disabled]','value':0},{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'rolechanges',
        'description':'Whether you want to track changes in roles (e.g. creation, deletion)',
        'required':True,
        'type':4,
        'choices':[{'name':'Skipped [Disabled]','value':0},{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'emojichanges',
        'description':'Whether you want to track emoji changes in the server',
        'required':True,
        'type':4,
        'choices':[{'name':'Skipped [Disabled]','value':0},{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'invitechanges',
        'description':'Whether you want to track invite link changes in the server',
        'required':True,
        'type':4,
        'choices':[{'name':'Skipped [Disabled]','value':0},{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'messagedelete',
        'description':'Whether you want to track deleted messages in the server',
        'required':True,
        'type':4,
        'choices':[{'name':'Skipped [Disabled]','value':0},{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
    ]

    # TOGGLES THE STATUS OF LOGS IN THE SERVER
    @slash_command(name="logs",description='Configure the logs settings in the server')
    async def logs(self,ctx,
            status:Option(int,description="Whether you want to allow server logs in the server",choices=[
                    OptionChoice(name="Enable",value=1), OptionChoice(name="Disable",value=0)]),
            channel:Option(discord.TextChannel,description="Channel where to send server logs (if enabled)"),
            serverchanges:Option(int,description="Whether you want to track changes in the server",choices=[
                    OptionChoice(name="Skip [Disabled]",value=0),
                    OptionChoice(name="Enable",value=1),
                    OptionChoice(name="Disable",value=0)]),
            rolechanges:Option(int,description="Whether you want to track changes in changes in roles (e.g. creation, deletion)",choices=[
                    OptionChoice(name="Skip [Disabled]",value=0),
                    OptionChoice(name="Enable",value=1),
                    OptionChoice(name="Disable",value=0)]),
            emojichanges:Option(int,description="Whether you want to track emoji changes in the server",choices=[
                    OptionChoice(name="Skip [Disabled]",value=0),
                    OptionChoice(name="Enable",value=1),
                    OptionChoice(name="Disable",value=0)]),
            messagedelete:Option(int,description="Whether you want to track deleted messages in the server",choices=[
                    OptionChoice(name="Skip [Disabled]",value=0),
                    OptionChoice(name="Enable",value=1),
                    OptionChoice(name="Disable",value=0)])):
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.send('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        await ctx.defer()
        embed = discord.Embed(title='Server Logs Settings')
        if status == 0:
            embed.add_field(name='Status',value='`Disabled`')
        else:
            embed.add_field(name='Status',value=f'`Enabled` in {channel.mention}')
            track = ''
            for change,status in [['Server Changes',serverchanges],['Role Changes',rolechanges],['Emoji Changes',emojichanges],['Deleted Messages',messagedelete]]:
                if status == 1:
                    track += change + '\n'
            embed.add_field(inline=False,name='Track',value=track)

        message = await ctx.send('Here\'s what I got from you. Do you want to save these changes?',embed=embed)
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        try:
            reaction = await self.bot.wait_for('reaction_add', timeout=60, check=lambda reaction,user: str(reaction.emoji) in ['👍','👎'] and user == ctx.author)
        except:
            return await ctx.respond('❌ | Process terminated. Please try again. [Timeout]')
        else:
            await message.delete()
            if str(reaction[0]) == '👍':
                if status == 1:
                    cursor.execute(f'UPDATE serverlog SET channel_id=?,server=?,role=?,emoji=?,msg_delete=? WHERE guild_id=?',\
                                    (channel.id,serverchanges,rolechanges,emojichanges,messagedelete,ctx.guild.id))
                    db.commit()
                cursor.execute(f'UPDATE logs_status SET serverlog=? WHERE guild_id=?',(status,ctx.guild.id))
                db.commit()
            else:
                return await ctx.send('Process terminated.')
            await ctx.respond('Server logs settings have been updated.')
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')


    # CHECKS IF SPECIFIC TYPE OF SERVER LOG IS ENABLED FOR THE SERVER
    def check_log(self,guild,type):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        return cursor.execute(f'SELECT serverlog FROM logs_status WHERE guild_id={guild.id}').fetchone()[0]==1 and \
               cursor.execute(f'SELECT {type} FROM serverlog WHERE guild_id={guild.id}').fetchone()[0]==1

    ## SERVER CHANGES ##
    @commands.Cog.listener()
    async def on_guild_update(self,before,after):
        # boost level
        # number of boosts
        # guild name
        # guild icon
        # transfer ownership
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
        if after.icon:
            log_embed.set_footer(icon_url=after.icon,text=after.name)
        else:
            log_embed.set_footer(text=after.name)
        print('server change',before.owner!=after.owner)
        if self.check_log(after,'server'):
            if before.icon != after.icon:
                if after.icon:
                    log_embed.add_field(inline=False,name='Server Icon Updated',value=f"Icon as [png]({after.icon.with_format('png').url}) | [jpg]({after.icon.with_format('jpg').url}) | [webp]({after.icon.with_format('webp').url})")
                    log_embed.set_thumbnail(url=after.icon.url)
                else:
                    log_embed.add_field(inline=False,name='Server Icon Updated',value='Removed')
            if before.name != after.name:
                log_embed.add_field(inline=False,name='Server Name Updated',value=f'{before.name} ➡ {after.name}')
            if before.owner != after.owner:
                log_embed.add_field(inline=False,name='Transfer Server Ownership',value=f'{before.owner.mention} ➡ {after.owner.mention}')
            if before.premium_subscription_count != after.premium_subscription_count:
                if before.premium_subscription_count > after.premium_subscription_count:
                    removed_boost = list(set(before.premium_subscribers) ^ set(after.premium_subscribers))[0]
                    log_embed.add_field(inline=False,name='Server Boost 🔚',value=f'{removed_boost} has revoked their boost for the server.')
                else:
                    added_boost = list(set(before.premium_subscribers) ^ set(after.premium_subscribers))[0]
                    log_embed.add_field(inline=False,name='Server Boost 🆕',value=f'{added_boost} has boosted the server.')
            if before.premium_tier != after.premium_tier:
                log_embed.add_field(inline=False,name='Server Boost level',value=f'{before.premium_tier} ➡ {after.premium_tier}')
            channel = discord.utils.get(after.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={after.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - guild update log | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if self.check_log(channel.guild,'server'):
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            if channel.guild.icon:
                log_embed.set_footer(icon_url=channel.guild.icon,text=channel.guild.name)
            else:
                log_embed.set_footer(text=channel.guild.name)
            log_embed.add_field(inline=False,name='Channel Deleted',value=f'{channel.name}\nCategory: `{channel.category}`')
            channel = discord.utils.get(channel.guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={channel.guild.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - channel delete log | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before,after):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if self.check_log(after.guild,'server'):
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            if after.guild.icon:
                log_embed.set_footer(icon_url=after.guild.icon,text=after.guild.name)
            else:
                log_embed.set_footer(text=after.guild.name)
            if before.name != after.name:
                log_embed.add_field(inline=False,name='Channel Name Updated',value=f'{before.name} ➡ {after.name}')
            if before.category != after.category:
                log_embed.add_field(inline=False,name='Channel Category Updated',value=f'`{before.category}` ➡ `{after.category}`')
            if len(log_embed.fields) == 0:
                return
            channel = discord.utils.get(after.guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={after.guild.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - channel update log | {time.time()-start_time} s')

    ## ROLE CHANGES ##
    @commands.Cog.listener()
    async def on_guild_role_create(self,role):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if self.check_log(role.guild,'role'):
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            if role.guild.icon:
                log_embed.set_footer(icon_url=role.guild.icon,text=role.guild.name)
            else:
                log_embed.set_footer(text=role.guild.name)
            log_embed.add_field(inline=False,name='New Role Created',value=f'{role.mention}\nColor: `#{str(role.color)}`\nID: `{role.id}`')
            channel = discord.utils.get(role.guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={role.guild.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - role create log | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_guild_role_delete(self,role):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if self.check_log(role.guild,'role'):
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            if role.guild.icon:
                log_embed.set_footer(icon_url=role.guild.icon,text=role.guild.name)
            else:
                log_embed.set_footer(text=role.guild.name)
            log_embed.add_field(inline=False,name='Role Deleted',value=f'{role.mention}\nColor: `#{str(role.color)}`\nID: `{role.id}`')
            channel = discord.utils.get(role.guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={role.guild.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - role delete log | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_guild_role_update(self,before, after):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if self.check_log(after.guild,'role'):
            log_embed = discord.Embed(color=0xFFFFFF,description=after.mention,timestamp=get_dt_now())
            if after.guild.icon:
                log_embed.set_footer(icon_url=after.guild.icon,text=after.guild.name)
            else:
                log_embed.set_footer(text=after.guild.name)
            if before.name != after.name:
                log_embed.add_field(inline=False,name='Role Name Updated',value=f'{before.name} ➡ {after.name}')
            if before.permissions != after.permissions:
                log_embed.add_field(inline=False,name='Role Permissions Updated',value=f'Permissions for role {after.name} has been updated.')
            if before.color != after.color:
                log_embed.add_field(inline=False,name='Role Color Updated',value=f'`#{str(before.color)}` ➡ `#{str(after.color)}`')
            if len(log_embed.fields) == 0:
                return
            channel = discord.utils.get(after.guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={after.guild.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - role update log | {time.time()-start_time} s')

    ## EMOJI CHANGES ##
    @commands.Cog.listener()
    async def on_guild_emojis_update(self,guild, before, after):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if self.check_log(guild,'emoji'):
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            if guild.icon:
                log_embed.set_footer(icon_url=guild.icon,text=guild.name)
            else:
                log_embed.set_footer(guild.name)
            if len(before) < len(after): # added emoji
                emoji = list(set(before) ^ set(after))[0]
                log_embed.add_field(inline=False,name='New Emoji Created',value=f'{str(emoji)} | \:{emoji.name}:')
            elif len(before) > len(after):
                emoji = list(set(before) ^ set(after))[0]
                log_embed.add_field(inline=False,name='Emoji Deleted',value=f'\:{emoji.name}:')
            else:
                return
            channel = discord.utils.get(guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={guild.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - emoji update log | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if self.check_log(channel.guild,'server'):
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            if channel.guild.icon:
                log_embed.set_footer(icon_url=channel.guild.icon,text=channel.guild.name)
            else:
                log_embed.set_footer(text=channel.guild.name)
            log_embed.add_field(inline=False,name='New Channel Created',value=f'{channel.mention}\nCategory: `{channel.category}`')
            channel = discord.utils.get(channel.guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={channel.guild.id}').fetchone()[0])
            await channel.send(embed=log_embed)
            return print(f'{self.__class__.__name__} - channel create log | {time.time()-start_time} s')


    ## MESSAGE DELETION ##
    @commands.Cog.listener()
    async def on_raw_message_delete(self,payload):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        try:
            prefix = cursor.execute(f'SELECT prefix FROM prefixes WHERE guild_id={payload.cached_message.guild.id}').fetchone()[0]
            if prefix is None:
                prefix = '$'
            if payload.cached_message.content:
                if payload.cached_message.content.startswith(prefix):
                    return
            elif not payload.cached_message.attachments:
                return
            try:
                if payload.cached_message.author != self.bot.user:
                    if self.check_log(payload.cached_message.guild,'msg_delete'):
                        log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
                        if payload.cached_message.content:
                            log_embed = discord.Embed(color=0xFFFFFF,description=f'>>> {payload.cached_message.content}',timestamp=get_dt_now())
                        if payload.cached_message.attachments:
                            attachments = '\n'.join([f'{attachment.filename}' for attachment in payload.cached_message.attachments])
                            log_embed.add_field(name="Attachment", value=attachments)
                        log_embed.set_author(name=payload.cached_message.author,icon_url=payload.cached_message.author.avatar.url)
                        if payload.cached_message.guild.icon:
                            log_embed.set_footer(icon_url=payload.cached_message.guild.icon,text=payload.cached_message.guild.name)
                        else:
                            log_embed.set_footer(text=payload.cached_message.guild.name)
                        channel = discord.utils.get(payload.cached_message.guild.channels,id=cursor.execute(f'SELECT channel_id FROM serverlog WHERE guild_id={payload.cached_message.guild.id}').fetchone()[0])
                        await channel.send(f'Deleted message in {payload.cached_message.channel.mention}',embed=log_embed)
                        return print(f'{self.__class__.__name__} - message delete log | {time.time()-start_time} s')
            except:
                pass
        except:
            # message from DM
            pass

class MemberLog(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    @commands.Cog.listener()
    async def on_member_join(self,member): #welcome message
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f"SELECT mlog FROM logs_status WHERE guild_id = {member.guild.id}").fetchone()[0]==1:
            await self.send_message('entry',member)
            return print(f'{self.__class__.__name__} - welcome member | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f"SELECT mlog FROM logs_status WHERE guild_id = {member.guild.id}").fetchone()[0]==1:
            await self.send_message('exit',member)
            return print(f'{self.__class__.__name__} - farewell member | {time.time()-start_time} s')

    @commands.group(invoke_without_command=True,aliases=['mlog','mlogs','memlog','memlogs','memberlogs'])
    @has_permissions(manage_guild=True)
    async def memberlog(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        ##
        result = cursor.execute(f"SELECT channel_id,entry,exit FROM mlog WHERE guild_id = {ctx.guild.id}").fetchone()
        if cursor.execute(f"SELECT mlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone()[0] is None or cursor.execute(f"SELECT mlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone()[0]==0:
            mlog_status = '❌'
            mlog_channel,entry_message,exit_message = '','Default','Default'
            if result[1] != None:
                entry_message = result[1]
            if result[2] != None:
                exit_message = result[2]
        else:
            mlog_status = '✅'
            mlog_channel = ('in '+discord.utils.get(ctx.guild.channels,id=int(result[0])).mention)
            entry_message, exit_message = 'None','None'
            if result[1] != None:
                entry_message = result[1]
            if result[2] != None:
                exit_message = result[2]

        ## EMBED ##
        embed = discord.Embed(color=discord.Colour.blue(),title=f'Member Log | {ctx.prefix}mlog',description=f"Logs who goes in and out of the server\nStatus: {mlog_status} {mlog_channel}")
        embed.add_field(name='_enable `channel`',value=f'Enable member logs for this server',inline=False)
        embed.add_field(name='_disable',value=f'Disable member logs for this server',inline=False)
        embed.add_field(name='_channel `channel`',value=f'Define where to send the message',inline=False)
        embed.add_field(name='_entry `text`',value=f'Add a welcome message\nCurrent: `{entry_message}`',inline=False)
        embed.add_field(name='_exit `text`',value='Add a farewell message\nCurrent: `{}`\n\nUse `{}` to mention the user and `{}` to get the server name.'.format(exit_message,'{mention}','{guild}'),inline=False)
        embed.set_footer(text=f'Example: {ctx.prefix}mlog enable #channel-name | {ctx.prefix}mlog channel #channel-name')
        await ctx.send(embed=embed)
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @memberlog.command(aliases=['on'])
    @has_permissions(manage_guild=True)
    async def enable(self,ctx,channel:discord.TextChannel=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        if channel is None:
            return await ctx.send('❌ | Channel is a required parameter.')
        # CHANNEL
        cursor.execute('UPDATE mlog SET channel_id = ? WHERE guild_id = ?',(channel.id,ctx.guild.id))
        # STATUS
        if cursor.execute(f"SELECT mlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone()[0]==1:
            return await ctx.send('Member logs are already enabled in the served.',delete_after=3)
        else:
            cursor.execute(f"UPDATE logs_status SET mlog = ? WHERE guild_id = ?",(1,ctx.guild.id))

        await ctx.message.delete()
        await ctx.send(f'✅ Member logs enabled for the server.\n\nTo disable, type `{ctx.prefix}mlog disable`')
        db.commit()
        return print(f'{self.__class__.__name__} - mlog {ctx.command} | {time.time()-start_time} s')

    @memberlog.command(aliases=['off'])
    @has_permissions(manage_guild=True)
    async def disable(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f"SELECT mlog FROM logs_status WHERE guild_id = {ctx.guild.id}").fetchone()[0]==0:
            # ALREADY DISABLED
            return await ctx.send('Member logs already disabled.')
        else:
            cursor.execute(f"UPDATE logs_status SET mlog = ? WHERE guild_id = ?",(0,ctx.guild.id))
            await ctx.message.delete()
            await ctx.send(f'✅ Member logs disabled for the server.\n\nTo enable, type `{ctx.prefix}mlog enable #channel`')
        db.commit()
        return print(f'{self.__class__.__name__} - mlog {ctx.command} | {time.time()-start_time} s')

    @memberlog.command(aliases=['c','ch'])
    @has_permissions(manage_guild=True)
    async def channel(self,ctx, channel:discord.TextChannel=None):
        ### SET WELCOME CHANNEL ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if channel is None:
            return await ctx.send('❌ | Channel is a required parameter.')
        await ctx.message.delete()
        cursor.execute('UPDATE mlog SET channel_id = ? WHERE guild_id = ?',(channel.id,ctx.guild.id))
        if channel:
            await ctx.send(f'✅ Channel for member logs has been set to {channel.mention}')
        else:
            await ctx.send(f'✅ Channel for member logs has been set to {channel}')
        db.commit()
        return print(f'{self.__class__.__name__} - mlog {ctx.command} | {time.time()-start_time} s')

    @memberlog.command(aliases=['welcome','greet'])
    @has_permissions(manage_guild=True)
    async def entry(self,ctx,*,msg:str=None):
        ### SET WELCOME TEXT ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        cursor.execute('UPDATE mlog SET entry = ? WHERE guild_id = ?',(msg,ctx.guild.id))
        await ctx.message.delete()
        await ctx.send(f'✅ Welcome message has been set to `{msg}`.')
        db.commit()
        return print(f'{self.__class__.__name__} - mlog {ctx.command} | {time.time()-start_time} s')

    @memberlog.command(aliases=['farewell','bye'])
    @has_permissions(manage_guild=True)
    async def exit(self,ctx,*,msg:str=None):
        ### SET FAREWELL TEXT ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        cursor.execute('UPDATE mlog SET exit = ? WHERE guild_id = ?',(msg,ctx.guild.id))
        await ctx.message.delete()
        await ctx.send(f'✅ Exit message has been set to `{msg}`.')
        db.commit()
        return print(f'{self.__class__.__name__} - mlog {ctx.command} | {time.time()-start_time} s')

    @memberlog.command(aliases=['try'])
    @has_permissions(manage_guild=True)
    async def test(self,ctx):
        ### TEST IF MEMBER LOGS IS WORKING ###
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f"SELECT channel_id FROM mlog WHERE guild_id = {ctx.guild.id}").fetchone()[0] is None:
            # NEEDS LOGGING CHANNEL FIRST
            return await ctx.send('❌ | Please set a member log channel using `$mlog channel #channel` first.')
        if cursor.execute(f"SELECT entry FROM mlog WHERE guild_id = {ctx.guild.id}").fetchone()[0] is None:
            await ctx.send('`No welcome message set`: default message will be used instead')
        await self.send_message('entry',ctx.author)
        if cursor.execute(f"SELECT exit FROM mlog WHERE guild_id = {ctx.guild.id}").fetchone()[0] is None:
            await ctx.send('`No farewell message set`: default message will be used instead')
        await self.send_message('exit',ctx.author)
        await ctx.send(f'✅ Member logs tested in {self.bot.get_channel(int(cursor.execute(f"SELECT channel_id FROM mlog WHERE guild_id = {ctx.guild.id}").fetchone()[0])).mention}')
        return print(f'{self.__class__.__name__} - mlog {ctx.command} | {time.time()-start_time} s')

    async def send_message(self,type,member):
        ### SEND MEMBER LOG MESSAGE ###
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        result = cursor.execute(f"SELECT channel_id,entry,exit FROM mlog WHERE guild_id = {member.guild.id}").fetchone()
        if result[0] is None:
            # NO CHANNEL HAS BEEN SET
            return
        else:
            mention,user,guild = member.mention,member.name,member.guild
            if type == 'entry':
                # WELCOME MESSAGE
                embed = discord.Embed(color=0x3B88C3,title='🆕',description=f'**{member}** has joined the server.')
                result_msg = result[1]
                if result_msg is None:
                    result_msg = '{user} has joined the server.'
                activity = 'Joined'
            else:
                # FAREWELL MESSAGE
                embed = discord.Embed(color=0xBE1931,title='⛔',description=f'**{member}** has left the server.')
                result_msg = result[2]
                if result_msg is None:
                    result_msg = '{user} has left the server.'
                activity = 'Left'
            embed.add_field(name='User ID',value=member.id)
            embed.set_thumbnail(url=member.avatar.url)
            embed.set_footer(text=f"Member Count: {len(member.guild.members)} | {activity} at {get_dt_now().strftime('%m/%d/%Y %I:%M %p')}")
            channel = self.bot.get_channel(int(result[0]))
            await channel.send(result_msg.format(mention=mention,user=user,guild=guild),embed=embed)
        db.commit()

def setup(bot):
    bot.add_cog(MemberLog(bot))
    bot.add_cog(ServerLog(bot))
    bot.add_cog(Logs(bot))
