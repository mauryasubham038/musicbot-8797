from pyrogram import Client, enums
from pytgcalls import PyTgCalls

import config

bot = Client(
    "musicbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    workdir=config.SESSION_DIR,
    parse_mode=enums.ParseMode.HTML,
)

assistant = Client(
    "assistant",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    in_memory=True,
)

call = PyTgCalls(assistant)
