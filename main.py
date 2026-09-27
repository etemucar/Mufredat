"""
Kur'an okuma API'si - kelimeye dokununca kok anlamini gostermek icin.

Calistirma:
    uvicorn main:app --reload
"""
import os
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# .env dosyasındaki ortam değişkenlerini yükler
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

ORIGINS = ["*"]  # gelistirme icin acik; production'da kendi domain(ler)inle degistir


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL ortam degiskeni tanimli degil.")
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

    app.state.sure_isimleri = {}
    try:
        async with app.state.pool.acquire() as conn:
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
            rows = await conn.fetch("SELECT sure_no, sure_adi FROM sureler")
            app.state.sure_isimleri = {r["sure_no"]: r["sure_adi"] for r in rows}
        if not app.state.sure_isimleri:
            print("Uyari: 'sureler' tablosu bos. 'python import_sureler.py' calistirdin mi?")
    except asyncpg.exceptions.UndefinedTableError:
        print("Uyari: 'sureler' tablosu yok. 'python import_sureler.py' calistirdin mi?")

    yield
    await app.state.pool.close()


def _sure_adi(app: FastAPI, sure_no: int) -> str:
    """Sûre ismini, startup'ta 'sureler' tablosundan yuklenen onbellekten dondurur."""
    return app.state.sure_isimleri.get(sure_no, "")


app = FastAPI(title="Kuran Mufredat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statik dosyalar (CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- Pydantic modelleri ----------

class Meal(BaseModel):
    yazar_kodu: str
    yazar_adi: str
    meal_metni: str


class Kelime(BaseModel):
    kelime_id: int
    kelime_no: int
    kelime_metni: str
    kok_id: Optional[int] = None
    normalized_root: Optional[str] = None


class Ayet(BaseModel):
    sure_no: int
    ayet_no: int
    ayet_metni: str
    mealler: list[Meal] = []
    kelimeler: list[Kelime]


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
async def sure_listesi():
    """Tum surelerin numarasi ve ayet sayisi (uygulamanin ana menusu icin)."""
    async with _pool(app).acquire() as conn:
        rows = await conn.fetch(
            "SELECT sure_no, COUNT(*) AS ayet_sayisi "
            "FROM ayetler GROUP BY sure_no ORDER BY sure_no"
        )
        return [
            {
                "sure_no": r["sure_no"],
                "sure_adi": _sure_adi(app, r["sure_no"]),
                "ayet_sayisi": r["ayet_sayisi"],
            }
            for r in rows
        ]


@app.get("/sure/{sure_no}", response_model=list[Ayet])
async def sure_detay(sure_no: int):
    """Bir surenin butun ayetlerini, her ayetin kelimeleri ve tum mealleriyle birlikte doner."""
    async with _pool(app).acquire() as conn:
        ayet_rows = await conn.fetch(
            "SELECT sure_no, ayet_no, ayet_metni FROM ayetler WHERE sure_no = $1 ORDER BY ayet_no",
            sure_no,
        )
        if not ayet_rows:
            raise HTTPException(status_code=404, detail="Sure bulunamadi")

        kelime_rows = await conn.fetch(
            "SELECT sure_no, ayet_no, kelime_id, kelime_no, kelime_metni, kok_id, normalized_root "
            "FROM kelimeler WHERE sure_no = $1 ORDER BY ayet_no, kelime_no",
            sure_no,
        )

        meal_rows = await conn.fetch(
            "SELECT sure_no, ayet_no, yazar_kodu, yazar_adi, meal_metni "
            "FROM mealler WHERE sure_no = $1 ORDER BY ayet_no, meal_id",
            sure_no,
        )

    kelimeler_by_ayet: dict[int, list[Kelime]] = {}
    for r in kelime_rows:
        kelimeler_by_ayet.setdefault(r["ayet_no"], []).append(
            Kelime(
                kelime_id=r["kelime_id"],
                kelime_no=r["kelime_no"],
                kelime_metni=r["kelime_metni"],
                kok_id=r["kok_id"],
                normalized_root=r["normalized_root"],
            )
        )

    mealler_by_ayet: dict[int, list[Meal]] = {}
    for r in meal_rows:
        mealler_by_ayet.setdefault(r["ayet_no"], []).append(
            Meal(
                yazar_kodu=r["yazar_kodu"],
                yazar_adi=r["yazar_adi"],
                meal_metni=r["meal_metni"],
            )
        )

    return [
        Ayet(
            sure_no=r["sure_no"],
            ayet_no=r["ayet_no"],
            ayet_metni=r["ayet_metni"],
            kelimeler=kelimeler_by_ayet.get(r["ayet_no"], []),
            mealler=mealler_by_ayet.get(r["ayet_no"], []),
        )
        for r in ayet_rows
    ]


@app.get("/ayet/{sure_no}/{ayet_no}", response_model=Ayet)
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

    return Ayet(
        sure_no=ayet_row["sure_no"],
        ayet_no=ayet_row["ayet_no"],
        ayet_metni=ayet_row["ayet_metni"],
        kelimeler=[
            Kelime(
                kelime_id=r["kelime_id"],
                kelime_no=r["kelime_no"],
                kelime_metni=r["kelime_metni"],
                kok_id=r["kok_id"],
                normalized_root=r["normalized_root"],
            )
            for r in kelime_rows
        ],
        mealler=[
            Meal(
                yazar_kodu=r["yazar_kodu"],
                yazar_adi=r["yazar_adi"],
                meal_metni=r["meal_metni"],
            )
            for r in meal_rows
        ],
    )


@app.get("/kelime/{kelime_id}", response_model=KelimeDetay)
async def kelime_anlami(kelime_id: int):
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

    return KelimeDetay(kelime=kelime, kok=kok)


@app.get("/kok/{kok_id}", response_model=KokAnlami)
async def kok_anlami(kok_id: int):
    """Bir kokun butun bilgisini dogrudan kok_id ile getirir."""
    async with _pool(app).acquire() as conn:
        row = await conn.fetchrow(
            "SELECT kok_id, baslik, aciklama FROM kokler WHERE kok_id = $1", kok_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Kok bulunamadi")
        return KokAnlami(kok_id=row["kok_id"], baslik=row["baslik"], aciklama=row["aciklama"])


@app.get("/kok/{kok_id}/ayetler")
async def kok_gectigi_ayetler(kok_id: int, limit: int = 100, offset: int = 0):
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
                mealler_map.setdefault((m["sure_no"], m["ayet_no"]), []).append({
                    "yazar_kodu": m["yazar_kodu"],
                    "yazar_adi": m["yazar_adi"],
                    "meal_metni": m["meal_metni"],
                })

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