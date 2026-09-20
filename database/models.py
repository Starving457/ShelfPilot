from sqlalchemy import Column, Integer, String, ForeignKey
from database.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    code = Column(String)
    ean = Column(String)
    name = Column(String)
    quantity = Column(Integer)
    location_id = Column(Integer, ForeignKey("locations.id"))


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    rack = Column(String)
    shelf = Column(String)