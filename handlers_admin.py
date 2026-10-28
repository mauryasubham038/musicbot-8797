import asyncio
import csv
import datetime
from collections import Counter

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Kb

import config
import database as db
import player
import radio
from clients import bot
from utils import esc, safe

owner = filters.user(config.OWNER_IDS)
# sirf pakka "nikala gaya" wale errors; PeerIdInvalid/ChannelInvalid ka matlab sirf "session ne group abhi dekha nahi"
DEAD = {"ChannelPrivate", "UserBannedInChannel"}


def _t(ts):
    return datetime.datetime.fromtimestamp(ts, db.IST).strftime("%d-%m %H:%M")


async def panel_text():
    s = await db.stats()
    top = "\n".join(f"  {i}. {esc(r['title'][:45])} ({r['c']})" for i, r in enumerate(s["top_month"], 1)) or "  -"
    return (
        "📊 <b>Admin Panel</b>\n\n"
        f"👥 Active groups: <b>{s['active']}</b>  (kicked total: {s['kicked_total']})\n"
        f"📻 Radio chal raha: {len(player.radio_on)} | 🎧 VC me abhi: {len(player.now)}\n\n"
        f"<b>Aaj</b>: ➕ {s['join_day']} join | ➖ {s['kick_day']} kick | 🚪 {s['left_day']} left\n"
        f"<b>Is mahine</b>: ➕ {s['join_month']} join | ➖ {s['kick_month']} kick | 🚪 {s['left_month']} left\n\n"
        f"🎵 Plays aaj: {s['plays_day']} | mahine: {s['plays_month']}\n"
        f"⚠️ Errors aaj: {s['err_day']} ({s['err_groups_day']} groups)\n"
        f"💿 Pool me gaane: {s['songs']}\n\n"
        f"🔥 <b>Is mahine top:</b>\n{top}"
    )


PANEL_KB = Kb([
    [Btn("🔄 Refresh", callback_data="panel:main"), Btn("⚠️ Errors", callback_data="panel:errors")],
    [Btn("👥 Problem groups", callback_data="panel:groups"), Btn("📣 Broadcast", callback_data="panel:bc")],
    [Btn("📤 Export CSV", callback_data="panel:export"), Btn("💿 Pool refresh", callback_data="panel:pool")],
])


async def errors_text(hours=24):
    rows = await db.recent_errors(db.now() - hours * 3600)
    if not rows:
        return "✅ Pichhle 24 ghante me koi error nahi."
    by = {}
    for r in rows:
        by.setdefault(r["chat_id"], []).append(r)
    lines = [f"⚠️ <b>Errors (24h): {len(rows)}</b>\n"]
    for cid, lst in sorted(by.items(), key=lambda x: -len(x[1]))[:15]:
        last = lst[0]
        lines.append(f"• <b>{esc(last['title'] or 'System')}</b> <code>{cid}</code> - {len(lst)}x\n"
                     f"  [{esc(last['where_'])}] {esc(last['error'][:110])}")
    return "\n".join(lines)


async def groups_text():
    rows = await db.problem_groups(db.now() - 86400)
    if not rows:
        return "✅ Kisi group me problem nahi mili (24h)."
    lines = ["👥 <b>Problem groups (24h)</b>\n"]
    for r in rows:
        lines.append(f"• {esc(r['title'])} <code>{r['chat_id']}</code> [{r['status']}] - {r['n']} errors\n  {esc((r['last_error'] or '')[:120])}")
    return "\n".join(lines)


BC_HELP = ("📣 <b>Broadcast</b>\nKisi message ko reply karke <code>/broadcast</code> likho (photo/video/text sab chalega),\n"
           "ya <code>/broadcast text yahan</code>. Group me pin ke liye <code>-pin</code> jodo.\n"
           "Flood-limit se bachne ke liye dheere bhejta hai aur har failure ka reason report karta hai.")


@bot.on_message(filters.command(["panel", "admin"]) & owner)
@safe("panel")
async def cmd_panel(_, m):
    await m.reply(await panel_text(), reply_markup=PANEL_KB)


@bot.on_callback_query(filters.regex(r"^panel:") & owner)
@safe("panel_cb")
async def cb_panel(_, cq):
    act = cq.data.split(":")[1]
    if act == "export":
        await cq.answer("Bhej raha hu...")
        return await _export(cq.message.chat.id)
    if act == "pool":
        await cq.answer("Pool refresh shuru (background)")
        asyncio.create_task(radio.refresh_pool(batch=20))
        return
    text = {"main": panel_text, "errors": errors_text, "groups": groups_text}.get(act)
    body = await text() if text else BC_HELP
    try:
        await cq.message.edit(body, reply_markup=PANEL_KB)
    except Exception:
        pass
    await cq.answer()


@bot.on_message(filters.command("errors") & owner)
@safe("errors")
async def cmd_errors(_, m):
    await m.reply(await errors_text())


@bot.on_message(filters.command("groups") & owner)
@safe("groups")
async def cmd_groups(_, m):
    await m.reply(await groups_text())


@bot.on_message(filters.command("clearerrors") & owner)
@safe("clearerrors")
async def cmd_clear(_, m):
    await db.clear_errors()
    await m.reply("🧹 Errors saaf.")


async def _export(chat_id):
    rows = await db.events_since(db.month_start())
    path = "group_events.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time_ist", "chat_id", "title", "event", "by_user"])
        for r in rows:
            w.writerow([_t(r["ts"]), r["chat_id"], r["title"], r["event"], r["by_user"]])
    await bot.send_document(chat_id, path, caption="Is mahine ke join/kick/left events")


@bot.on_message(filters.command("export") & owner)
@safe("export")
async def cmd_export(_, m):
    await _export(m.chat.id)


@bot.on_message(filters.command("broadcast") & owner)
@safe("broadcast")
async def cmd_broadcast(_, m):
    pin = "-pin" in m.command
    raw = (m.text or "").split(None, 1)
    text = raw[1].replace("-pin", "").strip() if len(raw) > 1 else ""
    src = m.reply_to_message
    if not src and not text:
        return await m.reply(BC_HELP)
    groups = await db.active_groups()
    status = await m.reply(f"📣 {len(groups)} groups me bhej raha hu...")
    asyncio.create_task(_do_broadcast(groups, src, text, pin, status))


async def _send(cid, src, text):
    return await (bot.copy_message(cid, src.chat.id, src.id) if src else bot.send_message(cid, text))


async def _do_broadcast(groups, src, text, pin, status):
    ok, fails = 0, Counter()
    for i, g in enumerate(groups, 1):
        cid = g["chat_id"]
        try:
            try:
                sent = await _send(cid, src, text)
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                sent = await _send(cid, src, text)
            if pin:
                try:
                    await sent.pin(disable_notification=True)
                except Exception:
                    pass
            ok += 1
        except Exception as e:
            name = type(e).__name__
            fails[name] += 1
            await db.log_error(cid, "broadcast", f"{name}: {e}", g["title"])
            if name in DEAD:
                await db.group_leave(cid, g["title"], "kick")
        await asyncio.sleep(0.35)
        if i % 25 == 0:
            try:
                await status.edit(f"📣 {i}/{len(groups)} ... ✅ {ok}")
            except Exception:
                pass
    failed = sum(fails.values())
    await db.save_broadcast(len(groups), ok, failed)
    why = "\n".join(f"  • {k}: {v}" for k, v in fails.most_common()) or "  -"
    await status.edit(f"✅ Broadcast pura\nBheja: <b>{ok}</b> / {len(groups)}\nFail: {failed}\n{why}")
