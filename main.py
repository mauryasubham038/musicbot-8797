import asyncio
import os

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import enums, idle

import config
import database as db
import radio
from clients import assistant, bot, call


async def health_loop():
    """Har 6 ghante: har group check karta hai - bot nikala gaya? admin hai? Error DB me jata hai."""
    while True:
        await asyncio.sleep(6 * 3600)
        me = await bot.get_me()
        for g in await db.active_groups():
            try:
                m = await bot.get_chat_member(g["chat_id"], me.id)
                if m.status in (enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED):
                    await db.group_leave(g["chat_id"], g["title"], "kick")
                elif m.status != enums.ChatMemberStatus.ADMINISTRATOR:
                    await db.log_error(g["chat_id"], "health", "Bot admin nahi hai (assistant ko invite nahi kar paayega)", g["title"])
            except Exception as e:
                name = type(e).__name__
                await db.log_error(g["chat_id"], "health", f"{name}: {e}", g["title"])
                if name in ("ChannelPrivate", "UserBannedInChannel"):
                    await db.group_leave(g["chat_id"], g["title"], "kick")
            await asyncio.sleep(0.4)


async def keepalive():
    """Render Web Service ko $PORT par kuch sunna padta hai; UptimeRobot isi URL ko ping karke bot jagaye rakhta hai."""
    port = int(os.getenv("PORT", "0") or 0)
    if not port:
        return

    async def handle(reader, writer):
        try:
            await reader.read(1024)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            await writer.drain()
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "0.0.0.0", port)
    asyncio.create_task(server.serve_forever())


async def main():
    await db.init()
    import handlers_admin  # noqa: F401  (handlers register ho jate hain)
    import handlers_user  # noqa: F401
    import player  # noqa: F401

    await bot.start()
    await assistant.start()
    await call.start()
    print("Bot chalu hai. Owners:", config.OWNER_IDS)
    asyncio.create_task(radio.pool_loop())
    asyncio.create_task(health_loop())
    await keepalive()
    await idle()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
