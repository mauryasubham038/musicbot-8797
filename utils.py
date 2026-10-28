import functools
import html
import time

from pyrogram import enums
from pyrogram.types import CallbackQuery, Message

import config
import database as db
from clients import bot


class UserError(Exception):
    """Aisa error jiska message seedha user ko dikhana hai (aur owner log me bhi jayega)."""


_cache = {}


async def is_admin(chat_id, user_id):
    if user_id in config.OWNER_IDS:
        return True
    k = (chat_id, user_id)
    c = _cache.get(k)
    if c and time.time() - c[1] < 60:
        return c[0]
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        ok = m.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except Exception as e:
        ok = False
        if type(e).__name__ == "ChatAdminRequired":
            await db.log_error(chat_id, "is_admin", "Bot admin nahi hai - admin check nahi ho pa raha")
    _cache[k] = (ok, time.time())
    return ok


def esc(t):
    return html.escape(str(t or ""))


def fmt_dur(s):
    s = int(s or 0)
    return f"{s // 60}:{s % 60:02d}"


def _chat_of(u):
    ch = getattr(u, "chat", None)
    if ch is None:
        ch = getattr(getattr(u, "message", None), "chat", None)
    return (ch.id, getattr(ch, "title", None)) if ch else (None, None)


_last_notify = {}


async def notify_log(text):
    k = text[:40]
    if time.time() - _last_notify.get(k, 0) < 60:
        return
    _last_notify[k] = time.time()
    if config.LOG_CHAT_ID:
        try:
            await bot.send_message(config.LOG_CHAT_ID, text[:3500])
        except Exception:
            pass


def safe(where):
    """Handler ko wrap karta hai: error DB me jata hai (kis group me, kahan), user ko friendly message."""
    def deco(fn):
        @functools.wraps(fn)
        async def wrap(client, update, *a, **k):
            if isinstance(update, Message) and update.from_user is None:
                return  # anonymous admin / channel post
            try:
                return await fn(client, update, *a, **k)
            except Exception as e:
                chat_id, title = _chat_of(update)
                msg = f"{type(e).__name__}: {e}"
                await db.log_error(chat_id, where, msg, title)
                user_msg = str(e) if isinstance(e, UserError) else "⚠️ Kuch gadbad hui, owner ko report ho gaya."
                if not isinstance(e, UserError):
                    await notify_log(f"⚠️ <b>Error</b> [{esc(where)}]\n{esc(title)} (<code>{chat_id}</code>)\n<code>{esc(msg[:300])}</code>")
                try:
                    if isinstance(update, CallbackQuery):
                        await update.answer(user_msg[:180], show_alert=True)
                    elif isinstance(update, Message):
                        await update.reply(user_msg)
                except Exception:
                    pass
        return wrap
    return deco
