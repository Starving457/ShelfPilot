ShelfPilot
==========

A warehouse app that answers one question: where is this product?
It tracks which rack each product lies on, lets you look it up by code, EAN or name,
and supports rotational inventory counting by manufacturer and category (in progress).

Status: work in progress. The console scripts work today. Inventory counting,
a web interface and the WAPRO Mag import are still being built.


Features
--------

- Products stored with code, EAN, name and stock level from WAPRO
- Locations, currently whole racks such as A1 and A2 (shelves can be added later)
- A product can lie on several locations at once
- Search by exact code, EAN, or any words of the name in any order
- Reverse lookup: what lies on a given location
- Manufacturer and category per product, editable by hand
- Inventory history: every count is stored together with the WAPRO stock at that moment


Tech stack
----------

Python 3.13, SQLAlchemy 2, SQLite, pytest.


Getting started
---------------

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python -m database.init_db
    python seed_test_data.py

The last command creates three racks and six fictional products for trying things out.


Scripts
-------

- add_location.py: add a location (with confirmation)
- delete_location.py: delete an empty location
- list_locations.py: list all locations with product counts
- add_product.py: add a product by hand (testing tool)
- list_products.py: list all products with their locations
- search_product.py: search by code, EAN or name
- assign_location.py: add, move or remove a product's locations
- products_on_shelf.py: show what lies on a location
- edit_product_attributes.py: set or correct manufacturer and category
- seed_test_data.py: fill the database with test data


Project layout
--------------

- database/: models and database setup
- services/: business logic, with no input or print, covered by tests
- tests/: pytest tests
- the *.py scripts in the main folder: interactive console scripts built on top of services/


Tests
-----

    pytest


Roadmap
-------

1. Rotational inventory counting: one manufacturer and category per day, compared with WAPRO stock
2. WAPRO Mag import: read-only, directly from its database
3. Automatic manufacturer and category suggestions with manual review
4. Web interface