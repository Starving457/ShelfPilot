from datetime import date

from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from database.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    # Stały identyfikator artykułu w WAPRO (ID_ARTYKULU); puste dla produktów dodanych ręcznie
    wapro_id = Column(Integer, unique=True, nullable=True)
    code = Column(String)
    ean = Column(String)
    name = Column(String)
    wapro_quantity = Column(Integer)

    # Producent i kategoria (wartości zatwierdzone)
    manufacturer = Column(String, nullable=True)
    category = Column(String, nullable=True)
    # Skąd pochodzi zatwierdzona wartość: "manual", "rule" albo "ai"
    classification_source = Column(String, nullable=True)
    # "pending" = czeka na sprawdzenie, "confirmed" = zatwierdzony przez człowieka
    review_status = Column(String, default="pending")
    first_seen_at = Column(Date, default=date.today)

    # Podpowiedź (czeka na zatwierdzenie albo odrzucenie)
    suggested_manufacturer = Column(String, nullable=True)
    suggested_category = Column(String, nullable=True)
    suggested_source = Column(String, nullable=True)


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


class InventoryCount(Base):
    """Jedno policzenie produktu. Wpisy się dopisuje, nigdy nie nadpisuje (historia)."""

    __tablename__ = "inventory_counts"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    counted_at = Column(Date, nullable=False, default=date.today)
    # Ile sztuk naprawdę policzono
    counted_quantity = Column(Integer, nullable=False)
    # Stan z WAPRO w chwili liczenia (zapisany, bo WAPRO zmienia się po sprzedaży)
    wapro_quantity = Column(Integer, nullable=True)