from odata1c import Connection, Manager
import asyncio
from typing import Literal, List

from .models import СтоимостьТоваров
from .db import get_pool

import logging

logger = logging.getLogger(__name__)
import json
import uuid
import functools
import datetime


from .utils import chunk_async_iterator


async def load_stoimost(config):
    dbpool = await get_pool(config)
    for key, baza in config["базы"].items():
        logger.info(f"Loading СтоимостьТоваров for baza {baza['base_url']}")
        async with Connection(**baza) as odata:
            async for models in chunk_async_iterator(
                odata.request()
                .InformationRegister(СтоимостьТоваров)
                .filter(
                    "РазделУчета eq 'ТоварыНаСкладах'"
                )
                .last(),
                1024,
            ):
                models
                pass
                print(
                    models[0].АналитикаУчетаНоменклатуры.Номенклатура.Ref_Key,
                    models[0].АналитикаУчетаНоменклатуры.СкладскаяТерритория_Key,
                    models[0].Стоимость,
                )

                async with dbpool.acquire() as db:
                    r = await db.executemany(
                        """--sql
                        insert into outstocking.СтоимостьТоваров 
                        (
                            owner, 
                            "Номенклатура_Key", 
                            "СкладскаяТерритория_Key",
                            "Стоимость"
                        )
                        values (
                            $1, $2, $3 , $4 
                        )
                        on conflict (owner, "СкладскаяТерритория_Key", "Номенклатура_Key") do update set 
                            "Стоимость" = excluded."Стоимость"
                        ;""",
                        [
                            (
                                key,
                                model.АналитикаУчетаНоменклатуры.Номенклатура.Ref_Key,
                                model.АналитикаУчетаНоменклатуры.СкладскаяТерритория_Key,
                                model.Стоимость,
                            )
                            for model in models
                        ],
                    )
