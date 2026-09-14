from pydantic import Field, BaseModel, AwareDatetime, NaiveDatetime
from uuid import UUID


class ТоварыНаСкладах(BaseModel):
    Склад_Key: UUID
    Номенклатура_Key: UUID
    ВНаличииBalance: float
    # КОтгрузкеBalance: float

class ЗапасыИПотребности(BaseModel):
    Склад: UUID
    # Склад_Type: Literal['StandardODATA.Catalog_Склады']
    Номенклатура_Key: UUID
    ВНаличииBalance: int | float
    # ПоступитBalance: int | float
    # ЗаказаноBalance: int | float
    РезервироватьНаСкладеBalance: int | float
    РезервироватьПоМереПоступленияBalance: int | float
    # ОтложитьРезервированиеBalance: int | float
    # КОбеспечениюBalance: int | float
    # НеОбеспечиватьBalance: int | float
    ЗаблокированоВНаличииBalance: int | float
    # ЗаблокированоПоступитBalance: int | float
    # КРазблокировкеBalance: int | float
    # РезервироватьНаСкладеИзЗаблокированныхBalance: int | float
    # РезервироватьПоМереПоступленияИзЗаблокированныхBalance: int | float

class Номенклатура(BaseModel):
    Ref_Key: UUID
    Description: str
    НаименованиеПолное: str
    # ПрослеживаемыйТовар: bool
    # КиЗГИСМ: bool
    # КиЗГИСМВид: str
    # КиЗГИСМСпособВыпускаВОборот: str
    # КиЗГИСМGTIN: str

    Code: str
    Артикул: str | None
    # Parent_Key: UUID
    ЕдиницаИзмерения_Key: UUID | None
    КодДляПоиска: str
    Качество: str
    # ТоварнаяКатегория_Key: UUID| None


class ВидыЦен(BaseModel):
    Ref_Key: UUID
    Description: str
    Статус: str


class ЦеныНоменклатуры(BaseModel):
    Номенклатура_Key: UUID
    ВидЦены_Key: UUID
    Упаковка_Key: UUID
    Цена: float
    Period: NaiveDatetime
    ВидЦены: ВидыЦен


