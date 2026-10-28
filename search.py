"""Search: galat spelling / Hinglish typing / copy-upload wale gaano me se best version dhundhna."""
import asyncio
import math
import re

from rapidfuzz import fuzz
from yt_dlp import YoutubeDL

import config
import database as db

NOISE = {
    "official", "video", "song", "songs", "full", "hd", "audio", "lyrics", "lyrical", "new", "latest",
    "mp3", "download", "gana", "gaana", "gaane", "bhojpuri", "hindi", "ka", "ki", "ke", "the", "by",
}

_DIGRAPHS = [
    ("ph", "f"), ("sh", "s"), ("ch", "c"), ("kh", "k"), ("gh", "g"), ("dh", "d"), ("th", "t"),
    ("bh", "b"), ("jh", "j"), ("ck", "k"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"),
    ("aa", "a"), ("ai", "e"), ("ei", "e"), ("au", "o"), ("ou", "o"),
]
_SINGLE = str.maketrans({"w": "v", "z": "j", "q": "k", "y": "i", "e": "i", "o": "u", "h": ""})


def phon(text: str) -> str:
    """Typing ki galtiyan (aa/a, ee/i, oo/u, v/w, double letters) mitakar ek 'sound key' banata hai."""
    t = (text or "").lower()
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t)
    t = re.sub(r"[^a-z0-9\u0900-\u097f ]", " ", t)
    out = []
    for tok in t.split():
        if tok in NOISE or re.fullmatch(r"20\d\d", tok):
            continue
        for a, b in _DIGRAPHS:
            tok = tok.replace(a, b)
        tok = tok.translate(_SINGLE)
        tok = re.sub(r"(.)\1+", r"\1", tok)
        if tok:
            out.append(tok)
    return " ".join(out)


BAD_WORDS = ["slowed", "reverb", "lofi", "lo-fi", "remix", "cover", "karaoke", "8d", "shorts", "reaction",
             "tutorial", "ringtone", "instrumental", "mashup", "bass boosted", "nightcore", "status video",
             "whatsapp", "edit"]
GOOD_CHANNELS = ["t-series", "t series", "zee music", "sony music", "saregama", "tips", "wave music",
                 "worldwide records", "vevo", "yrf", "shemaroo", "speed records", "jjust music", "times music",
                 "venus", "eros now", "- topic", "arijit singh", "pawan singh", "khesari", "bhojpuri"]


def _flat(entry):
    return {
        "video_id": entry.get("id"),
        "title": entry.get("title") or "",
        "channel": entry.get("channel") or entry.get("uploader") or "",
        "duration": int(entry.get("duration") or 0),
        "views": int(entry.get("view_count") or 0),
    }


def score_song(s, query):
    ql, tl, cl = query.lower(), s["title"].lower(), s["channel"].lower()
    sc = math.log10(s["views"] + 10)
    for w in BAD_WORDS:
        if w in tl and w not in ql:
            sc -= 2.0
    if any(g in cl for g in GOOD_CHANNELS):
        sc += 1.5
    sc += 4 * fuzz.token_set_ratio(phon(query), phon(s["title"])) / 100
    if 150 <= s["duration"] <= 420:
        sc += 0.7
    return sc


def _ytsearch(q, n):
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
    if config.COOKIES_FILE:
        opts["cookiefile"] = config.COOKIES_FILE
    with YoutubeDL(opts) as y:
        info = y.extract_info(f"ytsearch{n}:{q}", download=False)
    return info.get("entries") or []


async def web_search(query, n=10):
    entries = await asyncio.to_thread(_ytsearch, query, n)
    long_ok = any(w in query.lower() for w in ("jukebox", "nonstop", "non stop", "mashup"))
    out = []
    for e in entries:
        s = _flat(e)
        if not s["video_id"] or e.get("live_status") in ("is_live", "is_upcoming"):
            continue
        if s["duration"]:  # flat search me duration kabhi missing hoti hai - tab duration filter nahi
            if s["duration"] < 90:
                continue  # shorts
            if s["duration"] > config.MAX_SONG_MINUTES * 60 and not long_ok:
                continue
        s["score"] = score_song(s, query)
        out.append(s)
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


async def remember(s, genre=""):
    await db.upsert_song(s["video_id"], s["title"], s["channel"], s["duration"], s["views"],
                         phon(s["title"]), genre, max(s.get("score", 0), 0.1))


async def find_best(query, k=5):
    """Alias -> local DB fuzzy -> YouTube. Returns list of songs, best pehle."""
    key = phon(query)
    result, seen = [], set()

    def add(s):
        if s and s["video_id"] not in seen:
            seen.add(s["video_id"])
            result.append(s)

    al = await db.get_alias(key)
    if al:
        add(await db.get_song(al["video_id"]))

    strong_local = False
    if len(key) >= 4:
        scored = []
        for r in await db.all_songs_light():
            sc = fuzz.WRatio(key, r["phon"])
            if sc >= 88:
                scored.append((sc, r["ext_score"] or 0, r["video_id"]))
        scored.sort(reverse=True)
        for sc, _, vid in scored[:k]:
            add(await db.get_song(vid))
        strong_local = bool(scored and scored[0][0] >= 92)

    if not (al or strong_local):
        for s in await web_search(f"{query} song", 10):
            await remember(s)
            add(s)
    return result[:k]


def _extract(video_id):
    opts = {"quiet": True, "no_warnings": True, "format": "bestaudio/best", "noplaylist": True}
    if config.COOKIES_FILE:
        opts["cookiefile"] = config.COOKIES_FILE
    with YoutubeDL(opts) as y:
        info = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return {"url": info["url"], "title": info.get("title"), "duration": info.get("duration")}


async def get_stream(video_id):
    return await asyncio.to_thread(_extract, video_id)
