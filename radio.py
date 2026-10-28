"""Radio: pool (songs table) ko queries files se bharta rehta hai, aur har group ke liye best gaana chunta hai.
Score = YouTube popularity (ext_score) + pichhle 30 din me bot par kitna baja (plays30) + thoda randomness."""
import asyncio
import random

import build_queries
import config
import database as db
import search

DAY = 86400


async def refresh_pool(batch=None):
    """Queries ka ek hissa chalakar naye/popular gaane pool me daalta hai. Rotate hota rehta hai."""
    month_tag = __import__("datetime").date.today().strftime("%Y-%m")
    if await db.kv_get("queries_month") != month_tag or not build_queries.list_files():
        build_queries.build()
        await db.kv_set("queries_month", month_tag)

    allq = build_queries.load_queries()
    if not allq:
        return 0
    batch = batch or config.QUERIES_PER_REFRESH
    ptr = int(await db.kv_get("q_ptr", 0)) % len(allq)
    added = 0
    for i in range(batch):
        genre, query = allq[(ptr + i) % len(allq)]
        try:
            for s in (await search.web_search(query, 15))[:8]:
                await search.remember(s, genre)
                added += 1
        except Exception as e:
            await db.log_error(None, "pool_refresh", f"{type(e).__name__}: {e} | {query}")
        await asyncio.sleep(2)
    await db.kv_set("q_ptr", (ptr + batch) % len(allq))
    return added


async def pool_loop():
    if await db.song_count() < 50:
        await refresh_pool(batch=40)  # pehli baar bootstrap
    while True:
        await asyncio.sleep(config.POOL_REFRESH_MINUTES * 60)
        try:
            await refresh_pool()
        except Exception as e:
            await db.log_error(None, "pool_loop", f"{type(e).__name__}: {e}")


async def pick(chat_id):
    cfg = await db.get_radio(chat_id)
    wanted = set(filter(None, (cfg["genres"] if cfg else "").split(",")))
    rows = await db.radio_candidates(db.now() - 30 * DAY)
    if not rows:
        await refresh_pool(batch=10)
        rows = await db.radio_candidates(db.now() - 30 * DAY)
    rows = [r for r in rows if not r["duration"] or r["duration"] <= (config.MAX_SONG_MINUTES + 2) * 60] or rows
    if wanted:
        rows = [r for r in rows if wanted & set(r["genres"].split(","))] or [r for r in rows if r["genres"]] or rows
    else:
        # genre-less gaane (user ke search se aaye) tabhi, jab is mahine kaafi baje ho
        rows = [r for r in rows if r["genres"] or r["plays30"] >= 3] or rows
    recent = set(await db.recent_played(chat_id, 40))
    rows = [r for r in rows if r["video_id"] not in recent] or rows
    if not rows:
        return None
    mx_e = max(r["ext_score"] or 0 for r in rows) or 1
    mx_p = max(r["plays30"] for r in rows) or 1
    for r in rows:
        r["score"] = 0.55 * (r["ext_score"] or 0) / mx_e + 0.45 * r["plays30"] / mx_p + random.random() * 0.15
    top = sorted(rows, key=lambda r: r["score"], reverse=True)[:20]
    return dict(random.choices(top, weights=[r["score"] + 0.05 for r in top], k=1)[0])
