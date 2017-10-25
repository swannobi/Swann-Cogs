# Swann-Cogs
Cogs for birds and bird-people

* *WeebSh*
    * Weeb.sh is a content delivery network for anime reaction images. I've built a nice wrapper to allow your users to call it and post random reaction images keyed on "category." The Weeb.sh service categorizes all its images, and this cog pulls down the full list of categories on load. The categories are then translated to base-level command alias for the image command (i.e. [p]\<any weeb.sh category>).

* GarPR
    * Gar PR is a ranking system and tournament results archive for Super Smash Brothers Melee. It is based on Microsoft Trueskill, and supports tourament formats from Tio, Challonge, and SmashGG. It is now an open source project, and can be found at https://github.com/ripgarpr/garpr/
    * This cog queries the GarPR backend and does useful data processing to provide interesting stats to users in your Discord server. It loads all data upfront when the cog is loaded by the bot. Data can be refreshed at any time by using [p]reload garpr or by calling [p]garprset refresh.
    * This cog does some data caching in order to avoid excessive network queries. In particular, player ranks and the last 50 player-data objects are cached. Again, either reload the cog or call [p]garprset refresh to invalidate the cache and sync with GarPR.
