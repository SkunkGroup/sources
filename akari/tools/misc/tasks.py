import json
import random
import datetime
import logging
import aiohttp

from discord import Embed, NotFound, AllowedMentions

from discord.ext import tasks
from discord.ext.commands import AutoShardedBot as AB
from asyncio import log

log = logging.getLogger(__name__)


@tasks.loop(seconds=30)
async def shard_stats(bot: AB):
    log.info("Collecting shard stats")
    shards = []
    for shard_id, shard in bot.shards.items():
        guilds = [g for g in bot.guilds if g.shard_id == shard_id]
        users = len(bot.users)
        shard_info = {
            "shard_id": shard_id,
            "shard_name": f"Shard {shard_id}",
            "shard_ping": round(
                shard.latency * 1000
            ),  # Kept in milliseconds for internal use
            "shard_guild_count": f"{len(guilds):,}",
            "shard_user_count": f"{users:,}",
            "shard_guilds": [str(g.id) for g in guilds],
            "server_count": len(guilds),  # Added field
            "member_count": users,  # Added field
            "uptime": str(bot.uptime),  # Replace with actual uptime if available
            "latency": round(shard.latency * 1000) / 1000,  # Converted to seconds
            "last_updated": datetime.datetime.utcnow().isoformat(),  # Current timestamp in ISO format
        }
        shards.append(shard_info)

        shard_data = {
            "bot": "Akari",  # Replace with your bot's name or identifier
            "shards": shards,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.akari.bot/shards/post",  # Updated FastAPI server URL
                    json=shard_data,
                    headers={
                        "api-key": "04ced35d-34ab-4094-86b2-6b7e45f8ab83"
                    },  # Replace with your actual API key
                ) as response:
                    if response.status == 200:
                        log.info("Shard data successfully sent to the API")
                    else:
                        log.error(
                            f"Failed to send shard data: {response.status} - {await response.text()}"
                        )
                        log.debug(f"Response headers: {response.headers}")
                        log.debug(f"Request payload: {shard_data}")
        except aiohttp.ClientConnectorError as e:
            log.error(f"Connection error occurred while sending shard data: {e}")
        except aiohttp.ClientResponseError as e:
            log.error(f"Response error occurred while sending shard data: {e}")
        except Exception as e:
            log.error(f"Exception occurred while sending shard data: {e}")


@tasks.loop(minutes=10)
async def counter_update(bot: AB):
    results = await bot.db.fetch("SELECT * FROM counters")
    for result in results:
        channel = bot.get_channel(int(result["channel_id"]))
        if channel:
            guild = channel.guild

            if not guild.chunked:
                await guild.chunk(cache=True)

            if not guild.me.guild_permissions.manage_channels:
                continue

            module = result["module"]

            match module:
                case "members":
                    target = str(guild.member_count)
                case "humans":
                    target = str(len([m for m in guild.members if not m.bot]))
                case "bots":
                    target = str(len([m for m in guild.members if m.bot]))
                case "boosters":
                    target = str(len(guild.premium_subscribers))
                case "voice":
                    target = str(sum(len(c.members) for c in guild.voice_channels))

            name = result["channel_name"].replace("{target}", target)
            await channel.edit(name=name, reason="updating counter")


@tasks.loop(hours=6)
async def pomelo_task(bot: AB):
    bot.cache.delete("pomelo")


@tasks.loop(hours=2)
async def snipe_delete(bot: AB):
    for m in ["snipe", "edit_snipe", "reaction_snipe"]:
        bot.cache.delete(m)


@tasks.loop(seconds=5)
async def reminder_task(bot: AB):
    results = await bot.db.fetch("SELECT * FROM reminder")
    for result in results:
        if datetime.datetime.now().timestamp() > result["date"].timestamp():
            channel = bot.get_channel(int(result["channel_id"]))
            if channel:

                if not channel.guild.chunked:
                    await channel.guild.chunk(cache=True)

                await channel.send(f"🕰️ <@{result['user_id']}> - {result['task']}")
                await bot.db.execute(
                    """
          DELETE FROM reminder 
          WHERE guild_id = $1 
          AND user_id = $2 
          AND channel_id = $3
          """,
                    channel.guild.id,
                    result["user_id"],
                    channel.id,
                )


