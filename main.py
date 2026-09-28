"""
Kur'an okuma API'si - kelimeye dokununca kok anlamini gostermek icin.

Calistirma:
    uvicorn main:app --reload
"""
import json
import os
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# .env dosyasındaki ortam değişkenlerini yükler
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

ORIGINS = ["*"]  # gelistirme icin acik; production'da kendi domain(ler)inle degistir

# Kur'an verisi neredeyse hic degismiyor: tarayici / proxy onbellegi icin sure (saniye).
# Veriyi guncellersen kullanicilarda bu sure kadar eski veri gorunebilir.
CACHE_MAX_AGE = int(os.environ.get("CACHE_MAX_AGE", "86400"))
CACHE_CONTROL = f"public, max-age={CACHE_MAX_AGE}"

# Sunucu tarafinda en fazla kac surenin hazir JSON'u bellekte tutulsun (LRU).
SURE_CACHE_BOYUTU = int(os.environ.get("SURE_CACHE_BOYUTU", "24"))

# Sik kullanilan sorgular icin indeksler (idempotent; her acilista IF NOT EXISTS ile denenir).
INDEKSLER = [
    "CREATE INDEX IF NOT EXISTS idx_kelimeler_kok ON kelimeler (kok_id)",
    "CREATE INDEX IF NOT EXISTS idx_kelimeler_sure_ayet ON kelimeler (sure_no, ayet_no, kelime_no)",
    "CREATE INDEX IF NOT EXISTS idx_mealler_sure_ayet ON mealler (sure_no, ayet_no, meal_id)",
]


