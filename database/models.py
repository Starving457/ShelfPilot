from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from database.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    code = Column(String)
    ean = Column(String)
    name = Column(String)
    wapro_quantity = Column(Integer)
    counted_quantity = Column(Integer, nullable=True)
    counted_at = Column(Date, nullable=True)


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    rack = Column(String)
    shelf = Column(String)


class ProductLocation(Base):
    __tablename__ = "product_locations"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    quantity = Column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("product_id", "location_id"),)