@tasks.loop(minutes=1)
async def bump_remind(bot):
    results = await bot.db.fetch(
        "SELECT channel_id, reminder, user_id, time FROM bumpreminder WHERE time IS NOT NULL"
    )
    for result in [
        r for r in results if r[3].timestamp() < datetime.datetime.now().timestamp()
    ]:
        channel = bot.get_channel(result[0])
        if channel:
            if not channel.guild.chunked:
                await channel.guild.chunk(cache=True)

            try:
                user = channel.guild.get_member(result[2]) or channel.guild.owner
                x = await bot.embed_build.alt_convert(user, result[1])
                x["allowed_mentions"] = AllowedMentions.all()
                await channel.send(**x)
            except:
                continue
        await bot.db.execute(
            "UPDATE bumpreminder SET time = $1, channel_id = $2, user_id = $3 WHERE channel_id = $4",
            None,
            None,
            None,
            result[0],
        )


@tasks.loop(minutes=10)
async def check_monthly_guilds(bot: AB):
    results = await bot.db.fetch("SELECT * FROM authorize WHERE till IS NOT NULL")
    for result in results:
        if result["till"]:
            if datetime.datetime.now().timestamp() > result["till"].timestamp():
                guild = bot.get_guild(result["guild_id"])
                user = result["user_id"]
                await bot.db.execute(
                    "DELETE FROM authorize WHERE guild_id = $1", result["guild_id"]
                )

                val = await bot.db.fetchrow(
                    "SELECT * FROM authorize WHERE user_id = $1", user
                )
                if not val:
                    if support := bot.get_guild(1005150492382478377):
                        if member := support.get_member(user):
                            if role := support.get_role(1124447347783520318):
                                await member.remove_roles(role)

                if guild:
                    await guild.leave()
                    await bot.get_channel(1122993923422429274).send(
                        f"Left **{guild.name}** (`{guild.id}`). monthly payment not received"
                    )
                else:
                    await bot.get_channel(1122993923422429274).send(
                        f"Removing `{result['guild_id']}`. monthly payment not received"
                    )


@tasks.loop(seconds=5)
async def shit_loop(bot: AB):
    for player in bot.voice_clients:
        if not player.is_playing and not player.awaiting:
            await player.do_next()


@tasks.loop(seconds=5)
async def gw_loop(bot: AB):
    results = await bot.db.fetch("SELECT * FROM giveaway")
    date = datetime.datetime.now()
    for result in results:
        if date.timestamp() > result["finish"].timestamp():
            await gwend_task(bot, result, date)


async def gwend_task(bot: AB, result, date: datetime.datetime):
    members = json.loads(result["members"])
    winners = result["winners"]
    channel_id = result["channel_id"]
    message_id = result["message_id"]
    if channel := bot.get_channel(channel_id):
        if not channel.guild.chunked:
            await channel.guild.chunk(cache=True)

        try:
            message = await channel.fetch_message(message_id)
            wins = []
            if len(members) <= winners:
                embed = Embed(
                    color=bot.color,
                    title=message.embeds[0].title,
                    description=f"Hosted by: <@!{result['host']}>\n\nNot enough entries to determine the winners!",
                )
                await message.edit(embed=embed, view=None)
            else:
                for _ in range(winners):
                    wins.append(random.choice(members))

                embed = Embed(
                    color=bot.color,
                    title=message.embeds[0].title,
                    description=f"Ended <t:{int(date.timestamp())}:R>\nHosted by: <@!{result['host']}>",
                ).add_field(
                    name="winners",
                    value="\n".join([f"**{bot.get_user(w)}** ({w})" for w in wins]),
                )
                await message.edit(embed=embed, view=None)
                await message.reply(
                    f"**{result['title']}** winners:\n"
                    + "\n".join([f"<@{w}> ({w})" for w in wins])
                )
        except NotFound:
            pass

    await bot.db.execute(
        """
    INSERT INTO gw_ended 
    VALUES ($1,$2,$3)
    """,
        channel_id,
        message_id,
        json.dumps(members),
    )
    await bot.db.execute(
        """
    DELETE FROM giveaway 
    WHERE channel_id = $1 
    AND message_id = $2
    """,
        channel_id,
        message_id,
    )