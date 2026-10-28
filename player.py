import asyncio

from pyrogram.errors import ChatAdminRequired, UserAlreadyParticipant, UserNotParticipant
from pytgcalls.types import MediaStream

import database as db
import radio
import search
from clients import assistant, bot, call
from utils import UserError

queues = {}      # chat_id -> [song,...]  (user requests)
now = {}         # chat_id -> song jo abhi baj raha hai
radio_on = set()  # chat_ids jahan radio chal raha hai
_locks = {}
_assistant_id = None


def _lock(chat_id):
    return _locks.setdefault(chat_id, asyncio.Lock())


async def ensure_assistant(chat_id, username=None):
    """Assistant account group me na ho to bot invite link se usse join karwata hai."""
    global _assistant_id
    if _assistant_id is None:
        _assistant_id = (await assistant.get_me()).id
    try:
        await assistant.get_chat(chat_id)  # peer cache me hai aur member bhi
        await assistant.get_chat_member(chat_id, "me")
        return
    except Exception:
        pass
    try:
        target = username or await bot.export_chat_invite_link(chat_id)
        try:
            await assistant.join_chat(target)
        except UserAlreadyParticipant:
            await assistant.get_chat(target)  # already member: bas group assistant ke cache me daalna hai
    except ChatAdminRequired:
        raise UserError("❌ Mujhe admin banao (Invite users permission ke saath), tab assistant join kar payega.")
    except Exception as e:
        if type(e).__name__ in ("UserBannedInChannel", "ChannelBanned"):
            raise UserError("❌ Assistant account is group me banned hai. Usse unban karo.")
        raise


async def _leave(chat_id):
    try:
        await call.leave_call(chat_id)
    except Exception:
        pass


async def play_next(chat_id):
    async with _lock(chat_id):
        last = None
        for _ in range(4):
            song = None
            if queues.get(chat_id):
                song = queues[chat_id].pop(0)
            elif chat_id in radio_on:
                picked = await radio.pick(chat_id)
                if picked:
                    song = dict(picked, source="radio", user_id=None, req_id=None)
            if not song:
                now.pop(chat_id, None)
                await _leave(chat_id)
                return None
            try:
                info = await search.get_stream(song["video_id"])
                await call.play(chat_id, MediaStream(info["url"], video_flags=MediaStream.Flags.IGNORE))
                now[chat_id] = song
                await db.add_play(chat_id, song["video_id"], song.get("source", "search"), song.get("user_id"))
                return song
            except Exception as e:
                name = type(e).__name__
                last = e
                await db.log_error(chat_id, "play", f"{name}: {e} | {song.get('title', '')[:50]}")
                if name == "NoActiveGroupCall" or "No active" in str(e):
                    now.pop(chat_id, None)
                    raise UserError("🎙 Pehle group ka Voice Chat start karo, phir gaana chalao.")
        now.pop(chat_id, None)
        raise UserError(f"❌ Gaana play nahi ho paya ({type(last).__name__}). Dusra try karo.")


async def enqueue(chat_id, song, user_id, req_id=None, query=None):
    if len(queues.get(chat_id, [])) >= 30:
        raise UserError("Queue full (30). Thoda ruko.")
    song = dict(song, user_id=user_id, req_id=req_id, source="search", query=query)
    queues.setdefault(chat_id, []).append(song)
    if chat_id in now or _lock(chat_id).locked():  # gaana chal raha ya abhi start ho raha
        return len(queues[chat_id])
    await play_next(chat_id)
    return 0


async def start_radio(chat_id):
    radio_on.add(chat_id)
    if chat_id not in now:
        try:
            await play_next(chat_id)
        except Exception:
            radio_on.discard(chat_id)
            raise


def stop_radio(chat_id):
    radio_on.discard(chat_id)


async def stop(chat_id):
    queues.pop(chat_id, None)
    radio_on.discard(chat_id)
    now.pop(chat_id, None)
    await _leave(chat_id)


async def pause(chat_id):
    await call.pause(chat_id)


async def resume(chat_id):
    await call.resume(chat_id)


@call.on_update()
async def _on_update(_, update):
    name = type(update).__name__
    chat_id = getattr(update, "chat_id", None)
    if chat_id is None:
        return
    try:
        if name == "StreamEnded":
            await play_next(chat_id)
        elif name == "ChatUpdate":
            from pytgcalls.types import ChatUpdate
            bad = ChatUpdate.Status.CLOSED_VOICE_CHAT | ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP
            if update.status & bad:
                queues.pop(chat_id, None)
                radio_on.discard(chat_id)
                now.pop(chat_id, None)
    except Exception as e:
        await db.log_error(chat_id, "stream_update", f"{type(e).__name__}: {e}")