class _KucukLRU:
    """En son kullanilan N ogeyi tutan basit onbellek."""

    def __init__(self, maxsize: int):
        self.maxsize = max(1, maxsize)
        self._d: OrderedDict = OrderedDict()

    def get(self, key):
        val = self._d.get(key)
        if val is not None:
            self._d.move_to_end(key)
        return val

    def set(self, key, val):
        self._d[key] = val
        self._d.move_to_end(key)
        while len(self._d) > self.maxsize:
            self._d.popitem(last=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL ortam degiskeni tanimli degil.")
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

    app.state.sure_isimleri = {}
    app.state.ayet_sayilari = {}
    app.state.sure_listesi = []
    app.state.sure_cache = _KucukLRU(SURE_CACHE_BOYUTU)

    async with app.state.pool.acquire() as conn:
        # Indeksler (yetki/tablo sorunu olursa uygulamayi durdurma, uyar)
        for sql in INDEKSLER:
            try:
                await conn.execute(sql)
            except asyncpg.PostgresError as e:
                print(f"Uyari: indeks olusturulamadi ({e.__class__.__name__}): {sql}")

        # Gorus ve oneriler tablosunu otomatik olustur
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS oneriler (
                oneri_id SERIAL PRIMARY KEY,
                mesaj TEXT NOT NULL,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Sure basina ayet sayisi bir kez yuklenir (/suraler artik DB'ye gitmez)
        rows = await conn.fetch(
            "SELECT sure_no, COUNT(*) AS ayet_sayisi FROM ayetler GROUP BY sure_no ORDER BY sure_no"
        )
        app.state.ayet_sayilari = {r["sure_no"]: r["ayet_sayisi"] for r in rows}

        try:
            rows = await conn.fetch("SELECT sure_no, sure_adi FROM sureler")
            app.state.sure_isimleri = {r["sure_no"]: r["sure_adi"] for r in rows}
            if not app.state.sure_isimleri:
                print("Uyari: 'sureler' tablosu bos. 'python import_sureler.py' calistirdin mi?")
        except asyncpg.exceptions.UndefinedTableError:
            print("Uyari: 'sureler' tablosu yok. 'python import_sureler.py' calistirdin mi?")

    app.state.sure_listesi = [
        {
            "sure_no": no,
            "sure_adi": app.state.sure_isimleri.get(no, ""),
            "ayet_sayisi": adet,
        }
        for no, adet in app.state.ayet_sayilari.items()
    ]

    yield
    await app.state.pool.close()


def _sure_adi(app: FastAPI, sure_no: int) -> str:
    """Sûre ismini, startup'ta 'sureler' tablosundan yuklenen onbellekten dondurur."""
    return app.state.sure_isimleri.get(sure_no, "")


app = FastAPI(title="Kuran Mufredat API", lifespan=lifespan)

# Buyuk JSON yanitlari (ozellikle /sure/{n}) icin gzip
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statik dosyalar (CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- Pydantic modelleri ----------

class Kelime(BaseModel):
    kelime_id: int
    kelime_no: int
    kelime_metni: str
    kok_id: Optional[int] = None
    normalized_root: Optional[str] = None


class KokAnlami(BaseModel):
    kok_id: int
    baslik: str
    aciklama: Optional[str] = None


class KelimeDetay(BaseModel):
    kelime: Kelime
    kok: Optional[KokAnlami] = None


class OneriRequest(BaseModel):
    mesaj: str


# ---------- Yardimci ----------

def _pool(app: FastAPI):
    return app.state.pool


def _json_yanit(govde: bytes) -> Response:
    """Hazir JSON govdesini onbellek basligiyla dondurur."""
    return Response(
        content=govde,
        media_type="application/json",
        headers={"Cache-Control": CACHE_CONTROL},
    )


def _kelime_dict(r) -> dict:
    return {
        "kelime_id": r["kelime_id"],
        "kelime_no": r["kelime_no"],
        "kelime_metni": r["kelime_metni"],
        "kok_id": r["kok_id"],
        "normalized_root": r["normalized_root"],
    }


def _meal_dict(r) -> dict:
    return {
        "yazar_kodu": r["yazar_kodu"],
        "yazar_adi": r["yazar_adi"],
        "meal_metni": r["meal_metni"],
    }


def _json_bytes(veri) -> bytes:
    return json.dumps(veri, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# ---------- Sayfa Yönlendirmeleri ----------

@app.get("/")
async def ana_sayfa():
    """Tanıtım ve sade karşılama sayfası."""
    return FileResponse("templates/home.html")


@app.get("/oku")
async def okuma_sayfasi():
    """Masaüstü ve mobil uyumlu Kur'an & Müfredat arayüzü."""
    return FileResponse("templates/index.html")


@app.get("/oneri")
async def oneri_sayfasi():
    """Görüş ve öneri formu sayfası."""
    return FileResponse("templates/oneri.html")


# ---------- API Endpointleri ----------

@app.post("/api/oneri")
async def oneri_kaydet(talep: OneriRequest):
    """Kullanıcının gönderdiği görüş ve önerileri veritabanına kaydeder."""
    metin = talep.mesaj.strip()
    if not metin:
        raise HTTPException(status_code=400, detail="Mesaj boş olamaz.")

    async with _pool(app).acquire() as conn:
        await conn.execute("INSERT INTO oneriler (mesaj) VALUES ($1)", metin)
    return {"durum": "tamam"}


@app.get("/suraler")
async def sure_listesi(response: Response):
    """Tum surelerin numarasi ve ayet sayisi (uygulamanin ana menusu icin). Bellekten servis edilir."""
    response.headers["Cache-Control"] = CACHE_CONTROL
    return app.state.sure_listesi


async def _sure_govdesi(sure_no: int) -> bytes:
    """Bir surenin ayet + kelime + meal verisini tek JSON govdesi olarak uretir."""
    async with _pool(app).acquire() as conn:
        ayet_rows = await conn.fetch(
            "SELECT sure_no, ayet_no, ayet_metni FROM ayetler WHERE sure_no = $1 ORDER BY ayet_no",
            sure_no,
        )
        if not ayet_rows:
            raise HTTPException(status_code=404, detail="Sure bulunamadi")

        kelime_rows = await conn.fetch(
            "SELECT ayet_no, kelime_id, kelime_no, kelime_metni, kok_id, normalized_root "
            "FROM kelimeler WHERE sure_no = $1 ORDER BY ayet_no, kelime_no",
            sure_no,
        )

        meal_rows = await conn.fetch(
            "SELECT ayet_no, yazar_kodu, yazar_adi, meal_metni "
            "FROM mealler WHERE sure_no = $1 ORDER BY ayet_no, meal_id",
            sure_no,
        )

    kelimeler_by_ayet: dict[int, list[dict]] = {}
    for r in kelime_rows:
        kelimeler_by_ayet.setdefault(r["ayet_no"], []).append(_kelime_dict(r))

    mealler_by_ayet: dict[int, list[dict]] = {}
    for r in meal_rows:
        mealler_by_ayet.setdefault(r["ayet_no"], []).append(_meal_dict(r))

    return _json_bytes([
        {
            "sure_no": r["sure_no"],
            "ayet_no": r["ayet_no"],
            "ayet_metni": r["ayet_metni"],
            "mealler": mealler_by_ayet.get(r["ayet_no"], []),
            "kelimeler": kelimeler_by_ayet.get(r["ayet_no"], []),
        }
        for r in ayet_rows
    ])


@app.get("/sure/{sure_no}")
async def sure_detay(sure_no: int):
    """Bir surenin butun ayetlerini, her ayetin kelimeleri ve tum mealleriyle birlikte doner."""
    # Bilinmeyen sure numaralari DB'ye ve onbellege hic ulasmaz
    if sure_no not in app.state.ayet_sayilari:
        raise HTTPException(status_code=404, detail="Sure bulunamadi")

    govde = app.state.sure_cache.get(sure_no)
    if govde is None:
        govde = await _sure_govdesi(sure_no)
        app.state.sure_cache.set(sure_no, govde)
    return _json_yanit(govde)


@app.get("/ayet/{sure_no}/{ayet_no}")
async def ayet_detay(sure_no: int, ayet_no: int):
    """Tek bir ayeti kelime kelime ve tum mealleriyle doner."""
    async with _pool(app).acquire() as conn:
        ayet_row = await conn.fetchrow(
            "SELECT sure_no, ayet_no, ayet_metni FROM ayetler WHERE sure_no = $1 AND ayet_no = $2",
            sure_no, ayet_no,
        )
        if not ayet_row:
            raise HTTPException(status_code=404, detail="Ayet bulunamadi")

        kelime_rows = await conn.fetch(
            "SELECT kelime_id, kelime_no, kelime_metni, kok_id, normalized_root "
            "FROM kelimeler WHERE sure_no = $1 AND ayet_no = $2 ORDER BY kelime_no",
            sure_no, ayet_no,
        )

        meal_rows = await conn.fetch(
            "SELECT yazar_kodu, yazar_adi, meal_metni FROM mealler "
            "WHERE sure_no = $1 AND ayet_no = $2 ORDER BY meal_id",
            sure_no, ayet_no,
        )

    return _json_yanit(_json_bytes({
        "sure_no": ayet_row["sure_no"],
        "ayet_no": ayet_row["ayet_no"],
        "ayet_metni": ayet_row["ayet_metni"],
        "mealler": [_meal_dict(r) for r in meal_rows],
        "kelimeler": [_kelime_dict(r) for r in kelime_rows],
    }))


@app.get("/kelime/{kelime_id}", response_model=KelimeDetay)
async def kelime_anlami(kelime_id: int, response: Response):
    """
    Uygulamadaki asil ozellik: kullanici bir kelimeye dokundugunda
    bu endpoint cagrilir ve kok anlamini (Mufredat aciklamasi) doner.
    """
    async with _pool(app).acquire() as conn:
        row = await conn.fetchrow(
            "SELECT k.kelime_id, k.kelime_no, k.kelime_metni, k.kok_id, k.normalized_root, "
            "       ko.baslik, ko.aciklama "
            "FROM kelimeler k LEFT JOIN kokler ko ON k.kok_id = ko.kok_id "
            "WHERE k.kelime_id = $1",
            kelime_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Kelime bulunamadi")

    kelime = Kelime(
        kelime_id=row["kelime_id"],
        kelime_no=row["kelime_no"],
        kelime_metni=row["kelime_metni"],
        kok_id=row["kok_id"],
        normalized_root=row["normalized_root"],
    )
    kok = None
    if row["kok_id"] is not None:
        kok = KokAnlami(kok_id=row["kok_id"], baslik=row["baslik"], aciklama=row["aciklama"])

    response.headers["Cache-Control"] = CACHE_CONTROL
    return KelimeDetay(kelime=kelime, kok=kok)


@app.get("/kok/{kok_id}", response_model=KokAnlami)
async def kok_anlami(kok_id: int, response: Response):
    """Bir kokun butun bilgisini dogrudan kok_id ile getirir."""
    async with _pool(app).acquire() as conn:
        row = await conn.fetchrow(
            "SELECT kok_id, baslik, aciklama FROM kokler WHERE kok_id = $1", kok_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Kok bulunamadi")
        response.headers["Cache-Control"] = CACHE_CONTROL
        return KokAnlami(kok_id=row["kok_id"], baslik=row["baslik"], aciklama=row["aciklama"])


@app.get("/kok/{kok_id}/ayetler")
async def kok_gectigi_ayetler(kok_id: int, response: Response, limit: int = 100, offset: int = 0):
    """
    Bir kokun Kur'an'da hangi ayetlerde gectigini, o ayetlerin tum mealleriyle
    ve vurgulanacak kelimeleriyle birlikte doner.
    """
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    async with _pool(app).acquire() as conn:
        kok_row = await conn.fetchrow("SELECT kok_id FROM kokler WHERE kok_id = $1", kok_id)
        if not kok_row:
            raise HTTPException(status_code=404, detail="Kok bulunamadi")

        ayet_rows = await conn.fetch(
            """
            SELECT a.sure_no, a.ayet_no, a.ayet_metni, COUNT(k.kelime_id) AS adet,
                   ARRAY_AGG(k.kelime_metni) AS vurgulu_kelimeler,
                   COUNT(*) OVER() AS toplam_ayet_sayisi
            FROM kelimeler k
            JOIN ayetler a ON a.sure_no = k.sure_no AND a.ayet_no = k.ayet_no
            WHERE k.kok_id = $1
            GROUP BY a.sure_no, a.ayet_no, a.ayet_metni
            ORDER BY a.sure_no, a.ayet_no
            LIMIT $2 OFFSET $3
            """,
            kok_id, limit, offset,
        )

        toplam = ayet_rows[0]["toplam_ayet_sayisi"] if ayet_rows else 0

        mealler_map: dict[tuple[int, int], list[dict]] = {}
        if ayet_rows:
            sure_ve_ayetler = [(r["sure_no"], r["ayet_no"]) for r in ayet_rows]
            meal_rows = await conn.fetch(
                """
                SELECT m.sure_no, m.ayet_no, m.yazar_kodu, m.yazar_adi, m.meal_metni
                FROM mealler m
                JOIN (SELECT unnest($1::int[]) AS s, unnest($2::int[]) AS a) sub
                  ON m.sure_no = sub.s AND m.ayet_no = sub.a
                ORDER BY m.sure_no, m.ayet_no, m.meal_id
                """,
                [x[0] for x in sure_ve_ayetler],
                [x[1] for x in sure_ve_ayetler],
            )
            for m in meal_rows:
                mealler_map.setdefault((m["sure_no"], m["ayet_no"]), []).append(_meal_dict(m))

        response.headers["Cache-Control"] = CACHE_CONTROL
        return {
            "toplam": toplam,
            "limit": limit,
            "offset": offset,
            "ayetler": [
                {
                    "sure_no": r["sure_no"],
                    "sure_adi": _sure_adi(app, r["sure_no"]),
                    "ayet_no": r["ayet_no"],
                    "ayet_metni": r["ayet_metni"],
                    "mealler": mealler_map.get((r["sure_no"], r["ayet_no"]), []),
                    "vurgulu_kelimeler": list(r["vurgulu_kelimeler"]) if r["vurgulu_kelimeler"] else [],
                    "adet": r["adet"],
                }
                for r in ayet_rows
            ],
        }