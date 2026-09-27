import json
import urllib.request

out_file = "tr.suleymaniye.txt"

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

print("Süleymaniye Vakfı Meali (temiz API üzerinden) çekiliyor...")

with open(out_file, "w", encoding="utf-8") as f_out:
    toplam = 0
    for sure_no in range(1, 115):
        # Açık kuran API'si: Süleymaniye Vakfı (Abdulaziz Bayındır) meali
        url = f"https://api.acikkuran.com/surah/{sure_no}?author=10"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=20).read().decode('utf-8')
            data = json.loads(res)

            ayetler = data.get("data", {}).get("verses", [])
            for ayet in ayetler:
                ayet_no = ayet.get("verse_number")
                # Sadece salt meal metnini al
                meal_metni = ayet.get("translation", {}).get("text", "")
                
                # İçinde kalmış olabilecek HTML veya dipnot etiketlerini temizle
                meal_metni = " ".join(meal_metni.replace("\n", " ").split())
                
                if meal_metni:
                    f_out.write(f"{sure_no}|{ayet_no}|{meal_metni}\n")
                    toplam += 1
            print(f"[{sure_no}/114] Sûre tamamlandı ({len(ayetler)} ayet).")
        except Exception as e:
            # Alternatif kaynak (kuranmeali endpoint fallback)
            print(f"Hata sure {sure_no}: {e}")

print(f"\nİşlem tamamlandı! Toplam temiz ayet sayısı: {toplam}")