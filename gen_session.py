"""Assistant account ka SESSION_STRING banata hai.  Chalao:  python gen_session.py
Phone number (+91...), Telegram ka code (aur 2-step password agar ho) puchega.
Dhyan: ye string password jaisi hai, kisi ko mat dikhana."""
import asyncio
from pyrogram import Client

API_ID = int(input("API_ID: ").strip())
API_HASH = input("API_HASH: ").strip()


async def main():
    async with Client("gen", api_id=API_ID, api_hash=API_HASH, in_memory=True) as app:
        print("\n===== SESSION_STRING (neeche wali poori line copy karo) =====\n")
        print(await app.export_session_string())
        print("\n=============================================================")

asyncio.run(main())
