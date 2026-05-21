from telethon import TelegramClient

api_id = 123456        # <-- your api_id
api_hash = "your_hash"

channel = "ETHIOhouseagents"

async def main():
    async with TelegramClient("session", api_id, api_hash) as client:
        messages = await client.get_messages(channel, limit=20)

        for msg in messages:
            print("="*50)
            print("DATE:", msg.date)
            print("TEXT:", msg.text)

import asyncio
asyncio.run(main())