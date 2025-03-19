import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from misc import *
#from discord_slash import SlashCommand, SlashContext, cog_ext
import re
import os
import string
import asyncio
import time
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from typing import Union
from discord import Option,OptionChoice
from discord.ui import View, Button, Select
from discord.commands import slash_command

class Mod(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Mod ready!')
        self.bot.loop.create_task(self.check_mute())
        self.bot.loop.create_task(self.check_ban())

    async def create_log(self,guild,author,member,type,reason):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        actions = {
            'warn':'You have been **warned** for your behavior in the server.',
            'mute':'You have been **disallowed** from sending messages in the server.',
            'tempmute':'You have been **temporarily muted** in the server.',
            'unmute':'You can now send messages in the server.',
            'kick':'You have been **kicked** from the server.',
            'ban':'You were **banned** from the server',
            'softban':'You were **temporarily banned** from the server',
            'unban':'You can now join the server again'
        }

        dm_channel = await member.create_dm()
        dm_embed = discord.Embed(color=0x696969,timestamp=get_dt_now(),description=actions[type])
        if reason:
            dm_embed.add_field(inline=False,name='Reason',value=reason)
        dm_embed.set_footer(icon_url=guild.icon.url,text=guild.name)
        await dm_channel.send('`Notice Re: Moderation`',embed=dm_embed)

        log_actions = {
            'warn':'Warning',
            'mute':'Mute',
            'tempmute':'Temporary Mute',
            'unmute':'Unmute',
            'kick':'Kick',
            'ban':'Ban',
            'softban':'Soft Ban',
            'unban':'Unban'
        }

        if cursor.execute(f'SELECT logs_status FROM mod_settings WHERE guild_id={guild.id}').fetchone()[0] == 1 and type not in ['ban','softban']:
            settings = cursor.execute(f'SELECT * FROM mod_settings WHERE guild_id={guild.id}').fetchone()
            logs,channel,maxwarns,warnpunishment,censor,censorpunishment = settings[1], discord.utils.get(guild.channels,id=settings[2]), settings[4], settings[5], settings[6], settings[7]

            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            log_embed.add_field(inline=False,name='Action',value=f'{log_actions[type]}')
            log_embed.add_field(inline=False,name='Member ID',value=member.id)
            if reason:
                log_embed.add_field(inline=False,name='Reason',value=reason)
            if author:
                log_embed.add_field(inline=False,name='Moderator',value=author)
            log_embed.set_footer(icon_url=guild.icon.url,text=guild.name)
            log_embed.set_thumbnail(url=member.avatar.url)

            await channel.send('New moderation action...',embed=log_embed)

    options = [
        {
        'name':'user',
        'description':'User you are trying to perform an action on',
        'required':True,
        'type':9
        },
        {
        'name':'reason',
        'description':'Reason for performing the action',
        'required':False,
        'type':3
        }
    ]

    @commands.Cog.listener()
    async def on_member_join(self,member): # STICKY MUTE ROLE
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={member.guild.id}').fetchone()[0]:
            mute_role = discord.utils.get(member.guild.roles,id=cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={member.guild.id}').fetchone()[0])
            if cursor.execute(f"SELECT * FROM mute WHERE guild_id = {member.guild.id} AND user_id = {member.id}").fetchone():
                await member.add_roles(mute_role)
                return print(f'{self.__class__.__name__} - sticky mute role | {time.time()-start_time} s')

    async def check_mute(self):
        # to check if tempmute is already overdue
        # load the database

        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        while 1:
            dt_now = get_dt_now().replace(tzinfo=None)
            mutes = cursor.execute(f"SELECT * FROM mute WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={dt_now.year}").fetchall()
            for details in mutes:
                start_time = time.time()
                guild, user_id, iso = discord.utils.get(self.bot.guilds,id=details[0]), details[1], details[5]
                #user = discord.utils.get(guild.members,id=user_id)
                if (dt_now-datetime.fromisoformat(iso)).seconds <= 1:
                    user = discord.utils.get(guild.members,id=int(user_id))
                    if user:
                        mute_role = discord.utils.get(guild.roles,id=cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={guild.id}').fetchone()[0])
                        await user.remove_roles(mute_role)
                    cursor.execute(f'DELETE FROM mute WHERE guild_id={guild.id} AND user_id={user.id}')
                    db.commit()
                    print(f'{self.__class__.__name__} - unmute tempmute | {time.time()-start_time} s')
                    await self.create_log(guild,self.bot.user,user,'unmute',None)
            await asyncio.sleep(1)

    async def mute_command(self,ctx:Union[discord.abc.Messageable,discord.Message],type,user,reason,duration):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        try:
            ctx.message
        except:
            mute_role = discord.utils.get(ctx.guild.roles,id=cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0])
            try:
                await ctx.author.add_roles(mute_role)
            except:
                return await ctx.channel.send(f'❌ | Cannot mute {ctx.author.mention}. Please check the bot\'s permissions in the server.')
            if type == 'tempmute':
                unmute_datetime = (get_dt_now() + timedelta(hours=duration)).isoformat(' ')
                cursor.execute('INSERT INTO mute(guild_id,user_id,iso) VALUES(?,?,?)',(ctx.guild.id,ctx.author.id,unmute_datetime[:16]))
                db.commit()
            else:
                cursor.execute('INSERT INTO mute(guild_id,user_id) VALUES(?,?)',(ctx.guild.id,ctx.author.id))
                db.commit()
            await self.create_log(ctx.guild,self.bot.user,ctx.author,type,reason)
        else:
            print('yes')
            if str(user).isnumeric():
                user = discord.utils.get(ctx.guild.members,id=int(user))
            if user is None:
                return await ctx.respond('❌ | User does not exist.')
            if ctx.author.top_role < user.top_role:
                return await ctx.respond('❌ | You can only do moderation actions to users below you.')
            if type == 'tempmute' and duration<=0:
                return await ctx.respond('❌ | Duration must be greater than zero.')
            if cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0] == None:
                ask_create = await ctx.respond('There is no mute role created yet in the server. Would you like to create one?')
                await ask_create.add_reaction('👍')
                await ask_create.add_reaction('👎')
                try:
                    reaction = await self.bot.wait_for('reaction_add', timeout=60, check=lambda reaction,user: str(reaction.emoji) in ['👍','👎'] and user == ctx.author)
                except:
                    return await ctx.respond('❌ | Process terminated. Reason: `Timeout`')
                else:
                    if str(reaction[0]) == '👎':
                        return await ctx.respond('❌ | Role is needed to mute someone in the server. Please try again.')
                    if ctx.guild.roles[len(ctx.guild.roles)-1].name != self.bot.user.name:
                        return await ctx.respond(f'❌ | Cannot proceed with creating a mute role as the bot is not set-up in the server yet. Please make sure that {discord.utils.get(ctx.guild.roles,name=self.bot.user.name).mention} is at the top of the role hierarchy.')
                    async with ctx.channel.typing():
                        message = await ctx.respond('*Creating a mute role for the server...*')
                        mute_perms = discord.Permissions(send_messages=False, read_messages=True)
                        mute_role = await ctx.guild.create_role(name='muted',color=0x696969,permissions=mute_perms,reason='Mute role for the server')
                        bot_role = discord.utils.get(ctx.guild.roles,name=self.bot.user.name)
                        await mute_role.edit(position=bot_role.position-1)
                        await message.edit(content = '✅ Creating a mute role for the server\n*Overriding permissions for all channels...*')
                        for channel in ctx.guild.text_channels:
                            await channel.set_permissions(mute_role, send_messages=False)
                        await message.edit(content = '✅ Creating a mute role for the server\n✅ Overriding permissions for all channels')
                        cursor.execute(f'UPDATE mod_settings SET mute_id=? WHERE guild_id=?',(mute_role.id,ctx.guild.id))
                        db.commit()
                    await message.edit(content = f'✅ Creating a mute role for the server\n✅ Overriding permissions for all channels\n✅ Mute role {mute_role.mention} created and registered for the server')
                    await message.delete(delay=5)
            mute_role = discord.utils.get(ctx.guild.roles,id=cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0])

            if mute_role in user.roles:
                return await ctx.respond(f'❌ | User {user.mention} is already muted.')
            try:
                await user.add_roles(mute_role)
            except:
                return await ctx.respond('❌ | An error occured. Please check the bot\'s permissions in the server.')
            if type == 'tempmute':
                await ctx.respond(f'{user.mention} has been temporarily muted.')
                unmute_datetime = get_dt_now() + timedelta(hours=duration)
                month, day, year = unmute_datetime.strftime('%b'), unmute_datetime.day, unmute_datetime.year
                cursor.execute('INSERT INTO mute(guild_id,user_id,month,day,year,iso) VALUES(?,?,?,?,?,?)',(ctx.guild.id,user.id,month,day,year,unmute_datetime.isoformat(' ')[:16]))
                db.commit()
            else:
                await ctx.respond(f'{user.mention} has been muted.')
                cursor.execute('INSERT INTO mute(guild_id,user_id) VALUES(?,?)',(ctx.guild.id,user.id))
                db.commit()
            await self.create_log(ctx.guild,ctx.author,user,type,reason)

    @slash_command(name="mute",description='Mute a person in the server')
    async def mute(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on"),
            reason:Option(str,description="Reason for performing the action")=None):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        print('yes')
        await self.mute_command(ctx,'mute',user,reason,None)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command()
    async def muterole(self,ctx,role:discord.Role):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        bot_role = discord.utils.get(ctx.guild.roles,name=self.bot.user.name)
        await ctx.send('Changing hierarchy')
        await role.edit(position=bot_role.position-1)
        await ctx.send('Overriding channel permissions')
        for channel in ctx.guild.text_channels:
            await channel.set_permissions(role, send_messages=False)
        await ctx.send('Database')
        cursor.execute(f'UPDATE mod_settings SET mute_id=? WHERE guild_id=?',(role.id,ctx.guild.id))
        db.commit()
        await ctx.send(f'{role.mention} is ready to use!')

    temp_options = [
        {
        'name':'user',
        'description':'User you are trying to perform an action on',
        'required':True,
        'type':9
        },
        {
        'name':'duration',
        'description':'Number of hours that the user will be moderated for',
        'required':True,
        'type':4
        },
        {
        'name':'reason',
        'description':'Reason for performing the action',
        'required':False,
        'type':3
        }
    ]

    @slash_command(name="tempmute",description='Temporarily mute a person in the server')
    async def tempmute(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on"),
            duration:Option(int,description="Number of hours that the user will be moderated for")=0,
            reason:Option(str,description="Reason for performing the action")=None):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        await self.mute_command(ctx,'tempmute',user,reason,duration)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="unmute",description='Unmute a person in the server')
    async def unmute(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        #user = discord.utils.get(ctx.guild.members,id=int(user))
        if user is None:
            return await ctx.respond('❌ | User does not exist.')
        if cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone() == None:
            return await ctx.respond('❌ | There is no mute role in the server.')
        mute_role = discord.utils.get(ctx.guild.roles,id=cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0])
        if mute_role in user.roles:
            await user.remove_roles(mute_role)
            await ctx.respond(f'{user.mention} has been unmuted.')
            try:
                cursor.execute(f'DELETE FROM mute WHERE user_id={user.id} AND guild_id={ctx.guild.id}')
            except:
                pass
            else:
                db.commit()
            print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
            return await self.create_log(ctx.guild,ctx.author,user,'unmute',None)
        return await ctx.respond(f'❌ | User {user.mention} is not muted.')

    async def kick_command(self,ctx:Union[discord.abc.Messageable,discord.Message],user,reason):
        try:
            ctx.message
        except:
            await self.create_log(ctx.guild,self.bot.user,ctx.author,'kick',reason)
            await ctx.guild.kick(ctx.author,reason=reason)
        else:
            if str(user).isnumeric():
                user = discord.utils.get(ctx.guild.members,id=int(user))
            if user is None:
                return await ctx.respond('❌ | User does not exist.')
            if ctx.author.top_role <= user.top_role:
                return await ctx.respond('❌ | You can only do moderation actions to users below you.')
            await self.create_log(ctx.guild,ctx.author,user,'kick',reason)
            await ctx.guild.kick(user,reason=reason)
            return await ctx.respond(f'{user.mention} has been kicked from the server.')

    @slash_command(name="kick",description='Kick a member from the server')
    async def kick(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on"),
            reason:Option(str,description="Reason for performing the action")=None):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        await self.kick_command(ctx,user,reason)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    async def check_ban(self):
        # to check if tempban is already overdue
        # load the database
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        while 1:
            dt_now = get_dt_now().replace(tzinfo=None)
            bans = cursor.execute(f"SELECT * FROM tempban WHERE month='{dt_now.strftime('%b')}' AND day={dt_now.day} AND year={dt_now.year}").fetchall()
            for details in bans:
                guild, user_id, iso = discord.utils.get(self.bot.guilds,id=details[0]), details[1], details[5]
                if (dt_now-datetime.fromisoformat(iso)).seconds <= 1:
                    start_time = time.time()
                    banned_users = await guild.bans()
                    banned_users = [entry.user for entry in banned_users]
                    user = discord.utils.get(banned_users,id=int(user_id))
                    await guild.unban(user)
                    cursor.execute(f'DELETE FROM tempban WHERE guild_id={guild.id} AND user_id={user.id}')
                    db.commit()
                    print(f'{self.__class__.__name__} - unban softban | {time.time()-start_time} s')
            await asyncio.sleep(1)

    async def ban_command(self,ctx:Union[discord.abc.Messageable,discord.Message],type,user,reason,duration): # CHECK IF THERE'S RECORD IN DATABASE
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        try:
            ctx.message
        except:
            if type == 'softban':
                unban_datetime = (get_dt_now() + timedelta(hours=duration)).isoformat(' ')
                cursor.execute('INSERT INTO tempban(guild_id,user_id,iso) VALUES(?,?,?)',(ctx.guild.id,ctx.author.id,unban_datetime[:16]))
                db.commit()
                await self.create_log(ctx.guild,self.bot.user,ctx.author,'softban',reason)
                await ctx.author.ban(reason=reason)
            else:
                await self.create_log(ctx.guild,self.bot.user,ctx.author,'ban',reason)
                await ctx.author.ban(reason=reason)
        else:
            if str(user).isnumeric():
                user = discord.utils.get(ctx.guild.members,id=int(user))
            if user is None:
                return await ctx.respond('❌ | User does not exist.')
            if ctx.author.top_role < user.top_role:
                return await ctx.respond('❌ | You can only do moderation actions to users below you.')
            if type=='softban' and duration<=0:
                return await ctx.respond('❌ | Duration must be greater than zero.')
            if type == 'softban':
                unban_datetime = get_dt_now() + timedelta(hours=duration)
                month, day, year = unban_datetime.strftime('%b'), unban_datetime.day, unban_datetime.year
                cursor.execute('INSERT INTO tempban(guild_id,user_id,month,day,year,iso) VALUES(?,?,?,?,?,?)',(ctx.guild.id,user.id,month,day,year,unban_datetime.isoformat(' ')[:16]))
                db.commit()
                await self.create_log(ctx.guild,ctx.author,user,'softban',reason)
                await user.ban(reason=reason)
                await ctx.respond(f'{user.mention} has been temporarily banned from the server.')
            else:
                await self.create_log(ctx.guild,ctx.author,user,'ban',reason)
                await user.ban(reason=reason)
            # await self.create_log(ctx,user,'ban',reason)
                await ctx.respond(f'{user.mention} has been banned from the server.')


    @commands.Cog.listener()
    @has_permissions(manage_guild=True)
    async def on_member_ban(self,guild, user):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        # dm_channel = await user.create_dm()
        # dm_embed = discord.Embed(color=0x696969,timestamp=get_dt_now(),description='You were **banned** from the server')
        # dm_embed.set_footer(icon_url=guild.icon.url,text=guild.name)
        # await dm_channel.send('`Notice Re: Moderation`',embed=dm_embed)

        if cursor.execute(f'SELECT logs_status FROM mod_settings WHERE guild_id={guild.id}').fetchone()[0] not in [None,0]:
            channel = discord.utils.get(guild.text_channels,id=cursor.execute(f'SELECT logs_id FROM mod_settings WHERE guild_id={guild.id}').fetchone()[0])
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            log_embed.add_field(inline=False,name='Action',value=f'Ban')
            log_embed.add_field(inline=False,name='Member ID',value=user.id)
            log_embed.set_footer(icon_url=guild.icon.url,text=guild.name)
            log_embed.set_thumbnail(url=user.avatar.url)

            await channel.send('New moderation action...',embed=log_embed)
            return print(f'{self.__class__.__name__} - member ban | {time.time()-start_time} s')

    @commands.Cog.listener()
    @has_permissions(manage_guild=True)
    async def on_member_unban(self,guild, user):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        # dm_channel = await user.create_dm()
        # dm_embed = discord.Embed(color=0x696969,timestamp=get_dt_now(),description='You can now join the server again')
        # dm_embed.set_footer(icon_url=guild.icon.url,text=guild.name)
        # await dm_channel.send('`Notice Re: Moderation`',embed=dm_embed)

        if cursor.execute(f'SELECT logs_status FROM mod_settings WHERE guild_id={guild.id}').fetchone()[0] not in [None,0]:
            channel = discord.utils.get(guild.text_channels,id=cursor.execute(f'SELECT logs_id FROM mod_settings WHERE guild_id={guild.id}').fetchone()[0])
            log_embed = discord.Embed(color=0xFFFFFF,timestamp=get_dt_now())
            log_embed.add_field(inline=False,name='Action',value=f'Unban')
            log_embed.add_field(inline=False,name='Member ID',value=user.id)
            log_embed.set_footer(icon_url=guild.icon.url,text=guild.name)
            log_embed.set_thumbnail(url=user.avatar.url)

            await channel.send('New moderation action...',embed=log_embed)
            return print(f'{self.__class__.__name__} - member unban | {time.time()-start_time} s')

    @slash_command(name="ban",description='Ban a person from the server')
    async def ban(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on"),
            reason:Option(str,description="Reason for performing the action")=None):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        await self.ban_command(ctx,'ban',user,reason,None)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="softban",description='Temporarily ban a person in the server')
    async def softban(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on"),
            duration:Option(int,description="Number of hours that the user will be moderated for")=0,
            reason:Option(str,description="Reason for performing the action")=None):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        await self.ban_command(ctx,'softban',user,reason,duration)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="unban",description='Mute a person in the server')
    async def unban(self,ctx,id:Option(str,description="ID of the user you are trying to unban")):
        await ctx.defer()
        try:
            id = int(id)
        except:
            return await ctx.respond('❌ | Invalid ID')
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        banned_users = await ctx.guild.bans()
        banned_users = [entry.user for entry in banned_users]
        if discord.utils.get(banned_users,id=int(id)):
            member = discord.utils.get(banned_users,id=int(id))
            await ctx.respond(f'User {member.mention} has been unbanned.')
            if cursor.execute(f'SELECT * FROM tempban WHERE guild_id={ctx.guild.id} AND user_id={int(id)}').fetchone():
                cursor.execute(f'DELETE FROM tempban WHERE guild_id={ctx.guild.id} AND user_id={int(id)}')
                db.commit()
            await ctx.guild.unban(member)
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
            #insert logs
        return await ctx.respond(f'❌ | User with ID `{id}` is not banned.')

    @slash_command(name="warn",description='Warn a person in the server')
    async def warn(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on"),
            reason:Option(str,description="Reason for performing the action")=None):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        #user = discord.utils.get(ctx.guild.members,id=int(user))
        if user is None:
            return await ctx.respond('❌ | User does not exist.')
        # send message to user
        if cursor.execute(f'SELECT * FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone():
            count = cursor.execute(f'SELECT count FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone()[0] + 1
            if cursor.execute(f'SELECT max_warns FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0]:
                max_warns = cursor.execute(f'SELECT max_warns FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0]
                if max_warns == 0 or max_warns is None:
                    pass
                elif count >= max_warns:
                    if cursor.execute(f'SELECT warn_effect FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0]:
                        punishment = cursor.execute(f'SELECT warn_effect FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0]
                        message = await ctx.respond(f'User {user.mention} has reached the warn threshold. Punishment `{punishment}` will be applied accordingly.')
                        if punishment == 'mute':
                            await self.mute_command(ctx,'mute',user.id,'You have reached the warning threshold for the server',None)
                        elif punishment == 'tempmute':
                            await self.mute_command(ctx,'tempmute',user.id,'You have reached the warning threshold for the server',1)
                        elif punishment == 'kick':
                            await self.kick_command(ctx,user.id,'You have reached the warning threshold for the server')
                        elif punishment == 'ban':
                            await self.ban_command(ctx,'ban',user.id,'You have reached the warning threshold for the server',None)
                        elif punishment == 'softban':
                            await self.ban_command(ctx,'softban',user.id,'You have reached the warning threshold for the server',1)
                        cursor.execute('UPDATE warns SET count=? WHERE guild_id=? AND user_id=?',(0,ctx.guild.id,user.id))
                        await message.edit(content=message.content+f'\nWarn count for {user.mention} has been resetted.')
                        db.commit()
                        return print(f'{self.__class__.__name__} - warn threshold reached | {time.time()-start_time} s')
                    return await ctx.respond(f'User {user.mention} has reached warn threshold, but no punishment has been set in the server.')
            cursor.execute('UPDATE warns SET count=? WHERE guild_id=? AND user_id=?',(count,ctx.guild.id,user.id))
        else:
            cursor.execute(f'INSERT INTO warns(guild_id,user_id,count) VALUES(?,?,?)',(ctx.guild.id,user.id,1))
            count=1
        db.commit()
        await self.create_log(ctx.guild,ctx.author,user,'warn',reason)
        await ctx.respond(f'User {user.mention} has been warned.\n\nWarning Count: `{count}`')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="getwarns",description='Get all warnings attributed to a member')
    async def getwarns(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on")):
        await ctx.defer()
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        user,count = discord.utils.get(ctx.guild.members,id=int(user)),0
        if user is None:
            return await ctx.respond('❌ | User does not exist.')
        if cursor.execute(f'SELECT * FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone():
            count = cursor.execute(f'SELECT count FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone()[0]
        await ctx.respond(f'User `{user}` currently has `{count}` warnings.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="removewarn",description='Remove warn/s from a person in the server')
    async def removewarn(self,ctx,
            user:Option(discord.Member,description="User you are trying to perform an action on"),
            number:Option(int,description="Number of warns you are trying to remove from the user")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        #user = discord.utils.get(ctx.guild.members,id=int(user))
        if user is None:
            return await ctx.respond('❌ | User does not exist.')
        if number <= 0:
            return await ctx.respond('❌ | `Number of warns` to remove must be greater than zero!')
        if cursor.execute(f'SELECT * FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone():
            count = cursor.execute(f'SELECT count FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone()[0]
            if count-number < 0:
                number,count = count,0
            else:
                count -= number
            cursor.execute('UPDATE warns SET count=? WHERE guild_id=? AND user_id=?',(count,ctx.guild.id,user.id))
            db.commit()
            await ctx.respond(f'Removed `{number}` warning/s from `{user}`\n\nWarning Count: `{count}`')
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        return await ctx.respond(f'❌ | User `{user}` has no warnings yet.')

    @slash_command(name="clearwarns",description='Clear all warnings attributed to a member')
    async def clearwarns(self,ctx,user:Option(discord.Member,description="User you are trying to perform an action on")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        #user = discord.utils.get(ctx.guild.members,id=int(user))
        if user is None:
            return await ctx.respond('❌ | User does not exist.')
        if cursor.execute(f'SELECT * FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone():
            if cursor.execute(f'SELECT count FROM warns WHERE guild_id={ctx.guild.id} AND user_id={user.id}').fetchone()[0] == 0:
                return await ctx.respond(f'❌ | User `{user}` has no warnings yet.')
            cursor.execute('UPDATE warns SET count=? WHERE guild_id=? AND user_id=?',(0,ctx.guild.id,user.id))
            db.commit()
            await ctx.respond(f'Cleared warning count for {user}.')
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        return await ctx.respond(f'❌ | User `{user}` has no warnings yet.')

    settings = [
        {
        'name':'logs',
        'description':'Whether you want to allow moderation logs in the server',
        'required':True,
        'type':4,
        'choices':[{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'channel',
        'description':'Channel where to log moderation actions (if enabled)',
        'required':True,
        'type':7
        },
        {
        'name':'maxwarns',
        'description':'Threshold for the number of warns before action is done',
        'required':True,
        'type':4
        },
        {
        'name':'warnpunishment',
        'description':'Specific action for warnings',
        'required':True,
        'type':3,
        'choices':[
            {'name':'Skip [Disabled]','value':''},
            {'name':'Message the person only','value':'message'},
            {'name':'Mute the person indefinitely','value':'mute'},
            {'name':'Mute the person for 1 hour','value':'tempmute'},
            {'name':'Kick the person from the server','value':'kick'},
            {'name':'Ban the person in the server indefinitely','value':'ban'},
            {'name':'Ban the person in the server for 1 hour','value':'softban'}
        ]
        },
        {
        'name':'censor',
        'description':'Whether you want to filter messages sent in the server',
        'required':True,
        'type':4,
        'choices':[{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'censorpunishment',
        'description':'Specific action for filtered messages',
        'required':True,
        'type':3,
        'choices':[
            {'name':'Skip [Disabled]','value':''},
            {'name':'Delete the message only','value':'delete'},
            {'name':'Message the person only','value':'message'},
            {'name':'Warn the person','value':'warn'},
            {'name':'Mute the person indefinitely','value':'mute'},
            {'name':'Mute the person for 1 hour','value':'tempmute'},
            {'name':'Kick the person from the server','value':'kick'},
            {'name':'Ban the person in the server','value':'ban'},
            {'name':'Ban the person in the server for 1 hour','value':'softban'}
            ]
        }
    ]

    @slash_command(name="mod",description='Configuration the moderation settings in the server')
    async def mod(self,ctx,
            logs:Option(int,description="Whether you want to allow moderation logs in the server",choices=[
                    OptionChoice(name="Enable",value=1), OptionChoice(name="Disable",value=0)]),
            channel:Option(discord.TextChannel,description="Channel where to log moderation actions (if enabled)"),
            maxwarns:Option(int,description="Threshold for the number of warns before necessary action is done"),
            warnpunishment:Option(str,description="Specific action for warnings that reached the threshold",choices=[
                    OptionChoice(name='Skip [Disabled]',value=''),
                    OptionChoice(name='Message the person only',value='message'),
                    OptionChoice(name='Mute the person indefinitely',value='mute'),
                    OptionChoice(name='Mute the person for 1 hour',value='tempmute'),
                    OptionChoice(name='Kick the person from the server',value='kick'),
                    OptionChoice(name='Ban the person in the server indefinitely',value='ban'),
                    OptionChoice(name='Ban the person in the server for 1 hour',value='softban')]),
            censor:Option(int,description="Whether you want to filter messages sent in the server",choices=[
                    OptionChoice(name="Enable",value=1), OptionChoice(name="Disable",value=0)]),
            censorpunishment:Option(str,description="Specific action for warnings that reached the threshold",choices=[
                    OptionChoice(name='Skip [Disabled]',value=''),
                    OptionChoice(name='Delete the message only',value='delete'),
                    OptionChoice(name='Message the person only',value='message'),
                    OptionChoice(name='Mute the person indefinitely',value='mute'),
                    OptionChoice(name='Mute the person for 1 hour',value='tempmute'),
                    OptionChoice(name='Kick the person from the server',value='kick'),
                    OptionChoice(name='Ban the person in the server indefinitely',value='ban'),
                    OptionChoice(name='Ban the person in the server for 1 hour',value='softban')])):

        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        embed = discord.Embed(title='Moderation Settings')

        if logs == 1:
            embed.add_field(name='Logs',value=f'`Enabled` in {channel.mention}')
        else:
            embed.add_field(name='Logs',value=f'`Disabled`')

        punishments = {'':'None','message':'Message the user','delete':'Delete the message','warn':'Warn the user','mute':'Mute the user indefinitely','tempmute':'Mute the user for 1 hour',
                       'kick':'Kick the user','ban':'Ban the user','softban':'Temporarily ban the user for 1 hour'}
        if warnpunishment in ['mute','tempmute'] and cursor.execute(f'SELECT mute_id FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone() is None:
            return await ctx.respond(f'❌ | Cannot set `{warnpunishment}` as warn punishment because there is no mute role registered for the server yet. Use `$muterole <role>` to set one.')
        if maxwarns > 0:
            embed.add_field(inline=False,name='Warnings',value=f'Warn Threshold: `{maxwarns}`\nPunishment: `{punishments[warnpunishment]}`')

        else:
            embed.add_field(inline=False,name='Warnings',value=f'Warn Threshold: `Disabled`')
        if censor == 1:
            embed.add_field(inline=False,name='Auto-moderation of Messages',value=f'`Enabled`\nPunishment: `{punishments[censorpunishment]}`')
        else:
            embed.add_field(inline=False,name='Auto-moderation of Messages',value=f'`Disabled`')

        message = await ctx.respond('Here\'s what I got from you. Do you want to save these changes?',embed=embed)
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        try:
            reaction = await self.bot.wait_for('reaction_add', timeout=60, check=lambda reaction,user: str(reaction.emoji) in ['👍','👎'] and user == ctx.author)
        except:
            return await ctx.respond('❌ | Process terminated. Please try again. [Timeout]')
        else:
            await message.delete()
            if str(reaction[0]) == '👍':
                for option in [maxwarns,warnpunishment,censorpunishment]:
                    if option == 0 or option == '':
                        option = None
                cursor.execute(f'UPDATE mod_settings SET logs_status=?,logs_id=?,max_warns=?,warn_effect=?,censor_status=?,censor_effect=? WHERE guild_id=?',
                                (logs,channel.id,maxwarns,warnpunishment,censor,censorpunishment,ctx.guild.id))
                db.commit()
                await ctx.respond('Mod settings have been updated.')
                return print(f'{self.__class__.__name__} - configure {ctx.command} | {time.time()-start_time} s')
            return await ctx.respond('Process terminated.')

    @commands.command()
    @has_permissions(manage_guild=True)
    async def modsettings(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT logs_status FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()[0]:
            settings = cursor.execute(f'SELECT * FROM mod_settings WHERE guild_id={ctx.guild.id}').fetchone()
            logs,channel,maxwarns,warnpunishment,censor,censorpunishment = settings[1], discord.utils.get(ctx.guild.channels,id=settings[2]), settings[4], settings[5], settings[6], settings[7]

            embed = discord.Embed(title='Moderation Settings')

            if logs == 1:
                embed.add_field(inline=False,name='Logs',value=f'`Enabled` in {channel.mention}')
            else:
                embed.add_field(inline=False,name='Logs',value=f'`Disabled`')

            punishments = {'message':'Message the user','delete':'Delete the message','warn':'Warn the user','mute':'Mute the user indefinitely','tempmute':'Mute the user for 1 hour',
                           'kick':'Kick the user','ban':'Ban the user','softban':'Temporarily ban the user for 1 hour'}
            embed.add_field(inline=False,name='Warnings',value=f'Warn Threshold: `{maxwarns}`\nPunishment: `{punishments[warnpunishment]}`')

            if censor == 1:
                embed.add_field(inline=False,name='Auto-moderation of Messages',value=f'`Enabled`\nPunishment: `{punishments[censorpunishment]}`')
            else:
                embed.add_field(inline=False,name='Auto-moderation of Messages',value=f'`Disabled`')
            embed.set_footer(text='Use /modsettings for configuration')

            await ctx.send(embed=embed)
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        return await ctx.send('No moderation settings have been set yet. Use `/modsettings` to start configuring it.',delete_after=5)

    @commands.Cog.listener()
    async def on_message(self,message):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if message.author.bot:
            return
        if str(message.channel.type) == 'private':
            return
        profane = open(f'cogs/extras/profane.txt').readlines()
        profane = [prompt[:-1] for prompt in profane]
        if cursor.execute(f'SELECT censor_status FROM mod_settings WHERE guild_id={message.guild.id}').fetchone()[0] == 1:
            if cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={message.guild.id}').fetchone()[0] != None:
                profane.extend(cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={message.guild.id}').fetchone()[0].split(';'))

            separators = string.punctuation+string.digits+string.whitespace
            excluded = string.ascii_letters

            for word in profane:
                formatted_word = f"[{separators}]*".join(list(word))
                regex_true = re.compile(fr"{formatted_word}", re.IGNORECASE)
                regex_false = re.compile(fr"([{excluded}]+{word})|({word}[{excluded}]+)", re.IGNORECASE)


                if regex_true.search(message.content) is not None and regex_false.search(message.content) is None:
                    punishment = cursor.execute(f'SELECT censor_effect FROM mod_settings WHERE guild_id={message.guild.id}').fetchone()[0]
                    if punishment == 'message':
                        dm_channel = await message.author.create_dm()
                        await dm_channel.send(f'Hello! It looks like you sent something in the server that violates its content rules. Please refrain from doing these to avoid getting in trouble.\n\n> {regex_true.search(message.content).group()}')
                    if punishment == 'mute':
                        await self.mute_command(message,'mute',message.author.id,f'Sending a filtered prompt in the server: `{word}`',None)
                    elif punishment == 'tempmute':
                        await self.mute_command(message,'tempmute',message.author.id,f'Sending a filtered prompt in the server: `{word}`',1)
                    elif punishment == 'kick':
                        await self.kick_command(message,message.author.id,f'Sending a filtered prompt in the server: `{word}`')
                    elif punishment == 'ban':
                        await self.ban_command(message,'ban',message.author.id,f'Sending a filtered prompt in the server: `{word}`',None)
                    elif punishment == 'softban':
                        await self.ban_command(message,'softban',message.author.id,f'Sending a filtered prompt in the server: `{word}`',1)
                    await message.delete()
                    #await self.bot.process_commands(message)
                    return print(f'{self.__class__.__name__} - censor prompt real-time | {time.time()-start_time} s')

    @slash_command(name="censor",description='Add word/s or phrase/s to server\'s prompts to filter out')
    async def censor(self,ctx,prompts:Option(str,description="Word/s or phrase/s that will be filtered, each separated by ;")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        profane = open(f'cogs/extras/profane.txt').readlines()
        profane = [prompt[:-1] for prompt in profane]
        censor_prompts = [word.lower() for word in prompts.split(';')]
        filtered = []
        if cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={ctx.guild.id}').fetchone()[0]:
            filtered = cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={ctx.guild.id}').fetchone()[0].split(';')
            profane.extend(filtered)
            censor_prompts = [prompt for prompt in censor_prompts if prompt not in profane]
            if len(censor_prompts) == 0:
                return await ctx.respond('❌ | All entered prompts are already in the server\'s filter list.')
            filtered.extend(censor_prompts)
            cursor.execute('UPDATE censored SET prompts=? WHERE guild_id=?',(';'.join(filtered),ctx.guild.id))
        else:
            censor_prompts = [prompt for prompt in censor_prompts if prompt not in profane]
            if len(censor_prompts) == 0:
                return await ctx.respond('❌ | All entered prompts are already in the server\'s filter list.')
            filtered.extend(censor_prompts)
            cursor.execute('UPDATE censored SET prompts=? WHERE guild_id=?',(';'.join(filtered),ctx.guild.id))
        db.commit()
        await ctx.respond("Added to prompts to be filtered:\n```\n{}```".format('\n'.join(censor_prompts)))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="uncensor",description='Removes word/s or phrase/s from server\'s prompts to filter out')
    async def uncensor(self,ctx,prompts:Option(str,description="Word/s or phrase/s to be removed from the filtered list, each separated by ;")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        censor_prompts = [word.lower() for word in prompts.split(';')]
        profane = open(f'cogs/extras/profane.txt').readlines()
        profane = [prompt[:-1] for prompt in profane]
        if cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={ctx.guild.id}').fetchone()[0]:
            filtered = cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={ctx.guild.id}').fetchone()[0].split(';')
            default_prompts = [f'`{prompt}`' for prompt in censor_prompts if prompt in profane]
            censor_prompts = [prompt for prompt in censor_prompts if prompt in filtered]
            if len(default_prompts) != 0:
                await ctx.respond(f"❌ | {' '.join(default_prompts)} cannot be modified because they\'re part of the bot\'s built-in list of filtered prompts.")
                if len(censor_prompts) == 0:
                    return
            if len(censor_prompts) == 0:
                return await ctx.respond('❌ | Entered prompts are not in the server\'s list.')
            for prompt in censor_prompts:
                filtered.remove(prompt)
            cursor.execute('UPDATE censored SET prompts=? WHERE guild_id=?',(';'.join(filtered),ctx.guild.id))
            db.commit()
            await ctx.respond("Removed prompts from server\'s filter list:\n```\n{}```".format('\n'.join(censor_prompts)))
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        return await ctx.respond('❌ | There are no censored prompts in the server yet. Use `/censor [prompt/s]` to filter messages.')

    @commands.command(aliases=['censor'])
    @has_permissions(manage_guild=True)
    async def censored(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={ctx.guild.id}').fetchone()[0]:
            filtered = cursor.execute(f'SELECT prompts FROM censored WHERE guild_id={ctx.guild.id}').fetchone()[0].split(';')
            f = open(f"{ctx.guild.name}_Filtered.txt","w+")
            f.write('\n'.join(filtered))
            f.close()
            await ctx.send('Here are the censored prompts for the server:',file=discord.File(f"{ctx.guild.name}_Filtered.txt"))
            os.remove(f"{ctx.guild.name}_Filtered.txt")
            return print(f'{self.__class__.__name__} - list {ctx.command} | {time.time()-start_time} s')
        return await ctx.send('There are no censored prompts in the server yet. Use `/censor [prompt/s]` to filter messages.',delete_after=5)

    @slash_command(name="lockdown",description='Lock a specific channel to prevent people from sending messages')
    async def lockdown(self,ctx,channel:Option(discord.TextChannel,description="Channel that you want to lock")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        #channel = discord.utils.get(ctx.guild.channels,id=channel)
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages == False:
            return await ctx.respond(f'❌ | Channel {channel.mention} is already locked.')
        else:
            overwrite.send_messages=False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await ctx.respond(f'Channel {channel.mention} is now locked.')
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="unlock",description='Unlock a previously locked channel')
    async def unlock(self,ctx,channel:Option(discord.TextChannel,description="Channel that you want to unlock")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        #channel = discord.utils.get(ctx.guild.channels,id=channel)
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages == False:
            overwrite.send_messages=True
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
            await ctx.respond(f'Channel {channel.mention} is now unlocked.')
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        else:
            return await ctx.respond(f'❌ | Channel {channel.mention} is not locked.')

def setup(bot):
    bot.add_cog(Mod(bot))
