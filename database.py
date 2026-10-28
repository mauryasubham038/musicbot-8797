import datetime
import time

import aiosqlite

import config

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def now():
    return int(time.time())


def day_start():
    d = datetime.datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(d.timestamp())


def month_start():
    d = datetime.datetime.now(IST).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(d.timestamp())


SCHEMA = """
CREATE TABLE IF NOT EXISTS groups(chat_id INTEGER PRIMARY KEY, title TEXT, status TEXT, joined_at INTEGER,
  left_at INTEGER, added_by INTEGER, last_error TEXT, last_error_ts INTEGER);
CREATE TABLE IF NOT EXISTS group_events(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, title TEXT,
  event TEXT, ts INTEGER, by_user INTEGER);
CREATE INDEX IF NOT EXISTS ix_ge_ts ON group_events(ts);
CREATE TABLE IF NOT EXISTS songs(video_id TEXT PRIMARY KEY, title TEXT, channel TEXT, duration INTEGER,
  views INTEGER, phon TEXT, genres TEXT, ext_score REAL, added_ts INTEGER, updated_ts INTEGER);
CREATE TABLE IF NOT EXISTS plays(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, video_id TEXT,
  ts INTEGER, source TEXT, user_id INTEGER);
CREATE INDEX IF NOT EXISTS ix_plays_ts ON plays(ts);
CREATE TABLE IF NOT EXISTS aliases(phon TEXT PRIMARY KEY, video_id TEXT, hits INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS radio(chat_id INTEGER PRIMARY KEY, genres TEXT, set_by INTEGER, updated INTEGER);
CREATE TABLE IF NOT EXISTS errors(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, chat_id INTEGER,
  title TEXT, where_ TEXT, error TEXT);
CREATE INDEX IF NOT EXISTS ix_err_ts ON errors(ts);
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS broadcasts(id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, total INTEGER,
  ok INTEGER, failed INTEGER);
"""

_db = None


