from database.db import SessionLocal
from services.import_service import import_articles
from services.wapro_reader import (
    connect_wapro,
    fetch_articles,
    WAPRO_DATABASE,
    WAPRO_WAREHOUSE_ID,
    WAPRO_KINDS,
)


def print_summary(summary):
    print(f"  nowe produkty:             {summary.created}")
    print(f"  zaktualizowane:            {summary.updated}")
    print(f"  bez zmian:                 {summary.unchanged}")
    print(f"  zniknęły z WAPRO:          {summary.missing} (produkt zostaje, stan nieznany)")
    print(f"  pominięte (konflikt kodu): {len(summary.conflicts)}")

    if summary.new_products:
        print("\nNowe produkty (pierwsze 10):")
        for name in summary.new_products[:10]:
            print(f"  - {name}")
    if summary.conflicts:
        print("\nKody, które zajmuje już inny produkt:")
        for code in summary.conflicts[:10]:
            print(f"  - {code}")


print(f"Baza WAPRO: {WAPRO_DATABASE}, magazyn nr {WAPRO_WAREHOUSE_ID}, rodzaje: {', '.join(WAPRO_KINDS)}")

connection = connect_wapro()
articles, skipped = fetch_articles(connection)
connection.close()
print(f"Pobrano z WAPRO: {len(articles)} artykułów (pominięto bez kodu: {skipped})")

session = SessionLocal()

preview = import_articles(session, articles, apply=False)
if preview.status == "empty_source":
    print("WAPRO nie zwróciło żadnych artykułów, nic nie zmieniam. Sprawdź magazyn i rodzaje w ustawieniach.")
    session.close()
    raise SystemExit(1)

print("\nPo imporcie zmieni się:")
print_summary(preview)

if preview.created + preview.updated + preview.missing == 0:
    print("\nBrak zmian do zapisania.")
else:
    answer = input("\nZastosować zmiany? (T/N): ").strip().upper()
    if answer == "T":
        import_articles(session, articles)
        print("Zapisano.")
    else:
        print("Anulowano, nic nie zapisano.")

session.close()