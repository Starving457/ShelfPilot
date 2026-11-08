"""Sonda do bazy WAPRO (MS SQL Server): tylko odczyt, nic nie zapisuje.

Pozwala zobaczyć, jakie są bazy i tabele, znaleźć kolumny po fragmencie nazwy
(np. EAN, NAZWA, STAN) oraz podejrzeć pierwsze wiersze wybranej tabeli lub widoku. Można też wykonać
własne zapytanie SELECT (inne polecenia są odrzucane).
"""
import pyodbc

# Serwer SQL na tym komputerze (instancja domyślna MSSQLSERVER)
SERVER = "localhost"

PREFERRED_DRIVERS = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
]

SYSTEM_DATABASES = {"master", "tempdb", "model", "msdb"}


def pick_driver():
    installed = pyodbc.drivers()
    for name in PREFERRED_DRIVERS:
        if name in installed:
            return name
    print("Nie znaleziono sterownika ODBC dla SQL Server. Zainstalowane sterowniki:")
    for name in installed:
        print(" -", name)
    raise SystemExit(1)


def connect(driver, database=None):
    parts = [f"DRIVER={{{driver}}}", f"SERVER={SERVER}", "Trusted_Connection=yes"]
    if driver.startswith("ODBC Driver"):
        parts.append("TrustServerCertificate=yes")
    if database:
        parts.append(f"DATABASE={database}")
    return pyodbc.connect(";".join(parts), timeout=5)


def list_databases(conn):
    rows = conn.cursor().execute("SELECT name FROM sys.databases ORDER BY name").fetchall()
    return [row[0] for row in rows if row[0] not in SYSTEM_DATABASES]


def list_tables(conn, limit=40):
    sql = """
        SELECT s.name, t.name, SUM(p.rows)
        FROM sys.tables t
        JOIN sys.schemas s ON s.schema_id = t.schema_id
        JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
        GROUP BY s.name, t.name
        ORDER BY SUM(p.rows) DESC
    """
    rows = conn.cursor().execute(sql).fetchall()
    print(f"\nTabele (najwięcej wierszy na górze, pokazano {min(limit, len(rows))} z {len(rows)}):")
    for schema, table, count in rows[:limit]:
        print(f"  {schema}.{table}  ({count} wierszy)")


def find_columns(conn, keyword):
    sql = """
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE COLUMN_NAME LIKE ?
        ORDER BY TABLE_NAME, COLUMN_NAME
    """
    rows = conn.cursor().execute(sql, f"%{keyword}%").fetchall()
    if not rows:
        print("Nic nie znaleziono.")
        return
    for schema, table, column, data_type in rows[:60]:
        print(f"  {schema}.{table}.{column}  ({data_type})")
    if len(rows) > 60:
        print(f"  ... i {len(rows) - 60} kolejnych, zawęź słowo")


def find_object(conn, name):
    """Szuka tabeli lub widoku o podanej nazwie. Zwraca (schemat, nazwa) albo None."""
    rows = conn.cursor().execute(
        "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES"
    ).fetchall()
    wanted = name.lower().replace("dbo.", "")
    return next((row for row in rows if row[1].lower() == wanted), None)


def find_tables(conn, keyword):
    sql = """
        SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE ?
        ORDER BY TABLE_NAME
    """
    rows = conn.cursor().execute(sql, f"%{keyword}%").fetchall()
    if not rows:
        print("Nic nie znaleziono.")
        return
    for schema, table, table_type in rows[:60]:
        kind = "widok" if table_type == "VIEW" else "tabela"
        print(f"  {schema}.{table}  ({kind})")
    if len(rows) > 60:
        print(f"  ... i {len(rows) - 60} kolejnych, zawęź słowo")


def show_columns(conn, name):
    match = find_object(conn, name)
    if match is None:
        print("Nie ma takiej tabeli ani widoku.")
        return
    sql = """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """
    rows = conn.cursor().execute(sql, match[0], match[1]).fetchall()
    print(f"\nKolumny {match[0]}.{match[1]} ({len(rows)}):")
    for column, data_type in rows:
        print(f"  {column}  ({data_type})")