async def init():
    global _db
    _db = await aiosqlite.connect(config.DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.executescript(SCHEMA)
    await _db.commit()


async def q(sql, args=()):
    async with _db.execute(sql, args) as cur:
        return [dict(r) for r in await cur.fetchall()]


async def one(sql, args=()):
    rows = await q(sql, args)
    return rows[0] if rows else None


async def run(sql, args=()):
    await _db.execute(sql, args)
    await _db.commit()


async def _count(sql, args=()):
    return (await one(sql, args))["c"]


# ---------- key/value ----------
async def kv_get(k, default=None):
    r = await one("SELECT v FROM kv WHERE k=?", (k,))
    return r["v"] if r else default


async def kv_set(k, v):
    await run("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))


# ---------- groups ----------
async def group_join(chat_id, title, by=None):
    """True agar naya join record hua."""
    g = await one("SELECT status FROM groups WHERE chat_id=?", (chat_id,))
    if g and g["status"] == "active":
        return False
    await run(
        "INSERT INTO groups(chat_id,title,status,joined_at,added_by) VALUES(?,?,?,?,?) "
        "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title,status='active',joined_at=excluded.joined_at,"
        "added_by=excluded.added_by,last_error=NULL",
        (chat_id, title, "active", now(), by),
    )
    await run("INSERT INTO group_events(chat_id,title,event,ts,by_user) VALUES(?,?,?,?,?)",
              (chat_id, title, "join", now(), by))
    return True


async def group_leave(chat_id, title, event="kick", by=None):
    new = "kicked" if event == "kick" else "left"
    g = await one("SELECT status FROM groups WHERE chat_id=?", (chat_id,))
    if g and g["status"] == new:
        return False
    await run(
        "INSERT INTO groups(chat_id,title,status,left_at) VALUES(?,?,?,?) "
        "ON CONFLICT(chat_id) DO UPDATE SET title=COALESCE(excluded.title,title),status=excluded.status,left_at=excluded.left_at",
        (chat_id, title, new, now()),
    )
    await run("INSERT INTO group_events(chat_id,title,event,ts,by_user) VALUES(?,?,?,?,?)",
              (chat_id, title, event, now(), by))
    return True


async def touch_group(chat_id, title):
    """Purane groups (jo DB se pehle ke hain) bina event ke track me aa jayen."""
    await run(
        "INSERT INTO groups(chat_id,title,status,joined_at) VALUES(?,?,'active',?) "
        "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title",
        (chat_id, title, now()),
    )


async def active_groups():
    return await q("SELECT chat_id,title FROM groups WHERE status='active' ORDER BY joined_at")


async def groups_of_status(status):
    return await q("SELECT chat_id,title FROM groups WHERE status=?", (status,))


# ---------- errors ----------
async def log_error(chat_id, where, error, title=None):
    if title is None and chat_id:
        g = await one("SELECT title FROM groups WHERE chat_id=?", (chat_id,))
        title = g["title"] if g else None
    error = str(error)[:500]
    await run("INSERT INTO errors(ts,chat_id,title,where_,error) VALUES(?,?,?,?,?)",
              (now(), chat_id, title, where, error))
    if chat_id:
        await run("UPDATE groups SET last_error=?,last_error_ts=? WHERE chat_id=?",
                  (f"[{where}] {error[:200]}", now(), chat_id))


async def recent_errors(since, limit=300):
    return await q("SELECT * FROM errors WHERE ts>=? ORDER BY ts DESC LIMIT ?", (since, limit))


async def clear_errors():
    await run("DELETE FROM errors")
    await run("UPDATE groups SET last_error=NULL,last_error_ts=NULL")


# ---------- songs ----------
async def upsert_song(video_id, title, channel, duration, views, phon, genre, ext_score):
    old = await one("SELECT genres FROM songs WHERE video_id=?", (video_id,))
    genres = set(filter(None, (old["genres"] if old else "").split(",")))
    if genre:
        genres.add(genre)
    g = ",".join(sorted(genres))
    await run(
        "INSERT INTO songs(video_id,title,channel,duration,views,phon,genres,ext_score,added_ts,updated_ts) "
        "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(video_id) DO UPDATE SET views=excluded.views,"
        "ext_score=excluded.ext_score,updated_ts=excluded.updated_ts,genres=?",
        (video_id, title, channel, duration, views, phon, g, ext_score, now(), now(), g),
    )


async def get_song(video_id):
    return await one("SELECT * FROM songs WHERE video_id=?", (video_id,))


async def all_songs_light():
    return await q("SELECT video_id,title,phon,ext_score FROM songs")


async def song_count():
    return await _count("SELECT COUNT(*) c FROM songs")


async def get_alias(phon):
    return await one("SELECT * FROM aliases WHERE phon=?", (phon,))


async def set_alias(phon, video_id):
    await run(
        "INSERT INTO aliases(phon,video_id,hits) VALUES(?,?,1) "
        "ON CONFLICT(phon) DO UPDATE SET video_id=excluded.video_id,hits=hits+1",
        (phon, video_id),
    )


# ---------- plays / radio ----------
async def add_play(chat_id, video_id, source, user_id):
    await run("INSERT INTO plays(chat_id,video_id,ts,source,user_id) VALUES(?,?,?,?,?)",
              (chat_id, video_id, now(), source, user_id))


async def recent_played(chat_id, n=40):
    rows = await q("SELECT video_id FROM plays WHERE chat_id=? ORDER BY id DESC LIMIT ?", (chat_id, n))
    return [r["video_id"] for r in rows]


async def radio_candidates(since):
    return await q(
        "SELECT s.video_id,s.title,s.channel,s.duration,s.genres,s.ext_score,COALESCE(p.c,0) AS plays30 "
        "FROM songs s LEFT JOIN (SELECT video_id,COUNT(*) c FROM plays WHERE ts>? GROUP BY video_id) p "
        "ON p.video_id=s.video_id",
        (since,),
    )


async def get_radio(chat_id):
    return await one("SELECT * FROM radio WHERE chat_id=?", (chat_id,))


async def set_radio(chat_id, genres, by):
    await run(
        "INSERT INTO radio(chat_id,genres,set_by,updated) VALUES(?,?,?,?) "
        "ON CONFLICT(chat_id) DO UPDATE SET genres=excluded.genres,set_by=excluded.set_by,updated=excluded.updated",
        (chat_id, ",".join(genres), by, now()),
    )


# ---------- stats ----------
async def stats():
    d, mo = day_start(), month_start()
    ev = "SELECT COUNT(*) c FROM group_events WHERE event=? AND ts>=?"
    return {
        "active": await _count("SELECT COUNT(*) c FROM groups WHERE status='active'"),
        "kicked_total": await _count("SELECT COUNT(*) c FROM groups WHERE status='kicked'"),
        "join_day": await _count(ev, ("join", d)),
        "join_month": await _count(ev, ("join", mo)),
        "kick_day": await _count(ev, ("kick", d)),
        "kick_month": await _count(ev, ("kick", mo)),
        "left_day": await _count(ev, ("left", d)),
        "left_month": await _count(ev, ("left", mo)),
        "plays_day": await _count("SELECT COUNT(*) c FROM plays WHERE ts>=?", (d,)),
        "plays_month": await _count("SELECT COUNT(*) c FROM plays WHERE ts>=?", (mo,)),
        "err_day": await _count("SELECT COUNT(*) c FROM errors WHERE ts>=?", (d,)),
        "err_groups_day": await _count("SELECT COUNT(DISTINCT chat_id) c FROM errors WHERE ts>=?", (d,)),
        "songs": await _count("SELECT COUNT(*) c FROM songs"),
        "top_month": await q(
            "SELECT s.title, COUNT(*) c FROM plays p JOIN songs s ON s.video_id=p.video_id "
            "WHERE p.ts>=? GROUP BY p.video_id ORDER BY c DESC LIMIT 5", (mo,)),
    }


async def events_since(since):
    return await q("SELECT * FROM group_events WHERE ts>=? ORDER BY ts", (since,))


async def problem_groups(since, limit=25):
    return await q(
        "SELECT g.chat_id,g.title,g.status,g.last_error,COUNT(e.id) n FROM groups g "
        "JOIN errors e ON e.chat_id=g.chat_id WHERE e.ts>=? GROUP BY g.chat_id ORDER BY n DESC LIMIT ?",
        (since, limit),
    )


async def save_broadcast(total, ok, failed):
    await run("INSERT INTO broadcasts(ts,total,ok,failed) VALUES(?,?,?,?)", (now(), total, ok, failed))
