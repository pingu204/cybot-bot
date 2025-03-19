import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from misc import *
#from discord_slash import SlashCommand, SlashContext, cog_ext
import time
from discord import Option,OptionChoice
from discord.ui import View, Button, Select
from discord.commands import slash_command

class Bulletin(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Bulletin ready!')

    post_options = [
        {
        'name':'category',
        'description':'The category of your post in the bulletin',
        'required':True,
        'type':3,
        'choices':[
            {
                'name':'Question',
                'value':'Question',
            },
            {
                'name':'Feedback',
                'value':'Feedback'
            },
            {
                'name':'Random Thoughts',
                'value':'Random Thoughts'
            },
            {
                'name':'Suggestion',
                'value':'Suggestion'
            }
            ]
        },
        {
        'name':'message',
        'description':'The content of your post goes here...',
        'required':True,
        'type':3
        },
        {
        'name':'attachment',
        'description':'Enter the link (URL only) of the image/GIF that you may want to add to your post',
        'required':False,
        'type':3
        }
    ]

    @commands.command()
    async def bulletin(self,ctx):
        start_time = time.time()
        await ctx.send(embed=get_bulletin(ctx))
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command()
    @has_permissions(manage_guild=True)
    async def setbulletin(self,ctx,channel:discord.TextChannel):
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()

        if cursor.execute(f'SELECT bulletin FROM info WHERE guild_id={ctx.guild.id}').fetchone() is None:
            cursor.execute(f'INSERT INTO info(guild_id,bulletin) VALUES(?,?)',(ctx.guild.id,channel.id))
        else:
            cursor.execute(f'UPDATE info SET bulletin=? WHERE guild_id=?',(channel.id,ctx.guild.id))
        await ctx.send(f'{channel.mention} has been set as the channel for bulletin.',delete_after=5)
        db.commit()
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name="post",description='Bulletins can be a way for you to express your thoughts anonymously')
    async def post(self,ctx,
            category:Option(str,description="The category of your post in the bulletin",choices=[
                    OptionChoice(name="Question",value="Question"),
                    OptionChoice(name="Feedback",value="Feedback"),
                    OptionChoice(name="Random Thoughts",value="Random Thoughts"),
                    OptionChoice(name="Suggestion",value="Suggestion")]),
            message:Option(str,description="The content of your post goes here..."),
            attachment:Option(str,description="Enter the link (URL only) of the image/GIF that you may want to add to your post")=None):

        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        await ctx.defer()
        if cursor.execute(f'SELECT * FROM bulletin_muted WHERE author_id={ctx.author.id}').fetchone() is not None:
            return await ctx.respond('❌ | You have been muted from posting bulletins in this server. Please reach out to admin/s regarding this.')
        if cursor.execute(f'SELECT bulletin FROM info WHERE guild_id={ctx.guild.id}').fetchone() is None:
            return await ctx.respond('❌ | No channel has been set for bulletins yet. Use `$setbulletin <channel>` to set one.')
        channel = discord.utils.get(ctx.guild.channels,id=cursor.execute(f'SELECT bulletin FROM info WHERE guild_id={ctx.guild.id}').fetchone()[0])
        post_id = get_id('bulletin')
        embed = discord.Embed(title=f'Post #{post_id}',color=0xE6E6FA,description=f'`{category}`\n\n{message}')
        embed.set_footer(text='All bulletin posts are anonymous.')
        if attachment:
            embed.set_image(url=attachment)
        message = await channel.send(embed=embed)
        cursor.execute(f'INSERT INTO bulletin(id,guild_id,channel_id,message_id,author_id) VALUES(?,?,?,?,?)',(post_id,ctx.guild.id,channel.id,message.id,ctx.author.id))
        db.commit()
        await ctx.respond(f'✅ Your message has been posted. To delete it, use `/deletepost {post_id}`.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    reason_options = [
        {'name':'number',
        'description':'Post number of the post you\'re trying to perform an action on',
        'required':True,
        'type':3,
        },
        {
        'name':'reason',
        'description':'Reason for the specific action',
        'required':True,
        'type':3,
        }
    ]

    nonreason_options = [
        {'name':'number',
        'description':'Post number of the post you\'re trying to perform an action on',
        'required':True,
        'type':3,
        }
    ]

    @slash_command(name='deletepost',description='Users can delete their own post through its given identification number')
    async def deletepost(self,ctx,
            number:Option(int,description="Post number of the post you're trying to perform an action on")):
        await ctx.defer()
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT * FROM bulletin WHERE id={number} AND guild_id={ctx.guild.id} AND author_id={ctx.author.id}').fetchone() is None:
            return await ctx.respond('❌ | No such post found. Please make sure that you\'re trying to delete an existing post that is yours.')
        details = cursor.execute(f'SELECT * FROM bulletin WHERE id={number} AND guild_id={ctx.guild.id} AND author_id={ctx.author.id}').fetchone()
        # [id,guild_id,channel_id,message_id,author_id]
        post_channel = discord.utils.get(ctx.guild.channels,id=details[2])
        try:
            message = await post_channel.fetch_message(details[3])
            await message.delete()
        except:
            return await ctx.respond(f'Post #`{number}` has already been deleted.')
        await ctx.respond(f'✅ Post #`{number}` has been deleted.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name='warnpost',description='Admins can warn an author before muting them if they find abuse within their post')
    async def warnpost(self,ctx,
            number:Option(int,description="Post number of the post you're trying to perform an action on"),
            reason:Option(str,description="Reason for the specific action")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT * FROM bulletin WHERE id={int(number)} AND guild_id={ctx.guild.id}').fetchone() is None:
            return await ctx.respond(f'❌ | Author/post not found. Make sure that you\'re referring to an existing post.')
        author_id = cursor.execute(f'SELECT * FROM bulletin WHERE id={number} AND guild_id={ctx.guild.id}').fetchone()[4]
        embed = discord.Embed(color=0xFFFFFF,description='You have been **warned** regarding posting bulletins in the server.')
        embed.add_field(inline=False,name='Post #',value=number)
        embed.add_field(inline=False,name='Reason',value=reason)
        embed.set_footer(icon_url=ctx.guild.icon.url,text=ctx.guild.name)
        dm_channel = await discord.utils.get(ctx.guild.members,id=int(author_id)).create_dm()
        await dm_channel.send('`Notice Re: Bulletins`',embed=embed)
        await ctx.respond(f'✅ Author of Post #`{number}` has been been warned.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name='mutepost',description='Admins can mute an author if they find abuse within their post')
    async def mutepost(self,ctx,
            number:Option(int,description="Post number of the post you're trying to perform an action on"),
            reason:Option(str,description="Reason for the specific action")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT * FROM bulletin_muted WHERE id={number} AND guild_id={ctx.guild.id}').fetchone() is not None:
            return await ctx.respond(f'❌ | Author of Post #{number} is already muted. Use `/unmutepost` to unmute them.')
        if cursor.execute(f'SELECT * FROM bulletin WHERE id={int(number)} AND guild_id={ctx.guild.id}').fetchone() is None:
            return await ctx.respond(f'❌ | Author/post not found. Make sure that you\'re referring to an existing post.')
        author_id = cursor.execute(f'SELECT * FROM bulletin WHERE id={number} AND guild_id={ctx.guild.id}').fetchone()[4]
        cursor.execute(f"INSERT INTO bulletin_muted(id,guild_id,author_id) VALUES(?,?,?)",(number,ctx.guild.id,author_id))
        embed = discord.Embed(color=0xBE1931,description='You have been **disallowed** from posting bulletins in the server.')
        embed.add_field(inline=False,name='Post #',value=number)
        embed.add_field(inline=False,name='Reason',value=reason)
        embed.set_footer(icon_url=ctx.guild.icon.url,text=ctx.guild.name)
        dm_channel = await discord.utils.get(ctx.guild.members,id=int(author_id)).create_dm()
        await dm_channel.send('`Notice Re: Bulletins`',embed=embed)
        db.commit()
        await ctx.respond(f'✅ Author of Post #`{number}` has been muted.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @slash_command(name='unmutepost',description='Admins can unmute a muted author for their post')
    async def unmutepost(self,ctx,
            number:Option(int,description="Post number of the post you're trying to perform an action on")):
        await ctx.defer()
        if not ctx.author.guild_permissions.manage_guild:
            return await ctx.respond('❌ | You don\'t have permissions to do that.')
        start_time = time.time()
        db = sqlite3.connect('main.sqlite')
        cursor = db.cursor()
        if cursor.execute(f'SELECT * FROM bulletin_muted WHERE id={number} AND guild_id={ctx.guild.id}').fetchone() is None:
            return await ctx.respond(f'❌ | Author/post not found. Use `/mutepost` to mute the author of a post.')
        author_id = cursor.execute(f'SELECT author_id FROM bulletin_muted WHERE id={number} AND guild_id={ctx.guild.id}').fetchone()[0]
        cursor.execute(f"DELETE FROM bulletin_muted WHERE id={number} AND guild_id={ctx.guild.id}")
        embed = discord.Embed(color=0x3ADF00,description='You can now use bulletins in the server.')
        embed.add_field(name='Post #',value=number)
        embed.set_footer(icon_url=ctx.guild.icon.url,text=ctx.guild.name)
        dm_channel = await discord.utils.get(ctx.guild.members,id=int(author_id)).create_dm()
        await dm_channel.send('`Notice Re: Bulletins`',embed=embed)
        db.commit()
        await ctx.respond(f'✅Author of Post #`{number}` has been unmuted.')
        return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

def setup(bot):
    bot.add_cog(Bulletin(bot))
