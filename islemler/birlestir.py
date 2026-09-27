import sqlite3
import re

# 1. Buckwalter -> Arapça Harf Dönüşümü
BW_TO_ARABIC = {
    "'": "ء", ">": "أ", "&": "ؤ", "<": "إ", "}": "ئ", "A": "ا",
    "b": "ب", "p": "ة", "t": "ت", "v": "ث", "j": "ج", "H": "ح",
    "x": "خ", "d": "د", "*": "ذ", "r": "ر", "z": "ز", "s": "س",
    "$": "ش", "S": "ص", "D": "ض", "T": "ط", "Z": "ظ", "E": "ع",
    "g": "غ", "f": "ف", "q": "ق", "k": "ك", "l": "ل", "m": "م",
    "n": "ن", "h": "ه", "w": "و", "Y": "ى", "y": "ي"
}

BW_TO_LATIN = {
    "'": "e", ">": "e", "<": "e", "A": "e",
    "b": "b", "t": "t", "v": "s", "j": "c", "H": "h",
    "x": "h", "d": "d", "*": "z", "r": "r", "z": "z", "s": "s",
    "$": "s", "S": "s", "D": "d", "T": "t", "Z": "z", "E": "e",
    "g": "g", "f": "f", "q": "k", "k": "k", "l": "l", "m": "m",
    "n": "n", "h": "h", "w": "v", "y": "y", "Y": "y"
}

# Kelime sayılmaması gereken durak/secavend ve mushaf işaretleri
DURAK_ISARETLERI = {'ۚ', 'ۖ', 'ۗ', 'ۛ', 'ۙ', 'ۜ', '۞', '۩'}

# Fatiha dışındaki surelerin başındaki standart Besmele
BESMELE_METNI = "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ"
BESMELE_METNI_ALT = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"

def bw_to_arabic(bw_root: str) -> str:
    return "".join(BW_TO_ARABIC.get(c, c) for c in bw_root)

def bw_to_latin(bw_root: str) -> str:
    return "".join(BW_TO_LATIN.get(c, c) for c in bw_root.lower())

