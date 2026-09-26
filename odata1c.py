import aiohttp
import base64
import datetime
import pydantic
import uuid
from typing import Literal, Union
import urllib.parse

import json
from uuid import UUID


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def dumps(d, *a):
    print((d, *a))
    return json.dumps(d, default=str)

class Connection:
    session:aiohttp.ClientSession

    def __init__(self, base_url, username, password):
        headers = {
            # "Authorization": f"Basic {base64.b64encode(f"{username}:{password}".encode('utf-8'))}",
            "Accept": "application/json",
        }
        self.session = aiohttp.ClientSession(
            base_url=f"{base_url}/odata/standard.odata/",
            headers=headers,
            auth=aiohttp.BasicAuth(login=username, password=password),
            json_serialize=dumps
        )

    def get(self, path: str, query: dict):

        def quote(s,*a):
            return urllib.parse.quote(s, safe='/$')

        q = urllib.parse.urlencode(query, quote_via=quote)
        return self.session.get(f'{path}?{q}')


    async def patch(self, path: str, data: dict):
        return await self.session.patch(path, json=data)


    async def post(self, path: str, data: dict=None):
        return await self.session.post(path, json=data)


    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()
        if exc:
            raise exc

    def request(self):
        return Manager(self)


class Manager:
    def __init__(self, con: Connection):
        self.connection = con
        self.entity = None
        self.query = {}
        self.returntype = None
        self.type = None
        self._select = []
        self._expand = []

    def Collection(
        self,
        collectiontype,
        entity: str | pydantic.BaseModel,
        returntype: pydantic.BaseModel = None,
    ):

        self.type = collectiontype

        if type(entity) == str:
            self.entity = entity
        elif issubclass(entity, pydantic.BaseModel):
            self.entity = entity.model_json_schema()["title"]
            self.returntype = entity
        else:
            raise Exception("Collection not set")

        if returntype:
            self.returntype = returntype
        return self

    def Constant(self, entity, returntype=None):
        return self.Collection("Constant", entity, returntype)

    def Catalog(self, entity, returntype=None):
        return self.Collection("Catalog", entity, returntype)

    def Document(self, entity, returntype=None):
        return self.Collection("Document", entity, returntype)

    def AccumulationRegister(self, entity, returntype=None):
        return self.Collection("AccumulationRegister", entity, returntype)

    def InformationRegister(self, entity, returntype=None):
        return self.Collection("InformationRegister", entity, returntype)

    def set_select_by_model(self):
        if not self._select:

            def recurse(model, path=""):
                for name, field in model.model_fields.items():

                    if hasattr(field.annotation, "model_fields"):
                        recurse(field.annotation, path=f"{path}{name}/")
                        self.expand(f"{path}{name}")
                    else:
                        self.select(f"{path}{field.validation_alias or name}")

            recurse(self.returntype)

    def filter(self, f=None):
        if isinstance(f, str):
            self.query["$filter"] = f
        return self

    def select(self, *fields: str):
        for field in fields:
            self._select.append(field)
        return self

    def top(self, n: int):
        self.query["$top"] = n
        return self

    def skip(self, n: int):
        self.query["$skip"] = n
        return self

    def orderby(self, field: str, direction: Literal["asc", "desc"] = "asc"):
        self.query["$orderby"] = f"{field} {direction}"
        return self

    def balance(
        self,
        period: datetime.date | None = None,
        dimensions: list[str] = [],
        condition: str | None = None,
    ):
        assert self.type in ["AccumulationRegister"]
        params = []
        if type(period) in [datetime.date, datetime.datetime]:
            params.append(f"Period=datetime'{period.isoformat()}'")
        if dimensions:
            params.append(f"Dimensions='{','.join(dimensions)}'")
        if condition:
            params.append(f"Condition={condition}")
        path = f"{self.type}_{self.entity}/Balance({','.join(params)})"

        return self.__get_data(path)

    def last(
        self, period: datetime.datetime | None = None, condition: str | None = None
    ):
        assert self.type in ["InformationRegister"]
        params = []
        if type(period) in [datetime.date, datetime.datetime]:
            params.append(f"Period=datetime'{period.isoformat()}'")
        if condition:
            params.append(f"Condition={condition}")
        path = f"{self.type}_{self.entity}_RecordType/SliceLast({','.join(params)})"
        return self.__get_data(path)

    def balance_and_turnovers(
        self,
        start: datetime.datetime = None,
        end: datetime.datetime = None,
        condition: str | None = None,
    ):
        assert self.type in ["AccumulationRegister"]
        params = []
        if type(start) == datetime.date:
            params.append(f"StartPeriod­=datetime'{strat.isoformat()}'")
        if type(end) == datetime.date:
            params.append(f"EndPeriod=datetime'{end.isoformat()}'")
        if condition:
            params.append(f"Condition={condition}")
        path = f"{self.type}_{self.entity}/BalanceAndTurnovers({','.join(params)})"

        return self.__get_data(path)

    async def __get_data(self, path):
        if self.returntype:
            self.set_select_by_model()

        self.query["$select"] = ",".join(self._select)
        self.query["$expand"] = ",".join(self._expand)
        req = await self.connection.get(path, self.query)

        if req.status == 200:
            data = await req.json()

            self.returntype: pydantic.BaseModel
            if self.returntype:
                if isinstance(data.get("value"), list):
                    for r in data["value"]:
                        try:
                            yield self.returntype.model_validate(r)
                        except pydantic.ValidationError as e:
                            # print(r)
                            # print(e)
                            pass
                else:
                    yield self.returntype.model_validate(data["value"])
            else:
                if isinstance(data.get("value"), list):
                    for r in data["value"]:
                        yield r
                else:
                    yield data["value"]
        else:
            message = await req.json()
            print(path)
            print(message)
            req.raise_for_status()

    def expand(self, *models, path=""):
        for model in models:
            if type(model) == str:
                self._expand.append(model)
            if isinstance(model, pydantic.BaseModel):
                title = self.entity.model_json_schema()["title"]
                name = model.model_json_schema()["title"]
                self._expand.append(f"{path}{title}/{name}")
        return self


    async def metadata(self):
        path = f"$metadata"
        return await anext(self.__get_data(path))        


    def all(self):
        assert self.type
        path = f"{self.type}_{self.entity}"
        return self.__get_data(path)

    async def get(self, ref_key: uuid.UUID | str):
        assert self.type
        path = f"{self.type}_{self.entity}(guid'{ref_key}')"
        return await anext(self.__get_data(path))

    async def value(self):
        assert self.type == 'Constant'
        path = f"{self.type}_{self.entity}"
        return await anext(self.__get_data(path))
        

    def get_row(self, ref_key: uuid.UUID | str, line_number: int):
        assert self.type
        path = f"{self.type}_{self.entity}(Ref_Key=guid'{ref_key}', LineNumber={line_number})"
        return self.__get_data(path)


    async def patch(self, ref_key, data):
        path = f"{self.type}_{self.entity}(guid'{ref_key}')"
        req = await self.connection.patch(path, data)
        return await req.json()

    async def post(self, ref_key):
        path = f"{self.type}_{self.entity}(guid'{ref_key}')/Post"
        req = await self.connection.post(path)
        if req.status == 200 and req.content_type == 'application/json':
            return await req.json()
        else:
            pass