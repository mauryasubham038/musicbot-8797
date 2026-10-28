# Music + Radio Bot - Version 4

## Bot ke features

### Gaana (sab user)
- `/play naam` - search karke VC me gaana. Galat spelling chalti hai ("tum hee ho" = "Tum Hi Ho").
- Best version chunta hai: official channel + zyada views upar, remix/slowed/cover/shorts neeche.
- "🔁" buttons se sahi gaana chuno; wo spelling bot yaad rakhta hai.
- `/queue`, `/now`. `/skip` (admin ya jisne gaana lagaya). Radio chalte waqt `/play` band.

### Radio (sirf admin)
- Group ko pehle private form se connect karo (`/radio setup`), genre chuno.
- `/radio on`, `/radio off`, `/radio skip`. Radio band hone par hi users `/play` kar sakte hain.
- Gaane ka chunav = YouTube popularity + is mahine bot par kitna baja. Last 40 gaane repeat nahi.
- Playlist khud update: queries files har ghante thodi-thodi chalti hain, har mahine naye month/year ke saath dobara banti hain.

### Admin ke commands
- `/pause`, `/resume`, `/stop`, `/skip` (search aur radio dono gaane).

### Owner panel (aap)
- `/panel` - active groups, aaj / is mahine kitne join, kick, left, plays, errors, top gaane.
- `/errors` - kis group me kya error (24 ghante). `/groups` - problem wale groups.
- `/export` - is mahine ka join/kick CSV. `/clearerrors`.
- `/broadcast` - sab groups me ek saath promotion (message reply karke ya text; `-pin` se pin).
- Har 6 ghante health-check: bot nikala gaya? admin hai?

## File-wise kaam
| File | Kaam |
|---|---|
| main.py | Bot start karta hai, background kaam chalata hai (pool update, health check, Render keepalive) |
| config.py | .env se settings padhta hai |
| clients.py | Telegram bot, assistant account aur VC (pytgcalls) ke connection |
| database.py | SQLite: groups, join/kick record, gaane, plays, errors, radio form, broadcasts |
| search.py | Spelling-proof search, best version ranking, YouTube se stream link |
| player.py | VC me gaana: queue, play/skip/stop, radio on/off, assistant ko group me lana |
| radio.py | Radio ka gaana chunna aur pool (gaano ki list) bharte rehna |
| build_queries.py | queries/ ki files banata hai (genre__artist.txt) |
| queries/ | 81 files, ~520 search queries (Bhojpuri, Arijit, Hindi, Retro, Punjabi, Sad, DJ) |
| handlers_user.py | Group/private commands, radio form, bot ka join/kick pakadna |
| handlers_admin.py | Owner panel, errors, export, broadcast |
| utils.py | Admin check, error pakadna (DB + log group me), chhote helpers |
| requirements.txt | Python packages |
| Dockerfile | Render/server ke liye build (ffmpeg ke saath) |
| render.yaml | Render ki settings |
| deploy_termux.sh | Termux se GitHub push + Render link |
| .env.example | Secrets ka namuna (.env banao) |
| .gitignore / .dockerignore | Secrets aur kachra upload hone se rokte hain |
| README.md | Setup steps |
| DEPLOY_RENDER_TERMUX.md | Render deploy ke steps aur dikkatein |
| FEATURES.md | Ye file |
