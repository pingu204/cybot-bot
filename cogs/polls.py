import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from misc import *
import time

class Polls(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Polls ready!')

    @commands.group(invoke_without_command=True, aliases=['polls'])
    async def poll(self,ctx):
        start_time = time.time()
        await ctx.send(embed=get_poll(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @poll.command()
    @has_permissions(manage_guild=True)
    async def create(self,ctx,channel:discord.TextChannel=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if channel is None:
            return await ctx.send('❌ | Channel is a required parameter!',delete_after=5)
        message = await ctx.send('Please enter the category of the poll. Categories can be a question or a phrase.\n\n```Example:\nWhat is the best pizza flavor?\nPreferred schedule of exam```')
        category = await self.bot.wait_for('message',check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
        await message.delete()
        await category.add_reaction('✅')
        message = await ctx.send('Please enter at most 18 choices for the poll. Choices can be separated using line breaks or separate messages.\n\n```Example:\nPepperoni\nMeat Lovers\n-new message-\nHawaiian\n\nType \'done\' to complete this process.```')
        choices = []
        while 1:
            try:
                temp = await self.bot.wait_for('message',timeout=60,check=lambda message:message.author==ctx.author and message.channel==ctx.channel)
            except:
                await message.delete()
                return await ctx.send('❌ | Timeout error. Please try again.',delete_after=5)
            else:
                if temp.content == 'done':
                    await temp.delete()
                    break
                await temp.add_reaction('✅')
                choices.extend(temp.content.split('\n'))
                await temp.delete()
        await message.delete()
        poll_description = f'**{category.content}**\n\n'
        await category.delete()
        if len(choices) < 2:
            return await ctx.send('❌ | Not enough choices. Please try again.',delete_after=5)
        elif len(choices) <= 11:
            num_emojis = {0:'0️⃣',1:'1️⃣',2:'2️⃣',3:'3️⃣',4:'4️⃣',5:'5️⃣',6:'6️⃣',7:'7️⃣',8:'8️⃣',9:'9️⃣',10:'🔟'}
            for n in range(len(choices)):
                poll_description += f'{num_emojis[n]} {choices[n]}\n'
            embed=discord.Embed(color=0xFFFFFF,description=poll_description)
            embed.set_footer(text='Please react with the emoji of your choice. For admins, use 🔒 to close the poll.')
            message = await channel.send('A new poll has been created.',embed=embed)
            for n in range(len(choices)):
                await message.add_reaction(num_emojis[n])
        elif len(choices) <= 18:
            letter_emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                             14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}
            for n in range(len(choices)):
                poll_description += f'{letter_emojis[n]} {choices[n]}\n'
            embed=discord.Embed(color=0xFFFFFF,description=poll_description)
            embed.set_footer(text='Please react with the emoji of your choice. For admins, use 🔒 to close the poll.')
            message = await channel.send('A new poll has been created.',embed=embed)
            for n in range(len(choices)):
                await message.add_reaction(letter_emojis[n])
        else:
            return await ctx.send('❌ | There are too many choices. Please try again.',delete_after=5)
        await message.add_reaction('🔒')
        cursor.execute('INSERT INTO polls(guild_id,message_id,channel_id,category,choices) VALUES(?,?,?,?,?)',(ctx.guild.id,message.id,channel.id,category.content,';'.join(choices)))
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    async def update_poll(self,message,category,choices,emojis):
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        poll_description = f'**{category}**\n\n'
        for n in range(len(choices)):
            poll_description += f'{emojis[n]} {choices[n]}\n'
        embed=discord.Embed(color=0xFFFFFF,description=poll_description)
        embed.set_footer(text='Please react with the emoji of your choice. For admins, use 🔒 to close the poll.')
        await message.edit(embed=embed)
        await message.clear_reactions()
        for n in range(len(choices)):
            await message.add_reaction(emojis[n])
        await message.add_reaction('🔒')
        cursor.execute('UPDATE polls SET choices=? WHERE message_id=?',(';'.join(choices),message.id))
        db.commit()

    @poll.command()
    @has_permissions(manage_guild=True)
    async def add(self,ctx,*,choice=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if choice is None:
            return await ctx.send('❌ | Missing argument: `choices`')
        added_choices = choice.split('\n')
        try:
            ctx.message.reference.message_id
        except:
            return await ctx.message.reply('❌ | Please reply to a message that has an existing poll.')
        else:
            if cursor.execute(f'SELECT * FROM polls WHERE message_id={ctx.message.reference.message_id}').fetchone():
                details = cursor.execute(f'SELECT * FROM polls WHERE message_id={ctx.message.reference.message_id}').fetchone()
                category, choices, guild = details[3],details[4].split(';'),discord.utils.get(self.bot.guilds,id=details[0])
                channel = discord.utils.get(guild.channels,id=details[2])
                message = await channel.fetch_message(ctx.message.reference.message_id)
                choices.extend(added_choices)
                poll_description = f'**{category}**\n\n'
                if len(choices) <= 11:
                    num_emojis = {0:'0️⃣',1:'1️⃣',2:'2️⃣',3:'3️⃣',4:'4️⃣',5:'5️⃣',6:'6️⃣',7:'7️⃣',8:'8️⃣',9:'9️⃣',10:'🔟'}
                    await self.update_poll(message,category,choices,num_emojis)
                elif len(choices) <= 18:
                    letter_emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                                     14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}
                    await self.update_poll(message,category,choices,letter_emojis)
                else:
                    return await ctx.send('❌ | There are too many choices. Please try again.',delete_after=5)
                added_choices = '\n'.join(added_choices)
                await ctx.message.delete()
                if len(added_choices) == 1:
                    return await message.reply(f"Added to poll:`{added_choices}`",delete_after=5)
                await message.reply(f"Added to poll:\n```{added_choices}```",delete_after=5)
                return print(f'{self.__class__.__name__} - {ctx.command} choice | {time.time()-start_time} s')
            return await ctx.message.reply('❌ | No poll found in the message.')

    @poll.command()
    @has_permissions(manage_guild=True)
    async def remove(self,ctx,*,emoji:str=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        try:
            ctx.message.reference.message_id
        except:
            return await ctx.message.reply('❌ | Please reply to a message that has an existing poll.')
        else:
            if cursor.execute(f'SELECT * FROM polls WHERE message_id={ctx.message.reference.message_id}').fetchone():
                if emoji is None:
                    return await ctx.message.reply('❌ | Emoji is a required parameter.')
                elif len(emoji.split(' '))>1:
                    return await ctx.message.reply('❌ | Choices can only be removed one at a time.')
                details = cursor.execute(f'SELECT * FROM polls WHERE message_id={ctx.message.reference.message_id}').fetchone()
                category, choices, guild = details[3],details[4].split(';'),discord.utils.get(self.bot.guilds,id=details[0])
                num_emojis = {0:'0️⃣',1:'1️⃣',2:'2️⃣',3:'3️⃣',4:'4️⃣',5:'5️⃣',6:'6️⃣',7:'7️⃣',8:'8️⃣',9:'9️⃣',10:'🔟'}
                letter_emojis = {0:'🇦',1:'🇧',2:'🇨',3:'🇩',4:'🇪',5:'🇫',6:'🇬',7:'🇭',8:'🇮',9:'🇯',10:'🇰',11:'🇱',12:'🇲',13:'🇳',
                                 14:'🇴',15:'🇵',16:'🇶',17:'🇷',18:'🇸',19:'🇹',20:'🇺',21:'🇻',22:'🇼',23:'🇽',24:'🇾',25:'🇿'}
                channel = discord.utils.get(guild.channels,id=details[2])
                message = await channel.fetch_message(ctx.message.reference.message_id)
                #print(emoji in list({0:'🅰',1:'🅱'}.values()),list({0:'🅰',1:'🅱'}.values()))
                print(emoji)
                if len(choices) <= 11 and emoji in num_emojis.values():
                    for key,value in num_emojis.items():
                        if value == emoji:
                            removed_choice=choices.pop(key)
                            break
                    await self.update_poll(message,category,choices,num_emojis)
                elif len(choices) <= 18 and emoji in letter_emojis.values():
                    for key,value in letter_emojis.items():
                        if value == emoji:
                            removed_choice=choices.pop(key)
                            break
                    await self.update_poll(message,category,choices,letter_emojis)
                else:
                    return await ctx.message.reply(f'❌ | Emoji {emoji} not found in the choices.',delete_after=5)
                await ctx.message.delete()
                if len(choices)<=1:
                    await message.delete()
                    await ctx.send('Poll deleted. (Not enough choices)')
                    return print(f'{self.__class__.__name__} - {ctx.command} choice | {time.time()-start_time} s')
                await message.reply(f"Removed from the poll: `{removed_choice}`",delete_after=5)
                return print(f'{self.__class__.__name__} - {ctx.command} choice | {time.time()-start_time} s')
            return await ctx.message.reply('❌ | No poll found in the message.')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if payload.emoji.name == '🔒' and payload.member != self.bot.user and cursor.execute(f'SELECT * FROM polls WHERE message_id={payload.message_id}').fetchone():
            details = cursor.execute(f'SELECT * FROM polls WHERE message_id={payload.message_id}').fetchone()
            category, choices, guild = details[3],details[4].split(';'),discord.utils.get(self.bot.guilds,id=details[0])
            channel = discord.utils.get(guild.channels,id=details[2])
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction('🔒',payload.member)
            await message.remove_reaction('🔒',self.bot.user)
            emoji_count = []
            for reaction in message.reactions:
                if reaction.emoji != '🔒':
                    emoji_count.append(reaction.count-1)
            poll_description = f'**{category}**\n\n'
            for n in range(len(choices)):
                if sum(emoji_count) == 0:
                    poll_description += f'{message.reactions[n].emoji} {choices[n]} (0.00%)\n'
                elif emoji_count[n] == max(emoji_count):
                    poll_description += f'{message.reactions[n].emoji} **{choices[n]} ({round(((emoji_count[n]/sum(emoji_count))*100),1)}%)**\n'
                else:
                    poll_description += f'{message.reactions[n].emoji} {choices[n]} ({round(((emoji_count[n]/sum(emoji_count))*100),1)}%)\n'
            embed=discord.Embed(color=0xFFFFFF,description=poll_description)
            embed.set_footer(text='Poll is now closed, here are the final results.')
            await message.edit(content='Poll closed.',embed=embed)
            await message.clear_reactions()
            cursor.execute(f'DELETE FROM polls WHERE message_id={payload.message_id}')
            db.commit()
            return print(f'{self.__class__.__name__} - close | {time.time()-start_time} s')


def setup(bot):
    bot.add_cog(Polls(bot))
