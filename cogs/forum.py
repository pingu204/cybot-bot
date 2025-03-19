import discord
from discord.ext.commands import has_permissions
from discord.ext import commands
from misc import *
#from discord_slash import SlashCommand, SlashContext, cog_ext
import math
import time
from discord import Option,OptionChoice
from discord.ui import View, Button, Select
from discord.commands import slash_command

class Forum(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    @commands.command()
    @has_permissions(manage_guild=True)
    async def setforum(self,ctx,channel:discord.TextChannel):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        cursor.execute(f'UPDATE info SET forum=? WHERE guild_id=?',(channel.id,ctx.guild.id))
        await ctx.send(f'{channel.mention} has been set as the channel for forums.',delete_after=5)
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    forum_options = [
        {
        'name':'question',
        'description':'Question to be asked in the server',
        'required':True,
        'type':3
        },
        {
        'name':'details',
        'description':'Additional instructions (e.g.  extra questions, sentence limit, etc.)',
        'required':True,
        'type':3
        },
        {
        'name':'anonymity',
        'description':'Whether you like the participants to remain anonymous',
        'required':True,
        'type':4,
        'choices':[{'name':'Enable','value':1},{'name':'Disable','value':0}]
        },
        {
        'name':'votingsystem',
        'description':'Whether you want to enable an upvote-downvote system for this question',
        'required':True,
        'type':4,
        'choices':[{'name':'Enable','value':1},{'name':'Disable','value':0}]
        }
    ]

    @slash_command(name="ask",description='Ask a forum question in the server')
    async def ask(self,ctx,
            question:Option(str, description="Question to be asked in the server"),
            details:Option(str, description="Additional instructions (e.g.  extra questions, sentence limit, etc.)"),
            anonymity:Option(int, description="Whether you like the participants to remain anonymous", choices=[
                    OptionChoice(name="Enable",value=1),
                    OptionChoice(name="Disable",value=0)]),
            votingsystem:Option(int, description="Whether you want to enable an upvote-downvote system for this question",choices=[
                    OptionChoice(name="Enable",value=1),
                    OptionChoice(name="Disable",value=0)])):

        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        #print('aaa')
        if cursor.execute(f'SELECT forum FROM info WHERE guild_id={ctx.guild.id}').fetchone()[0] == None:
            return await ctx.respond('❌ | No channel has been set for forums yet. Please use `$setforum <channel>` to set one.')
        forum_id = get_id('forum')
        embed = discord.Embed(color=0xF48274,timestamp=get_dt_now(),title=question,description=details)
        embed.set_author(name=f'Forum #{forum_id}',icon_url=ctx.guild.icon.url)
        embed.set_footer(text=f'To answer this forum question, use /answer id:{forum_id}')

        if anonymity == 1:
            embed.add_field(inline=False,name=f'Anonymity',value='All responses will remain **anonymous**')
        if votingsystem == 1:
            embed.add_field(inline=False,name=f'Voting System',value='Upvote 🔼 | Downvote 🔽')

        forum_channel = discord.utils.get(ctx.guild.channels,id=cursor.execute(f'SELECT forum FROM info WHERE guild_id={ctx.guild.id}').fetchone()[0])
        message = await forum_channel.send('`New forum question...`',embed=embed)
        #forum_thread = await create_thread(name=f'Forum #{forum_id}',message=message)

        cursor.execute(f"INSERT INTO forum(id,guild_id,channel_id,message_id,question,anon,voting_system) VALUES(?,?,?,?,?,?,?)",\
                       (forum_id,ctx.guild.id,forum_channel.id,message.id,question,anonymity,votingsystem))
        db.commit()

        await ctx.respond('Forum has been posted.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    answer_options = [
        {
        'name':'forumnumber',
        'description':'ID of the forum you are answering (found at the top of the embed)',
        'required':True,
        'type':4
        },
        {
        'name':'answer',
        'description':'Main idea or one-sentence summary of your answer',
        'required':True,
        'type':3
        },
        {
        'name':'details',
        'description':'Explanation of your main idea',
        'required':True,
        'type':3
        }
    ]

    @slash_command(name="answer",description='Answer an existing forum question')
    async def answer(self,ctx,
            forumnumber:Option(int,description="ID of the forum you are answering (found at the top of the embed)"),
            answer:Option(str,description="Main idea or one-sentence summary of your answer"),
            details:Option(str,description="Explanation of your main idea")):

        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        if cursor.execute(f'SELECT * FROM forum WHERE guild_id={ctx.guild.id} AND id={forumnumber}').fetchone() is None:
            return await ctx.respond(f'❌ | No forum with `[ID: {forumnumber}]` is found in the server.')

        forum_details = cursor.execute(f'SELECT channel_id,message_id,question,anon,voting_system FROM forum WHERE guild_id={ctx.guild.id} AND id={forumnumber}').fetchone()
        channel_id,message_id,question,anon,voting_system = forum_details[0],forum_details[1],forum_details[2],forum_details[3],forum_details[4]
        forum_channel = ctx.guild.get_channel(channel_id)
        forum_message = await forum_channel.fetch_message(message_id)

        user_name = cursor.execute(f'SELECT surname,name FROM names WHERE id={ctx.author.id}').fetchone()
        full_name = ctx.author.nick
        if user_name != None:
            full_name = f'{user_name[0]}, {user_name[1]}'

        embed = discord.Embed(timestamp=get_dt_now(),title=answer,description=details)
        embed.set_author(name='Anonymous#0000',icon_url='https://i2.wp.com/howtodoanything.org/wp-content/uploads/2018/03/clownfish.jpg')
        if anon == 0:
            embed.set_author(name=full_name,icon_url=ctx.author.avatar.url)
        embed.set_footer(text=f'Question: {question}')

        if voting_system == 1:
            message = await forum_message.reply('`0` | `0` 🔼  `0` 🔽',embed=embed)
            await message.add_reaction('🔼')
            await message.add_reaction('🔽')

        else:
            message = await forum_message.reply(embed=embed)

        cursor.execute(f"INSERT INTO forum_answers(guild_id,post_id,message_id,author_id,count) VALUES(?,?,?,?,?)",\
                       (ctx.guild.id,forumnumber,message.id,ctx.author.id,0))
        db.commit()
        await ctx.respond(f'Your response to Forum #{forumnumber} has been recorded.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        if payload.emoji.name in ['🔼','🔽'] and payload.member != self.bot.user and cursor.execute(f'SELECT * FROM forum_answers WHERE message_id={payload.message_id}').fetchone() != None:
            post_id = cursor.execute(f'SELECT post_id FROM forum_answers WHERE message_id={payload.message_id}').fetchone()[0]
            if cursor.execute(f'SELECT voting_system FROM forum WHERE id={post_id}').fetchone()[0] == 1:
                answer = cursor.execute(f'SELECT * FROM forum_answers WHERE message_id={payload.message_id}').fetchone()
                message, count, voted = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id), answer[4], answer[5]

                if voted is None:
                    voted = []
                else:
                    voted = voted.split(';')
                if f'{payload.member.id}:+' not in voted and f'{payload.member.id}:-' not in voted:
                    if payload.emoji.name == '🔼':
                        count += 1
                        vote = f'{payload.member.id}:+'
                    else:
                        count -= 1
                        vote = f'{payload.member.id}:-'
                    voted.append(vote)
                elif f'{payload.member.id}:-' in voted:
                    if payload.emoji.name == '🔽':
                        return await message.remove_reaction(payload.emoji.name,payload.member)
                    count += 2
                    voted.remove(f'{payload.member.id}:-')
                    voted.append(f'{payload.member.id}:+')
                else:
                    if payload.emoji.name == '🔼':
                        return await message.remove_reaction(payload.emoji.name,payload.member)
                    count -= 2
                    voted.remove(f'{payload.member.id}:+')
                    voted.append(f'{payload.member.id}:-')

                temp = (len(voted) - abs(count))//2
                if count > 0:
                    description = f'`+{count}` | `{temp+count}` 🔼  `{temp}` 🔽'
                elif count < 0:
                    description = f'`{count}` | `{temp}` 🔼  `{temp+abs(count)}` 🔽'
                else:
                    description = f'`0` | `{temp}` 🔼, `{temp}` 🔽'

                await message.edit(content=description)
                cursor.execute(f'UPDATE forum_answers SET count=?,voted=? WHERE message_id=?',(count,';'.join(voted),payload.message_id))
                db.commit()
                await message.remove_reaction(payload.emoji.name,payload.member)
                return print(f'{self.__class__.__name__} - updated votes | {time.time()-start_time} s')




def setup(bot):
    bot.add_cog(Forum(bot))
