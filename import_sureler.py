# -*- coding: utf-8 -*-
"""
main.py içindeki SURE_ISIMLERI listesini 'sureler' tablosuna aktarır.

Kullanım:
    python import_sureler.py

DATABASE_URL ortam değişkeninin ayarlı olması gerekir (import_meal.py'de
kullandığın aynı bağlantıyı kullanır).
"""
import asyncio
import os
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL")

# main.py'deki SURE_ISIMLERI ile birebir aynı (0. index boş, sureler 1'den başlar)
SURE_ISIMLERI = [
    "", "Fâtiha", "Bakara", "Âl-i İmrân", "Nisâ", "Mâide", "En'âm", "A'râf", "Enfâl",
    "Tevbe", "Yunus", "Hûd", "Yusuf", "Ra'd", "İbrahim", "Hicr", "Nahl", "İsrâ", "Kehf",
    "Meryem", "Tâ-Hâ", "Enbiyâ", "Hac", "Mü'minûn", "Nûr", "Furkan", "Şuarâ", "Neml",
    "Kasas", "Ankebût", "Rûm", "Lokman", "Secde", "Ahzâb", "Sebe'", "Fâtır", "Yâsin",
    "Sâffât", "Sâd", "Zümer", "Mü'min", "Fussilet", "Şûrâ", "Zuhruf", "Duhân", "Câsiye",
    "Ahkaf", "Muhammed", "Fetih", "Hucurât", "Kaf", "Zâriyât", "Tûr", "Necm", "Kamer",
    "Rahmân", "Vâkıa", "Hadid", "Mücâdele", "Haşr", "Mümtehine", "Saf", "Cum'a",
    "Münâfikûn", "Teğabün", "Talâk", "Tahrim", "Mülk", "Kalem", "Hâkka", "Meâric", "Nuh",
    "Cin", "Müzzemmil", "Müddessir", "Kıyamet", "İnsan", "Mürselât", "Nebe'", "Nâziât",
    "Abese", "Tekvir", "İnfitâr", "Mutaffifin", "İnşikak", "Bürûc", "Târık", "A'lâ",
    "Gâşiye", "Fecr", "Beled", "Şems", "Leyl", "Duhâ", "İnşirâh", "Tin", "Alak", "Kadir",
    "Beyyine", "Zilzâl", "Âdiyât", "Kâria", "Tekâsür", "Asr", "Hümeze", "Fil", "Kureyş",
    "Mâûn", "Kevser", "Kâfirûn", "Nasr", "Tebbet", "İhlâs", "Felâk", "Nâs",
]


async def aktar():
    if not DATABASE_URL:
        print("Hata: DATABASE_URL ortam değişkeni tanımlı değil.")
        return

    if len(SURE_ISIMLERI) != 115:  # index 0 boş + 114 sure
        print(f"Uyarı: liste 115 eleman bekliyordu, {len(SURE_ISIMLERI)} bulundu. Kontrol et.")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sureler (
                sure_no INT PRIMARY KEY,
                sure_adi VARCHAR(32) NOT NULL
            );
        """)

        kayitlar = [
            (sure_no, isim)
            for sure_no, isim in enumerate(SURE_ISIMLERI)
            if sure_no > 0 and isim  # 0. indexi (boş) atla
        ]

        await conn.executemany(
            """
            INSERT INTO sureler (sure_no, sure_adi)
            VALUES ($1, $2)
            ON CONFLICT (sure_no) DO UPDATE SET sure_adi = EXCLUDED.sure_adi;
            """,
            kayitlar,
        )

        print(f"Başarılı: {len(kayitlar)} sûre ismi 'sureler' tablosuna aktarıldı.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(aktar())