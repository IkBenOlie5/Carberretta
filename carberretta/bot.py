# Copyright (c) 2020-2021, Carberra Tutorials
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging
import os
from pathlib import Path

import hikari
from aiohttp import ClientSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from lightbulb.app import BotApp
from pytz import utc

import carberretta
from carberretta import Config, Database

log = logging.getLogger(__name__)

bot = BotApp(
    Config.TOKEN,
    prefix=Config.PREFIX,
    default_enabled_guilds=Config.GUILD_ID,
    owner_ids=Config.OWNER_IDS,
    case_insensitive_prefix_commands=True,
    intents=hikari.Intents.ALL,
)
bot.d._dynamic = Path("./data/dynamic")
bot.d._static = bot.d._dynamic.parent / "static"

bot.d.scheduler = AsyncIOScheduler()
bot.d.scheduler.configure(timezone=utc)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

bot.load_extensions_from("./carberretta/extensions")


@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    bot.d.scheduler.start()
    bot.d.session = ClientSession(trust_env=True)
    log.info("AIOHTTP session started")

    bot.d.database = Database(bot.d._dynamic, bot.d._static)
    await bot.d.database.connect()
    bot.d.scheduler.add_job(bot.d.database.commit, CronTrigger(second=0))


@bot.listen(hikari.StartedEvent)
async def on_started(_: hikari.StartedEvent) -> None:
    await bot.rest.create_message(
        Config.STDOUT_CHANNEL_ID,
        f"Carberretta is now online! (Version {carberretta.__version__})",
    )


@bot.listen(hikari.StoppingEvent)
async def on_stopping(_: hikari.StoppingEvent) -> None:
    await bot.d.database.close()
    await bot.d.session.close()
    log.info("AIOHTTP session closed")
    bot.d.scheduler.shutdown()

    await bot.rest.create_message(
        Config.STDOUT_CHANNEL_ID,
        f"Carberretta is shutting down. (Version {carberretta.__version__})",
    )


@bot.listen(hikari.DMMessageCreateEvent)
async def on_dm_message_create(event: hikari.DMMessageCreateEvent) -> None:
    if event.message.author.is_bot:
        return

    await event.message.respond(
        f"You need to DM <@{795985066530439229}> to send a message to moderators."
    )


def run() -> None:
    if os.name != "nt":
        import uvloop

        uvloop.install()

    bot.run(
        activity=hikari.Activity(
            name=f"/help • Version {carberretta.__version__}",
            type=hikari.ActivityType.WATCHING,
        )
    )