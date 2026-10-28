# Render par deploy (Termux se)

Render sidha phone se upload nahi lete - code GitHub par jaata hai, Render wahan se deploy karta hai.

## 1. Termux me (ek baar)
```
pkg update && pkg install git unzip -y
cd ~ && unzip musicbot_v4_1.zip && cd musicbot
git init && git add . && git commit -m "music bot"
git branch -M main
git remote add origin https://github.com/<aapka-username>/musicbot.git   # pehle github.com par PRIVATE empty repo banao
git push -u origin main    # password ki jagah GitHub Personal Access Token (repo scope) daalo
```
`.env` file kabhi push mat karna (secrets Render dashboard me daalo).

## 2. Render dashboard
1. dashboard.render.com -> New -> **Blueprint** -> apna repo chuno (render.yaml mil jayega) -> Apply.
2. Environment me bharo: `API_ID`, `API_HASH`, `BOT_TOKEN`, `SESSION_STRING`, `OWNER_IDS`.
3. Deploy hone do (Docker build 5-10 min).

## 3. Jagaye rakhna (free plan)
Free web service 15 min bina traffic ke so jaati hai -> bot band. Render ka URL (https://music-radio-bot.onrender.com) uptimerobot.com par har 5 min ping par lagao.

## 4. Dhyan rakhne wali baatein
- Free plan par disk mitt jaati hai: har redeploy/restart par database (groups ka record, plays, radio form) **reset** ho jayega. Pakka record chahiye to paid plan + disk (render.yaml me comment diya hai) ya Postgres.
- Render ke shared IP par YouTube aksar "sign in to confirm you're not a bot" deta hai -> cookies.txt lagani padegi, warna gaane fail ho sakte hain. VPS par ye kam hota hai.
- SESSION_STRING (dusre Telegram account ka) Termux me banao:
  `pkg install python -y && pip install pyrofork` phir `python gen_session.py`
  (phone number + Telegram code puchega, aakhir me string print hogi. Ye password jaisi hai, kisi ko mat do).
- Cookies (YouTube bot-check ke liye): Render -> Environment -> Secret Files -> filename `cookies.txt`,
  phir env `COOKIES_FILE=/etc/secrets/cookies.txt`.
