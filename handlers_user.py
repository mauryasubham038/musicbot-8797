from pyrogram import enums, filters
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Kb

import build_queries
import database as db
import player
import search
from clients import bot
from utils import UserError, esc, fmt_dur, is_admin, safe

forms = {}  # (user_id, chat_id) -> set(genres)
_last_play = {}  # user_id -> time
_me = None


async def bot_username():
    global _me
    if not _me:
        _me = (await bot.get_me()).username
    return _me


def pretty(g):
    return g.replace("_", " ").title()


HELP = (
    "🎵 <b>Music Bot</b>\n\n"
    "/play <i>gaane ka naam</i> - VC me gaana (spelling galat ho tab bhi chalega)\n"
    "/skip /stop /pause /resume /queue /now\n\n"
    "📻 <b>Radio</b> (sirf admin): /radio on, /radio off, /radio setup"
)


@bot.on_message(filters.command(["start", "help"]) & filters.private)
@safe("start_dm")
async def start_dm(_, m):
    arg = m.command[1] if len(m.command) > 1 else ""
    if arg.startswith("setup_"):
        return await show_form(m, m.from_user.id, int(arg[6:]))
    await m.reply(HELP + "\n\nRadio ka form bharne ke liye: /radio_setup",
                  reply_markup=Kb([[Btn("📻 Radio setup (private form)", callback_data="rs:list")]]))


@bot.on_message(filters.command(["start", "help"]) & filters.group)
@safe("start_group")
async def start_group(_, m):
    await db.touch_group(m.chat.id, m.chat.title)
    await m.reply(HELP)


@bot.on_message(filters.command(["play", "p"]) & filters.group)
@safe("play")
async def cmd_play(_, m):
    await db.touch_group(m.chat.id, m.chat.title)
    if m.chat.id in player.radio_on:
        return await m.reply("📻 Abhi radio chal raha hai. Gaana maangne ke liye admin pehle <code>/radio off</code> kare.")
    import time
    if time.time() - _last_play.get(m.from_user.id, 0) < 4:
        return  # spam se bachne ke liye 4 sec cooldown
    _last_play[m.from_user.id] = time.time()
    query = " ".join(m.command[1:]).strip()
    if not query:
        return await m.reply("Aise likho: <code>/play tum hi ho</code>")
    status = await m.reply("🔎 Dhundh raha hu...")
    results = await search.find_best(query)
    if not results:
        return await status.edit("😕 Kuch nahi mila, thoda alag likh ke try karo.")
    await player.ensure_assistant(m.chat.id, m.chat.username)
    best = results[0]
    pos = await player.enqueue(m.chat.id, best, m.from_user.id, req_id=m.id, query=query)
    head = "▶️ <b>Ab baj raha hai</b>" if pos == 0 else f"📝 <b>Queue #{pos}</b>"
    text = f"{head}\n{esc(best['title'])}\n⏱ {fmt_dur(best.get('duration'))}"
    kb = None
    if len(results) > 1:
        rows = [[Btn(f"🔁 {r['title'][:40]}", callback_data=f"pick:{m.from_user.id}:{m.id}:{r['video_id']}")]
                for r in results[1:4]]
        kb = Kb(rows)
        text += "\n\n<i>Ye nahi tha? Neeche se sahi wala chuno:</i>"
    await status.edit(text, reply_markup=kb)


@bot.on_callback_query(filters.regex(r"^pick:"))
@safe("pick")
async def cb_pick(_, cq):
    _, uid, req_id, vid = cq.data.split(":", 3)
    chat_id = cq.message.chat.id
    if cq.from_user.id != int(uid) and not await is_admin(chat_id, cq.from_user.id):
        return await cq.answer("Ye request tumhari nahi hai.", show_alert=True)
    song = await db.get_song(vid)
    if not song:
        return await cq.answer("Gaana nahi mila.", show_alert=True)
    req_id = int(req_id)
    cur = player.now.get(chat_id)
    query = None
    q = player.queues.setdefault(chat_id, [])
    new = dict(song, user_id=int(uid), req_id=req_id, source="search")
    if cur and cur.get("req_id") == req_id:
        query = cur.get("query")
        new["query"] = query
        q.insert(0, new)
        await player.play_next(chat_id)
    else:
        for i, s in enumerate(q):
            if s.get("req_id") == req_id:
                query = s.get("query")
                new["query"] = query
                q[i] = new
                break
        else:
            return await cq.answer("Wo request ab queue me nahi hai.", show_alert=True)
    if query:
        await db.set_alias(search.phon(query), vid)  # agli baar yehi galat spelling seedha sahi gaana laayegi
    await cq.message.edit(f"✅ Badal diya: <b>{esc(song['title'])}</b>")


async def _admin_or_requester(m):
    cur = player.now.get(m.chat.id)
    if await is_admin(m.chat.id, m.from_user.id):
        return True
    return bool(cur and cur.get("user_id") == m.from_user.id)


