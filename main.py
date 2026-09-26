"""
Kur'an okuma API'si - kelimeye dokununca kok anlamini gostermek icin.

Calistirma:
    $env:DATABASE_URL="postgresql://db_owner:SIFRENIZ@ep-...aws.neon.tech/kuran?sslmode=require"
    uvicorn main:app --reload
"""
import os
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

DATABASE_URL = os.environ.get("DATABASE_URL")

ORIGINS = ["*"]  # gelistirme icin acik; production'da kendi domain(ler)inle degistir


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL ortam degiskeni tanimli degil.")
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    yield
    await app.state.pool.close()


app = FastAPI(title="Kuran Mufredat API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Pydantic modelleri ----------

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
    kelimeler: list[Kelime]


class KokAnlami(BaseModel):
    kok_id: int
    baslik: str
    aciklama: Optional[str] = None


class KelimeDetay(BaseModel):
    kelime: Kelime
    kok: Optional[KokAnlami] = None


# ---------- Yardimci ----------

def _pool(app: FastAPI):
    return app.state.pool


# ---------- Endpointler ----------

@app.get("/", response_class=HTMLResponse)
async def ana_sayfa():
    """Solda ayetler, sağda Müfredat, merkezde şık navigasyonlu header arayüzü."""
    return """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kur'an-ı Kerim & Müfredat</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #b58941;
            --primary-light: #fef3c7;
            --border: #e5e7eb;
            --text-dark: #1f2937;
            --text-muted: #6b7280;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f9fafb;
            color: var(--text-dark);
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            direction: ltr; /* Sayfa bütününde LTR düzen garantiye alınır */
        }

        /* 1. Header */
        header {
            height: 60px;
            background: #ffffff;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 24px;
            z-index: 10;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            position: relative;
        }

        .header-nav-group {
            display: inline-flex;
            align-items: center;
            gap: 16px;
        }

        .header-title {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-dark);
            min-width: 140px;
            text-align: center;
        }

        .nav-btn {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 50%;
            width: 38px;
            height: 38px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: var(--text-dark);
            transition: all 0.2s ease;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .nav-btn:hover:not(:disabled) {
            background: #f8fafc;
            border-color: var(--primary);
            color: var(--primary);
            transform: scale(1.05);
        }

        .nav-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
            transform: none;
        }

        .nav-btn svg {
            width: 18px;
            height: 18px;
            stroke-width: 2.2;
        }

        /* Sol Kenar Sure Menüsü: Kulakçık ve Drawer */
        .drawer-container {
            position: fixed;
            top: 60px;
            left: 0;
            height: calc(100vh - 110px);
            z-index: 999;
            display: flex;
            transform: translateX(-260px);
            transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .drawer-container:hover {
            transform: translateX(0);
        }

        .sidebar-drawer {
            width: 260px;
            height: 100%;
            background: #ffffff;
            border-right: 1px solid var(--border);
            box-shadow: 4px 0 15px rgba(0,0,0,0.08);
            overflow-y: auto;
            padding: 16px 8px;
        }

        .drawer-tab {
            width: 36px;
            height: 120px;
            background: #ffffff;
            border: 1px solid var(--border);
            border-left: none;
            border-radius: 0 8px 8px 0;
            box-shadow: 3px 0 8px rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin-top: 30px;
            writing-mode: vertical-rl;
            text-orientation: mixed;
            font-size: 12px;
            font-weight: 600;
            color: var(--primary);
            letter-spacing: 1px;
            user-select: none;
        }

        .sidebar-drawer h3 {
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            padding: 0 12px 8px 12px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 8px;
        }

        .sure-list-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.15s;
        }

        .sure-list-item:hover {
            background: #f3f4f6;
        }

        .sure-list-item.active {
            background: var(--primary-light);
            color: #92400e;
            font-weight: 600;
        }

        /* 2. Ana Çalışma Alanı */
        main {
            flex: 1;
            display: flex;
            height: calc(100vh - 110px);
            overflow: hidden;
            margin-left: 36px;
        }

        /* SOL PANEL: Kur'an Ayetleri */
        .panel-ayetler {
            width: 58%;
            padding: 32px 48px;
            overflow-y: auto;
            background: #ffffff;
            border-right: 1px solid var(--border);
        }

        .ayet-card {
            margin-bottom: 40px;
            text-align: center;
            scroll-margin-top: 24px;
        }

        .ayet-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 12px;
        }

        .ayet-divider {
            height: 1px;
            background-color: #f3f4f6;
            margin-bottom: 20px;
        }

        .arabic-row {
            direction: rtl; /* Sadece Arapça yazının akışı RTL kalır */
            font-family: 'Amiri', serif;
            font-size: 34px;
            line-height: 2.3;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 12px;
        }

        .ayet-num-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            background: var(--primary);
            color: white;
            font-size: 14px;
            font-weight: 700;
            border-radius: 50%;
            font-family: 'Inter', sans-serif;
            user-select: none;
            margin-right: 8px;
        }

        .kelime-token {
            position: relative;
            cursor: default;
            padding: 2px 6px;
            border-radius: 6px;
            transition: all 0.15s ease;
        }

        .kelime-token.has-kok {
            cursor: pointer;
        }

        .kelime-token.has-kok:hover,
        .kelime-token.selected {
            background-color: var(--primary-light);
            color: #92400e;
        }

        /* SAĞ PANEL: Müfredat Kök Açıklaması */
        .panel-mufredat {
            width: 42%;
            background: #fafafa;
            padding: 28px;
            overflow-y: auto;
        }

        .mufredat-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 24px;
            background: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            min-height: 220px;
        }

        .mufredat-header {
            font-size: 18px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }

        .mufredat-body {
            font-size: 14px;
            line-height: 1.8;
            color: #374151;
        }

        .mufredat-body p {
            margin-bottom: 12px;
        }

        .mufredat-body .arabi {
            font-family: 'Amiri', serif;
            font-size: 20px;
            direction: rtl;
            unicode-bidi: isolate;
            color: #111827;
            padding: 0 4px;
            font-weight: 600;
        }

        /* 3. Footer */
        footer {
            height: 50px;
            background: #ffffff;
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 0 20px;
            z-index: 10;
        }

        .goto-form {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }

        .goto-input {
            width: 70px;
            padding: 5px 8px;
            border: 1px solid var(--border);
            border-radius: 4px;
            font-size: 13px;
            text-align: center;
            outline: none;
        }

        .goto-input:focus {
            border-color: var(--primary);
        }

        .goto-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            transition: opacity 0.2s;
        }

        .goto-btn:hover {
            opacity: 0.9;
        }
    </style>
</head>
<body>

    <!-- Header: Şık ok ikonları ve ortalanmış başlık grubu -->
    <header>
        <div class="header-nav-group">
            <button id="prev-btn" class="nav-btn" onclick="degistirSure(mevcutSureNo - 1)" title="Önceki Sûre">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
                </svg>
            </button>
            <div id="header-sure-title" class="header-title">Yükleniyor...</div>
            <button id="next-btn" class="nav-btn" onclick="degistirSure(mevcutSureNo + 1)" title="Sonraki Sûre">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
                </svg>
            </button>
        </div>
    </header>

    <!-- Sol Menü: Kulakçık ve Drawer -->
    <div class="drawer-container">
        <div id="sidebar-drawer" class="sidebar-drawer">
            <h3>Sûreler</h3>
            <div id="sure-list">Yükleniyor...</div>
        </div>
        <div class="drawer-tab">☰ SÛRELER</div>
    </div>

    <!-- İki Bölmeli Ana Alan -->
    <main>
        <!-- SOL BÖLÜM: Kur'an Ayetleri -->
        <section class="panel-ayetler" id="panel-ayetler">
            <div id="ayetler-container">Yükleniyor...</div>
        </section>

        <!-- SAĞ BÖLÜM: Müfredat Kök Açıklaması -->
        <section class="panel-mufredat" id="panel-mufredat">
            <div class="mufredat-card">
                <div id="mufredat-title" class="mufredat-header">Müfredat</div>
                <div id="mufredat-desc" class="mufredat-body">
                    İncelemek istediğiniz kelimenin kök anlamını görmek için soldaki ayetlerden bir kelimenin üzerine gelin.
                </div>
            </div>
        </section>
    </main>

    <!-- Footer: Ayete Atlama ve Otomatik Senkronize Kutu -->
    <footer>
        <form class="goto-form" onsubmit="handleGotoAyet(event)">
            <label for="ayet-input">Ayet No:</label>
            <input type="number" id="ayet-input" class="goto-input" min="1" placeholder="Ayet No" required>
            <button type="submit" class="goto-btn">Git</button>
        </form>
    </footer>

    <script>
        let mevcutSureNo = 1;
        let tumSureler = [];
        const cache = {};
        let observer = null;
        let isUserScrolling = true;

        async function init() {
            await fetchSureler();
            await yukleSure(mevcutSureNo);
        }

        async function fetchSureler() {
            try {
                const res = await fetch('/suraler');
                tumSureler = await res.json();
                renderSureListesi();
            } catch (err) {
                console.error("Sure listesi alınamadı:", err);
            }
        }

        function renderSureListesi() {
            const container = document.getElementById('sure-list');
            container.innerHTML = '';

            tumSureler.forEach(s => {
                const item = document.createElement('div');
                item.className = 'sure-list-item' + (s.sure_no === mevcutSureNo ? ' active' : '');
                item.innerHTML = `<span>${s.sure_no}. Sûre</span><span style="color:var(--text-muted); font-size:12px;">${s.ayet_sayisi} Ayet</span>`;
                item.onclick = () => degistirSure(s.sure_no);
                container.appendChild(item);
            });
        }

        async function yukleSure(sureNo) {
            mevcutSureNo = sureNo;
            document.getElementById('header-sure-title').textContent = `${sureNo}. Sûre`;
            
            // Navigasyon buton kontrolleri
            document.getElementById('prev-btn').disabled = sureNo <= 1;
            document.getElementById('next-btn').disabled = tumSureler.length > 0 && sureNo >= tumSureler.length;

            renderSureListesi();

            const ayetlerContainer = document.getElementById('ayetler-container');
            ayetlerContainer.innerHTML = '<div style="text-align:center; padding:20px;">Ayetler yükleniyor...</div>';

            try {
                const res = await fetch(`/sure/${sureNo}`);
                const ayetler = await res.json();
                renderAyetler(ayetler);
                setupIntersectionObserver();
            } catch (err) {
                ayetlerContainer.innerHTML = '<div style="color:red; text-align:center;">Sure getirilemedi.</div>';
            }
        }

        function degistirSure(sureNo) {
            if (sureNo < 1 || (tumSureler.length > 0 && sureNo > tumSureler.length)) return;
            yukleSure(sureNo);
        }

        function renderAyetler(ayetler) {
            const container = document.getElementById('ayetler-container');
            container.innerHTML = '';

            ayetler.forEach(ayet => {
                const card = document.createElement('div');
                card.className = 'ayet-card';
                card.id = `ayet-${ayet.ayet_no}`;
                card.dataset.ayetNo = ayet.ayet_no;

                const title = document.createElement('div');
                title.className = 'ayet-title';
                title.textContent = `${ayet.sure_no}. Sûre, ${ayet.ayet_no}. Ayet`;

                const divider = document.createElement('div');
                divider.className = 'ayet-divider';

                const arabicRow = document.createElement('div');
                arabicRow.className = 'arabic-row';

                // Kelimeler
                ayet.kelimeler.forEach(k => {
                    const span = document.createElement('span');
                    span.className = 'kelime-token' + (k.kok_id ? ' has-kok' : '');
                    span.textContent = k.kelime_metni;

                    if (k.kok_id) {
                        span.addEventListener('mouseenter', () => gosterMufredat(k.kelime_id, span));
                    }
                    arabicRow.appendChild(span);
                });

                // Ayet numarası dairesi
                const numBadge = document.createElement('span');
                numBadge.className = 'ayet-num-badge';
                numBadge.textContent = ayet.ayet_no;
                arabicRow.appendChild(numBadge);

                card.appendChild(title);
                card.appendChild(divider);
                card.appendChild(arabicRow);
                container.appendChild(card);
            });
        }

        // Scroll esnasında en üstte görünen ayeti bulup footer kutusuna yazan observer
        function setupIntersectionObserver() {
            if (observer) observer.disconnect();

            const scrollContainer = document.getElementById('panel-ayetler');
            const ayetCards = document.querySelectorAll('.ayet-card');
            const ayetInput = document.getElementById('ayet-input');

            observer = new IntersectionObserver((entries) => {
                if (!isUserScrolling) return;

                // Görünen elemanlar arasında üst kısıma en yakın olanı tespit et
                const visibleEntries = entries.filter(e => e.isIntersecting);
                if (visibleEntries.length > 0) {
                    visibleEntries.sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
                    const topmost = visibleEntries[0];
                    if (topmost && topmost.target.dataset.ayetNo) {
                        ayetInput.value = topmost.target.dataset.ayetNo;
                    }
                }
            }, {
                root: scrollContainer,
                threshold: [0.1, 0.5, 0.9]
            });

            ayetCards.forEach(card => observer.observe(card));
        }

        async function gosterMufredat(kelimeId, element) {
            // Önceki seçili kelime vurgusunu temizle
            document.querySelectorAll('.kelime-token.selected').forEach(el => el.classList.remove('selected'));
            element.classList.add('selected');

            const titleEl = document.getElementById('mufredat-title');
            const descEl = document.getElementById('mufredat-desc');

            if (!cache[kelimeId]) {
                try {
                    const res = await fetch(`/kelime/${kelimeId}`);
                    cache[kelimeId] = await res.json();
                } catch (err) {
                    titleEl.textContent = 'Hata';
                    descEl.innerHTML = '<span style="color:red;">Kök açıklaması alınamadı.</span>';
                    return;
                }
            }

            const data = cache[kelimeId];
            if (data.kok) {
                titleEl.textContent = data.kok.baslik || 'Kök Bilgisi';
                descEl.innerHTML = data.kok.aciklama || 'Açıklama bulunamadı.';
            } else {
                titleEl.textContent = 'Müfredat';
                descEl.innerHTML = 'Bu kelime için kayıtlı kök açıklaması bulunmuyor.';
            }
        }

        function handleGotoAyet(event) {
            event.preventDefault();
            const input = document.getElementById('ayet-input');
            const targetAyet = input.value;
            const ayetEl = document.getElementById(`ayet-${targetAyet}`);

            if (ayetEl) {
                isUserScrolling = false;
                ayetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                
                // Vurgu efekti
                ayetEl.style.transition = 'background-color 0.5s';
                ayetEl.style.backgroundColor = '#fef9c3';
                setTimeout(() => {
                    ayetEl.style.backgroundColor = 'transparent';
                    isUserScrolling = true;
                }, 1000);
            } else {
                alert(`${targetAyet}. ayet bulunamadı.`);
            }
        }

        init();
    </script>
</body>
</html>
    """


@app.get("/suraler")
async def sure_listesi():
    """Tum surelerin numarasi ve ayet sayisi (uygulamanin ana menusu icin)."""
    async with _pool(app).acquire() as conn:
        rows = await conn.fetch(
            "SELECT sure_no, COUNT(*) AS ayet_sayisi "
            "FROM ayetler GROUP BY sure_no ORDER BY sure_no"
        )
        return [{"sure_no": r["sure_no"], "ayet_sayisi": r["ayet_sayisi"]} for r in rows]


@app.get("/sure/{sure_no}", response_model=list[Ayet])
async def sure_detay(sure_no: int):
    """Bir surenin butun ayetlerini, her ayetin kelime listesiyle birlikte doner."""
    async with _pool(app).acquire() as conn:
        ayet_rows = await conn.fetch(
            "SELECT sure_no, ayet_no, ayet_metni FROM ayetler "
            "WHERE sure_no = $1 ORDER BY ayet_no",
            sure_no,
        )
        if not ayet_rows:
            raise HTTPException(status_code=404, detail="Sure bulunamadi")

        kelime_rows = await conn.fetch(
            "SELECT sure_no, ayet_no, kelime_id, kelime_no, kelime_metni, "
            "kok_id, normalized_root FROM kelimeler "
            "WHERE sure_no = $1 ORDER BY ayet_no, kelime_no",
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

    return [
        Ayet(
            sure_no=r["sure_no"],
            ayet_no=r["ayet_no"],
            ayet_metni=r["ayet_metni"],
            kelimeler=kelimeler_by_ayet.get(r["ayet_no"], []),
        )
        for r in ayet_rows
    ]


@app.get("/ayet/{sure_no}/{ayet_no}", response_model=Ayet)
async def ayet_detay(sure_no: int, ayet_no: int):
    """Tek bir ayeti kelime kelime doner (okuma ekraninda tek ayet acmak icin)."""
    async with _pool(app).acquire() as conn:
        ayet_row = await conn.fetchrow(
            "SELECT sure_no, ayet_no, ayet_metni FROM ayetler "
            "WHERE sure_no = $1 AND ayet_no = $2",
            sure_no, ayet_no,
        )
        if not ayet_row:
            raise HTTPException(status_code=404, detail="Ayet bulunamadi")

        kelime_rows = await conn.fetch(
            "SELECT kelime_id, kelime_no, kelime_metni, kok_id, normalized_root "
            "FROM kelimeler WHERE sure_no = $1 AND ayet_no = $2 ORDER BY kelime_no",
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