from services.wapro_reader import (
    connect_wapro,
    fetch_articles,
    WAPRO_DATABASE,
    WAPRO_WAREHOUSE_ID,
    WAPRO_KINDS,
)

print(f"Baza: {WAPRO_DATABASE}, magazyn nr {WAPRO_WAREHOUSE_ID}, rodzaje: {', '.join(WAPRO_KINDS)}")

connection = connect_wapro()
articles, skipped = fetch_articles(connection)
connection.close()

codes = [article.code for article in articles]
with_stock = [a for a in articles if a.quantity is not None and a.quantity > 0]
with_ean = [a for a in articles if a.ean]
with_producer = [a for a in articles if a.producer]

print(f"Pobrano artykułów: {len(articles)} (pominięto bez kodu: {skipped})")
print(f"Ze stanem większym od zera: {len(with_stock)}")
print(f"Z kodem EAN: {len(with_ean)}")
print(f"Z wypełnionym producentem: {len(with_producer)}")
print(f"Powtórzone kody: {len(codes) - len(set(codes))}")

print("\nPierwsze 10:")
for article in articles[:10]:
    print(
        f"{article.wapro_id} | {article.code} | EAN: {article.ean or '-'} | "
        f"{article.name} | stan: {article.quantity} | producent: {article.producer or '-'}"
    )