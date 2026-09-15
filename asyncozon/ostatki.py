from odata1c import Connection, Manager
import asyncio
from typing import Literal, List

from .models import ЗапасыИПотребности, Номенклатура, Склады
from .db import get_pool

import logging

logger = logging.getLogger(__name__)

async def load_catalogs(config):
    db = await get_pool(config)
    for key, baza in config["базы"].items():
        logger.info(f"Loading catalogs for baza {baza['base_url']}")
        async with Connection(**baza) as conn:
            async for model in (
                conn.request().Catalog(Номенклатура).all()
            ):
                async with db.acquire() as conn:
                    r = await conn.execute(
                        """insert into catalogs."Номенклатура" 
                            (owner, "Ref_Key", "ЕдиницаИзмерения_Key", "Description", "Code", "КодДляПоиска", "Качество", "Артикул")
                        values (
                            $1, $2, $3, $4, $5, $6, $7, $8
                        )
                        
                        on conflict (owner, "Ref_Key") do update set ("ЕдиницаИзмерения_Key", "Description", "Code", "КодДляПоиска", "Качество", "Артикул") =
                        (excluded."ЕдиницаИзмерения_Key", excluded."Description", excluded."Code", excluded."КодДляПоиска", excluded."Качество", excluded."Артикул")
                        ;""",
                        key,
                        model.Ref_Key,
                        model.ЕдиницаИзмерения_Key,
                        model.Description,
                        model.Code,
                        model.КодДляПоиска,
                        model.Качество,
                        model.Артикул,
                    )
                    logger.info(f"Inserted {r} rows into catalogs.Номенклатура for {baza['base_url']}")

            async for model in (
                conn.request().Catalog(Склады).all()
            ):
                async with db.acquire() as conn:
                    r = await conn.execute('''
                        insert into "Склады" (owner, "Ref_Key", "DeletionMark", "Description") 
                        values ( $1, $2, $3, $4)
                        on conflict (owner, "Ref_Key") do update set 
                        ("DeletionMark", "Description") = (
                            excluded."DeletionMark", excluded."Description"
                        )
                        ;
                        ''',
                        key,
                        model.Ref_Key,
                        model.DeletionMark,
                        model.Description,
                        )
                                    
