# ShelfPilot

Aplikacja magazynowa: znajduje, na której półce leży produkt, i pokazuje, co leży na danej półce.

## Uruchomienie

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m database.init_db
```

## Skrypty

- `add_location.py` - dodawanie lokalizacji (regał + półka)
- `add_product.py` - ręczne dodawanie produktu (narzędzie testowe)
- `assign_location.py` - dodawanie, przenoszenie i usuwanie półek produktu
- `search_product.py` - szukanie po kodzie, EAN lub nazwie
- `products_on_shelf.py` - co leży na danej półce
- `list_products.py` - lista wszystkich produktów

## Testy

```
pytest
```

## Plany

Inwentaryzacja rotacyjna, interfejs webowy, import z WAPRO Mag.