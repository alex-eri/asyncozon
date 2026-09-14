import asyncpg
import json
import os

pool = None

async def get_pool(config):
    global pool
    if pool is not None:
        return pool
    
    async def conninit(conn):
        await conn.set_type_codec(
            "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )
        await conn.set_type_codec(
            "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )

    pool = await asyncpg.create_pool(
        dsn=config["pg"],
        min_size=1,
        max_size=4,
        ssl=False,
        command_timeout=10,
        init=conninit,
    )
    return pool