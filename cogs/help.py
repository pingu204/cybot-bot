import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from misc import *
import asyncio
from discord.ui import View, Button, Select

class Help(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    @commands.group(invoke_without_command=True)
    async def help(self,ctx):
        await get_help(ctx,self.bot)

    ### help commands for features ###

    @help.command(aliases=['mod'])
    async def moderation(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        embeds = get_moderation(ctx)
        await ctx.send(embed=embeds[0])
        await ctx.send(embed=embeds[1])
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['announce'])
    async def announcement(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_announcements(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['remind'])
    async def reminder(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_reminders(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['consult'])
    async def consultation(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_consultation(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['attend'])
    async def attendance(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_attendance(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['role'])
    async def roles(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_roles(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['sched','reqs','req'])
    async def schedule(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_sched(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['log'])
    async def logs(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_logs(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['convert'])
    async def math(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_math(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    # @help.command(aliases=['grade'])
    # async def grades(self,ctx):
    #     await ctx.send(embed=get_grades(ctx))

    @help.command(aliases=['poll'])
    async def polls(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_polls(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command(aliases=['forum'])
    async def forums(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_forum(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command()
    async def utility(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_utility(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command()
    async def info(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_info(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @help.command()
    async def bulletin(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_bulletin(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command(aliases=['feature'])
    async def features(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        await ctx.send(embed=get_features(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command(aliases=['command','comm','com'])
    async def commands(self,ctx):
        start_time = time.time()
        await ctx.message.delete()
        pages = [get_features(ctx)]
        pages.extend(get_moderation(ctx))
        pages.extend([get_announcements(ctx),
                get_bulletin(ctx),
                get_reminders(ctx),
                get_consultation(ctx),
                get_attendance(ctx),
                get_roles(ctx),
                get_sched(ctx),
                get_todolist(ctx),
                get_logs(ctx),
                get_math(ctx),
                get_polls(ctx),
                get_forum(ctx),
                get_utility(ctx),
                get_info(ctx)])

        for n in range(1,len(pages)+1):
            pages[n-1].set_author(name=f'Page {n}/{len(pages)}')
        message = await ctx.send(embed=pages[0])
        for reaction in ['⏪','◀️','▶️','⏩']:
            await message.add_reaction(reaction)
        print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
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
                    i=0
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

    ### help commands [miscellaneous] ###

    @help.command()
    async def embed(self,ctx):
        start_time = time.time()
        async with ctx.channel.typing():
            await ctx.send('Embeds are another way to present text in Discord by making use of rich text and special formatting. If you want to send your messages with a special structure, embeds are the way to go.')
            embed = discord.Embed(title='Title',description='This is where the body of the message goes')
            embed.set_image(url='https://images.unsplash.com/photo-1542831371-29b0f74f9713?ixid=MXwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHw%3D&ixlib=rb-1.2.1&auto=format&fit=crop&w=750&q=80')
            embed.add_field(name='Sub-heading/Field',value='This is an example of a field which can be used to divide your message into sections.')
            embed.set_author(name=f'<- Author icon | Author name: {ctx.author.display_name}',icon_url=ctx.author.avatar.url)
            embed.set_footer(text='Footers? No problem.')
            await asyncio.sleep(5)
            await ctx.send('This is an example of an embed with its parts labelled:',embed=embed)
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

def setup(bot):
    bot.add_cog(Help(bot))
