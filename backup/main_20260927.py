"""
Kur'an okuma API'si - kelimeye dokununca kok anlamini gostermek icin.

Calistirma:
    $env:DATABASE_URL="postgresql://db_owner:SIFRENIZ@ep-...aws.neon.tech/kuran?sslmode=require"
    uvicorn main_2:app --reload
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

    app.state.sure_isimleri = {}
    try:
        async with app.state.pool.acquire() as conn:
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


# ---------- Yardimci ----------

def _pool(app: FastAPI):
    return app.state.pool


# ---------- Endpointler ----------

@app.get("/", response_class=HTMLResponse)
async def ana_sayfa():
    """Masaüstü ve mobil uyumlu Kur'an & Müfredat arayüzü."""
    return """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Kur'an-ı Kerim & Müfredat</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
            direction: ltr;
        }

        /* 1. Header (Ayetler Panelini Ortalayacak Şekilde Dizayn Edildi) */
        header {
            height: 56px;
            background: #ffffff;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 16px;
            z-index: 10;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            flex-shrink: 0;
            position: relative;
        }

        .header-ayetler-alan {
            width: calc(58% + 16px);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 32px;
        }

        .header-nav-group {
            display: inline-flex;
            align-items: center;
            gap: 12px;
        }

        .header-title-btn {
            background: none;
            border: 1px solid transparent;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 18px;
            font-weight: 700;
            color: var(--text-dark);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
            user-select: none;
        }

        .header-title-btn:hover {
            background: #f8fafc;
            border-color: var(--border);
            color: var(--primary);
        }

        .header-title-btn svg {
            width: 14px;
            height: 14px;
            stroke-width: 2.2;
            color: var(--text-muted);
        }

        .nav-btn {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 50%;
            width: 36px;
            height: 36px;
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
        }

        .nav-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }

        .nav-btn svg {
            width: 16px;
            height: 16px;
            stroke-width: 2.2;
        }

        /* Sol Menü: Kulakçık ve Drawer */
        .drawer-container {
            position: fixed;
            top: 56px;
            left: 0;
            height: calc(100vh - 106px);
            z-index: 999;
            display: flex;
            transform: translateX(-310px);
            transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .drawer-container:hover,
        .drawer-container.open {
            transform: translateX(0);
        }

        .sidebar-drawer {
            width: 310px;
            height: 100%;
            background: #ffffff;
            border-right: 1px solid var(--border);
            box-shadow: 4px 0 15px rgba(0,0,0,0.08);
            overflow-y: auto;
            padding: 16px 8px;
        }

        .drawer-tab {
            width: 32px;
            height: 100px;
            background: #ffffff;
            border: 1px solid var(--border);
            border-left: none;
            border-radius: 0 8px 8px 0;
            box-shadow: 3px 0 8px rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin-top: 20px;
            writing-mode: vertical-rl;
            text-orientation: mixed;
            font-size: 11px;
            font-weight: 600;
            color: var(--primary);
            letter-spacing: 1px;
            user-select: none;
        }

        .sidebar-drawer h3 {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            padding: 0 12px 8px 12px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 8px;
        }

        .sure-list-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            gap: 6px;
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

        .sure-isim-alani {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .sure-ayet-input {
            width: 44px;
            padding: 2px 4px;
            font-size: 11px;
            text-align: center;
            border: 1px solid var(--border);
            border-radius: 4px;
            outline: none;
            background: #ffffff;
            color: var(--text-dark);
        }

        .sure-ayet-input:focus {
            border-color: var(--primary);
            background: #fff;
        }

        .sure-ayet-sayisi {
            color: var(--text-muted);
            font-size: 11px;
            white-space: nowrap;
            min-width: 48px;
            text-align: right;
        }

        /* 2. Masaüstü Yerleşimi: Yan Yana */
        main {
            flex: 1;
            display: flex;
            height: calc(100vh - 106px);
            overflow: hidden;
            margin-left: 32px;
        }

        .panel-ayetler {
            width: 58%;
            padding: 24px 36px;
            overflow-y: auto;
            background: #ffffff;
            border-right: 1px solid var(--border);
        }

        .ayet-card {
            margin-bottom: 30px;
            text-align: center;
            scroll-margin-top: 20px;
        }

        .ayet-title {
            font-size: 16px;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 12px;
            letter-spacing: 0.01em;
        }

        .arabic-row {
            direction: rtl;
            font-family: 'Amiri', serif;
            font-size: 32px;
            line-height: 2.2;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 1px;
        }

        .ayet-num-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: var(--primary);
            color: white;
            font-size: 13px;
            font-weight: 700;
            border-radius: 50%;
            font-family: 'Inter', sans-serif;
            user-select: none;
            margin-right: 6px;
        }

        .kelime-token {
            position: relative;
            cursor: default;
            padding: 2px 3px;
            border-radius: 6px;
            transition: all 0.15s ease;
            -webkit-tap-highlight-color: transparent;
        }

        .kelime-token.has-kok {
            cursor: pointer;
        }

        .kelime-token.has-kok:hover,
        .kelime-token.selected {
            background-color: var(--primary-light);
            color: #92400e;
        }

        /* 3. Meal Kutusu: align-items: flex-start İle Üste Sabitlendi */
        .ayet-meal-box {
            margin-top: 14px;
            padding: 10px 16px;
            background: #fbfbfb;
            border-left: 3px solid var(--primary);
            border-radius: 0 6px 6px 0;
            display: flex;
            align-items: flex-start; /* Metin uzasa da butonlar yukarıda sabit kalır */
            justify-content: space-between;
            gap: 16px;
            font-size: 15px;
            line-height: 1.6;
            color: #4b5563;
        }

        .ayet-meal-sol {
            flex-shrink: 0;
            font-size: 11px;
            font-weight: 700;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-align: left;
            min-width: 100px;
            cursor: pointer;
            user-select: none;
            padding: 2px 4px;
            border-radius: 4px;
            transition: background 0.15s;
        }

        .ayet-meal-sol:hover {
            background: var(--primary-light);
            color: #92400e;
        }

        .ayet-meal-orta {
            flex: 1;
            text-align: center;
            color: #374151;
            padding-top: 1px;
        }

        .ayet-meal-sag {
            flex-shrink: 0;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
            padding-top: 1px;
        }

        .meal-sayac-inline {
            font-size: 10px;
            color: var(--text-muted);
            min-width: 28px;
            text-align: center;
        }

        .meal-nav-btn {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 2px 7px;
            font-size: 11px;
            cursor: pointer;
            color: var(--text-dark);
            transition: all 0.15s;
        }

        .meal-nav-btn:hover {
            background: #f3f4f6;
            border-color: var(--primary);
            color: var(--primary);
        }

        /* 4. Çiçekli / Sarmaşık Motifli Ayraç */
        .ayet-floral-divider {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 28px auto 8px auto;
            width: 100%;
            max-width: 520px;
            opacity: 0.85;
            user-select: none;
        }

        .ayet-floral-divider svg {
            width: 100%;
            height: 28px;
            fill: none;
            stroke: #2b2b2b;
            stroke-width: 1.2;
            stroke-linecap: round;
            stroke-linejoin: round;
        }

        .panel-mufredat {
            width: 42%;
            background: #fafafa;
            padding: 24px;
            overflow-y: auto;
        }

        .mufredat-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            background: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            min-height: 180px;
        }

        .mufredat-header {
            font-size: 16px;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 10px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 6px;
        }

        .mufredat-header.tiklanabilir {
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }

        .mufredat-header.tiklanabilir:hover {
            color: #92400e;
            text-decoration: underline;
        }

        .mufredat-header .kok-ipucu {
            font-size: 11px;
            font-weight: 500;
            color: var(--text-muted);
            text-decoration: none;
            white-space: nowrap;
        }

        .kok-vurgulu {
            background-color: #fef08a !important;
            color: #dc2626 !important;
            padding: 1px 5px !important;
            border-radius: 4px !important;
            font-weight: 700 !important;
        }

        /* Hızlı Sûre Seçici Modal */
        .sure-secici-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(17, 24, 39, 0.45);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2100;
            padding: 20px;
        }

        .sure-secici-backdrop.acik {
            display: flex;
        }

        .sure-secici-modal {
            background: #ffffff;
            border-radius: 12px;
            width: 100%;
            max-width: 400px;
            max-height: 75vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 12px 35px rgba(0,0,0,0.2);
            overflow: hidden;
        }

        .sure-secici-header {
            padding: 14px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: #fbfbfb;
        }

        .sure-secici-input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 14px;
            outline: none;
        }

        .sure-secici-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(181, 137, 65, 0.15);
        }

        .sure-secici-liste {
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .sure-secici-item {
            padding: 9px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13.5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.15s;
        }

        .sure-secici-item:hover,
        .sure-secici-item.secili {
            background: var(--primary-light);
            color: #92400e;
            font-weight: 600;
        }

        /* Meal Seçici Modal */
        .meal-secici-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(17, 24, 39, 0.45);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2200;
            padding: 20px;
        }

        .meal-secici-backdrop.acik {
            display: flex;
        }

        .meal-secici-modal {
            background: #ffffff;
            border-radius: 12px;
            width: 100%;
            max-width: 360px;
            max-height: 70vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 12px 35px rgba(0,0,0,0.2);
            overflow: hidden;
        }

        .meal-secici-header {
            padding: 14px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fbfbfb;
        }

        .meal-secici-liste {
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .meal-secici-item {
            padding: 10px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.15s;
        }

        .meal-secici-item:hover,
        .meal-secici-item.secili {
            background: var(--primary-light);
            color: #92400e;
            font-weight: 600;
        }

        /* Kok modal */
        .kok-modal-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(17, 24, 39, 0.45);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 2000;
            padding: 20px;
        }

        .kok-modal-backdrop.acik {
            display: flex;
        }

        .kok-modal {
            background: #ffffff;
            border-radius: 10px;
            width: 100%;
            max-width: 500px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }

        .kok-modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }

        .kok-modal-header h4 {
            font-size: 15px;
            font-weight: 700;
            color: var(--text-dark);
        }

        .kok-modal-kapat {
            background: none;
            border: none;
            font-size: 20px;
            line-height: 1;
            cursor: pointer;
            color: var(--text-muted);
            padding: 4px;
        }

        .kok-modal-kapat:hover {
            color: var(--text-dark);
        }

        .kok-modal-body {
            overflow-y: auto;
            padding: 8px;
        }

        .kok-ayet-item {
            padding: 12px 14px;
            border-radius: 6px;
            cursor: pointer;
            border-bottom: 1px solid #f3f4f6;
            transition: background 0.15s;
        }

        .kok-ayet-item:last-child {
            border-bottom: none;
        }

        .kok-ayet-item:hover {
            background: #f8fafc;
        }

        .kok-ayet-ust {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }

        .kok-ayet-badge {
            font-size: 13px;
            font-weight: 700;
            color: var(--primary);
        }

        .adet-badge {
            font-size: 11px;
            color: var(--text-muted);
            background: #f3f4f6;
            border-radius: 999px;
            padding: 2px 8px;
        }

        .kok-ayet-metin {
            font-family: 'Amiri', serif;
            font-size: 19px;
            line-height: 1.8;
            direction: rtl;
            text-align: right;
            color: #374151;
            margin-bottom: 6px;
        }

        .kok-daha-fazla {
            display: block;
            width: calc(100% - 16px);
            margin: 8px;
            padding: 10px;
            background: #f3f4f6;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            color: var(--text-dark);
        }

        .kok-daha-fazla:hover {
            background: #e5e7eb;
        }

        .kok-modal-durum {
            padding: 20px;
            text-align: center;
            color: var(--text-muted);
            font-size: 13px;
        }

        .mufredat-body {
            font-size: 14px;
            line-height: 1.7;
            color: #374151;
        }

        .mufredat-body p {
            margin-bottom: 10px;
        }

        .mufredat-body .arabi {
            font-family: 'Amiri', serif;
            font-size: 19px;
            direction: rtl;
            unicode-bidi: isolate;
            color: #111827;
            padding: 0 4px;
            font-weight: 600;
        }

        /* 5. Footer */
        footer {
            height: 50px;
            background: #ffffff;
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 0 16px;
            z-index: 10;
            flex-shrink: 0;
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

        .goto-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
        }

        /* Mobil Düzen */
        @media (max-width: 768px) {
            header {
                justify-content: center;
            }
            .header-ayetler-alan {
                width: 100%;
                margin-left: 0;
            }

            main {
                flex-direction: column;
                margin-left: 0;
            }

            .panel-ayetler {
                width: 100%;
                height: 55%;
                padding: 16px 18px;
                border-right: none;
                border-bottom: 2px solid var(--border);
            }

            .arabic-row {
                font-size: 26px;
                line-height: 2.1;
                gap: 1px;
            }

            .ayet-meal-box {
                flex-direction: column;
                align-items: center;
                gap: 8px;
                text-align: center;
            }
            .ayet-meal-sol, .ayet-meal-sag {
                align-self: center;
            }

            .panel-mufredat {
                width: 100%;
                height: 45%;
                padding: 14px 16px;
                background: #ffffff;
            }

            .mufredat-card {
                padding: 14px;
                min-height: auto;
                height: 100%;
                overflow-y: auto;
                border: 1px solid #e2e8f0;
            }

            .drawer-container {
                top: 56px;
                height: calc(100vh - 106px);
                transform: translateX(-310px);
            }

            .drawer-tab {
                width: 26px;
                height: 80px;
                font-size: 10px;
            }
        }
    </style>
</head>
<body>

    <!-- Header (Sûre Başlığı Sol Ayet Alanını Ortalar) -->
    <header>
        <div class="header-ayetler-alan">
            <div class="header-nav-group">
                <button id="prev-btn" class="nav-btn" onclick="degistirSure(mevcutSureNo - 1)" title="Önceki Sûre">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
                    </svg>
                </button>
                <button id="header-sure-btn" class="header-title-btn" onclick="acSureSeciciModal()" title="Sûre Seçmek veya Aramak İçin Tıklayın">
                    <span id="header-sure-title">Yükleniyor...</span>
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
                    </svg>
                </button>
                <button id="next-btn" class="nav-btn" onclick="degistirSure(mevcutSureNo + 1)" title="Sonraki Sûre">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
                    </svg>
                </button>
            </div>
        </div>
    </header>

    <!-- Sol Menü: Kulakçık ve Drawer -->
    <div id="drawer-container" class="drawer-container">
        <div id="sidebar-drawer" class="sidebar-drawer">
            <h3>Sûreler</h3>
            <div id="sure-list">Yükleniyor...</div>
        </div>
        <div class="drawer-tab" onclick="toggleDrawer()">☰ SÛRELER</div>
    </div>

    <!-- İki Bölmeli Ana Alan -->
    <main>
        <!-- SOL/ÜST PANEL: Ayetler -->
        <section class="panel-ayetler" id="panel-ayetler">
            <div id="ayetler-container">Yükleniyor...</div>
        </section>

        <!-- SAĞ/ALT PANEL: Müfredat -->
        <section class="panel-mufredat" id="panel-mufredat">
            <div class="mufredat-card">
                <div id="mufredat-title" class="mufredat-header">Müfredat</div>
                <div id="mufredat-desc" class="mufredat-body">
                    İncelemek istediğiniz kelimenin kök anlamını görmek için ayetlerden bir kelimeye gelin/dokunun.
                </div>
            </div>
        </section>
    </main>

    <!-- Hızlı Sûre Arama & Seçim Modalı -->
    <div id="sure-secici-backdrop" class="sure-secici-backdrop" onclick="if(event.target===this) kapatSureSeciciModal()">
        <div class="sure-secici-modal">
            <div class="sure-secici-header">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; font-size:15px;">Sûre Seç veya Ara</span>
                    <button class="kok-modal-kapat" onclick="kapatSureSeciciModal()">&times;</button>
                </div>
                <input type="text" id="sure-arama-input" class="sure-secici-input" placeholder="Sûre adı veya numarası yazın..." oninput="filtreleSureler(this.value)" onkeydown="sureAramaKeydown(event)">
            </div>
            <div id="sure-secici-liste" class="sure-secici-liste"></div>
        </div>
    </div>

    <!-- Genel Meal Seçim Modalı (Uzun Basınca Açılır) -->
    <div id="meal-secici-backdrop" class="meal-secici-backdrop" onclick="if(event.target===this) kapatMealSeciciModal()">
        <div class="meal-secici-modal">
            <div class="meal-secici-header">
                <span style="font-weight:700; font-size:15px;">Varsayılan Meali Seçin</span>
                <button class="kok-modal-kapat" onclick="kapatMealSeciciModal()">&times;</button>
            </div>
            <div id="meal-secici-liste" class="meal-secici-liste"></div>
        </div>
    </div>

    <!-- Kökün geçtiği sûreler modalı -->
    <div id="kok-modal-backdrop" class="kok-modal-backdrop" onclick="if(event.target===this) kapatKokModal()">
        <div class="kok-modal">
            <div class="kok-modal-header">
                <h4 id="kok-modal-baslik">Kök</h4>
                <button class="kok-modal-kapat" onclick="kapatKokModal()" aria-label="Kapat">&times;</button>
            </div>
            <div id="kok-modal-body" class="kok-modal-body"></div>
        </div>
    </div>

    <!-- Footer: Ayete Atlama -->
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
        let mevcutAyetlerVerisi = [];
        const cache = {};
        let observer = null;
        let isUserScrolling = true;

        // LocalStorage'dan tercih edilen meali al (yoksa varsayılan: 'diyanet')
        let aktifTercihEdilenMealKodu = localStorage.getItem('tercih_edilen_meal') || 'diyanet';

        // Vektörel Çiçekli / Kıvrımlı Ayraç SVG Şablonu
        const FLORAL_DIVIDER_HTML = `
            <div class="ayet-floral-divider">
                <svg viewBox="0 0 600 50">
                    <line x1="20" y1="25" x2="190" y2="25" stroke="#1f2937" stroke-width="1.2" />
                    <path d="M 195 25 Q 235 5 280 25" fill="none" stroke="#1f2937" stroke-width="1.3" />
                    <path d="M 215 17 Q 210 9 220 12 C 228 15 220 22 215 17 Z" fill="#2b2b2b" />
                    <path d="M 245 13 Q 248 5 256 9 C 260 14 252 20 245 13 Z" fill="#2b2b2b" />
                    <g transform="translate(250, 27) scale(0.65)">
                        <path d="M 0 0 C -10 15, -15 25, 0 35 C 15 25, 10 15, 0 0 Z" fill="none" stroke="#1f2937" stroke-width="1.8" />
                        <path d="M -5 12 C -18 10, -18 25, -2 22" fill="none" stroke="#1f2937" stroke-width="1.5" />
                        <path d="M 5 12 C 18 10, 18 25, 2 22" fill="none" stroke="#1f2937" stroke-width="1.5" />
                    </g>
                    <path d="M 270 12 C 270 34, 330 34, 330 12" fill="none" stroke="#1f2937" stroke-width="1.8" />
                    <g transform="translate(300, 10) scale(0.7)">
                        <path d="M 0 0 C -12 -18, 12 -18, 0 0 Z" fill="none" stroke="#1f2937" stroke-width="1.8" />
                        <path d="M -5 -4 C -22 -10, -15 -25, -2 -14" fill="none" stroke="#1f2937" stroke-width="1.5" />
                        <path d="M 5 -4 C 22 -10, 15 -25, 2 -14" fill="none" stroke="#1f2937" stroke-width="1.5" />
                    </g>
                    <path d="M 320 25 Q 365 5 405 25" fill="none" stroke="#1f2937" stroke-width="1.3" />
                    <path d="M 355 13 Q 352 5 344 9 C 340 14 348 20 355 13 Z" fill="#2b2b2b" />
                    <path d="M 385 17 Q 390 9 380 12 C 372 15 380 22 385 17 Z" fill="#2b2b2b" />
                    <g transform="translate(350, 27) scale(0.65)">
                        <path d="M 0 0 C -10 15, -15 25, 0 35 C 15 25, 10 15, 0 0 Z" fill="none" stroke="#1f2937" stroke-width="1.8" />
                        <path d="M -5 12 C -18 10, -18 25, -2 22" fill="none" stroke="#1f2937" stroke-width="1.5" />
                        <path d="M 5 12 C 18 10, 18 25, 2 22" fill="none" stroke="#1f2937" stroke-width="1.5" />
                    </g>
                    <line x1="410" y1="25" x2="580" y2="25" stroke="#1f2937" stroke-width="1.2" />
                </svg>
            </div>
        `;

        async function init() {
            await fetchSureler();
            await yukleSure(mevcutSureNo);
        }

        function toggleDrawer() {
            document.getElementById('drawer-container').classList.toggle('open');
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
                
                const isimSpan = document.createElement('span');
                isimSpan.className = 'sure-isim-alani';
                isimSpan.textContent = `${s.sure_no}. ${s.sure_adi || ''}`;

                const inputAyet = document.createElement('input');
                inputAyet.type = 'number';
                inputAyet.min = '1';
                inputAyet.max = String(s.ayet_sayisi);
                inputAyet.placeholder = 'Ayet';
                inputAyet.className = 'sure-ayet-input';

                inputAyet.addEventListener('click', (e) => e.stopPropagation());

                inputAyet.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        e.stopPropagation();
                        const ayetNo = parseInt(inputAyet.value);
                        if (ayetNo && ayetNo >= 1 && ayetNo <= s.ayet_sayisi) {
                            sureVeAyeteGit(s.sure_no, ayetNo);
                            document.getElementById('drawer-container').classList.remove('open');
                        } else {
                            alert(`Lütfen 1 ile ${s.ayet_sayisi} arasında geçerli bir ayet numarası girin.`);
                        }
                    }
                });

                const adetSpan = document.createElement('span');
                adetSpan.className = 'sure-ayet-sayisi';
                adetSpan.textContent = `${s.ayet_sayisi} Ayet`;

                item.appendChild(isimSpan);
                item.appendChild(inputAyet);
                item.appendChild(adetSpan);

                item.onclick = () => {
                    degistirSure(s.sure_no);
                    document.getElementById('drawer-container').classList.remove('open');
                };

                container.appendChild(item);
            });
        }

        /* Hızlı Sûre Arama / Modal İşlemleri */
        function acSureSeciciModal() {
            const backdrop = document.getElementById('sure-secici-backdrop');
            const input = document.getElementById('sure-arama-input');
            backdrop.classList.add('acik');
            input.value = '';
            filtreleSureler('');
            setTimeout(() => input.focus(), 50);
        }

        function kapatSureSeciciModal() {
            document.getElementById('sure-secici-backdrop').classList.remove('acik');
        }

        function filtreleSureler(query) {
            const liste = document.getElementById('sure-secici-liste');
            liste.innerHTML = '';
            const q = query.trim().toLowerCase();

            const eslesenler = tumSureler.filter(s => {
                if (!q) return true;
                const noStr = String(s.sure_no);
                const adi = (s.sure_adi || '').toLowerCase();
                return noStr === q || noStr.startsWith(q) || adi.includes(q);
            });

            if (eslesenler.length === 0) {
                liste.innerHTML = '<div style="text-align:center; padding:15px; color:var(--text-muted); font-size:13px;">Eşleşen sûre bulunamadı.</div>';
                return;
            }

            eslesenler.forEach((s) => {
                const row = document.createElement('div');
                row.className = 'sure-secici-item' + (s.sure_no === mevcutSureNo ? ' secili' : '');
                row.dataset.sureNo = s.sure_no;
                row.innerHTML = `<span><strong>${s.sure_no}.</strong> ${s.sure_adi || ''}</span><span style="color:var(--text-muted); font-size:12px;">${s.ayet_sayisi} Ayet</span>`;
                row.onclick = () => {
                    degistirSure(s.sure_no);
                    kapatSureSeciciModal();
                };
                liste.appendChild(row);
            });
        }

        function sureAramaKeydown(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const ilk = document.querySelector('.sure-secici-item');
                if (ilk && ilk.dataset.sureNo) {
                    degistirSure(parseInt(ilk.dataset.sureNo));
                    kapatSureSeciciModal();
                }
            } else if (e.key === 'Escape') {
                kapatSureSeciciModal();
            }
        }

        /* Tüm Sayfayı Seçilen Meale Döndürme & LocalStorage Yönetimi */
        function acMealSeciciModal() {
            // Mevcut ayetlerde bulunan tüm benzersiz yazarları topla
            const yazarlarMap = {};
            mevcutAyetlerVerisi.forEach(a => {
                (a.mealler || []).forEach(m => {
                    if (!yazarlarMap[m.yazar_kodu]) {
                        yazarlarMap[m.yazar_kodu] = m.yazar_adi;
                    }
                });
            });

            const liste = document.getElementById('meal-secici-liste');
            liste.innerHTML = '';

            const kodlar = Object.keys(yazarlarMap);
            if (kodlar.length === 0) {
                liste.innerHTML = '<div style="padding:15px; text-align:center; color:var(--text-muted);">Kayıtlı meal bulunamadı.</div>';
            } else {
                kodlar.forEach(kod => {
                    const row = document.createElement('div');
                    row.className = 'meal-secici-item' + (kod === aktifTercihEdilenMealKodu ? ' secili' : '');
                    row.innerHTML = `<span>${yazarlarMap[kod]}</span>${kod === aktifTercihEdilenMealKodu ? '<span>✓</span>' : ''}`;
                    row.onclick = () => {
                        aktifTercihEdilenMealKodu = kod;
                        localStorage.setItem('tercih_edilen_meal', kod);
                        kapatMealSeciciModal();
                        // Tüm sayfadaki ayetleri yeniden render ederek bu meale odakla
                        renderAyetler(mevcutAyetlerVerisi);
                    };
                    liste.appendChild(row);
                });
            }

            document.getElementById('meal-secici-backdrop').classList.add('acik');
        }

        function kapatMealSeciciModal() {
            document.getElementById('meal-secici-backdrop').classList.remove('acik');
        }

        async function sureVeAyeteGit(sureNo, ayetNo) {
            if (sureNo !== mevcutSureNo) {
                await yukleSure(sureNo);
                requestAnimationFrame(() => vurgulaVeGit(ayetNo));
            } else {
                vurgulaVeGit(ayetNo);
            }
        }

        async function yukleSure(sureNo) {
            mevcutSureNo = sureNo;
            const sureBilgisi = tumSureler.find(s => s.sure_no === sureNo);
            document.getElementById('header-sure-title').textContent =
                sureBilgisi ? `${sureNo}. ${sureBilgisi.sure_adi}` : `${sureNo}. Sûre`;
            
            document.getElementById('prev-btn').disabled = sureNo <= 1;
            document.getElementById('next-btn').disabled = tumSureler.length > 0 && sureNo >= tumSureler.length;

            renderSureListesi();

            const ayetlerContainer = document.getElementById('ayetler-container');
            ayetlerContainer.innerHTML = '<div style="text-align:center; padding:20px;">Ayetler yükleniyor...</div>';

            try {
                const res = await fetch(`/sure/${sureNo}`);
                mevcutAyetlerVerisi = await res.json();
                renderAyetler(mevcutAyetlerVerisi);
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

                // 1. Ayet Numarası ve Başlığı
                const title = document.createElement('div');
                title.className = 'ayet-title';
                const sureBilgisiK = tumSureler.find(s => s.sure_no === ayet.sure_no);
                const sureAdiK = sureBilgisiK ? sureBilgisiK.sure_adi : 'Sûre';
                title.textContent = `${ayet.sure_no}. ${sureAdiK}, ${ayet.ayet_no}. Ayet`;

                // 2. Arapça Ayet Metni
                const arabicRow = document.createElement('div');
                arabicRow.className = 'arabic-row';

                ayet.kelimeler.forEach(k => {
                    const span = document.createElement('span');
                    span.className = 'kelime-token' + (k.kok_id ? ' has-kok' : '');
                    span.textContent = k.kelime_metni;

                    if (k.kok_id) {
                        span.addEventListener('mouseenter', () => gosterMufredat(k.kelime_id, span));
                        span.addEventListener('click', (e) => {
                            e.stopPropagation();
                            gosterMufredat(k.kelime_id, span);
                        });
                    }
                    arabicRow.appendChild(span);
                });

                const numBadge = document.createElement('span');
                numBadge.className = 'ayet-num-badge';
                numBadge.textContent = ayet.ayet_no;
                arabicRow.appendChild(numBadge);

                card.appendChild(title);
                card.appendChild(arabicRow);

                // 3. Türkçe Meal (Solda Yazar, Sağda Seçici Sabit, Ortada Metin)
                if (ayet.mealler && ayet.mealler.length > 0) {
                    // Tercih edilen meal kodunu bul, yoksa ilkini seç
                    let mealIndex = ayet.mealler.findIndex(m => m.yazar_kodu === aktifTercihEdilenMealKodu);
                    if (mealIndex === -1) mealIndex = 0;

                    const mealDiv = document.createElement('div');
                    mealDiv.className = 'ayet-meal-box';

                    const guncelleMealIcerik = () => {
                        const m = ayet.mealler[mealIndex];
                        mealDiv.innerHTML = `
                            <div class="ayet-meal-sol" title="Tüm mealleri değiştirmek için tıklayın">${m.yazar_adi}</div>
                            <div class="ayet-meal-orta">${m.meal_metni}</div>
                            <div class="ayet-meal-sag">
                                ${ayet.mealler.length > 1 ? `
                                    <button class="meal-nav-btn prev-m">‹</button>
                                    <span class="meal-sayac-inline">${mealIndex + 1}/${ayet.mealler.length}</span>
                                    <button class="meal-nav-btn next-m">›</button>
                                ` : ''}
                            </div>
                        `;

                        // Meal yazarının üzerine tıklayınca veya uzun basınca modal aç
                        const solYazarEl = mealDiv.querySelector('.ayet-meal-sol');
                        let pressTimer = null;

                        solYazarEl.addEventListener('click', (e) => {
                            e.stopPropagation();
                            acMealSeciciModal();
                        });

                        solYazarEl.addEventListener('touchstart', (e) => {
                            pressTimer = setTimeout(() => {
                                acMealSeciciModal();
                            }, 500); // 500ms uzun basma süresi
                        }, {passive: true});

                        solYazarEl.addEventListener('touchend', () => {
                            clearTimeout(pressTimer);
                        });

                        // Yön oklarıyla o ayet özelinde gezinme
                        if (ayet.mealler.length > 1) {
                            mealDiv.querySelector('.prev-m').onclick = (e) => {
                                e.stopPropagation();
                                mealIndex = (mealIndex - 1 + ayet.mealler.length) % ayet.mealler.length;
                                guncelleMealIcerik();
                            };
                            mealDiv.querySelector('.next-m').onclick = (e) => {
                                e.stopPropagation();
                                mealIndex = (mealIndex + 1) % ayet.mealler.length;
                                guncelleMealIcerik();
                            };
                        }
                    };

                    guncelleMealIcerik();
                    card.appendChild(mealDiv);
                }

                // 4. Sonraki Ayete Geçmeden Önceki Çiçekli Ayraç (En Altta)
                const dividerWrapper = document.createElement('div');
                dividerWrapper.innerHTML = FLORAL_DIVIDER_HTML;
                card.appendChild(dividerWrapper);

                container.appendChild(card);
            });
        }

        function setupIntersectionObserver() {
            if (observer) observer.disconnect();

            const scrollContainer = document.getElementById('panel-ayetler');
            const ayetCards = document.querySelectorAll('.ayet-card');
            const ayetInput = document.getElementById('ayet-input');

            observer = new IntersectionObserver((entries) => {
                if (!isUserScrolling) return;

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
                titleEl.innerHTML = `<span>${data.kok.baslik || 'Kök Bilgisi'}</span><span class="kok-ipucu">Geçtiği ayetler ›</span>`;
                titleEl.classList.add('tiklanabilir');
                titleEl.dataset.kokId = data.kok.kok_id;
                descEl.innerHTML = data.kok.aciklama || 'Açıklama bulunamadı.';
            } else {
                titleEl.textContent = 'Müfredat';
                titleEl.classList.remove('tiklanabilir');
                delete titleEl.dataset.kokId;
                descEl.innerHTML = 'Bu kelime için kayıtlı kök açıklaması bulunmuyor.';
            }
        }

        document.getElementById('mufredat-title').addEventListener('click', (e) => {
            const kokId = e.currentTarget.dataset.kokId;
            if (kokId) gosterKokAyetleri(kokId, 0);
        });

        let onizlemeOncesiBaslik = '';
        let onizlemeOncesiAciklama = '';

        function renderAyetHtmlVurgulu(ayetMetni, vurguluKelimeler) {
            const tokens = ayetMetni.split(/\\s+/);
            const vurguSeti = new Set(vurguluKelimeler || []);
            return tokens.map(tok => {
                if (vurguSeti.has(tok)) {
                    return `<span class="kok-vurgulu">${tok}</span>`;
                }
                return tok;
            }).join(' ');
        }

        function olusturOnizlemeHtml(item, mealIdx) {
            const sureAdi = item.sure_adi ? `${item.sure_no}. ${item.sure_adi}` : `${item.sure_no}. Sûre`;
            const vurguluHtml = renderAyetHtmlVurgulu(item.ayet_metni, item.vurgulu_kelimeler);
            let html = `<div class="arabic-row" style="font-size:24px; line-height:2.2; justify-content:center;">${vurguluHtml}</div>`;

            if (item.mealler && item.mealler.length > 0) {
                const m = item.mealler[mealIdx];
                html += `
                    <div class="ayet-meal-box" style="margin-top:14px;">
                        <div class="ayet-meal-sol">${m.yazar_adi}</div>
                        <div class="ayet-meal-orta">${m.meal_metni}</div>
                        <div class="ayet-meal-sag">
                            ${item.mealler.length > 1 ? `
                                <button class="meal-nav-btn prev-onizleme">‹</button>
                                <span class="meal-sayac-inline">${mealIdx + 1}/${item.mealler.length}</span>
                                <button class="meal-nav-btn next-onizleme">›</button>
                            ` : ''}
                        </div>
                    </div>
                `;
            }
            return html;
        }

        async function gosterKokAyetleri(kokId, offsetParam) {
            const backdrop = document.getElementById('kok-modal-backdrop');
            const body = document.getElementById('kok-modal-body');
            const baslikEl = document.getElementById('kok-modal-baslik');
            const titleEl = document.getElementById('mufredat-title');
            const descEl = document.getElementById('mufredat-desc');

            if (offsetParam === 0) {
                onizlemeOncesiBaslik = titleEl.innerHTML;
                onizlemeOncesiAciklama = descEl.innerHTML;

                const kokAdi = titleEl.querySelector('span') ? titleEl.querySelector('span').textContent : 'Kök';
                baslikEl.textContent = `${kokAdi} — geçtiği ayetler`;
                backdrop.classList.add('acik');
                body.innerHTML = '<div class="kok-modal-durum">Yükleniyor...</div>';
            }

            try {
                const res = await fetch(`/kok/${kokId}/ayetler?limit=100&offset=${offsetParam}`);
                if (!res.ok) throw new Error('İstek başarısız');
                const veri = await res.json();

                if (offsetParam === 0) {
                    body.innerHTML = '';
                    if (!veri.ayetler.length) {
                        body.innerHTML = '<div class="kok-modal-durum">Bu kök için ayet bulunamadı.</div>';
                        return;
                    }
                } else {
                    const eskiButon = body.querySelector('.kok-daha-fazla');
                    if (eskiButon) eskiButon.remove();
                }

                veri.ayetler.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'kok-ayet-item';

                    const sureAdi = item.sure_adi ? `${item.sure_no}. ${item.sure_adi}` : `${item.sure_no}. Sûre`;
                    const vurguluHtml = renderAyetHtmlVurgulu(item.ayet_metni, item.vurgulu_kelimeler);

                    const ust = document.createElement('div');
                    ust.className = 'kok-ayet-ust';
                    ust.innerHTML = `<span class="kok-ayet-badge">${sureAdi}, ${item.ayet_no}. Ayet</span>` +
                        (item.adet > 1 ? `<span class="adet-badge">${item.adet} kez</span>` : '');

                    const metin = document.createElement('div');
                    metin.className = 'kok-ayet-metin';
                    metin.innerHTML = vurguluHtml;

                    row.appendChild(ust);
                    row.appendChild(metin);

                    // Modal içi mealler
                    let modalMealIndex = (item.mealler || []).findIndex(m => m.yazar_kodu === aktifTercihEdilenMealKodu);
                    if (modalMealIndex === -1) modalMealIndex = 0;

                    if (item.mealler && item.mealler.length > 0) {
                        const mealDiv = document.createElement('div');
                        mealDiv.className = 'ayet-meal-box';
                        mealDiv.style.marginTop = '6px';
                        mealDiv.style.padding = '8px 12px';

                        const guncelleModalMeal = () => {
                            const m = item.mealler[modalMealIndex];
                            mealDiv.innerHTML = `
                                <div class="ayet-meal-sol" style="font-size:10px;">${m.yazar_adi}</div>
                                <div class="ayet-meal-orta" style="font-size:13px;">${m.meal_metni}</div>
                                <div class="ayet-meal-sag">
                                    ${item.mealler.length > 1 ? `
                                        <button class="meal-nav-btn m-prev">‹</button>
                                        <span class="meal-sayac-inline">${modalMealIndex + 1}/${item.mealler.length}</span>
                                        <button class="meal-nav-btn m-next">›</button>
                                    ` : ''}
                                </div>
                            `;

                            if (item.mealler.length > 1) {
                                mealDiv.querySelector('.m-prev').onclick = (e) => {
                                    e.stopPropagation();
                                    modalMealIndex = (modalMealIndex - 1 + item.mealler.length) % item.mealler.length;
                                    guncelleModalMeal();
                                    guncelleOnizleme(modalMealIndex);
                                };
                                mealDiv.querySelector('.m-next').onclick = (e) => {
                                    e.stopPropagation();
                                    modalMealIndex = (modalMealIndex + 1) % item.mealler.length;
                                    guncelleModalMeal();
                                    guncelleOnizleme(modalMealIndex);
                                };
                            }
                        };

                        guncelleModalMeal();
                        row.appendChild(mealDiv);
                    }

                    // Önizleme fonksiyonu
                    const guncelleOnizleme = (idx) => {
                        titleEl.innerHTML = `<span>${sureAdi}, ${item.ayet_no}. Ayet</span><span class="kok-ipucu">‹ kök açıklaması</span>`;
                        titleEl.classList.remove('tiklanabilir');
                        descEl.innerHTML = olusturOnizlemeHtml(item, idx);

                        if (item.mealler && item.mealler.length > 1) {
                            const prevBtn = descEl.querySelector('.prev-onizleme');
                            const nextBtn = descEl.querySelector('.next-onizleme');
                            if (prevBtn && nextBtn) {
                                prevBtn.onclick = (e) => {
                                    e.stopPropagation();
                                    modalMealIndex = (modalMealIndex - 1 + item.mealler.length) % item.mealler.length;
                                    guncelleOnizleme(modalMealIndex);
                                };
                                nextBtn.onclick = (e) => {
                                    e.stopPropagation();
                                    modalMealIndex = (modalMealIndex + 1) % item.mealler.length;
                                    guncelleOnizleme(modalMealIndex);
                                };
                            }
                        }
                    };

                    row.addEventListener('mouseenter', () => guncelleOnizleme(modalMealIndex));
                    row.addEventListener('mouseleave', () => {
                        titleEl.innerHTML = onizlemeOncesiBaslik;
                        titleEl.classList.add('tiklanabilir');
                        descEl.innerHTML = onizlemeOncesiAciklama;
                    });

                    row.addEventListener('click', () => kokAyetineGit(item.sure_no, item.ayet_no));
                    body.appendChild(row);
                });

                if (veri.offset + veri.ayetler.length < veri.toplam) {
                    const buton = document.createElement('button');
                    buton.className = 'kok-daha-fazla';
                    buton.textContent = `Daha fazla göster (${veri.offset + veri.ayetler.length} / ${veri.toplam})`;
                    buton.onclick = () => gosterKokAyetleri(kokId, veri.offset + veri.ayetler.length);
                    body.appendChild(buton);
                }
            } catch (err) {
                body.innerHTML = '<div class="kok-modal-durum" style="color:red;">Ayet listesi alınamadı.</div>';
            }
        }

        function kapatKokModal() {
            document.getElementById('kok-modal-backdrop').classList.remove('acik');
            if (onizlemeOncesiBaslik) {
                document.getElementById('mufredat-title').innerHTML = onizlemeOncesiBaslik;
                document.getElementById('mufredat-title').classList.add('tiklanabilir');
                document.getElementById('mufredat-desc').innerHTML = onizlemeOncesiAciklama;
            }
        }

        function vurgulaVeGit(ayetNo) {
            const ayetEl = document.getElementById(`ayet-${ayetNo}`);
            if (!ayetEl) return false;
            isUserScrolling = false;
            ayetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
            ayetEl.style.transition = 'background-color 0.5s';
            ayetEl.style.backgroundColor = '#fef9c3';
            setTimeout(() => {
                ayetEl.style.backgroundColor = 'transparent';
                isUserScrolling = true;
            }, 1000);
            return true;
        }

        async function kokAyetineGit(sureNo, ayetNo) {
            kapatKokModal();
            sureVeAyeteGit(sureNo, ayetNo);
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                kapatKokModal();
                kapatSureSeciciModal();
                kapatMealSeciciModal();
            }
        });

        function handleGotoAyet(event) {
            event.preventDefault();
            const input = document.getElementById('ayet-input');
            const targetAyet = input.value;
            if (!vurgulaVeGit(targetAyet)) {
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