def preview_table(conn, name, rows_count=3):
    """Pokazuje pierwsze wiersze, ale tylko kolumny, które mają jakąś wartość."""
    match = find_object(conn, name)
    if match is None:
        print("Nie ma takiej tabeli ani widoku.")
        return

    cursor = conn.cursor()
    total = cursor.execute(f"SELECT COUNT(*) FROM [{match[0]}].[{match[1]}]").fetchone()[0]
    print(f"\n{match[0]}.{match[1]}: {total} wierszy (pokazuję {rows_count}, bez pustych kolumn)")

    cursor.execute(f"SELECT TOP {rows_count} * FROM [{match[0]}].[{match[1]}]")
    columns = [col[0] for col in cursor.description]
    for number, row in enumerate(cursor.fetchall(), start=1):
        print(f"\n--- wiersz {number} ---")
        for column, value in zip(columns, row):
            if value is None or str(value).strip() == "":
                continue
            print(f"  {column}: {str(value)[:60]}")


def show_definition(conn, name):
    """Pokazuje, z czego zbudowany jest widok (jego zapytanie SELECT)."""
    match = find_object(conn, name)
    if match is None:
        print("Nie ma takiej tabeli ani widoku.")
        return
    row = conn.cursor().execute(
        "SELECT OBJECT_DEFINITION(OBJECT_ID(?))", f"{match[0]}.{match[1]}"
    ).fetchone()
    if row is None or row[0] is None:
        print("Brak definicji (to zwykła tabela albo brak uprawnień).")
        return
    print(row[0])


def run_select(conn, sql, limit=30):
    """Wykonuje własne zapytanie, ale tylko pojedyncze SELECT."""
    sql = sql.strip().rstrip(";")
    if not sql.lower().startswith("select") or ";" in sql:
        print("Dozwolone jest tylko pojedyncze zapytanie zaczynające się od SELECT.")
        return
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(limit)
    except pyodbc.Error as error:
        print("Błąd zapytania:", error)
        return

    print(" | ".join(columns))
    for row in rows:
        print(" | ".join(str(value)[:80] for value in row))
    print(f"({len(rows)} wierszy, limit {limit})")


def main():
    driver = pick_driver()
    print(f"Sterownik: {driver}\nSerwer: {SERVER}")

    try:
        conn = connect(driver)
    except pyodbc.Error as error:
        print("Nie udało się połączyć:", error)
        return

    databases = list_databases(conn)
    print("\nBazy na serwerze:")
    for number, name in enumerate(databases, start=1):
        print(f"{number}. {name}")
    conn.close()

    choice = input("\nNumer bazy WAPRO: ").strip()
    if not (choice.isdigit() and 1 <= int(choice) <= len(databases)):
        return
    conn = connect(driver, databases[int(choice) - 1])
    print(f"Połączono z bazą {databases[int(choice) - 1]}.")

    while True:
        print("\n[T] największe tabele  [N] szukaj tabeli po nazwie  [K] szukaj kolumny")
        print("[C] kolumny tabeli  [P] podgląd tabeli  [D] definicja widoku")
        print("[S] własne zapytanie SELECT  [Q] koniec")
        answer = input("> ").strip().upper()
        if answer == "Q":
            break
        elif answer == "T":
            list_tables(conn)
        elif answer == "K":
            keyword = input("Fragment nazwy kolumny (np. EAN): ").strip()
            if keyword:
                find_columns(conn, keyword)
        elif answer == "N":
            keyword = input("Fragment nazwy tabeli (np. ARTYKUL): ").strip()
            if keyword:
                find_tables(conn, keyword)
        elif answer == "C":
            table = input("Nazwa tabeli lub widoku: ").strip()
            if table:
                show_columns(conn, table)
        elif answer == "D":
            table = input("Nazwa widoku: ").strip()
            if table:
                show_definition(conn, table)
        elif answer == "S":
            sql = input("SELECT ...: ").strip()
            if sql:
                run_select(conn, sql)
        elif answer == "P":
            table = input("Nazwa tabeli lub widoku: ").strip()
            if table:
                preview_table(conn, table)
        else:
            print("Nieznana opcja.")

    conn.close()


main()