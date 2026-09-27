"""
Meal verilerini PostgreSQL'e yükler. İki modu destekler:

1) TEK MEALCİ, Tanzil formatı (sure|ayet|meal) txt dosyası:
    python import_meal.py tr.suleymaniye.txt suleymaniye "Süleymaniye Vakfı"
    python import_meal.py tr.golpinarli.txt golpinarli "Abdülbaki Gölpınarlı"

2) TÜM MEALCİLER BİRDEN, scraper'ın ürettiği .jsonl dosyası:
    python import_meal.py kuran_tum_mealler.jsonl
   (Her satırda {"sure":.., "ayet":.., "translations": {"İsim": "metin", ...}}
    olan dosya. yazar_kodu, mealci isminden otomatik üretilir; örn.
    "Süleymaniye Vakfı" -> "suleymaniye_vakfi".)

Hangi mod çalışacağı, dosya uzantısına (.jsonl mi, değil mi) bakılarak otomatik
seçilir.
"""
import asyncio
import json
import os
import re
import sys
import unicodedata
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL")


def slugify(name: str) -> str:
    """'Süleymaniye Vakfı' -> 'suleymaniye_vakfi' gibi veritabanı kodu üretir.
    Scraper'daki slugify ile aynı mantık; iki taraf da aynı yazar_kodu'nu
    üretsin diye burada da tutarlı tutuldu."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.lower()
    ascii_name = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")
    return ascii_name or "isimsiz"


async def _tabloyu_hazirla(conn):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS mealler (
            meal_id SERIAL PRIMARY KEY,
            sure_no INT NOT NULL,
            ayet_no INT NOT NULL,
            yazar_kodu VARCHAR(32) NOT NULL,
            yazar_adi VARCHAR(64) NOT NULL,
            meal_metni TEXT NOT NULL,
            CONSTRAINT uq_meal UNIQUE (sure_no, ayet_no, yazar_kodu)
        );
        CREATE INDEX IF NOT EXISTS idx_mealler_sure_ayet ON mealler(sure_no, ayet_no);
    """)


async def _kayitlari_yukle(conn, kayitlar):
    query = """
        INSERT INTO mealler (sure_no, ayet_no, yazar_kodu, yazar_adi, meal_metni)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (sure_no, ayet_no, yazar_kodu)
        DO UPDATE SET
            yazar_adi = EXCLUDED.yazar_adi,
            meal_metni = EXCLUDED.meal_metni;
    """
    batch_size = 500
    for i in range(0, len(kayitlar), batch_size):
        batch = kayitlar[i:i + batch_size]
        await conn.executemany(query, batch)
        print(f"Yüklendi: {min(i + batch_size, len(kayitlar))} / {len(kayitlar)}")


async def aktar(dosya_yolu: str, yazar_kodu: str, yazar_adi: str):
    """Tek mealci, Tanzil formatı (sure|ayet|meal) txt dosyasını yükler."""
    if not DATABASE_URL:
        print("Hata: DATABASE_URL ortam değişkeni tanımlı değil.")
        return

    if not os.path.exists(dosya_yolu):
        print(f"Hata: {dosya_yolu} bulunamadı.")
        return

    print(f"Dosya okunuyor: {dosya_yolu}")
    kayitlar = []

    with open(dosya_yolu, "r", encoding="utf-8") as f:
        for satir_no, satir in enumerate(f, start=1):
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue

            parcalar = satir.split("|", 2)
            if len(parcalar) == 3:
                try:
                    sure_no = int(parcalar[0].strip())
                    ayet_no = int(parcalar[1].strip())
                    meal_metni = parcalar[2].strip()
                    kayitlar.append((sure_no, ayet_no, yazar_kodu, yazar_adi, meal_metni))
                except ValueError:
                    print(f"Geçersiz satır ({satir_no}): {satir}")

    print(f"Toplam {len(kayitlar)} ayet meali bulundu. Veritabanına bağlanılıyor...")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await _tabloyu_hazirla(conn)
        await _kayitlari_yukle(conn, kayitlar)
        print(f"Başarılı: '{yazar_adi}' meali veritabanına aktarıldı.")
    finally:
        await conn.close()


async def aktar_jsonl(dosya_yolu: str):
    """Scraper'ın ürettiği .jsonl dosyasındaki TÜM mealcileri tek seferde yükler.
    Her satır: {"sure": int, "ayet": int, "translations": {"İsim": "metin", ...}}"""
    if not DATABASE_URL:
        print("Hata: DATABASE_URL ortam değişkeni tanımlı değil.")
        return

    if not os.path.exists(dosya_yolu):
        print(f"Hata: {dosya_yolu} bulunamadı.")
        return

    print(f"Dosya okunuyor: {dosya_yolu}")
    kayitlar = []
    gorulen_yazarlar = {}  # yazar_kodu -> yazar_adi (özet için)
    hatali_satir = 0

    with open(dosya_yolu, "r", encoding="utf-8") as f:
        for satir_no, satir in enumerate(f, start=1):
            satir = satir.strip()
            if not satir:
                continue
            try:
                obj = json.loads(satir)
                sure_no = int(obj["sure"])
                ayet_no = int(obj["ayet"])
                for yazar_adi, meal_metni in obj["translations"].items():
                    yazar_adi = yazar_adi.strip()
                    meal_metni = meal_metni.strip()
                    if not yazar_adi or not meal_metni:
                        continue
                    yazar_kodu = slugify(yazar_adi)
                    gorulen_yazarlar[yazar_kodu] = yazar_adi
                    kayitlar.append((sure_no, ayet_no, yazar_kodu, yazar_adi, meal_metni))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                hatali_satir += 1
                print(f"Geçersiz satır ({satir_no}): {e}")

    print(f"Toplam {len(kayitlar)} ayet-meal çifti bulundu "
          f"({len(gorulen_yazarlar)} mealci). Veritabanına bağlanılıyor...")
    if hatali_satir:
        print(f"Uyarı: {hatali_satir} satır atlandı (bozuk JSON).")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await _tabloyu_hazirla(conn)
        await _kayitlari_yukle(conn, kayitlar)
        print("\nBaşarılı: aşağıdaki mealler veritabanına aktarıldı:")
        for yazar_kodu, yazar_adi in sorted(gorulen_yazarlar.items()):
            print(f"  - {yazar_adi}  (yazar_kodu: {yazar_kodu})")
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım:")
        print('  Tek mealci : python import_meal.py tr.suleymaniye.txt suleymaniye "Süleymaniye Vakfı"')
        print("  Tüm mealler: python import_meal.py kuran_tum_mealler.jsonl")
        sys.exit(1)

    dosya = sys.argv[1]

    if dosya.lower().endswith(".jsonl"):
        asyncio.run(aktar_jsonl(dosya))
    else:
        kod = sys.argv[2] if len(sys.argv) > 2 else "golpinarli"
        ad = sys.argv[3] if len(sys.argv) > 3 else "Abdülbaki Gölpınarlı"
        asyncio.run(aktar(dosya, kod, ad))