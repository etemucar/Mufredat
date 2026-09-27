# -*- coding: utf-8 -*-
"""
kuran_tum_mealler.jsonl dosyasındaki mojibake (yanlış kodlama) hatasını düzeltir.

Sorunun sebebi: requests kütüphanesi sunucudan charset bilgisi gelmediğinde
UTF-8 baytlarını yanlışlıkla Latin-1 (ISO-8859-1) olarak okudu. Bu yüzden
"Bayraklı" gibi kelimeler "BayraklÄ±" olarak kaydedildi.

Düzeltme mantığı tam tersini yapar: bozuk string'i Latin-1 olarak byte'lara
çevirip, o byte'ları UTF-8 olarak yeniden okur. Böylece orijinal doğru metin
geri elde edilir.

Kullanım:
    python fix_encoding.py

Girdi : kuran_tum_mealler.jsonl (bozuk)
Çıktı : kuran_tum_mealler_fixed.jsonl (düzeltilmiş)
        mealler_ayri_dosyalar/ klasörü de düzeltilmiş haliyle YENİDEN üretilir.
"""

import json
import os
import re
import unicodedata

IN_FILE = "kuran_tum_mealler.jsonl"
OUT_FILE = "kuran_tum_mealler_fixed.jsonl"
TRANSLATOR_DIR = "mealler_ayri_dosyalar"


def slugify(name):
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.lower()
    ascii_name = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")
    return ascii_name or "isimsiz"


def duzelt(metin: str) -> str:
    """Mojibake'i düzeltmeyi dener. Başarısız olursa (zaten doğruysa ya da
    başka türden bir sorunsa) metni olduğu gibi bırakır."""
    if not metin:
        return metin
    try:
        duzeltilmis = metin.encode("latin-1").decode("utf-8")
        return duzeltilmis
    except (UnicodeEncodeError, UnicodeDecodeError):
        return metin


def main():
    if not os.path.exists(IN_FILE):
        print(f"Hata: {IN_FILE} bulunamadı.")
        return

    ornek_once = None
    ornek_sonra = None
    toplam = 0
    translator_names = set()

    with open(IN_FILE, "r", encoding="utf-8") as f_in, \
         open(OUT_FILE, "w", encoding="utf-8") as f_out:

        for satir in f_in:
            satir = satir.strip()
            if not satir:
                continue

            obj = json.loads(satir)
            yeni_translations = {}
            for isim, metin in obj["translations"].items():
                yeni_isim = duzelt(isim)
                yeni_metin = duzelt(metin)
                yeni_translations[yeni_isim] = yeni_metin
                translator_names.add(yeni_isim)

                if ornek_once is None and isim != yeni_isim:
                    ornek_once = isim
                    ornek_sonra = yeni_isim

            yeni_obj = {"sure": obj["sure"], "ayet": obj["ayet"], "translations": yeni_translations}
            f_out.write(json.dumps(yeni_obj, ensure_ascii=False) + "\n")
            toplam += 1

    print(f"Toplam {toplam} ayet düzeltildi -> {OUT_FILE}")
    if ornek_once:
        print(f"Örnek düzeltme: {ornek_once!r}  ->  {ornek_sonra!r}")

    # Ayrı mealci dosyalarını da düzeltilmiş veriden YENİDEN üret
    os.makedirs(TRANSLATOR_DIR, exist_ok=True)
    name_to_slug = {name: slugify(name) for name in translator_names}
    files = {
        name: open(os.path.join(TRANSLATOR_DIR, f"tr.{slug}.txt"), "w", encoding="utf-8")
        for name, slug in name_to_slug.items()
    }
    try:
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            for satir in f:
                obj = json.loads(satir)
                for isim, metin in obj["translations"].items():
                    files[isim].write(f"{obj['sure']}|{obj['ayet']}|{metin}\n")
    finally:
        for fh in files.values():
            fh.close()

    print(f"\n{len(translator_names)} mealci için '{TRANSLATOR_DIR}/' klasörü düzeltilmiş haliyle yeniden yazıldı:")
    for name, slug in sorted(name_to_slug.items()):
        print(f"  - {name}  ->  tr.{slug}.txt")


if __name__ == "__main__":
    main()