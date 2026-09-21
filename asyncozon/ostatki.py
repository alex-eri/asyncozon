from odata1c import Connection, Manager
import asyncio
from typing import Literal, List

from .models import ЗапасыИПотребности, Номенклатура, Склады
from .db import get_pool

import logging

logger = logging.getLogger(__name__)
import json
import uuid
import functools
import datetime


from .utils import chunk_async_iterator


async def load_catalogs(config):
    dbpool = await get_pool(config)
    for key, baza in config["базы"].items():
        logger.info(f"Loading catalogs for baza {baza['base_url']}")
        async with Connection(**baza) as odata:
            async for models in chunk_async_iterator(
                odata.request().Catalog(Номенклатура).all(), 1024
            ):
                async with dbpool.acquire() as db:
                    r = await db.executemany(
                        """insert into catalogs."Номенклатура" 
                            (owner, "Ref_Key", "ЕдиницаИзмерения_Key", "Description", "Code", "КодДляПоиска", "Качество", "Артикул")
                        values (
                            $1, $2, $3, $4, $5, $6, $7, $8
                        )
                        
                        on conflict (owner, "Ref_Key") do update set ("ЕдиницаИзмерения_Key", "Description", "Code", "КодДляПоиска", "Качество", "Артикул") =
                        (excluded."ЕдиницаИзмерения_Key", excluded."Description", excluded."Code", excluded."КодДляПоиска", excluded."Качество", excluded."Артикул")
                        ;""",
                        [
                            (
                                key,
                                model.Ref_Key,
                                model.ЕдиницаИзмерения_Key,
                                model.Description,
                                model.Code,
                                model.КодДляПоиска,
                                model.Качество,
                                model.Артикул,
                            )
                            for model in models
                        ],
                    )
                    logger.info(
                        f"Inserted rows into catalogs.Номенклатура for {baza['base_url']}"
                    )

            async for models in chunk_async_iterator(
                odata.request().Catalog(Склады).all(), 1024
            ):
                async with dbpool.acquire() as db:
                    r = await db.executemany(
                        """--sql
                        insert into catalogs."Склады" (owner, "Ref_Key", "DeletionMark", "Description") 
                        values ( $1, $2, $3, $4)
                        on conflict (owner, "Ref_Key") do update set 
                        ("DeletionMark", "Description") = (
                            excluded."DeletionMark", excluded."Description"
                        )
                        ;
                        """,
                        [
                            (key, model.Ref_Key, model.DeletionMark, model.Description)
                            for model in models
                        ],
                    )
                    logger.info(
                        f"Inserted rows into catalogs.Склады for {baza['base_url']}"
                    )


async def load_balance(config):
    dbpool = await get_pool(config)
    for key, baza in config["базы"].items():
        logger.info(f"Loading catalogs for baza {baza['base_url']}")
        async with Connection(**baza) as odata:
            async for models in chunk_async_iterator(
                odata.request()
                .AccumulationRegister(ЗапасыИПотребности)
                .balance(dimensions=["Склад", "Номенклатура"]),
                1024,
            ):
                async with dbpool.acquire() as db:
                    r = await db.executemany(
                        """--sql
        insert into outstocking."ЗапасыИПотребности" 
        (owner, Склад, "Номенклатура_Key", ВНаличии, РезервироватьНаСкладе,
                РезервироватьПоМереПоступления, ЗаблокированоВНаличии)
        values (
            $1, $2, $3 , $4, $5, $6, $7
        )
        on conflict (owner, "Склад", "Номенклатура_Key") do update set 
        (
            ВНаличии, РезервироватьНаСкладе,
            РезервироватьПоМереПоступления, ЗаблокированоВНаличии
            ) 
            = (
            excluded.ВНаличии, excluded.РезервироватьНаСкладе,
            excluded.РезервироватьПоМереПоступления, excluded.ЗаблокированоВНаличии
            )
        ;
                        """,
                        [
                            (
                                key,
                                model.Склад,
                                model.Номенклатура_Key,
                                model.ВНаличииBalance,
                                model.РезервироватьНаСкладеBalance,
                                model.РезервироватьПоМереПоступленияBalance,
                                model.ЗаблокированоВНаличииBalance,
                            )
                            for model in models
                        ],
                    )
                logging.info("Inserted ЗапасыИПотребности")


