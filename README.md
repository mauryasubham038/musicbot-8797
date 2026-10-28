# 🎵 Telegram Music + Radio Bot

## Setup
1. `pip install -r requirements.txt` (aur system me `ffmpeg` chahiye) - ya Dockerfile use karo.
2. `.env.example` ko `.env` banao aur bharo:
   - `API_ID`, `API_HASH` -> my.telegram.org
   - `BOT_TOKEN` -> @BotFather
   - `SESSION_STRING` -> **dusre** Telegram account ka Pyrogram session (ye "assistant" hai jo VC me gaana bajata hai)
   - `OWNER_IDS` -> aapki user id
3. `python build_queries.py` (queries/ folder banta hai) - bot khud bhi bana leta hai.
4. `python main.py`
5. Bot ko group me **admin** banao (Invite users permission) - assistant khud join ho jayega. Pehle group me Voice Chat start karna zaroori hai.

## Group commands
`/play naam` `/skip` `/stop` `/pause` `/resume` `/queue` `/now`
Radio (sirf admin): `/radio on`, `/radio off`, `/radio setup`

## Radio kaise kaam karta hai
- Admin `/radio setup` dabata hai -> bot **private me form** kholta hai -> genre chunta hai (Bhojpuri romantic, Arijit, Hindi sad, Retro, Punjabi, Party/DJ...).
- `/radio on` -> sirf admin chala/band kar sakta hai, aur tabhi jab group private form se connect ho chuka ho. Radio chalte waqt `/play` band rehta hai; admin `/radio off` kare tabhi user search karke gaana baja sakte hain. Search wale gaane ko admin kabhi bhi `/skip` ya `/stop` kar sakta hai.
- Gaane ka chunav = YouTube popularity + **pichhle 30 din me bot par kitna baja** + randomness. Pichhle 40 gaane repeat nahi hote.
- `queries/` folder ki files (`genre__artist.txt`) har ghante thodi-thodi chalti hain aur pool me naye gaane aate rehte hain. Har mahine files naye month/year ke saath khud dobara bante hain.

## Galat spelling
- `search.phon()` aa/a, ee/i, oo/u, v/w, double letters ko ek jaisa bana deta hai ("tum hee ho" = "Tum Hi Ho").
- Local pool me fuzzy match -> nahi mila to YouTube; result me official channels aur high views ko upar, remix/slowed/cover/shorts ko neeche rakha jata hai.
- User "🔁 Ye nahi tha" me sahi gaana chune to wahi galat spelling **yaad** ho jati hai (aliases table).

## Owner panel (/panel)
Active groups, aaj/is mahine join-kick-left, plays, errors, top gaane, Problem groups (kahan kya error), CSV export, pool refresh.
- `/errors`, `/groups`, `/export`, `/clearerrors`
- `/broadcast` (kisi message ko reply karke, ya text; `-pin` se pin) - sab active groups me dheere dheere bhejta hai, FloodWait sambhalta hai, fail hone ka reason batata hai, nikale gaye groups ko "kicked" mark karta hai.
- Har 6 ghante health-check: bot nikala gaya? admin hai ya nahi?

## Dhyan rakhne wali baatein
- Pehli baar chalane par pool bharne me 5-10 min lagte hain.
- YouTube kabhi "sign in to confirm you're not a bot" deta hai -> `cookies.txt` banakar `COOKIES_FILE` me daalo.
- Assistant ke liye alag account use karo (main account nahi). Telegram bahut zyada groups me join karne par limit lagata hai.
- Gaane YouTube se stream hote hain - copyright/YouTube ToS aapki zimmedari hai.
- pytgcalls ka v2 API use hua hai; version badle to `player.py` me `call.play/pause/resume/leave_call` check karo.
