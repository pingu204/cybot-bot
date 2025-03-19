import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import sqlite3
from typing import Union
from misc import *
import asyncio
import time

class Consultation(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    async def confirm_message(self,message):
        if message.content[0] == '@':
            content = message.content[6:]
        else:
            content=message.content
        confirm_embed = discord.Embed(description=f'Please react with 👍 to confirm your message.\n\n>>> {content}')
        confirm_message = await message.channel.send(embed=confirm_embed)
        await confirm_message.add_reaction('👍')
        try:
            reaction = await self.bot.wait_for('reaction_add',timeout=20,check=lambda reaction,user: str(reaction.emoji)=='👍' and user==message.author)
        except:
            await confirm_message.delete()
            return False
        else:
            await confirm_message.delete()
            return True

    @commands.Cog.listener()
    async def on_message(self,message):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if str(message.channel.type) == 'private':
            if message.author == self.bot.user:
                return
            prefixes = []
            for guild in message.author.mutual_guilds:
                if cursor.execute(f'SELECT prefix FROM prefixes WHERE guild_id={guild.id}').fetchone():
                    prefixes.append(cursor.execute(f'SELECT prefix FROM prefixes WHERE guild_id={guild.id}').fetchone()[0])
                else:
                    prefixes.append('$')
            if message.content[0] in prefixes and '$consult' not in message.content:
                return
            if message.content[0] == '@':
                # replying to ticket
                if cursor.execute(f'SELECT * FROM consultation WHERE id={int(message.content[1:5])}').fetchone() is None:
                    return await message.channel.send('❌ | Invalid ticket ID.',delete_after=3)

                ticket_details = cursor.execute(f'SELECT * FROM consultation WHERE id={int(message.content[1:5])}').fetchone()
                ticket_id, guild, author_id, to_reply, quote = int(ticket_details[0]), discord.utils.get(message.author.mutual_guilds,id=int(ticket_details[1])), int(ticket_details[2]), ticket_details[3], ticket_details[4]

                # GET ADMINS
                admins = []
                if cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={guild.id}").fetchone() is None:
                    admins.append(guild.owner.id)
                else:
                    for id in cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={guild.id}").fetchone()[0].split(';'):
                        admins.append(int(id))

                message_embed = discord.Embed(description=f'>>> {quote}',color=0xfd9cff)
                message_embed.add_field(name='Reply',value=f'{message.content[6:]}')
                message_embed.set_footer(text=f'Reply: @{str(ticket_id).zfill(4)} <your message> | Close ticket: close @{str(ticket_id).zfill(4)}')
                if to_reply == 'author':
                    if message.author.id != author_id: # ignore message
                        return
                    if await self.confirm_message(message):
                        message_embed.set_author(icon_url='https://static.wikia.nocookie.net/dogelore/images/0/05/322c936a8c8be1b803cd94861bdfa868.png/revision/latest?cb=20190621163928',name=f'Ticket#{str(ticket_id).zfill(4)}')
                        for admin_id in admins:
                            dm_channel = await discord.utils.get(guild.members,id=int(admin_id)).create_dm()
                            await dm_channel.send(embed=message_embed)
                        cursor.execute(f"UPDATE consultation SET quote=?, to_reply=? WHERE id=?",(message.content[6:],'admin',ticket_id))
                else:
                    if message.author.id not in admins: # ignore message
                        return
                    if await self.confirm_message(message):
                        message_embed.set_author(icon_url=message.author.avatar.url,name=f'{message.author.name} | Ticket#{str(ticket_id).zfill(4)}')
                        dm_channel = await discord.utils.get(guild.members,id=int(author_id)).create_dm()
                        await dm_channel.send(embed=message_embed)
                        admins.remove(message.author.id)
                        for admin_id in admins:
                            dm_channel = await discord.utils.get(guild.members,id=int(admin_id)).create_dm()
                            await dm_channel.send(f"{message.author} has replied to Ticket#{str(ticket_id).zfill(4)}.")
                        cursor.execute(f"UPDATE consultation SET quote=?,to_reply=? WHERE id=?",(message.content[6:],'author',ticket_id))
                    else:
                        return await message.channel.send('❌ | User took long to respond.',delete_after=5)
                await message.channel.send(f'✅ Reply to Ticket#{str(ticket_id).zfill(4)} has been sent.')
                db.commit()
                return print(f'{self.__class__.__name__} - reply | {time.time()-start_time} s')
            elif message.content[0:5].lower() == 'close':
                # closes existing ticket
                temp_id = message.content.split('@')[1]
                if cursor.execute(f'SELECT * FROM consultation WHERE id={int(temp_id)}').fetchone() is None:
                    return await message.channel.send('❌ | Invalid ticket ID.',delete_after=5)
                ticket_details = cursor.execute(f'SELECT * FROM consultation WHERE id={int(message.content[7:11])}').fetchone()
                ticket_id, guild, author_id = int(ticket_details[0]), discord.utils.get(message.author.mutual_guilds,id=int(ticket_details[1])), int(ticket_details[2])

                embed = discord.Embed(title='Closed Ticket',color=0x9c249e,description=f'Ticket#{str(ticket_id).zfill(4)} has been closed. You cannot reply to this conversation anymore.')

                recipients = []
                # GET AUTHOR
                recipients.append(author_id)
                # GET ADMINS
                if cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={guild.id}").fetchone() is None:
                    recipients.append(guild.owner.id)
                else:
                    for id in cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={guild.id}").fetchone()[0].split(';'):
                        recipients.append(int(id))

                if message.author.id in recipients:
                    cursor.execute(f'DELETE FROM consultation WHERE id={ticket_id}')
                    for user_id in recipients:
                        dm_channel = await discord.utils.get(guild.members,id=int(user_id)).create_dm()
                        await dm_channel.send(embed=embed)
                else:
                    return await message.channel.send('❌ | Cannot close a ticket that you\'re not part of',delete_after=5)
                db.commit()
                return print(f'{self.__class__.__name__} - close | {time.time()-start_time} s')
            else:
                # creates a new ticket
                if '$consult' in message.content:
                    message.content = message.content.split('$consult')[1]
                embed = discord.Embed(title='Create a new ticket',description='Where do you want to send your message?')
                embed.add_field(name='Note:',value=f'This process creates a new consultation ticket. If you want to reply to an existing ticket instead, use `@XXXX <message>` with your assigned ticket ID.\nExample: `@0000 Test message`')
                num_emojis = {0:'0️⃣',1:'1️⃣',2:'2️⃣',3:'3️⃣',4:'4️⃣',5:'5️⃣',6:'6️⃣',7:'7️⃣',8:'8️⃣',9:'9️⃣',10:'🔟'}
                emoji_id = {}
                n = 0
                mutual_guilds = message.author.mutual_guilds
                for guild in mutual_guilds:
                    embed.add_field(inline=False,name=f'{num_emojis[n]} : {guild.name}',value=f'ID: {guild.id}')
                    emoji_id[num_emojis[n]]=guild.id
                    n+=1
                embed.set_footer(text='The message will be delivered to the admin/s of the chosen server anonymously.')
                ask_guild = await message.channel.send(embed=embed)
                for emoji in emoji_id.keys():
                    await ask_guild.add_reaction(emoji)
                try:
                    reaction = await self.bot.wait_for('reaction_add',timeout=30,check=lambda reaction,user: str(reaction.emoji) in emoji_id.keys() and user == message.author)
                except:
                    await ask_guild.delete()
                    return await message.channel.send('❌ | User took long to respond.',delete_after=5)

                await ask_guild.delete()
                guild = discord.utils.get(self.bot.guilds,id=emoji_id[str(reaction[0])])
                recipients = []
                if cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={guild.id}").fetchone() is None:
                    recipients.append(guild.owner.id)
                else:
                    for id in cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={guild.id}").fetchone()[0].split(';'):
                        recipients.append(int(id))
                if await self.confirm_message(message):
                    ticket_id = get_id('consultation')
                    message_embed = discord.Embed(description=message.content,color=0xfd9cff)
                    message_embed.set_footer(text=f'Reply: @{str(ticket_id).zfill(4)} <your message> | Close ticket: close @{str(ticket_id).zfill(4)}')
                    message_embed.set_author(icon_url='https://static.wikia.nocookie.net/dogelore/images/0/05/322c936a8c8be1b803cd94861bdfa868.png/revision/latest?cb=20190621163928',name=f'Ticket#{str(ticket_id).zfill(4)}')
                    for admin_id in recipients:
                        dm_channel = await discord.utils.get(guild.members,id=int(admin_id)).create_dm()
                        await dm_channel.send(embed=message_embed)
                    await message.channel.send(f"✅ Ticket#{str(ticket_id).zfill(4)} has been created. Please wait for a response to your message.")
                    cursor.execute(f"INSERT INTO consultation(id,guild_id,author_id,to_reply,quote) VALUES(?,?,?,?,?)",(ticket_id,guild.id,message.author.id,'admin',message.content))
                    db.commit()
                    return print(f'{self.__class__.__name__} - new ticket | {time.time()-start_time} s')

    @commands.group(invoke_without_command=True)
    async def consult(self,ctx,message=None):
        if message is None:
            await ctx.send(embed=get_consultation(ctx))
        if str(ctx.channel.type) != 'private':
            await ctx.message.reply(f'Consultation tickets can only be done by sending a DM to {self.bot.user.mention}')

    @consult.command()
    async def test(self,ctx):
        start_time = time.time()
        list_messages = []
        dm_channel = await ctx.author.create_dm()
        msg = await dm_channel.send('Hello! 😃 I will demonstrate how consultations work.')
        list_messages.append(msg)
        await asyncio.sleep(5)
        msg = await dm_channel.send('Let\'s say I want to consult regarding a math problem that I do not understand...🤔')
        list_messages.append(msg)
        async with dm_channel.typing():
            await asyncio.sleep(5)
        quote = f'Good day! I am {self.bot.user.name} and I\'m having trouble with this problem. 🥺👉👈 How exactly do I solve for the roots? Thanks!'
        msg = await dm_channel.send(f'> {quote}\n\nPS. Always remember to be polite!')
        list_messages.append(msg)
        await asyncio.sleep(5)
        msg = await dm_channel.send('The bot will then send this embed to the admin/s of the server:')
        list_messages.append(msg)
        await asyncio.sleep(3)
        message_embed = discord.Embed(description=quote,color=0xfd9cff)
        message_embed.set_footer(text=f'Reply: @0000 <your message> | Close ticket: close @0000')
        message_embed.set_author(icon_url='https://static.wikia.nocookie.net/dogelore/images/0/05/322c936a8c8be1b803cd94861bdfa868.png/revision/latest?cb=20190621163928',name=f'Ticket#0000')
        msg = await dm_channel.send(embed=message_embed)
        list_messages.append(msg)
        await asyncio.sleep(5)
        msg = await dm_channel.send('Yes, it\'s completely anonymous. 🤫')
        list_messages.append(msg)
        await asyncio.sleep(5)
        for message in list_messages:
            await message.delete()
        list_messages.clear()
        msg = await dm_channel.send('Once the admin replies using `@0000 <their reply>`, an embed will be sent to you like this:')
        list_messages.append(msg)
        await asyncio.sleep(3)
        message_embed = discord.Embed(description=f'> {quote}',color=0xfd9cff)
        message_embed.add_field(name='Reply',value='Hey there. Roots can be solved by finding the values that make the function equivalent to zero. Happy solving! :)')
        message_embed.set_footer(text=f'Reply: @0000 <your message> | Close ticket: close @0000')
        message_embed.set_author(icon_url=f'{self.bot.user.avatar.url}',name=f'Admin Name | Ticket#0000')
        msg = await dm_channel.send(embed=message_embed)
        list_messages.append(msg)
        await asyncio.sleep(6)
        for message in list_messages:
            await message.delete()
        list_messages.clear()
        msg = await dm_channel.send('Accordingly, you can reply to their message using `@0000 <your reply>`. However, let\'s try closing this ticket.')
        list_messages.append(msg)
        async with dm_channel.typing():
            await asyncio.sleep(5)
        msg = await dm_channel.send('> close @0000\n\nPS. Make sure to put the correct ID!')
        list_messages.append(msg)
        await asyncio.sleep(5)
        msg = await dm_channel.send('The bot will then send this embed to the the admin/s of the server, as well as to you, for receipt of closing the ticket:')
        list_messages.append(msg)
        await asyncio.sleep(5)
        embed = discord.Embed(title='Closed Ticket',color=0x9c249e,description=f'Ticket#0000 has been closed. You cannot reply to this conversation anymore.')
        msg = await dm_channel.send(embed=embed)
        list_messages.append(msg)
        await asyncio.sleep(5)
        for message in list_messages:
            await message.delete()
        list_messages.clear()
        msg = await dm_channel.send('...And that\'s it! So easy, right? 😎')
        await asyncio.sleep(5)
        await msg.delete()
        return print(f'{self.__class__.__name__} - test | {time.time()-start_time} s')

    @commands.group(invoke_without_command=True,aliases=['admins'])
    async def admin(self,ctx):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        # DATABASE
        admins = []
        if cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={ctx.guild.id}").fetchone() is None:
            admins = [f'{str(ctx.guild.owner)} | `ID: {ctx.guild.owner.id}`']
        else:
            for id in cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={ctx.guild.id}").fetchone()[0].split(';'):
                admins.append(f'{str(discord.utils.get(ctx.guild.members,id=int(id)))} | `ID: {id}`')
        embed = discord.Embed(description=f'Here are the admins of `{ctx.guild.name}`:')
        embed.add_field(name='Admin',value='\n'.join(admins))
        embed.set_footer(text='The members above will be receiving messages for consultation | $help consultation')
        await ctx.send(embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @admin.command(aliases=['set'])
    @has_permissions(manage_guild=True)
    async def set_admin(self,ctx,member=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if member is None:
            return await ctx.send('❌ | Member is a required parameter.',delete_after=3)

        if member.lower() == 'me':
            member = ctx.author
        elif member.isnumeric():
            member = discord.utils.get(ctx.guild.members,id=int(member))
            if member is None:
                return await ctx.send(f'❌ | Member not found.',delete_after=3)
        elif '<@!' in member:
            member = discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')]))
        else:
            return await ctx.send('❌ | Please mention a user or input their ID.',delete_after=3)

        # DATABASE
        if cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={ctx.guild.id}").fetchone() is None:
            admin_id = [str(ctx.guild.owner.id),str(member.id)]
            cursor.execute(f"INSERT INTO admins(guild_id,admin_id) VALUES(?,?)",(ctx.guild.id,';'.join(admin_id)))
        else:
            admin_id = cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={ctx.guild.id}").fetchone()[0].split(';')
            if str(member.id) not in admin_id:
                admin_id.append(str(member.id))
            else:
                return await ctx.send(f'❌ | {member} is already in the server\'s admin list',delete_after=3)
            cursor.execute(f"UPDATE admins SET admin_id=? WHERE guild_id=?",(';'.join(admin_id),ctx.guild.id))
        await ctx.send(f'{member} has been added to the server\'s admin list.')
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @admin.command(aliases=['remove'])
    @has_permissions(manage_guild=True)
    async def remove_admin(self,ctx,member=None):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if member is None:
            return await ctx.send('❌ | Member is a required parameter.',delete_after=3)

        if member.lower() == 'me':
            member = ctx.author
        elif member.isnumeric():
            member = discord.utils.get(ctx.guild.members,id=int(member))
            if member is None:
                return await ctx.send(f'❌ | Member not found.',delete_after=3)
        elif '<@!' in member:
            member = discord.utils.get(ctx.guild.members,id=int(member[3:member.index('>')]))
        else:
            return await ctx.send('❌ | Please mention a user or input their ID.',delete_after=3)

        # DATABASE
        if cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={ctx.guild.id}").fetchone() is None:
            return await ctx.send('❌ | No existing record of set admins.')
        admin_id = cursor.execute(f"SELECT admin_id FROM admins WHERE guild_id={ctx.guild.id}").fetchone()[0].split(';')
        try:
            admin_id.remove(str(member.id))
        except:
            return await ctx.send(f'❌ | {member} is not an admin of the server.')
        else:
            cursor.execute(f"UPDATE admins SET admin_id=? WHERE guild_id=?",(';'.join(admin_id),ctx.guild.id))
            await ctx.send(f'{member} has been removed from the server\'s admin list.')
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')


def setup(bot):
    bot.add_cog(Consultation(bot))
