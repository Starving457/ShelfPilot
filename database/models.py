from sqlalchemy import Column, Integer, String
from database.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    code = Column(String)
    name = Column(String)
    quantity = Column(Integer)