@bot.on_message(filters.command("skip") & filters.group)
@safe("skip")
async def cmd_skip(_, m):
    if m.chat.id not in player.now:
        return await m.reply("Abhi kuch nahi baj raha.")
    if not await _admin_or_requester(m):
        return await m.reply("Skip sirf admin ya jisne gaana lagaya wo kar sakta hai.")
    song = await player.play_next(m.chat.id)
    await m.reply(f"⏭ Ab: <b>{esc(song['title'])}</b>" if song else "⏹ Queue khatam, VC chhod diya.")


@bot.on_message(filters.command(["stop", "end"]) & filters.group)
@safe("stop")
async def cmd_stop(_, m):
    if not await is_admin(m.chat.id, m.from_user.id):
        return await m.reply("Ye sirf admin kar sakte hain.")
    await player.stop(m.chat.id)
    await m.reply("⏹ Band kar diya.")


@bot.on_message(filters.command("pause") & filters.group)
@safe("pause")
async def cmd_pause(_, m):
    if not await is_admin(m.chat.id, m.from_user.id):
        return await m.reply("Ye sirf admin kar sakte hain.")
    await player.pause(m.chat.id)
    await m.reply("⏸ Pause")


@bot.on_message(filters.command("resume") & filters.group)
@safe("resume")
async def cmd_resume(_, m):
    if not await is_admin(m.chat.id, m.from_user.id):
        return await m.reply("Ye sirf admin kar sakte hain.")
    await player.resume(m.chat.id)
    await m.reply("▶️ Resume")


@bot.on_message(filters.command(["queue", "q"]) & filters.group)
@safe("queue")
async def cmd_queue(_, m):
    cur, q = player.now.get(m.chat.id), player.queues.get(m.chat.id, [])
    if not cur:
        return await m.reply("Queue khali hai.")
    tag = "📻" if cur.get("source") == "radio" else "▶️"
    lines = [f"{tag} {esc(cur['title'])}"] + [f"{i}. {esc(s['title'])}" for i, s in enumerate(q[:10], 1)]
    if player.radio_on and m.chat.id in player.radio_on:
        lines.append("\n📻 Radio ON - queue ke baad auto gaane bajte rahenge")
    await m.reply("\n".join(lines))


@bot.on_message(filters.command(["now", "np"]) & filters.group)
@safe("now")
async def cmd_now(_, m):
    cur = player.now.get(m.chat.id)
    await m.reply(f"🎶 {esc(cur['title'])}" if cur else "Abhi kuch nahi baj raha.")


# ---------------- Radio ----------------
@bot.on_message(filters.command("radio") & filters.group)
@safe("radio")
async def cmd_radio(_, m):
    await db.touch_group(m.chat.id, m.chat.title)
    if not await is_admin(m.chat.id, m.from_user.id):
        return await m.reply("📻 Radio sirf admin chala sakte hain. Aap gaana /play se maang sakte ho.")
    arg = (m.command[1] if len(m.command) > 1 else "on").lower()
    if arg == "skip":
        if m.chat.id not in player.radio_on:
            return await m.reply("📻 Radio abhi chalu nahi hai.")
        song = await player.play_next(m.chat.id)
        return await m.reply(f"⏭ Ab: <b>{esc(song['title'])}</b>" if song else "⏹ Koi gaana nahi mila.")
    if arg == "setup":
        link = f"https://t.me/{await bot_username()}?start=setup_{m.chat.id}"
        return await m.reply("📝 Radio ka form private me bharo:", reply_markup=Kb([[Btn("Form kholo", url=link)]]))
    if arg == "off":
        player.stop_radio(m.chat.id)
        cur = player.now.get(m.chat.id)
        if cur and cur.get("source") == "radio":
            await player.play_next(m.chat.id)  # radio ka gaana turant band, queue khali to VC chhod dega
        return await m.reply("📻 Radio band. Ab sab <code>/play naam</code> se gaana maang sakte hain.")
    cfg = await db.get_radio(m.chat.id)
    if not cfg:  # group abhi connect nahi hua -> pehle private form
        link = f"https://t.me/{await bot_username()}?start=setup_{m.chat.id}"
        return await m.reply("🔗 Radio chalane se pehle group ko connect karo - private me form bharo (1 minute):",
                             reply_markup=Kb([[Btn("📻 Group connect / Form", url=link)]]))
    await player.ensure_assistant(m.chat.id, m.chat.username)
    await player.start_radio(m.chat.id)
    info = ", ".join(pretty(g) for g in cfg["genres"].split(",")) if cfg["genres"] else "Sab genre"
    await m.reply(f"📻 <b>Radio ON</b>\nGenre: {esc(info)}\nRadio chalte waqt /play band rahega; <code>/radio off</code> ke baad user gaana maang sakte hain.")


