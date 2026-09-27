# -*- coding: utf-8 -*-
"""
acikkuran.com'dan sayfadaki TÜM mealleri (Süleymaniye Vakfı, Bayraktar Bayraklı,
Mehmet Okuyan, Erhan Aktaş, Ali Rıza Safa, ve sayfada ne kadar mealci varsa hepsi)
ayet ayet çeken script.

Nasıl çalışır:
1) Her ayet için https://acikkuran.com/{sure}/{ayet} sayfasını çeker.
2) Sayfadaki her <h6> bloğunu bulur (her biri bir mealin başlığıdır: isim + kısa
   açıklama), h6'nın kardeşi olan <div><p> içindeki meal metnini alır.
3) Sonucu kuran_tum_mealler.jsonl dosyasına, her satırda bir ayet olacak şekilde
   yazar:
     {"sure": 1, "ayet": 1, "translations": {"Süleymaniye Vakfı": "...", ...}}
4) Tarama bitince, aynı veriden otomatik olarak her mealci için ayrı bir
   tr.<mealci_slug>.txt dosyası üretir ("sure|ayet|metin" formatında — orijinal
   script'inle aynı format).

Gereken kütüphaneler:
    pip install requests beautifulsoup4 --break-system-packages

Kesintiye uğrarsa: script kaldığı yerden devam edebilmesi için jsonl dosyasında
zaten çekilmiş olan (sure, ayet) çiftlerini baştan okuyup atlar. Yani script'i
tekrar çalıştırmak güvenlidir, kaldığı yerden sürer.
"""

import json
import os
import re
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

OUT_JSONL = "kuran_tum_mealler.jsonl"
LOG_FILE = "tum_mealler_hatalar.log"
TRANSLATOR_DIR = "mealler_ayri_dosyalar"

BASE_URL = "https://acikkuran.com/{sure}/{ayet}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# Sûrelerin ayet sayıları (1 - 114)
AYET_SAYILARI = [
    0, 7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110,
    98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83,
    182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55,
    78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28,
    28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19,
    26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9,
    5, 4, 7, 3, 6, 3, 5, 4, 5, 6
]

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def slugify(name):
    """'Süleymaniye Vakfı' -> 'suleymaniye_vakfi' gibi dosya adına uygun hale getirir."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.lower()
    ascii_name = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")
    return ascii_name or "isimsiz"


def fetch_ayet_translations(sure_no, ayet_no, retries=3):
    """Bir ayet sayfasındaki TÜM meal bloklarını {isim: metin} sözlüğü olarak döner.
    Hata olursa (None, hata_mesaji) döner."""
    url = BASE_URL.format(sure=sure_no, ayet=ayet_no)

    for attempt in range(1, retries + 1):
        try:
            res = SESSION.get(url, timeout=20)
        except requests.RequestException as e:
            if attempt == retries:
                return None, f"Bağlantı hatası: {e}"
            time.sleep(1.5 * attempt)
            continue

        if res.status_code != 200:
            if attempt == retries:
                return None, f"HTTP {res.status_code}"
            time.sleep(1.5 * attempt)
            continue

        # requests, sunucu charset belirtmediğinde yanlışlıkla Latin-1
        # varsayabiliyor; site aslında UTF-8 gönderiyor. Bunu elle sabitliyoruz
        # ki Türkçe karakterler bozulmasın (bkz. fix_encoding.py'deki not).
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        translations = {}
        for h6 in soup.find_all("h6"):
            name_node = h6.find(text=True, recursive=False)
            if not name_node:
                continue
            name = name_node.strip()
            if not name:
                continue

            sibling = h6.find_next_sibling("div")
            if sibling is None:
                continue
            p_tag = sibling.find("p")
            if p_tag is None:
                continue

            text = " ".join(p_tag.get_text().split())
            if text:
                # Aynı isim tekrar gelirse (olmamalı ama garanti olsun) üzerine yazma
                translations.setdefault(name, text)

        if not translations:
            return None, "Sayfada hiç meal bloğu bulunamadı"

        return translations, None

    return None, "Bilinmeyen hata"


def load_already_done(path):
    """jsonl dosyasından daha önce çekilmiş (sure, ayet) çiftlerini okur."""
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                done.add((obj["sure"], obj["ayet"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def scrape_all():
    already_done = load_already_done(OUT_JSONL)
    if already_done:
        print(f"Daha önce çekilmiş {len(already_done)} ayet bulundu, kaldığı yerden devam ediliyor.")

    total_new = 0
    failed = []
    all_translator_names = set()

    with open(OUT_JSONL, "a", encoding="utf-8") as f_out, \
         open(LOG_FILE, "a", encoding="utf-8") as f_log:

        for sure_no in range(1, 115):
            ayet_sayisi = AYET_SAYILARI[sure_no]
            for ayet_no in range(1, ayet_sayisi + 1):
                if (sure_no, ayet_no) in already_done:
                    continue

                translations, err = fetch_ayet_translations(sure_no, ayet_no)

                if err:
                    msg = f"[{sure_no}:{ayet_no}] HATA: {err}"
                    print(msg)
                    f_log.write(msg + "\n")
                    f_log.flush()
                    failed.append((sure_no, ayet_no))
                    continue

                record = {"sure": sure_no, "ayet": ayet_no, "translations": translations}
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                f_out.flush()

                all_translator_names.update(translations.keys())
                total_new += 1

                time.sleep(0.3)  # siteyi yormamak için kısa bekleme

            print(f"[{sure_no}/114] sûre tamamlandı.")

    print(f"\nTarama tamamlandı! Bu çalıştırmada çekilen yeni ayet: {total_new}")
    if failed:
        print(f"Başarısız olan {len(failed)} ayet var, detaylar: {LOG_FILE}")
        print("İlk birkaçı:", failed[:10])
    if all_translator_names:
        print(f"\nBu çalıştırmada görülen mealci sayısı: {len(all_translator_names)}")
        for n in sorted(all_translator_names):
            print(f"  - {n}")


def export_per_translator():
    """kuran_tum_mealler.jsonl dosyasını okuyup her mealci için ayrı
    tr.<mealci>.txt dosyası üretir (sure|ayet|metin formatında)."""
    if not os.path.exists(OUT_JSONL):
        print(f"{OUT_JSONL} bulunamadı, önce scrape_all() çalıştırılmalı.")
        return

    os.makedirs(TRANSLATOR_DIR, exist_ok=True)

    # Önce tüm mealci isimlerini topla
    translator_names = set()
    with open(OUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            translator_names.update(obj["translations"].keys())

    name_to_slug = {name: slugify(name) for name in translator_names}

    # Her mealci için dosya aç
    files = {
        name: open(os.path.join(TRANSLATOR_DIR, f"tr.{slug}.txt"), "w", encoding="utf-8")
        for name, slug in name_to_slug.items()
    }

    try:
        with open(OUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                sure_no = obj["sure"]
                ayet_no = obj["ayet"]
                for name, text in obj["translations"].items():
                    files[name].write(f"{sure_no}|{ayet_no}|{text}\n")
    finally:
        for f in files.values():
            f.close()

    print(f"\n{len(translator_names)} mealci için ayrı dosyalar '{TRANSLATOR_DIR}/' klasörüne yazıldı:")
    for name, slug in sorted(name_to_slug.items()):
        print(f"  - {name}  ->  {TRANSLATOR_DIR}/tr.{slug}.txt")


if __name__ == "__main__":
    scrape_all()
    export_per_translator()