"""
Last Updated: 01/29/2022

"""

import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from typing import Union
import sqlite3
import time
from misc import *
from discord.ui import View, Button, Select

intents = discord.Intents.all()
intents.members = True
intents.guilds = True
intents.reactions = True

def get_prefix(bot,message):
    db = sqlite3.connect('main.sqlite')
    cursor = db.cursor()
    try:
        prefix = cursor.execute(f'SELECT prefix FROM prefixes WHERE guild_id={message.guild.id}').fetchone()[0]
    except:
        prefix = '$'
    return str(prefix)

bot = commands.Bot(command_prefix=get_prefix,help_command=None,intents=intents)
load_dotenv()
TOKEN = os.getenv("CYBOT")

@bot.event
async def on_ready(): #if bot is online
    print(f'{bot.user.name} has connected to Discord!')
    activity = discord.Activity(name='$help', type=discord.ActivityType.playing)
    await bot.change_presence(activity=activity)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.lower()==('test'):
        message = await message.channel.send(f'Hello there, {message.author.mention}!',view = View(Button(label = "Ping", emoji='🏓',style=1, custom_id = "ping")))
        interaction = await bot.wait_for("button_click", check = lambda i: i.custom_id == "ping")
        await message.delete()
        await message.channel.send(content = f"🏓 Pong!\nBot latency: `{round(bot.latency,4)} s`")
    if message.content.lower()=='ping':
        await message.channel.send(content = f"🏓 Pong!\nBot latency: `{round(bot.latency,4)} s`")
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,commands.MissingPermissions):
        return await ctx.message.reply('❌ | You don\'t have permissions to do that.',delete_after=5)
    else:
        print(error)

@bot.event
async def on_guild_join(guild):
    db = sqlite3.connect('main.sqlite')
    cursor = db.cursor()

    def initialize_db():
        for table in ['prefixes','rules','admins','info','logs_status','mlog','mod_settings','serverlog','censored']:
            cursor.execute(f'DELETE FROM {table} WHERE guild_id={guild.id}')
        for table in ['prefixes','rules','admins','info','logs_status','mlog','mod_settings','serverlog','censored']:
            if table == 'prefixes':
                cursor.execute('INSERT INTO prefixes(guild_id,prefix) VALUES(?,?)',(guild.id,'$'))
            elif table == 'admins':
                cursor.execute('INSERT INTO admins(guild_id,admin_id) VALUES(?,?)',(guild.id,guild.owner.id))
            else:
                cursor.execute(f'INSERT INTO {table}(guild_id) VALUES(?)',(guild.id,))
            db.commit()

    if cursor.execute(f'SELECT guild_id FROM admins WHERE guild_id={guild.id}').fetchone() != None:
        for channel in guild.text_channels:
            try:
                message = await channel.send('The server has existing record in database. Do you want to keep this or reset everything instead?\n\n📄 Keep\n🗑️ Reset')
            except:
                continue
            else:
                channel = channel
                await message.add_reaction('📄')
                await message.add_reaction('🗑️')
                break
        reaction = await bot.wait_for('reaction_add',timeout=20,check=lambda reaction,user: str(reaction.emoji) in ['📄','🗑️'] and user != bot.user)
        await message.delete()
        if str(reaction[0]) == '📄':
            await channel.send('Existing record will be kept.',delete_after=5)
        else:
            await channel.send('Database records will be resetted.',delete_after=5)
            initialize_db()
    else:
        initialize_db()

    embed = discord.Embed(color=0xf48274,title='Cybot—your academic buddy',description=f"Hey there, I'm {bot.user.mention}! I have finally arrived at your wonderful server.\
                                                                                        \n\nMy functionality centers around managing academic-oriented servers, which include creating announcements, scheduling appointments, and even moderation!\
                                                                                        To learn more about what I can do, do not hesitate to use the `$help` command or the attached documentation guide.")
    embed.add_field(name='Setting up the server',value='Click the button below to make it easier for the bot to carry out its functions')
    embed.set_image(url='https://media.discordapp.net/attachments/833541236387479573/927881908992483378/banner.png?width=1025&height=355')

    class HelpButton(Button):
        def __init__(self):
            super().__init__(label = 'What can I do?',row=0,style = discord.ButtonStyle.primary)

        async def callback(self,interaction:discord.Interaction):
            view = self.view
            self.disabled = True
            self.style = discord.ButtonStyle.secondary
            self.label = 'Not working? Use $help instead!'
            await interaction.response.edit_message(view=view)
            await get_help(interaction,bot)

    class SetupButton(Button):
        def __init__(self):
            super().__init__(label = 'Set up the server',row=0,style = discord.ButtonStyle.primary)

        async def callback(self,interaction:discord.Interaction):
            view = self.view
            self.disabled = True
            self.style = discord.ButtonStyle.secondary
            self.label = 'Not working? Use $setup instead!'
            await interaction.response.edit_message(view=view)
            await setup(interaction)

    for channel in guild.text_channels:
        try:
            await channel.send(embed=embed,view=View(SetupButton(),HelpButton(),DocumentationButton()))
        except:
            continue
        else:
            break
##########################
### LOADING COGS FILES ###
##########################


@bot.command()
async def getguild(ctx):
    print(get_guilds())

