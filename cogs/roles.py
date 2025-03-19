import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
import datetime
from typing import Union
from misc import *
import time

class Roles(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload): #reaction roles
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if payload.member != self.bot.user:
            try:
                combinations=cursor.execute(f'SELECT combinations FROM roles WHERE guild_id={int(payload.guild_id)} AND message_id={int(payload.message_id)}').fetchone()[0].split(';')
            except:
                # no roles/emojis found sa database so walang kailangan gawin
                return
            else:
                 #list of combinations
                for combination in combinations:
                    combination = combination.split('%')
                    emoji, role_id = combination[0], int(combination[1])
                    if str(payload.emoji.name)==emoji: #if same emoji
                        await payload.member.add_roles(discord.utils.get(self.bot.get_guild(payload.guild_id).roles,id=int(role_id)))
                        return print(f'{self.__class__.__name__} - add RR role | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self,payload):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if payload.member != self.bot.user:
            try:
                #SELECT emoji doesn't work so i just got the role_id,emoji combinations then loop if match sa payload.emoji
                combinations=cursor.execute(f'SELECT combinations FROM roles WHERE guild_id={payload.guild_id} AND message_id={payload.message_id}').fetchone()[0].split(';')
            except:
                #no roles/emojis found sa database so walang kailangan gawin
                return
            else:
                # combinations=cursor.fetchone().split(';') #list of combinations
                for combination in combinations:
                    combination = combination.split('%')
                    emoji, role_id = combination[0], int(combination[1])
                    if str(payload.emoji.name)==emoji: #if same emoji
                        member = discord.utils.get(self.bot.get_guild(payload.guild_id).members,id=payload.user_id)
                        await member.remove_roles(discord.utils.get(self.bot.get_guild(payload.guild_id).roles,id=int(role_id)))
                        return print(f'{self.__class__.__name__} - remove RR role | {time.time()-start_time} s')

    @commands.group(invoke_without_command=True,aliases=['roles'])
    async def role(self,ctx):
        await ctx.send(embed=get_roles(ctx))

    @role.command()
    @has_permissions(manage_roles=True)
    async def create(self,ctx,*,role_name='new role'):
        start_time = time.time()
        embed = discord.Embed(title='Role Creation',description='Pick the color of the role.')
        embed.add_field(name='Colors',value='⚫ Default\n🔴 Red\n🟠 Orange\n🟡 Yellow\n🟢 Green\n🔵 Blue\n🟣 Purple')
        ask_color = await ctx.send(embed=embed)
        colors = {'⚫':discord.Colour.default(),'🔴':discord.Colour.red(),'🟠':discord.Colour.orange(),'🟡':discord.Colour.gold(),'🟢':discord.Colour.green(),
                  '🔵':discord.Colour.blue(),'🟣':discord.Colour.purple()}
        for emoji in colors.keys():
            await ask_color.add_reaction(emoji)
        reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in colors.keys())
        try:
            await ctx.guild.create_role(name=role_name,colour=colors[str(reaction[0])],mentionable=True)
        except:
            await ctx.send(f'❌ | Missing permissions to perform this action. Please make sure that `{ctx.prefix}setup` has already been done.',delete_after=5)
        else:
            await ctx.send(f'Role successfully created.\n\nName: `{role_name}`\nColor: `{str(colors[str(reaction[0])])}`',delete_after=5)
            return print(f'{self.__class__.__name__} - {ctx.command} role | {time.time()-start_time} s')

    @role.command()
    @has_permissions(manage_roles=True)
    async def delete(self,ctx,*,role:Union[discord.Role,str]):
        start_time = time.time()
        if isinstance(role,str):
            temp_role=None
            for name in [role.lower(),role.capitalize(),role.upper()]:
                if discord.utils.get(ctx.guild.roles,name=name) is not None:
                    temp_role=discord.utils.get(ctx.guild.roles,name=name)
                    break
            if temp_role is None:
                return await ctx.send('❌ | Role cannot be found.',delete_after=5)
            role=temp_role
        try:
            await role.delete()
        except:
            return await ctx.send(f'❌ | Missing permissions to perform this action. Please make sure that `{ctx.prefix}setup` has already been done.',delete_after=5)
        else:
            await ctx.send(f'Role `{role.name}` has been deleted.',delete_after=5)
            return print(f'{self.__class__.__name__} - {ctx.command} role | {time.time()-start_time} s')

    @role.command()
    @has_permissions(manage_roles=True)
    async def edit(self,ctx,*,role:Union[discord.Role,str]):
        start_time = time.time()
        if isinstance(role,str):
            temp_role=None
            for name in [role.lower(),role.capitalize(),role.upper()]:
                if discord.utils.get(ctx.guild.roles,name=name) is not None:
                    temp_role=discord.utils.get(ctx.guild.roles,name=name)
                    break
            if temp_role is None:
                return await ctx.send('❌ | Role cannot be found.',delete_after=5)
            role=temp_role
        embed = discord.Embed(title='Role Modification',description=f'React with the emoji that corresponds to the field that you want to edit.')
        embed.add_field(name='💬 Role Name',value=f'{role.name}')
        embed.add_field(name='🌈 Role Color',value=f'{str(role.color)}')
        ask_edit = await ctx.send(embed=embed)
        await ask_edit.add_reaction('💬')
        await ask_edit.add_reaction('🌈')
        reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in ['💬','🌈'])
        if str(reaction[0])=='💬':
            message = await ctx.send(f'Please enter a new name for the role `{role.name}`')
            text = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
            await role.edit(name=text.content)
            await message.delete()
        else:
            embed = discord.Embed(description='Pick the new color of the role.')
            embed.add_field(name='Colors',value='⚫ Default\n🔴 Red\n🟠 Orange\n🟡 Yellow\n🟢 Green\n🔵 Blue\n🟣 Purple')
            ask_color = await ctx.send(embed=embed)
            colors = {'⚫':discord.Colour.default(),'🔴':discord.Colour.red(),'🟠':discord.Colour.orange(),'🟡':discord.Colour.gold(),'🟢':discord.Colour.green(),
                      '🔵':discord.Colour.blue(),'🟣':discord.Colour.purple()}
            for emoji in colors.keys():
                await ask_color.add_reaction(emoji)
            reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in colors.keys())
            await role.edit(color=colors[str(reaction[0])])
            await ask_color.delete()
        await ask_edit.delete()
        await ctx.send(f'Successfully updated role.\n\nName: `{role.name}`\nColor: `{str(role.color)}`',delete_after=5)
        return print(f'{self.__class__.__name__} - {ctx.command} role | {time.time()-start_time} s')

    @role.command()
    @has_permissions(manage_roles=True)
    async def assign(self,ctx,*,role:Union[discord.Role,str]):
        start_time = time.time()
        if isinstance(role,str):
            temp_role=None
            for name in [role.lower(),role.capitalize(),role.upper()]:
                if discord.utils.get(ctx.guild.roles,name=name) is not None:
                    temp_role=discord.utils.get(ctx.guild.roles,name=name)
                    break
            if temp_role is None:
                return await ctx.send('❌ | Role cannot be found.',delete_after=5)
            role=temp_role
        embed = discord.Embed(title='Role Assignment')
        embed.add_field(name='Add role to:',value='👥 Everyone\n👪 Humans\n🤖 Bots\n🧑 Specific user/s')
        ask_target = await ctx.send(embed=embed)
        for emoji in ['👥','👪','🤖','🧑']:
            await ask_target.add_reaction(emoji)
        reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in ['👥','👪','🤖','🧑'])
        async with ctx.channel.typing():
            if str(reaction[0])=='👥':
                for member in ctx.guild.members:
                    await member.add_roles(role)
                await ctx.send(f'✅ Role `{role.name}` assigned to all members.')
            elif str(reaction[0])=='👪':
                for member in ctx.guild.members:
                    if not member.bot:
                        await member.add_roles(role)
                await ctx.send(f'✅ Role `{role.name}` assigned to human members.')
            elif str(reaction[0])=='🤖':
                for member in ctx.guild.members:
                    if member.bot:
                        await member.add_roles(role)
                await ctx.send(f'✅ Role `{role.name}` assigned to bots.')
            else:
                embed = discord.Embed(title='Role Assignment',description='Please mention target user/s.')
                embed.add_field(inline=False,name='Example:',value=f'{ctx.author.mention} OR\n{ctx.author.id}')
                embed.add_field(inline=False,name='Multiple Inputs (separated by line)',value=f'{ctx.author.mention}\n{ctx.guild.owner.mention}\n{self.bot.user.mention}')
                message=await ctx.send(embed=embed)
                text = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
                members = (text.content.split('\n'))
                for member in members:
                    print(member)
                    if member.isnumeric():
                        try:
                            await discord.utils.get(ctx.guild.members,id=int(member)).add_roles(role)
                        except:
                            await ctx.send(f'Member with ID `{member}` not found.')
                        else:
                            await ctx.send(f'✅ Role `{role.name}` assigned to {discord.utils.get(ctx.guild.members,id=int(member))}.',delete_after=5)
                    elif member[0] == '<':
                        try:
                            await discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')])).add_roles(role)
                        except:
                            await ctx.send(f'Member `{member}` not found.')
                        else:
                            await ctx.send(f"✅ Role `{role.name}` assigned to {discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')]))}.",delete_after=5)
                    else:
                        await ctx.send('❌ | Please mention a user or input their user ID.')
                await message.delete()
        await ask_target.delete()
        return print(f'{self.__class__.__name__} - {ctx.command} role | {time.time()-start_time} s')

    @role.command(aliases=['remove'])
    @has_permissions(manage_roles=True)
    async def unassign(self,ctx,*,role:Union[discord.Role,str]):
        start_time = time.time()
        if isinstance(role,str):
            temp_role=None
            for name in [role.lower(),role.capitalize(),role.upper()]:
                if discord.utils.get(ctx.guild.roles,name=name) is not None:
                    temp_role=discord.utils.get(ctx.guild.roles,name=name)
                    break
            if temp_role is None:
                return await ctx.send('❌ | Role cannot be found.',delete_after=5)
            role=temp_role
        embed = discord.Embed(title='Role Removal')
        embed.add_field(name='Remove role from:',value='👥 Everyone\n👪 Humans\n🤖 Bots\n🧑 Specific user/s')
        ask_target = await ctx.send(embed=embed)
        for emoji in ['👥','👪','🤖','🧑']:
            await ask_target.add_reaction(emoji)
        reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in ['👥','👪','🤖','🧑'])
        async with ctx.channel.typing():
            if str(reaction[0])=='👥':
                for member in ctx.guild.members:
                    await member.remove_roles(role)
                await ctx.send(f'✅ Role `{role.name}` removed from all members.')
            elif str(reaction[0])=='👪':
                for member in ctx.guild.members:
                    if not member.bot:
                        await member.remove_roles(role)
                await ctx.send(f'✅ Role `{role.name}` removed from all human members.')
            elif str(reaction[0])=='🤖':
                for member in ctx.guild.members:
                    if member.bot:
                        await member.remove_roles(role)
                await ctx.send(f'✅ Role `{role.name}` removed from all bots.')
            else:
                embed = discord.Embed(title='Role Removal',description='Please mention target user/s.')
                embed.add_field(inline=False,name='Example:',value=f'{ctx.author.mention} OR\n{ctx.author.id}')
                embed.add_field(inline=False,name='Multiple Inputs (separated by line)',value=f'{ctx.author.mention}\n{ctx.guild.owner.mention}\n{self.bot.user.mention}')
                message=await ctx.send(embed=embed)
                text = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
                members = (text.content.split('\n'))
                for member in members:
                    if member[0] != '<':
                        try:
                            await discord.utils.get(ctx.guild.members,id=int(member)).remove_roles(role)
                        except:
                            await ctx.send(f'Member with ID `{member}` not found.')
                            pass
                        else:
                            await ctx.send(f'Successfully removed role from {discord.utils.get(ctx.guild.members,id=int(member))}.',delete_after=5)
                    else:
                        await discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')])).remove_roles(role)
                        await ctx.send(f"Successfully removed role from {discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')]))}.",delete_after=5)
                await message.delete()
        await ask_target.delete()
        return print(f'{self.__class__.__name__} - {ctx.command} role | {time.time()-start_time} s')

    async def get_combinations(self,ctx):
        emojis,role_id = [],[]
        while 1:
            try:
                role_msg = await self.bot.wait_for('message',timeout=240,check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
            except:
                await ctx.send(f'❌ | No response obtained from the user. Please try again later.',delete_after=3)
            if role_msg.content.lower()[:4] == 'done':
                return emojis,role_id
            else:
                roles_line = role_msg.content.split('\n')
                role_list = [i.split(' ',1) for i in roles_line]
                print(role_list)
                for emoji,role in role_list:
                    try:
                        await ctx.message.add_reaction(emoji)
                    except:
                        await ctx.send(f'❌ | {emoji} is not a valid emoji. Try a different one.',delete_after=3)
                    else:
                        if emoji in emojis:
                            await ctx.send(f'❌ | {emoji} is already registered. Try a different one.',delete_after=3)
                        else:
                            if role[0] == '<': # mentioned role
                                if int(role[3:role.index('>')]) in role_id:
                                    await ctx.send(f'❌ | {role} is already registered. Try a different one.',delete_after=3)
                                else:
                                    emojis.append(str(emoji))
                                    role_id.append(int(role[3:role.index('>')]))
                                    await ctx.send(f"✅ | {emoji} - {discord.utils.get(ctx.guild.roles,id=int(role[3:role.index('>')])).mention}",delete_after=5)
                            else: # role name
                                id = None
                                for name in [role.lower(),role.capitalize(),role.title()]:
                                    temp_role = (discord.utils.get(ctx.guild.roles,name=name))
                                    if temp_role:
                                        if temp_role.id in role_id:
                                            await ctx.send(f'❌ | {temp_role.name} is already registered. Try a different one.',delete_after=3)
                                            break
                                        else:
                                            emojis.append(str(emoji))
                                            role_id.append(temp_role.id)
                                            await ctx.send(f'✅ | {emoji} - {temp_role.mention}',delete_after=5)
                                            break
                                    elif name == role.title():
                                        await ctx.send(f'❌ | Role {role} not found. Please try again.',delete_after=2)
                                        break
                # except error as e:
                #     #await ctx.send('❌ | Invalid combinations. Please follow the format.')
                #     print(e)
                # else:
                #     await role_msg.delete()

    @commands.group(invoke_without_command=True)
    @has_permissions(manage_guild=True,manage_roles=True)
    async def rr(self,ctx): #reaction roles
        start_time = time.time()
        ask_roles = discord.Embed(title='Reaction Roles',description='Please enter emojis with their corresponding roles in the format:\n`<emoji> <@role>`\n\n(Multi-line inputs allowed)')
        ask_roles.add_field(name='Example',value=f':white_circle: {ctx.guild.roles[-1].mention}\n:yellow_circle: {ctx.guild.roles[-2].name.lower()}')
        ask_roles.set_footer(text='If done, type \'done\'.')
        ask_roles = await ctx.send(embed=ask_roles)
        emojis,role_id = await self.get_combinations(ctx)
        await ask_roles.delete()
        if len(emojis)==0:
            return await ctx.send('❌ | Empty arguments.',delete_after=3.0)
        else:
            combinations = ';'.join([f'{emojis[n]}%{role_id[n]}' for n in range(len(emojis))])
            ask_details = discord.Embed(title='Reaction Roles Message',description='Please enter a destination channel and message (excluding the legend).')
            ask_details.add_field(name='Example',value=f'{ctx.guild.channels[0].mention} Pick your desired role!')
            await ctx.send(embed=ask_details)
            ask_message = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
            try:
                rr_channel = discord.utils.get(ctx.guild.channels,id=int(ask_message.content.split(' ')[0][2:len(ask_message.content.split(' ')[0])-1]))
            except:
                await ask_message.add_reaction('❌')
                return await ctx.send('❌ | Invalid channel.',delete_after=3.0)
            else:
                pass
            rr_message = ask_message.content.split(' ',1)[1]
            rr_legend = ''
            for n in range(len(emojis)):
                rr_legend+='{} - {}\n'.format(emojis[n],discord.utils.get(ctx.guild.roles,id=role_id[n]).mention)
            rr_embed = discord.Embed(description=f'{rr_message}\n\n**Legend**\n{rr_legend}')
            confirm_msg = await ctx.send('React with 👍 to confirm announcement',embed=rr_embed)
            await confirm_msg.add_reaction('👍')
            try:
                reaction = await self.bot.wait_for('reaction_add',timeout=30,check=lambda reaction,user: user == ctx.author and str(reaction.emoji) == '👍')
            except:
                await confirm_msg.delete()
                return await ctx.send('❌ | Timeout error. Please try again.', delete_after=2.0)
            else:
                message_id = await rr_channel.send(embed=rr_embed)
                ## database stuff ##
                db = sqlite3.connect('main.sqlite')
                cursor = db.cursor()
                cursor.execute('INSERT INTO roles(guild_id,message_id,combinations) VALUES(?,?,?)',
                               (ctx.guild.id,message_id.id,combinations))
                db.commit()
                for n in range(len(emojis)):
                    await message_id.add_reaction(emojis[n])
        await confirm_msg.delete()
        await ctx.send(f'✅ Reaction role created in {rr_channel.mention}')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    async def check_combinations(self,ctx,emoji,role,emojis,role_id):
        if emoji in emojis:
            await ctx.send(f'❌ | {emoji} is already registered. Try a different one.',delete_after=3)
        else:
            if role[0] == '<': # mentioned role
                if int(role.rstrip()[3:-1]) in role_id:
                    await ctx.send(f'❌ | {role} is already registered. Try a different one.',delete_after=3)
                else:
                    emojis.append(str(emoji))
                    role_id.append(int(role.rstrip()[3:role.index('>')]))
                    await ctx.send(f"✅ | {emoji} - {discord.utils.get(ctx.guild.roles,id=int(role[3:role.index('>')])).mention}")
            else: # role name
                id = None
                for name in [role.lower(),role.capitalize(),role.title()]:
                    temp_role = (discord.utils.get(ctx.guild.roles,name=name))
                    if temp_role:
                        if temp_role.id in role_id:
                            await ctx.send(f'❌ | {temp_role.name} is already registered. Try a different one.',delete_after=3)
                            break
                        else:
                            emojis.append(str(emoji))
                            role_id.append(temp_role.id)
                            await ctx.send(f'✅ | {emoji} - {temp_role.mention}',delete_after=5)
                            found = True
                            break
                    elif name == role.title():
                        await ctx.send(f'❌ | Role {role} not found. Please try again.',delete_after=5)
                        break


    @rr.command()
    @has_permissions(manage_guild=True,manage_roles=True)
    async def add(self,ctx,*,combinations):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        try:
            ctx.message.reference.message_id
        except:
            return await ctx.message.reply('❌ | Please reply to a message that has an existing reaction role instance.')
        else:
            if cursor.execute(f'SELECT * FROM roles WHERE message_id={ctx.message.reference.message_id}').fetchone():
                message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                combo_record = cursor.execute(f'SELECT combinations FROM roles WHERE message_id={message.id}').fetchone()[0]
                emojis, role_id = [],[]
                for combination in combo_record.split(';'):
                    emojis.append(combination.split('%')[0])
                    role_id.append(int(combination.split('%')[1]))
                temp_len = len(emojis)

                combinations = [combination.split(' ',1) for combination in combinations.split('\n')]

                added_combo,added_legend = [],''

                for emoji,role in combinations:
                    try:
                        await ctx.message.add_reaction(emoji)
                    except:
                        await ctx.send(f'❌ | {emoji} is not a valid emoji. Try another one.',delete_after=3)
                    else:
                        await self.check_combinations(ctx,emoji,role.rstrip(),emojis,role_id)
                        if len(emojis) != temp_len:
                            added_combo.append([emoji,role])

                if len(added_combo)==0:
                    return await ctx.message.reply('❌ | Process terminated. Reason: `All combinations are invalid.`',delete_after=3.0)

                updated_combo = ';'.join([f'{emojis[n]}%{role_id[n]}' for n in range(len(emojis))])
                cursor.execute(f"UPDATE roles SET combinations=? WHERE guild_id=? AND message_id=?",(updated_combo,ctx.guild.id,message.id))
                db.commit()

                for n in range(temp_len,len(emojis)):
                    await message.add_reaction(emojis[n])
                    added_legend += ('\n{} - {}'.format(emojis[n],discord.utils.get(ctx.guild.roles,id=role_id[n]).mention))

                embed=discord.Embed(description=''.join([message.embeds[0].description,(added_legend)]))
                await message.edit(embed=embed)

                return print(f'{self.__class__.__name__} - {ctx.command} RR roles | {time.time()-start_time} s')
            return await ctx.message.reply('❌ | No RR instance found in the message.')

def setup(bot):
    bot.add_cog(Roles(bot))
