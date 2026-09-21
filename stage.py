import asyncio
from main import config

from asyncozon import stoimost

async def main():
    await stoimost.load_stoimost(config)

asyncio.run(main())