async def upload_balance(config):
    dbpool = await get_pool(config)
    async with dbpool.acquire() as db:

        bases = await db.fetch("""--sql
        select distinct ln.owner as left_owner, rn.owner as right_owner, s."Ref_Key" as warehouse
        from outstocking.СопоставлениеНоменклатуры nn
        join catalogs.Номенклатура ln on ln.id = nn.left_key
        join catalogs.Номенклатура rn on rn.id = nn.right_key
        join outstocking.КоэфицентыПередачи kp on "СопоставлениеНоменклатуры_id" = nn.id
        join catalogs.Склады s on kp."Склад_id" = s.id
        where kp.k > 0
        """)

    print(bases)
    for left, right, ware in bases:
        print((left, right, ware))

        async with dbpool.acquire() as db:
            goods = await db.fetch(
                """--sql
SELECT  rn."Ref_Key",
 rn."Code", rn.Артикул, rn."Description", 
 TRUNC( (((z.ВНаличии - z.РезервироватьНаСкладе - z.РезервироватьПоМереПоступления - z.ЗаблокированоВНаличии )*k.k + k.b) / k.r)::numeric ,0)* k.r  as КЗаказу,
 z.ВНаличии, z.РезервироватьНаСкладе, k.price as Цена
FROM outstocking.ЗапасыИПотребности z
join catalogs.Номенклатура ln on ln."Ref_Key" = z."Номенклатура_Key" AND ln.owner = z.owner
join outstocking.СопоставлениеНоменклатуры nn on ln.id = nn.left_key
join catalogs.Номенклатура rn on rn.id = nn.right_key
join outstocking.КоэфицентыПередачи k on nn.id = k.СопоставлениеНоменклатуры_id

WHERE $1 = z.owner and $2 = z.Склад and rn.owner = $3
;
            """,
                left,
                ware,
                right,
            )

        print(goods)
        baza = config["базы"][str(right)]
        print(baza)


        now = datetime.datetime.now().isoformat(timespec='seconds')
        tomorow = (datetime.datetime.now()+datetime.timedelta(hours=2)).isoformat(timespec='seconds')


        async with Connection(**baza) as odata:
            zakaz = await anext(
                odata.request()
                .Document("ЗаказПоставщику")
                .filter(f"НомерПоДаннымПоставщика eq '{ware}'")
                .all()
            )


        json.dump(zakaz, open('zakaz.tmp','w'), indent=2)
        
        ТоварыДля1С = []

        n=1

        for t in goods:
            Цена = float(t['Цена'])
            o = False
            k = t["КЗаказу"]
            total = Цена * k

            if k <= 0:
                k = 1
                o = True
                total = 0
                continue

            ТоварыДля1С.append(
                {
                    "LineNumber": n,
                    "Номенклатура_Key": t["Ref_Key"],
                    "Характеристика_Key": "00000000-0000-0000-0000-000000000000",
                    "Упаковка_Key": "00000000-0000-0000-0000-000000000000",
                    "КоличествоУпаковок": k,
                    "Количество": k,
                    "ДатаПоступления": tomorow,
                    "Цена": Цена,
                    "Сумма": total,
                    "СуммаСНДС": total,
                    "Отменено": o,
                    "СтавкаНДС_Key": "0879466a-d4cf-11f0-90af-cee641da0f98",
                    "Склад_Key": zakaz['Склад_Key']
                }
            )
            n+=1


        СуммаДокумента = functools.reduce(lambda y,x: y+x['Сумма'], ТоварыДля1С, initial=0)

        async with Connection(**baza) as odata:

            zakaz2 = await odata.request().Document("ЗаказПоставщику").patch(
                zakaz["Ref_Key"], {
                    "Posted": True,
                    "Date": now,
                    "ДатаПоступления": tomorow,
                    "Товары": ТоварыДля1С,
                    "СуммаДокумента":СуммаДокумента,
                    'DeletionMark': False,
                    "Согласован": True,
                }
            )

        json.dump(zakaz2, open('zakaz2.tmp','w'), indent=2)


        async with Connection(**baza) as odata:

            zakaz2 = await odata.request().Document("ЗаказПоставщику").post(zakaz["Ref_Key"])

        # async with Connection(**baza) as odata:
        #     zakaz = await odata.request().Document('ЗаказПоставщику').get(uuid.UUID('8b8700163e88a74c11f1ab79c1a91d6e'))
        #     print(zakaz)

    #     res = await db.fetch("""--sql
    # SELECT  rn."Ref_Key",
    # rn."Code", rn.Артикул, rn."Description",
    # TRUNC( (((z.ВНаличии - z.РезервироватьНаСкладе - z.РезервироватьПоМереПоступления - z.ЗаблокированоВНаличии )*k.k + k.b) / k.r)::numeric ,0)* k.r  as КЗаказу,
    # z.ВНаличии, z.РезервироватьНаСкладе
    # FROM outstocking.ЗапасыИПотребности z
    # join catalogs.Номенклатура ln on ln."Ref_Key" = z."Номенклатура_Key" AND ln.owner = z.owner
    # join outstocking.СопоставлениеНоменклатуры nn on ln.id = nn.left_key
    # join catalogs.Номенклатура rn on rn.id = nn.right_key
    # join outstocking.КоэфицентыПередачи k on nn.id = k.СопоставлениеНоменклатуры_id

    # WHERE 'a66c4be8-b813-4115-9aad-4e4717cd7134' = z.owner and 'b96b10e4-cf83-11eb-cf83-7656f1ea1c1c' = z.Склад and rn.owner = 'f4fb3e16-2e71-43cc-80e5-1c50f6a8adaf'
    # ;
    #         """)
