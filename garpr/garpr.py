# GarPR integration cog for Red-DiscordBot by Twentysix, an
#   open-source discord bot (github.com/Cog-Creators/Red-DiscordBot)
#
# Authored by Swann (github.com/swannobi)
# GarPR at github.com/garsh0p/garrpr
#
# Route class based on martmists' work on the ram.moe wrapper
#
# Last updated Oct 19, 2017

import discord
import os
import re
import requests
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import urllib
from types import SimpleNamespace

RESOURCES = "data/smashing/"
RANK_EMOTES = ["<:champion:261390756898537473>",
               ":fire:",
               "<:Melee:260154755706257408>",
               ":ok_hand:"]

class GarPR:
    """Contains most smash-based static commands"""

    def __init__(self, bot, resources_folder):
        self.bot = bot
        # Resources
        self.settings = dataIO.load_json(RESOURCES+"garpr_settings.json")
        self.rankings_uri = self.settings["region"]+"/rankings"
        self.players_uri = self.settings["region"]+"/players"
        self.matches_uri = self.settings["region"]+"/matches/"
        self.tournaments_uri = self.settings["region"]+"/tournaments"
        self.url = "https://www.notgarpr.com/#/"
        self.data_url = "https://www.notgarpr.com:3001/"
        # Determine if rankings should be reloaded
        cachedTournies = self.settings["tournaments on record"]
        actualTournies = len(Route(base_url=self.data_url,path=self.tournaments_uri).sync_query()["tournaments"])
        if cachedTournies != actualTournies:
            # Invalidate cached resources
            self._refresh_cog()
            self.matchup_cache = {}
            self.settings["tournaments on record"] = actualTournies
            dataIO.save_json(RESOURCES+"garpr_settings.json", self.settings)
        else:
            # Load cached resources
            self.rankings_cache = dataIO.load_json(RESOURCES+"garpr_rankings.json")
            self.matchup_cache = dataIO.load_json(RESOURCES+"garpr_match_records.json")
            self.players = dataIO.load_json(RESOURCES+"garpr_players.json")

    def _refresh_cog(self):
        """Attempt to sync the bot with the actual GarPR."""
        try:
            self.players = Route(base_url=self.data_url,path=self.players_uri).sync_query()
            self.rankings_cache = Route(base_url=self.data_url,path=self.rankings_uri).sync_query()
            dataIO.save_json(RESOURCES+"garpr_players.json", self.players)
            dataIO.save_json(RESOURCES+"garpr_rankings.json", self.rankings_cache)
        except ResponseError as e:
            print("Couldn't properly refresh garpr. Some commands may not work as expected.")
            print(e)

    def _get_rankings(self):
        try:
            return deepcopy(self.rankings_cache["ranking"])
        except:
            print("Helper.py: something went wrong when copying self.rankings_cache")

    async def _get_player_stats(self, playerid : str):
        """Do the http call to garpr for some playerdata."""
        match_records = deepcopy(self.matchup_cache)
        # If player match data exists in the in-memory cache, return it
        if playerid in match_records:
            return match_records[playerid]
        # Otherwise, get it, store it in the cache
        playerdata = Route(base_url=self.data_url,path=self.matches_uri+playerid).sync_query()
        self.matchup_cache[playerid] = playerdata
        dataIO.save_json(RESOURCES+"garpr_match_records.json", self.matchup_cache)
        return playerdata

    def _get_playerid(self, player : str):
        """Checks for a player in the garpr database given a playername."""
        for entry in self.players["players"]:
            if player.lower() == entry["name"].lower():
                return entry
        raise KeyError("Player not found: "+player)

    @commands.command(pass_context=True, no_pm=False)
    async def stats(self, ctx, *, player : str):
        """Gets garpr tournament statistics for a player.
        
        Use ~stats <player1> VS <player2> to get historical matchup stats, if they exist.

        Be aware that GarPR is created with in-state players in mind. If you want to check
        the match history of an in-state player vs an out-of-state player, the in-state
        player should be listed FIRST.
        """
        # Parse the parameter for any occurance of a delimiter ("vs"), 
        #  which would make this a pvp stats query.
        if any(delim in player.lower() for delim in [" vs ", " vs. ", " versus "]):
            # Grab the two players' names
            p1,p2 = re.sub(r"( vs\. | VS\. | VS )", " vs ", player).split(" vs ")
            try: 
                p1_info = self._get_playerid( p1 )
                p1_matches = await self._get_player_stats( p1_info["id"] )
                matchup = SimpleNamespace()
                matchup.wins = matchup.losses = 0
                matchup.last_tournament = None
                matchup.since = None
                for match in p1_matches["matches"]:
                    if match["opponent_name"].lower() == p2.lower():
                        if not matchup.since:
                            matchup.since = match["tournament_date"]
                        if match["result"] == "win":
                            matchup.wins += 1
                        else:
                            matchup.losses += 1
                        matchup.last_tournament = match["tournament_name"]
                        matchup.last_played = match["tournament_date"]
                if not matchup.since:
                    await self.bot.say("No data for "+p1+"/"+p2+". Use ~stats for more info.")
                    return
            except KeyError as e:
                print(e)
                return
            message = p1+" is ("+str(matchup.wins)+"-"+str(matchup.losses)+") vs "+p2+", since "+str(matchup.since)+"."
            if matchup.last_tournament:
                message += "\nThey last played at "+matchup.last_tournament+" ("+matchup.last_played+")."
            await self.bot.say(message)
            return
        # Since no delimiter was present, this is a single-player stats query.
        try:
            stats = await self._get_player_stats( self._get_playerid( player )["id"] )
            # The PPMD Contingency
            if stats["losses"] == 0:
                ratio = "∞"
            else:
                ratio = str(round(stats["wins"]/stats["losses"], 3))
            await self.bot.say("I can see "+player+" has "+str(len(stats["matches"]))+" match "
            "records, since "+stats["matches"][0]["tournament_date"]+"\n"
            "This player has "+str(stats["wins"])+" wins "
            "and "+str(stats["losses"])+" losses ("+ratio+")")
        except KeyError as e:
            print(e)

    @commands.command(pass_context=True, no_pm=True)
    async def garpr(self, ctx, *, player : str=None):
        """Returns the state garpr, or the ranking for a particular player."""
        if not player:
            await self.bot.say(self.url+self.rankings_uri)
        else:
            try:
                playerinfo = self._get_playerid( player )
            except KeyError as e:
                print(e)
                return
            stats = await self._get_player_stats( playerinfo["id"] )
            rating = playerinfo["ratings"][self.settings["region"]]["mu"]
            sigma = playerinfo["ratings"][self.settings["region"]]["sigma"]
            data = discord.Embed(title=playerinfo["name"], url=self.url+self.players_uri+"/"+playerinfo["id"])
            # Sorry for the magic numbers. This is just how garpr calculates the adjusted
            #  rating behind the scenes. Since it only exposes the unadjusted ratings, we
            #  have do to this calculation on the fly.
            data.add_field(name="Adjusted rating:", value="*_"+str(round(rating-(3*sigma), 3))+"_*")
            for guy in self._get_rankings():
                # Only add the rank field if the player is, indeed, ranked
                if guy["name"] == playerinfo["name"]:
                    data.add_field(name="rank", value=guy["rank"])
                    if 1 == guy["rank"]:
                        # TODO make the colors and emotes customizable
                        data.colour = discord.Colour.dark_green()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+RANK_EMOTES[0])
                    elif 1 < guy["rank"] < 11:
                        data.colour = discord.Colour.gold()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+RANK_EMOTES[1])
                    elif 11 <= guy["rank"] < 26:
                        data.colour = discord.Colour.light_grey()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+RANK_EMOTES[2])
                    elif 26 <= guy["rank"] < 51:
                        data.colour = discord.Colour.purple()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+RANK_EMOTES[3])
                    elif 51 <= guy["rank"] < 101:
                        data.colour = discord.Colour(0x998866)
            data.set_footer(text="notgarpr-discord integration by Swann")
            try:
                await self.bot.say(embed=data) 
            except discord.HTTPException:
                await self.bot.say("I need the embed links permission :(")

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def garprset(self, ctx):
        """Changes the settings for retrieving data from GarPR"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @garprset.command(pass_context=True, no_pm=False, name="region")
    @checks.mod_or_permissions()
    async def _region(self, ctx, state : str):
        """Sets the state for GarPR. Must match the GarPR URI exactly (e.g. "Central Florida" region is "cfl")."""
        self.settings["region"] = state
        dataIO.save_json(RESOURCES+"garpr_settings.json", self.settings)
        # Invalidate all local caches
        await self.bot.say("Set new region: "+state+", refreshing data now...")
        await self._refresh_cog()

# Handles request routing
class Route:
    def __init__(self, base_url, path, headers=None, method="GET"):
        self.base_url = base_url
        self.path = path
        self.headers = headers
        self.method = method

    # Introspection: call the requests.get(url, headers) method
    def sync_query(self, url_params=None):
        result = getattr( requests, self.method.lower() )(
                self.base_url+self.path, headers=self.headers)
        if 200 <= result.status_code < 300:
            return result.json()
        else:
            raise ResponseError("Got an unsuccessful response code: {}, from {}".format(result.status_code, self.base_url+self.path))

    def __call__(self, url_params=None):
        return self.sync_query(url_params)

class ResponseError(BaseException):
    pass

def check_folders():
    if not os.path.exists(RESOURCES):
        print("Creating smashing data folder...")
        os.makedirs(RESOURCES)

def check_files():
    garpr = RESOURCES+"garpr_rankings.json"
    records = RESOURCES+"garpr_match_records.json"
    settings = RESOURCES+"garpr_settings.json"
    if not dataIO.is_valid_json(garpr):
        print("Creating empty "+str(garpr)+"...")
        dataIO.save_json(garpr, {})
    if not dataIO.is_valid_json(records):
        print("Creating empty "+str(records)+"...")
        dataIO.save_json(records, {})
    if not dataIO.is_valid_json(settings):
        print("Creating empty "+str(settings)+"...")
        dataIO.save_json(settings, {})

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(GarPR(bot, RESOURCES))
