import databases
import ormar
import sqlalchemy

from config import settings

database = databases.Database(settings.db_url)
metadata = sqlalchemy.MetaData()

class BaseMeta(ormar.ModelMeta):
    metadata = metadata
    database = database

class Herd(ormar.Model):
    class Meta(BaseMeta):
        tablename = "herd"
    
    yak_id:             int = ormar.Integer(primary_key=True)
    name:               str = ormar.String(max_length=128, nullable=False)
    sex:                str = ormar.String(max_length=128, nullable=False)
    age:                float = ormar.Float()
    age_last_shaved:    float = ormar.Float()
    yield_milk_litres:  float = ormar.Float()
    yield_wool_skins:   int = ormar.Integer()

class Order(ormar.Model):
    class Meta(BaseMeta):
        tablename = "order"
    
    id:                 int = ormar.Integer(primary_key=True)
    order_id:           str = ormar.String(max_length=128, unique=True, nullable=False)
    order_day:          int = ormar.Integer(nullable=False)
    customer:           str = ormar.String(max_length=128, nullable=False)
    requested_milk:     float = ormar.Float(nullable=False)
    requested_wool:     int = ormar.Integer(nullable=False)
    received_milk:      float = ormar.Float(nullable=True)
    received_wool:      int = ormar.Integer(nullable=True)


class Stock(ormar.Model):
    class Meta(BaseMeta):
        tablename = "stock"

    id: int = ormar.Integer(primary_key=True, unique=True)
    yield_milk_litres: float = ormar.Float()
    yield_wool_skins: float = ormar.Float()

engine = sqlalchemy.create_engine(settings.db_url)
metadata.create_all(engine)