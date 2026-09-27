"""
kuran_mufredat.db (SQLite) icerigini PostgreSQL'e tasir.

Kullanim:
    export DATABASE_URL="postgresql://kullanici:sifre@localhost:5432/kuran"
    python migrate_to_postgres.py kuran_mufredat.db

Once schema.sql'i hedef veritabaninda calistirmis olmaniz gerekir:
    psql "$DATABASE_URL" -f schema.sql
"""
import os
import sys
import sqlite3

import psycopg2
from psycopg2.extras import execute_values


def get_pg_connection():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit(
            "HATA: DATABASE_URL ortam degiskeni tanimli degil.\n"
            'Ornek: export DATABASE_URL="postgresql://kullanici:sifre@localhost:5432/kuran"'
        )
    return psycopg2.connect(dsn)


def migrate(sqlite_path: str):
    sconn = sqlite3.connect(sqlite_path)
    scur = sconn.cursor()

    pconn = get_pg_connection()
    pcur = pconn.cursor()

    # --- Kokler ---
    print("Kokler tablosu tasiniyor...")
    scur.execute("SELECT KokId, Baslik, NormalizedRoot, Aciklama FROM Kokler")
    rows = scur.fetchall()
    execute_values(
        pcur,
        "INSERT INTO kokler (kok_id, baslik, normalized_root, aciklama) VALUES %s "
        "ON CONFLICT (kok_id) DO NOTHING",
        rows,
        page_size=1000,
    )
    print(f"  {len(rows)} kok satiri eklendi.")

    # --- Ayetler ---
    print("Ayetler tablosu tasiniyor...")
    scur.execute("SELECT SureNo, AyetNo, AyetMetni FROM Ayetler")
    rows = scur.fetchall()
    execute_values(
        pcur,
        "INSERT INTO ayetler (sure_no, ayet_no, ayet_metni) VALUES %s "
        "ON CONFLICT (sure_no, ayet_no) DO NOTHING",
        rows,
        page_size=2000,
    )
    print(f"  {len(rows)} ayet satiri eklendi.")

    # --- Kelimeler ---
    print("Kelimeler tablosu tasiniyor (biraz surebilir)...")
    scur.execute(
        "SELECT SureNo, AyetNo, KelimeNo, KelimeMetni, KokId, NormalizedRoot FROM Kelimeler"
    )
    rows = scur.fetchall()
    execute_values(
        pcur,
        "INSERT INTO kelimeler "
        "(sure_no, ayet_no, kelime_no, kelime_metni, kok_id, normalized_root) VALUES %s",
        rows,
        page_size=5000,
    )
    print(f"  {len(rows)} kelime satiri eklendi.")

    # SERIAL sutununu, elle eklenen id'lerden sonra devam edecek sekilde ayarla
    pcur.execute("SELECT setval(pg_get_serial_sequence('kelimeler','kelime_id'), "
                 "COALESCE((SELECT MAX(kelime_id) FROM kelimeler), 1))")

    pconn.commit()
    pcur.close()
    pconn.close()
    sconn.close()
    print("Tasima tamamlandi.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Kullanim: python migrate_to_postgres.py <kuran_mufredat.db yolu>")
    migrate(sys.argv[1])
