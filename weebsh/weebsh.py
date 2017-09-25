# WeebSH cog for Red-DiscordBot by Twentysix, an
#  open-source discord bot (github.com/Cog-Creators/Red-DiscordBot)
# Authored by Swann (github.com/swannobi)
# Last updated Sept 25, 2017

import discord
from discord.ext import commands
import aiohttp
import sys
import os
import random
from .utils import checks
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
from .utils.async import Route
from .utils.sync import ResponseError

# This list intentionally left blank.
TYPES=[]

class WeebSh:
    """Responsible for requesting the weeb.sh API to serve anime reaction images."""

    def __init__(self, bot):
        print("Loading anime...")
        self.bot = bot
        self.settings_file = "data/weeb/settings.json"
        self.settings = dataIO.load_json(self.settings_file)
        self.api_key = self.settings['WEEB_SH_API_KEY']
        # Weeb.sh
        self.api_url = "https://api.weeb.sh/"
        self.cdn_url = "https://cdn.weeb.sh/"
        self.base_uri = "images/"
        self.tags_uri = "images/tags"
        self.types_uri = "images/types"
        self.random_uri = "images/random"
        # Request headers
        # If you don't have an auth key, get one from Wolke!
        self.headers = {"Authorization":"Bearer "+str(self.api_key),"Content-Type":"application/json"}
        # Dynmically load valid types when cog is loaded
        try:
            self.types = self._get(self.api_url, self.types_uri, self.headers).sync_query()["types"]
            self.nsfw_types = self._get(self.api_url, self.types_uri+"?nsfw=true", self.headers).sync_query()["types"]
            # Workaround. self attributes are outside the scope 
            #  of the discord.ext.commands decorator.
            TYPES.extend(self.types)
            # Set the tags; TODO currently unused.
            self.tags = self._get(self.api_url, self.tags_uri, self.headers).sync_query()["tags"]
            self.nsfw_tags = self._get(self.api_url, self.tags_uri+"?nsfw=true", self.headers).sync_query()["tags"]
            # Get the current API information as of the time this cog was loaded.
            self.info = self._get(self.api_url, self.base_uri, self.headers).sync_query()
        except:
            print("API Key is probably not set.")

    # Inner method to create the request object. Invoke it with .sync_query()
    def _get(self, api, uri, http_headers):
        return Route(base_url=api,path=uri,headers=http_headers)

    # Responsible for invoking the request object and creating an Embed to post in the channel.
    # Uses embed.description instead of embed.title because apparently titles don't get 
    #  evaluated/cleaned up. In a title you get <@123123123123> instead of @Swann. ¯\_(-_-)_/¯
    async def anime(self, imgtype, nsfw="false", random=False, description=""):
        """Posts an anime reaction image"""
        # Will fail silently if the user tries to invoke an invalid image type.
        if imgtype not in self.types:
            return
        path = self.random_uri + "?type=" + imgtype + "&nsfw=" + nsfw
        try:
            result = self._get(self.api_url, path, self.headers).sync_query()
            data = discord.Embed()
            if description != "":
                data.description = description 
            if random:
                data.title = "Randomly chose: "+imgtype
            data.set_image(url=result["url"])
            data.set_footer(text="Powered by Wolfe's weeb.sh")
            await self.bot.say(embed=data)
        # Fails silently & dumps to console whenever the query returns a non-200-level http code.
        except ResponseError as err:
            print("Query failed :(")
            print(err)
        # Fails loudly if the bot lacks the proper permissions.
        except discord.HTTPException:
            await self.bot.say("[sad awoo~] I need the embed links permission :(")

    @commands.command(pass_context=True, aliases=TYPES)
    async def image(self, ctx, *, text : str=None):
        """Posts a random anime reaction image macro, typed according to the alias."""
        category = ctx.message.content.replace("~","").split(" ")[0]
        # Posts the command help message if this was invoked without a type.
        if category == "image":
            await send_cmd_help(ctx)
            return
        # NSFW images are enabled in NSFW channels.
        # TODO once discord.py is updated, use Channel.is_nsfw().
        if ctx.message.channel.name == "nsfw":
            await self.anime( category, description=text, nsfw="true" )
        else:
            await self.anime( category, description=text )

    # Calls the core anime() function with a random type.
    @commands.command(pass_context=True)
    async def random(self, ctx, *, text : str=None):
        """Picks a random image from a random category (SFW).""" 
        await self.anime( random.choice(self.types), random=True, description=text )

    @commands.command(pass_context=False)
    async def weebinfo(self):
        """Posts the weeb.sh gateway info."""
        await self.bot.say(self.info)

    # Use this method to set your API key.
    @commands.command(pass_context=True, name='weebkey')
    @checks.is_owner()
    async def _weebkey(self, ctx, key : str):
        """Set your weeb.sh API key."""
        self.settings['WEEB_SH_API_KEY'] = key
        dataIO.save_json(self.settings_file, self.settings)
        await self.bot.delete_message(ctx.message)
        await self.bot.say("Weeb.sh API Key accepted.")
        self.__init__(self.bot)

def check_folder():
    if not os.path.exists("data/weeb"):
        print("Creating data/weeb folder...")
        os.makedirs("data/weeb")

def check_file():
    settings = {}
    settings['WEEB_SH_API_KEY'] = "" 
    f = "data/weeb/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default settings.json...")
        dataIO.save_json(f, settings)

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(WeebSh(bot))