# ---------------- Private form ----------------
async def _admin_groups(user_id):
    out = []
    for g in (await db.active_groups())[:150]:
        if await is_admin(g["chat_id"], user_id):
            out.append(g)
    return out


@bot.on_message(filters.command("radio_setup") & filters.private)
@safe("radio_setup")
async def cmd_radio_setup(_, m):
    await list_groups(m, m.from_user.id)


async def list_groups(target, user_id, edit=False):
    groups = await _admin_groups(user_id)
    if not groups:
        text = "Aap kisi aise group ke admin nahi mile jisme ye bot hai. Pehle bot ko group me add karo."
        return await (target.edit(text) if edit else target.reply(text))
    rows = [[Btn(g["title"][:40], callback_data=f"rs:g:{g['chat_id']}")] for g in groups[:30]]
    text = "📻 Kaunsa group connect karna hai?"
    kb = Kb(rows)
    await (target.edit(text, reply_markup=kb) if edit else target.reply(text, reply_markup=kb))


async def show_form(target, user_id, chat_id, edit=False):
    if not await is_admin(chat_id, user_id):
        raise UserError("Aap us group ke admin nahi ho.")
    key = (user_id, chat_id)
    if key not in forms:
        cfg = await db.get_radio(chat_id)
        forms[key] = set(filter(None, (cfg["genres"] if cfg else "").split(",")))
    sel, gl = forms[key], build_queries.genres()
    btns = [Btn(("✅ " if g in sel else "▫️ ") + pretty(g), callback_data=f"rs:t:{chat_id}:{i}") for i, g in enumerate(gl)]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append([Btn("💾 Save", callback_data=f"rs:s:{chat_id}"), Btn("🌐 Sab genre", callback_data=f"rs:a:{chat_id}")])
    g = await db.one("SELECT title FROM groups WHERE chat_id=?", (chat_id,))
    text = f"📻 <b>Radio form</b> - {esc(g['title'] if g else chat_id)}\nJo genre bajane hain wo chuno, phir Save:"
    kb = Kb(rows)
    await (target.edit(text, reply_markup=kb) if edit else target.reply(text, reply_markup=kb))


@bot.on_callback_query(filters.regex(r"^rs:"))
@safe("radio_form")
async def cb_form(_, cq):
    parts = cq.data.split(":")
    uid = cq.from_user.id
    if parts[1] == "list":
        return await list_groups(cq.message, uid, edit=True)
    chat_id = int(parts[2])
    if not await is_admin(chat_id, uid):
        return await cq.answer("Aap us group ke admin nahi ho.", show_alert=True)
    if parts[1] == "g":
        await show_form(cq.message, uid, chat_id, edit=True)
    elif parts[1] == "t":
        key = (uid, chat_id)
        g = build_queries.genres()[int(parts[3])]
        forms.setdefault(key, set()).symmetric_difference_update({g})
        await show_form(cq.message, uid, chat_id, edit=True)
    elif parts[1] == "a":
        forms[(uid, chat_id)] = set()
        await show_form(cq.message, uid, chat_id, edit=True)
    elif parts[1] == "s":
        sel = sorted(forms.get((uid, chat_id), set()))
        await db.set_radio(chat_id, sel, uid)
        label = ", ".join(pretty(g) for g in sel) if sel else "Sab genre"
        await cq.message.edit(f"✅ Save ho gaya: <b>{esc(label)}</b>\nAb group me <code>/radio on</code> likho.")
    await cq.answer()


# ---------------- Bot ka join / kick tracking ----------------
@bot.on_chat_member_updated()
@safe("member_update")
async def on_member(_, u):
    me = await bot.get_me()
    new = u.new_chat_member
    if not new or new.user.id != me.id or u.chat.type not in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        return
    S = enums.ChatMemberStatus
    by = u.from_user.id if u.from_user else None
    title = u.chat.title
    if new.status in (S.MEMBER, S.ADMINISTRATOR):
        if await db.group_join(u.chat.id, title, by):
            link = f"https://t.me/{me.username}?start=setup_{u.chat.id}"
            try:
                await bot.send_message(
                    u.chat.id,
                    "🎵 Namaste! Gaana: <code>/play naam</code>\n📻 Admin radio chalane ke liye neeche form bharo, phir <code>/radio on</code>.",
                    reply_markup=Kb([[Btn("📻 Radio form (private)", url=link)]]))
            except Exception as e:
                await db.log_error(u.chat.id, "welcome", f"{type(e).__name__}: {e}", title)
    elif new.status in (S.LEFT, S.BANNED):
        kicked = new.status == S.BANNED or (u.from_user and u.from_user.id != new.user.id)
        await db.group_leave(u.chat.id, title, "kick" if kicked else "left", by)
        await player.stop(u.chat.id)