def clean_arabic_root(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    text = re.sub(r'[إأآءؤئ]', 'ا', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[^\u0600-\u06FF]', '', text)
    return text.strip()

def clean_latin_root(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = text.replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ğ", "g")
    text = re.sub(r'[^a-z]', '', text)
    return text.strip()

# Veritabanını Başlat
conn_out = sqlite3.connect("kuran_mufredat.db")
cur_out = conn_out.cursor()

cur_out.executescript("""
DROP TABLE IF EXISTS Kelimeler;
DROP TABLE IF EXISTS Ayetler;
DROP TABLE IF EXISTS Kokler;

CREATE TABLE Kokler (
    KokId INTEGER PRIMARY KEY,
    Baslik TEXT,
    NormalizedRoot TEXT,
    Aciklama TEXT
);

CREATE TABLE Ayetler (
    SureNo INTEGER,
    AyetNo INTEGER,
    AyetMetni TEXT,
    PRIMARY KEY (SureNo, AyetNo)
);

CREATE TABLE Kelimeler (
    KelimeId INTEGER PRIMARY KEY AUTOINCREMENT,
    SureNo INTEGER,
    AyetNo INTEGER,
    KelimeNo INTEGER,
    KelimeMetni TEXT,
    KokId INTEGER,
    NormalizedRoot TEXT,
    FOREIGN KEY (KokId) REFERENCES Kokler(KokId)
);
""")

# 1. Müfredat Tablosunu İndeksle
print("Müfredat kökleri işleniyor...")
conn_muf = sqlite3.connect("Mufredat.db")
cur_muf = conn_muf.cursor()
cur_muf.execute("SELECT KayitId, Baslik, Aciklama FROM Kayit")
mufredat_rows = cur_muf.fetchall()

root_dict_ar = {}
root_dict_lat = {}

for kid, baslik, aciklama in mufredat_rows:
    if not baslik:
        continue
    parts = baslik.split('/')
    ar_part = parts[0].strip()
    lat_part = parts[1].strip() if len(parts) > 1 else ""
    
    clean_ar = clean_arabic_root(ar_part)
    clean_lat = clean_latin_root(lat_part)
    
    cur_out.execute(
        "INSERT INTO Kokler (KokId, Baslik, NormalizedRoot, Aciklama) VALUES (?, ?, ?, ?)",
        (kid, baslik, clean_ar, aciklama)
    )
    # NOT: ilk kayıt kazanır (üzerine yazma yok) - aynı köke ait birden fazla
    # satır varsa sonraki satırların yanlışlıkla önceki doğru eşleşmeyi
    # ezmesini engeller.
    if clean_ar and clean_ar not in root_dict_ar:
        root_dict_ar[clean_ar] = kid
    if clean_lat and clean_lat not in root_dict_lat:
        root_dict_lat[clean_lat] = kid

conn_muf.close()

# --- NAKIS/İLLETLİ (zayıf harfli) köklerin genişletilmesi ---
# Müfredat'ta "أب", "أخ", "يد", "دم" gibi bazı kökler başlıkta 2 harfle
# (üçüncü zayıf harf düşürülmüş hâlde) yazılır; ama morfoloji dosyasındaki
# ROOT etiketi eksiksiz 3 harfli kökü verir (يدي، اخو، دمي...).
# Bu yüzden 2 harfli her kök için, sonuna و / ي eklenmiş hâllerini de
# (gerçek bir kayıtla çakışmadıkça) sözlüğe ekliyoruz. Var olan "ikizleme"
# (شد -> شدد gibi) davranışı da korunuyor.
def _genislet(sozluk, ek_harfler):
    ekler = {}
    for anahtar, kid in list(sozluk.items()):
        if len(anahtar) == 2:
            for ek in ek_harfler + (anahtar[-1],):
                aday = anahtar + ek
                if aday not in sozluk and aday not in ekler:
                    ekler[aday] = kid
    sozluk.update(ekler)

_genislet(root_dict_ar, ("و", "ي"))
_genislet(root_dict_lat, ("v", "y"))

# --- İlleti (zayıf) harflerin birbirinin yerine geçtiği durumlar ---
# Bazı "nakıs/ecvef" kökler Müfredat başlığında fiilin çekimli/vasıflı
# yüzey biçimiyle yazılır (örn. "جاء" kökü ج-ي-ء iken başlık düz "جاء" =
# ج-ا-ء şeklinde görünür). Bu yüzden kök aranırken و/ي/ا harflerinin
# birbirinin yerine geçtiği varyantları da deniyoruz.
ZAYIF_HARF_CIFTLERI = [("و", "ي"), ("ي", "و"), ("و", "ا"), ("ا", "و"), ("ي", "ا"), ("ا", "ي")]

def ar_kok_adaylari(kok: str):
    adaylar = [kok]
    for a, b in ZAYIF_HARF_CIFTLERI:
        if a in kok:
            adaylar.append(kok.replace(a, b))
    return adaylar


# 2. Morfoloji Dosyasını Oku
print("Morfoloji dosyası okunuyor...")
word_roots = {}

with open("quranic-corpus-morphology.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("LOCATION"):
            continue
        cols = line.split("\t")
        if len(cols) < 4:
            continue
        loc_raw, features = cols[0], cols[3]
        loc_parts = loc_raw.strip("()").split(":")
        s_no, a_no, w_no = int(loc_parts[0]), int(loc_parts[1]), int(loc_parts[2])
        
        if "ROOT:" in features:
            match = re.search(r'ROOT:([^\s\|]+)', features)
            if match:
                word_roots[(s_no, a_no, w_no)] = match.group(1)

# 3. Tanzil Metnini Temizleyerek Eşleştir
print("Ayetler ve kelimeler durak işaretleri temizlenerek eşleştiriliyor...")
kelimeler_to_insert = []
eslesen_sayisi = 0

with open("quran-uthmani.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 3:
            s_no, a_no, text = int(parts[0]), int(parts[1]), parts[2].strip()
            
            # Fatiha (1) ve Tevbe (9) haricindeki surelerin 1. ayetindeki Besmeleyi temizle
            if s_no not in (1, 9) and a_no == 1:
                if text.startswith(BESMELE_METNI):
                    text = text[len(BESMELE_METNI):].strip()
                elif text.startswith(BESMELE_METNI_ALT):
                    text = text[len(BESMELE_METNI_ALT):].strip()

            cur_out.execute("INSERT INTO Ayetler VALUES (?, ?, ?)", (s_no, a_no, text))
            
            # Durak işaretlerini kelime listesinden çıkar
            raw_words = text.split()
            valid_words = [w for w in raw_words if w not in DURAK_ISARETLERI]
            
            for idx, word_text in enumerate(valid_words, start=1):
                bw_root = word_roots.get((s_no, a_no, idx), None)
                
                kok_id = None
                ar_root_clean = None
                
                if bw_root:
                    ar_root = bw_to_arabic(bw_root)
                    ar_root_clean = clean_arabic_root(ar_root)
                    lat_root_clean = bw_to_latin(bw_root)
                    
                    for aday in ar_kok_adaylari(ar_root_clean):
                        if aday in root_dict_ar:
                            kok_id = root_dict_ar[aday]
                            break
                    if kok_id is None and lat_root_clean in root_dict_lat:
                        kok_id = root_dict_lat[lat_root_clean]
                    
                    if kok_id:
                        eslesen_sayisi += 1
                
                kelimeler_to_insert.append((s_no, a_no, idx, word_text, kok_id, ar_root_clean))

cur_out.executemany("""
    INSERT INTO Kelimeler (SureNo, AyetNo, KelimeNo, KelimeMetni, KokId, NormalizedRoot)
    VALUES (?, ?, ?, ?, ?, ?)
""", kelimeler_to_insert)

conn_out.commit()
conn_out.close()

print(f"\nİşlem Başarıyla Tamamlandı!")
print(f"Müfredat ile Eşleşen Kelime Sayısı: {eslesen_sayisi}")