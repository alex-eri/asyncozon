import asyncio
from main import config
from odata1c import Connection, Manager


async def main():
    key, baza = list(config["базы"].items())[0]
    async with Connection(**baza) as odata:
        #sk= await anext(odata.request().InformationRegister('ШтрихкодыНоменклатуры').all())
        async for r in odata.request().Document('РеализацияТоваровУслуг').filter(f"Ref_Key eq guid'5e87000a-ada6-11f1-8922-00163e88a74c'").all():
            #print(r)
            for k in r.get('ШтрихкодыУпаковок',[]):
                print(k)
                s = await odata.request().Catalog('ШтрихкодыУпаковокТоваров').get(k['ШтрихкодУпаковки_Key'])
                print(s)
            # async for m in odata.request().Document('РеализацияТоваровУслуг_АкцизныеМарки').filter(f"Ref_Key eq guid'5e87000a-ada6-11f1-8922-00163e88a74c'").all():
            #         print(m)

asyncio.run(main())