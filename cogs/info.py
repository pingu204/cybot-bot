import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
from misc import *
import time
from discord import Option,OptionChoice
from discord.ui import View, Button, Select
from discord.commands import slash_command

class Info(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    post_options = [
        {
        'name':'surname',
        'description':'Your last name goes here...',
        'required':True,
        'type':3,
        },
        {
        'name':'name',
        'description':'Your given name goes here...',
        'required':True,
        'type':3
        }
    ]

    @slash_command(name="setname",description='This allows for easier identification within the server')
    async def setname(self,ctx,
            surname:Option(str,description="Your last name goes here..."),
            name:Option(str,description="Your given name goes here...")):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT * FROM names WHERE id={ctx.author.id}').fetchone():
            cursor.execute(f'UPDATE names SET surname=?,name=? WHERE id=?',(surname.upper(),name.upper(),ctx.author.id))
            db.commit()
            await ctx.respond(f'Name updated:\n`{surname.upper()}, {name.upper()}`')
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        cursor.execute(f'INSERT INTO names(id,surname,name) VALUES(?,?,?)',(ctx.author.id,surname.upper(),name.upper()))
        db.commit()
        await ctx.respond(f'Name recorded:\n`{surname.upper()}, {name.upper()}`')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')


    @commands.group(invoke_without_command=True,aliases=['rule'])
    async def rules(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        description = ''
        if cursor.execute(f'SELECT rules FROM rules WHERE guild_id={ctx.guild.id}').fetchone()[0] is None:
            description = 'No rules added yet for the server'
        else:
            rule_list = cursor.execute(f'SELECT rules FROM rules WHERE guild_id={ctx.guild.id}').fetchone()[0].split(';')
            for n in range(1,len(rule_list)+1):
                description += f'{n}. {rule_list[n-1]}\n'
        embed = discord.Embed(color=0xFFFFFF,title='Rules',description=description)
        embed.set_footer(icon_url=ctx.guild.icon.url,text=ctx.guild.name)
        await ctx.send(embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @rules.command()
    @has_permissions(manage_guild=True)
    async def add(self,ctx,*,rules):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT rules FROM rules WHERE guild_id={ctx.guild.id}').fetchone()[0] is None:
            rule_list = []
        else:
            rule_list =  cursor.execute(f'SELECT rules FROM rules WHERE guild_id={ctx.guild.id}').fetchone()[0].split(';')
        new_rules, description = [rule for rule in rules.split('\n') if rule not in rule_list],''
        if len(new_rules) == 0:
            return await ctx.send('❌ | All of the rules already exist in the server. Please try again.')
        rule_list.extend(new_rules)
        for n in range(1,len(rule_list)+1):
            if n > (len(rule_list)-len(new_rules)):
                description += f'**{n}. {rule_list[n-1]}**\n'
            else:
                description += f'{n}. {rule_list[n-1]}\n'
        embed = discord.Embed(color=0xFFFFFF,title='Updated Rules',description=description)
        embed.set_footer(text='Added rules are highlighted in bold')
        cursor.execute('UPDATE rules SET rules=? WHERE guild_id=?',(';'.join(rule_list),ctx.guild.id))
        db.commit()
        await ctx.send('Rules have been added',embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @rules.command()
    @has_permissions(manage_guild=True)
    async def remove(self,ctx,*,numbers):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT rules FROM rules WHERE guild_id={ctx.guild.id}').fetchone()[0] is None:
            return await ctx.send('❌ | No rules have been set for the server yet.',delete_after=4)
        rule_list =  cursor.execute(f'SELECT rules FROM rules WHERE guild_id={ctx.guild.id}').fetchone()[0].split(';')
        numbers, description, removed_rules = [int(n) for n in numbers.split(',')],'', []
        numbers.sort(reverse=True)
        for n in numbers:
            try:
                removed_rule = rule_list.pop(n-1)
            except:
                await ctx.send(f'Rule `{n}` does not exist.')
            else:
                removed_rules.append(removed_rule)
        if len(removed_rules) == 0:
            return
        for n in range(1,len(rule_list)+1):
            description += f'{n}. {rule_list[n-1]}\n'
        embed = discord.Embed(color=0xFFFFFF,title='Updated Rules',description=description)
        embed.add_field(name='Removed Rules',value='\n'.join(removed_rules))
        if len(rule_list)==0:
            cursor.execute('UPDATE rules SET rules=? WHERE guild_id=?',(None,ctx.guild.id))
        else:
            cursor.execute('UPDATE rules SET rules=? WHERE guild_id=?',(';'.join(rule_list),ctx.guild.id))
        db.commit()
        await ctx.send('Rules have been removed',embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command()
    async def info(self,ctx):
        start_time = time.time()
        await ctx.send(embed=get_info(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command(aliases=['id'])
    async def member(self,ctx,member=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        await ctx.message.delete()
        if member == 'me' or member == None:
            member = ctx.author
        elif member.isnumeric():
            if discord.utils.get(ctx.guild.members,id=int(member)) is None:
                return await ctx.send(f'❌ | User ID `{member}` not found.')
            member = discord.utils.get(ctx.guild.members,id=int(member))
        elif '<@!' in member:
            member = discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')]))
        else:
            return await ctx.send('❌ | Please mention a member or input their user ID.')


        user_name = cursor.execute(f'SELECT surname,name FROM names WHERE id={member.id}').fetchone()
        full_name = 'No full name set'
        if user_name != None:
            full_name = f'{user_name[0]}, {user_name[1]}'
        embed = discord.Embed(color=member.color,description=f'{full_name}\n{member.mention}\nRole Color: `{member.color}`')
        embed.add_field(inline=False,name='ID',value=member.id)
        embed.add_field(inline=False,name='Joined at',value=member.joined_at.strftime('%B %d %Y'))
        embed.set_thumbnail(url=member.display_avatar.url)

        await ctx.send(embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command()
    async def avatar(self,ctx,member=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        await ctx.message.delete()
        if member == 'me' or member == None:
            member = ctx.author
        elif member.isnumeric():
            if discord.utils.get(ctx.guild.members,id=int(member)) is None:
                return await ctx.send(f'❌ | User ID `{member}` not found.')
            member = discord.utils.get(ctx.guild.members,id=int(member))
        elif '<@!' in member:
            member = discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')]))
        else:
            return await ctx.send('❌ | Please mention a member or input their user ID.')

        if member.display_avatar:
            embed = discord.Embed(color=member.color,description=f"**{member}** | {member.display_name}\nRole Color: `{member.color}`\n\nAvatar as [png]({member.display_avatar.with_format('png').url}) | [jpg]({member.display_avatar.with_format('jpg').url}) | [webp]({member.display_avatar.with_format('webp').url})")
            if member.display_avatar.is_animated():
                embed = discord.Embed(color=member.color,description=f"**{member}** | {member.display_name}\nRole Color: `{member.color}`\n\nAvatar as [png]({member.display_avatar.with_format('png').url}) | [jpg]({member.display_avatar.with_format('jpg').url}) | [gif]({member.display_avatar.with_format('gif').url})")
            embed.set_image(url=member.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f'User `{member}` has no avatar.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command()
    async def bot(self,ctx):
        start_time = time.time()
        embed = discord.Embed(color=0xf48274,description=f'Server Prefix: `{ctx.prefix}`')
        embed.add_field(inline=False,name='Language',value='Python 3.9.7')
        embed.add_field(inline=False,name='Libraries Used',value=f'[PyCord {discord.__version__}](https://docs.pycord.dev/en/master/) | [SQLite3](https://www.sqlite.org/index.html) | [DB Browser](https://sqlitebrowser.org/)')
        embed.set_author(icon_url=self.bot.user.avatar.url,name='Cybot')
        embed.set_image(url='https://media.discordapp.net/attachments/889473930119774208/899620663940227102/banner.png?width=1025&height=453')

        await ctx.message.delete()
        await ctx.send(embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.group(invoke_without_command=True,aliases=['serverinfo','server_info'])
    async def server(self,ctx):
        start_time = time.time()
        ### sends server info embed ###
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        result = cursor.execute(f'SELECT gmeet,subject FROM info WHERE guild_id = {ctx.guild.id}').fetchone()
        # result = [gmeet,subject]
        if result[0] is None:
            meetLink = 'NA'
        else:
            meetLink = str(result[0])
        if result[1] is None:
            subj = 'NA'
        else:
            subj = str(result[1])

        embed = discord.Embed(title=ctx.guild.name,color=discord.Colour.red())
        embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name='Subject',value=subj,inline=True)
        embed.add_field(name='ID',value=str(ctx.guild.id),inline=True)
        embed.add_field(name='Owner',value=ctx.guild.owner.nick,inline=True)
        embed.add_field(name='Meet Link',value=meetLink, inline=True)
        embed.add_field(name='Created at',value=ctx.guild.created_at.strftime('%B %d %Y'))
        embed.set_footer(text='{}'.format(ctx.guild.owner.nick),icon_url=ctx.guild.owner.avatar.url)
        await ctx.send(embed=embed)
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @server.command(aliases=['gmeet','link','meetlink','meet_link','gmeetlink','gmeet_link'])
    @has_permissions(manage_guild=True)
    async def meet(self,ctx, *, link):
        start_time = time.time()
        ### sets meeting link for info embed ###
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        cursor.execute('UPDATE info SET gmeet = ? WHERE guild_id = ?',(link,ctx.guild.id))
        await ctx.send(f'Server meeting link has been updated to `{link}`.',delete_after=5)
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @server.command(aliases=['subj','s','topic'])
    @has_permissions(manage_guild=True)
    async def subject(self,ctx, *, subj):
        start_time = time.time()
        ### sets server subject/topic for info embed ###
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        cursor.execute('UPDATE info SET subject = ? WHERE guild_id = ?',(subj,ctx.guild.id))
        await ctx.send(f'Server subject has been updated to `{subj}`.',delete_after=5)
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @server.command()
    @has_permissions(manage_guild=True)
    async def reset(self,ctx):
        start_time = time.time()
        ### resets server information ###
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        message = await ctx.send('Reset server information?')
        await message.add_reaction('👍')
        await message.add_reaction('👎')
        reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and (str(reaction.emoji) in ['👍','👎']))
        if str(reaction[0]) == '👍':
            cursor.execute('UPDATE info SET subject=?,gmeet=? WHERE guild_id = ?',(None,None,ctx.guild.id))
            await ctx.send('🗑️ Server information resetted.',delete_after=5)
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        else:
            return await ctx.send('*Process terminated.*',delete_after=2)

def setup(bot):
    bot.add_cog(Info(bot))