@bot.command()
async def load(ctx,extension):
    bot.load_extension(f'cogs.{extension}')
    print(f"{extension} has been loaded.")

@bot.command()
async def unload(ctx,extension):
    bot.unload_extension(f'cogs.{extension}')
    print(f"{extension} has been unloaded.")

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

##########################
### LOADING COGS FILES ###
##########################

@bot.command()
async def echo(ctx,*,text):
    print('{:^42}'.format(text))

@bot.command(aliases=['prefix','sp','set_prefix'])
@has_permissions(manage_guild=True)
async def setprefix(ctx,*,prefix=None):
    start_time = time.time()
    ### sets prefix for the server of the ctx ###
    db = sqlite3.connect('main.sqlite')
    cursor = db.cursor()
    if prefix is None:
        return await ctx.send(f'❌ | Cannot change prefix to `None`.\n\nServer prefix: `{get_prefix(bot,ctx.message)}`',delete_after=5)
    if cursor.execute(f'SELECT prefix FROM prefixes WHERE guild_id={ctx.guild.id}').fetchone() is None:
        # new input
        cursor.execute(f'INSERT INTO prefixes(guild_id,prefix) VALUES(?,?)',(ctx.guild.id,prefix))
    else:
        # exists
        cursor.execute(f'UPDATE prefixes SET prefix = ? WHERE guild_id=?',(prefix,ctx.guild.id))
    db.commit()
    await ctx.message.add_reaction('✅')
    await ctx.send(f'Prefix for the server has been set to `{prefix}`.')
    print(f'{ctx.command} | {time.time()-start_time} s')

async def setup(ctx):
    channel = ctx.channel
    if ctx.guild.roles[len(ctx.guild.roles)-1].name == bot.user.name:
        return await channel.send('The bot is already set-up for the server.',delete_after=5)
    embed = discord.Embed(title='Setting-up the Bot',description=f'Setting up {bot.user.mention} is so easy!\n\nStep 1: Drag the `@bot role` towards the top of the role hierarchy.\nStep 2: [Optional] Change the server\'s prefix using `$prefix <new prefix>`.\n\n')
    embed.set_image(url='https://media.discordapp.net/attachments/780619727113683026/927891305164570634/unknown.png?width=652&height=473')
    embed.set_footer(text='Putting the bot role at the top of the hierarchy allows the bot to perform server tasks smoothly.')
    await channel.send(embed=embed)
    message=await channel.send('React with ✅ to authenticate the set-up process.')
    await message.add_reaction('✅')
    role = ctx.guild.roles[len(ctx.guild.roles)-1]
    while(role.name != bot.user.name):
        reaction = await bot.wait_for('reaction_add',check=lambda reaction,user: str(reaction.emoji) == '✅' and user != bot.user)
        role = ctx.guild.roles[len(ctx.guild.roles)-1]
        if role.name != bot.user.name:
            await channel.send('Authentication failed. Please try again.',delete_after=5)
        await message.remove_reaction(reaction[0].emoji,reaction[1])
    await message.delete()
    return await channel.send('The bot is ready to use!',delete_after=5)
    pass

@bot.command(aliases=['setup'])
async def botsetup(ctx):
    if is_setup(ctx.guild,bot):
        return await ctx.send('The bot is already set-up for the server.',delete_after=5)
    await setup(ctx)

@bot.command(aliases=['purge'])
@has_permissions(manage_messages=True)
async def prune(ctx,n:int=None,*,member:Union[discord.Member,str]=None):
    ### DELETES N+1 [N<100] MESSAGES ###
    start_time = time.time()
    await ctx.message.delete()
    if n is None:
        return await ctx.send('❌ | Number of message/s is a required parameter.')
    if n < 1:
        return await ctx.send('❌ | Number of message/s to delete must be greater than zero.')
    print(str(member))
    #print(int((member)[3:21]))
    if member in ['bot','Bot'] or '@Cybot' in str(member):
        # KEYWORDS FOR BOT
        member = bot.user
    check_func,author = None,''
    #print('yuh')
    if member != None:
        # USER-SPECIFIC DELETION
        check_func,author = lambda message: message.author == member,f' by **@{member}**'
    if n > 100:
        n = 100
    #print('yuh')
    try:
        if check_func:
            messages = await ctx.message.channel.purge(limit=(n),check=check_func)
        else:
            messages = await ctx.message.channel.purge(limit=(n))
        #print('yuh')
    except discord.HTTPException:
        return await ctx.send('❌ | Failed to delete messages. Please try again.')
    else:
        #print('yuh')
        temp = len(messages)
        while temp < n:
            # ONLY FOR USER-SPECIFIC DELETION W/ OVERLAPPING MESSAGES
            messages = []
            # GET 200 MESSAGES IN CHANNEL HISTORY
            temp_messages = await ctx.channel.history(limit=200).flatten()
            for message in temp_messages:
                if message.author == member:
                    # ADD TO DELETION LIST
                    messages.append(message)
                    temp+=1
                if temp == n:
                    break
            await ctx.channel.delete_messages(messages)
    await ctx.send('*Deleted {} messages{}*'.format(temp,author),delete_after=5)
    print(f'{ctx.command} | {time.time()-start_time} s')

bot.run(TOKEN)