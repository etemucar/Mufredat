let mevcutSureNo = 1;
let tumSureler = [];
let mevcutAyetlerVerisi = [];
const cache = {};
let observer = null;
let isUserScrolling = true;

// 1. LocalStorage: Kaldığı yer (Sûre ve Ayet)
const kayitliSure = parseInt(localStorage.getItem('son_sure_no'));
if (kayitliSure && kayitliSure >= 1 && kayitliSure <= 114) {
    mevcutSureNo = kayitliSure;
}
let baslangicAyetHedefi = parseInt(localStorage.getItem('son_ayet_no')) || 1;

// 2. LocalStorage: Tercih Edilen Mealler Listesi
let aktifMealler = [];
try {
    const rawMealler = localStorage.getItem('aktif_mealler');
    if (rawMealler) aktifMealler = JSON.parse(rawMealler);
} catch (e) {
    aktifMealler = [];
}

// 3. LocalStorage: Ayet Notları
let ayetNotlari = {};
try {
    const rawNotlar = localStorage.getItem('ayet_notlari');
    if (rawNotlar) ayetNotlari = JSON.parse(rawNotlar);
} catch (e) {
    ayetNotlari = {};
}

let duzenlenenAyetKey = null;

// 4. LocalStorage: Türkçe meal yazı boyutu çarpanı
const MEAL_OLCEK_MIN = 0.8;
const MEAL_OLCEK_MAX = 1.8;
let mealOlcek = 1;
try {
    const kayitliOlcek = parseFloat(localStorage.getItem('meal_olcek'));
    if (kayitliOlcek >= MEAL_OLCEK_MIN && kayitliOlcek <= MEAL_OLCEK_MAX) mealOlcek = kayitliOlcek;
} catch (e) { /* varsayılan */ }
document.documentElement.style.setProperty('--meal-olcek', mealOlcek);

// SVG: Büyüteç
const MEAL_ZOOM_ICON = `
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <circle cx="11" cy="11" r="7"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
</svg>`;

// SVG: Boş Not İkonu
const NOTE_ICON_EMPTY = `
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="9" y1="13" x2="15" y2="13"></line>
    <line x1="9" y1="17" x2="13" y2="17"></line>
</svg>`;

// SVG: Dolu Not İkonu (Not Var)
const NOTE_ICON_FILLED = `
<svg viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <path d="M19.41 7.41l-4.83-4.83C14.21 2.21 13.7 2 13.17 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8.83c0-.53-.21-1.04-.59-1.42zM13 3.5L18.5 9H13V3.5zM8 12h8v2H8v-2zm8 5H8v-2h8v2z"/>
</svg>`;

// Vektörel Çiçekli / Kıvrımlı Ayraç: şekiller index.html içindeki <symbol id="floral"> tanımında.
// Her ayet yalnızca hafif bir <use> referansı taşır (binlerce DOM düğümü tasarrufu).
const FLORAL_DIVIDER_HTML =
    '<div class="ayet-floral-divider"><svg viewBox="0 0 600 50" aria-hidden="true"><use href="#floral"></use></svg></div>';

async function init() {
    await fetchSureler();
    await yukleSure(mevcutSureNo);

    if (baslangicAyetHedefi > 1) {
        setTimeout(() => {
            vurgulaVeGit(baslangicAyetHedefi);
            baslangicAyetHedefi = 1;
        }, 300);
    }
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

/* Hızlı Sûre Arama / Modal */
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

/* 1. Geliştirme: Çoklu Meal Seçimi & LocalStorage */
function acMealSeciciModal() {
    const yazarlarMap = {};
    mevcutAyetlerVerisi.forEach(a => {
        (a.mealler || []).forEach(m => {
            if (!yazarlarMap[m.yazar_kodu]) {
                yazarlarMap[m.yazar_kodu] = m.yazar_adi;
            }
        });
    });

    const tumKodlar = Object.keys(yazarlarMap);
    if (aktifMealler.length === 0) {
        aktifMealler = [...tumKodlar];
    }

    const liste = document.getElementById('meal-secici-liste');
    liste.innerHTML = '';

    tumKodlar.forEach(kod => {
        const label = document.createElement('label');
        label.className = 'meal-secici-row';

        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.value = kod;
        chk.checked = aktifMealler.includes(kod);

        chk.onchange = () => {
            if (chk.checked) {
                if (!aktifMealler.includes(kod)) aktifMealler.push(kod);
            } else {
                aktifMealler = aktifMealler.filter(k => k !== kod);
            }
            localStorage.setItem('aktif_mealler', JSON.stringify(aktifMealler));
            guncelleHepsiniSecCheckbox(tumKodlar);
            mealKutulariniYenile();
        };

        const span = document.createElement('span');
        span.textContent = yazarlarMap[kod];

        // Onay kutusu sağda (popup'ın sağ kenarına dayalı)
        label.appendChild(span);
        label.appendChild(chk);
        liste.appendChild(label);
    });

    guncelleHepsiniSecCheckbox(tumKodlar);
    document.getElementById('meal-secici-backdrop').classList.add('acik');
}

function guncelleHepsiniSecCheckbox(tumKodlar) {
    const topChk = document.getElementById('hepsini-sec-checkbox');
    const hepsiSecili = tumKodlar.length > 0 && tumKodlar.every(k => aktifMealler.includes(k));
    topChk.checked = hepsiSecili;
}

function toggleTumMealler(seciliOlsunMu) {
    const tumCheckboxlar = document.querySelectorAll('#meal-secici-liste input[type="checkbox"]');
    if (seciliOlsunMu) {
        aktifMealler = Array.from(tumCheckboxlar).map(c => c.value);
    } else {
        aktifMealler = [];
    }
    tumCheckboxlar.forEach(c => c.checked = seciliOlsunMu);
    localStorage.setItem('aktif_mealler', JSON.stringify(aktifMealler));
    mealKutulariniYenile();
}

function kapatMealSeciciModal() {
    document.getElementById('meal-secici-backdrop').classList.remove('acik');
}

/* 3. Geliştirme: Ayete Özel Notlar */
function acNotModal(sureNo, ayetNo) {
    duzenlenenAyetKey = `${sureNo}:${ayetNo}`;
    const baslikEl = document.getElementById('not-modal-baslik');
    const inputEl = document.getElementById('not-metin-input');
    const silBtn = document.getElementById('not-sil-btn');

    const sureBilgisi = tumSureler.find(s => s.sure_no === sureNo);
    const sureAdi = sureBilgisi ? sureBilgisi.sure_adi : 'Sûre';
    baslikEl.textContent = `${sureAdi}, ${ayetNo}. Ayet Notu`;

    const mevcutNot = ayetNotlari[duzenlenenAyetKey] || '';
    inputEl.value = mevcutNot;
    silBtn.style.display = mevcutNot ? 'inline-block' : 'none';

    document.getElementById('not-modal-backdrop').classList.add('acik');
    setTimeout(() => inputEl.focus(), 50);
}

function kapatNotModal() {
    document.getElementById('not-modal-backdrop').classList.remove('acik');
    duzenlenenAyetKey = null;
}

// Not ikonunun görünümünü (dolu/boş) ayarlar
function notButonuDurumu(btn, hasNote) {
    btn.className = 'ayet-note-trigger' + (hasNote ? ' has-note' : '');
    btn.title = hasNote ? 'Notu Görüntüle / Düzenle' : 'Bu Ayete Not Ekle';
    btn.innerHTML = hasNote ? NOTE_ICON_FILLED : NOTE_ICON_EMPTY;
}

// Tüm listeyi yeniden çizmek yerine yalnızca ilgili ayetin not ikonunu günceller
function notButonunuGuncelle(key) {
    const [sureNo, ayetNo] = key.split(':').map(Number);
    if (sureNo !== mevcutSureNo) return;
    const btn = document.querySelector(`#ayet-${ayetNo} > .ayet-note-trigger`);
    if (btn) notButonuDurumu(btn, Boolean(ayetNotlari[key]));
}

function notuKaydet() {
    if (!duzenlenenAyetKey) return;
    const key = duzenlenenAyetKey;
    const metin = document.getElementById('not-metin-input').value.trim();

    if (metin) {
        ayetNotlari[key] = metin;
    } else {
        delete ayetNotlari[key];
    }
    localStorage.setItem('ayet_notlari', JSON.stringify(ayetNotlari));
    kapatNotModal();
    notButonunuGuncelle(key);
}

function notuSil() {
    if (!duzenlenenAyetKey) return;
    const key = duzenlenenAyetKey;
    delete ayetNotlari[key];
    localStorage.setItem('ayet_notlari', JSON.stringify(ayetNotlari));
    kapatNotModal();
    notButonunuGuncelle(key);
}

/* Sûre & Ayet Yükleme */
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
    localStorage.setItem('son_sure_no', sureNo);

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
        
        // İlk açılışta aktif mealler henüz yoksa tümünü seçili yap
        if (aktifMealler.length === 0 && mevcutAyetlerVerisi.length > 0) {
            const setMealler = new Set();
            mevcutAyetlerVerisi[0].mealler.forEach(m => setMealler.add(m.yazar_kodu));
            aktifMealler = Array.from(setMealler);
            localStorage.setItem('aktif_mealler', JSON.stringify(aktifMealler));
        }

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
        const notKey = `${ayet.sure_no}:${ayet.ayet_no}`;
        const hasNote = Boolean(ayetNotlari[notKey]);

        const card = document.createElement('div');
        card.className = 'ayet-card';
        card.id = `ayet-${ayet.ayet_no}`;
        card.dataset.ayetNo = ayet.ayet_no;

        // Sticky Note Butonu
        const noteBtn = document.createElement('button');
        notButonuDurumu(noteBtn, hasNote);
        noteBtn.onclick = (e) => {
            e.stopPropagation();
            acNotModal(ayet.sure_no, ayet.ayet_no);
        };
        card.appendChild(noteBtn);

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
            // Dinleyici yok: hover/click #ayetler-container üzerinde tek noktadan (delegation) yönetilir
            if (k.kok_id) span.dataset.kelimeId = k.kelime_id;
            arabicRow.appendChild(span);
        arabicRow.appendChild(document.createTextNode(' ')); // iki yana yaslama için kelime boşluğu
        });

        const numBadge = document.createElement('span');
        numBadge.className = 'ayet-num-badge';
        numBadge.textContent = ayet.ayet_no;
        arabicRow.appendChild(numBadge);

        card.appendChild(title);
        card.appendChild(arabicRow);

        // 3. Türkçe Mealler (Sadece Filtrelenen Mealler Arasında Gezinir)
        const mealKutusu = mealKutusuOlustur(ayet);
        if (mealKutusu) card.appendChild(mealKutusu);

        // 4. Çiçekli Ayraç (tek <use> referansı)
        card.insertAdjacentHTML('beforeend', FLORAL_DIVIDER_HTML);

        container.appendChild(card);
    });
}

// ---------- Meal yazı boyutu kaydırıcısı (tek, ortak popover) ----------
let mealBoyutPopover = null;
let mealBoyutDugme = null;
let mealBoyutKapatZamanlayici = null;
let mealBoyutSurukleniyor = false;

function mealOlcegiUygula(deger, kaydet) {
    mealOlcek = Math.min(MEAL_OLCEK_MAX, Math.max(MEAL_OLCEK_MIN, deger));
    document.documentElement.style.setProperty('--meal-olcek', mealOlcek);
    if (kaydet) {
        try { localStorage.setItem('meal_olcek', String(mealOlcek)); } catch (e) { /* yoksay */ }
    }
}

function mealBoyutKapatPlanla() {
    clearTimeout(mealBoyutKapatZamanlayici);
    mealBoyutKapatZamanlayici = setTimeout(() => {
        if (!mealBoyutSurukleniyor) mealBoyutPopoverKapat();
    }, 250);
}

function mealBoyutKapatIptal() {
    clearTimeout(mealBoyutKapatZamanlayici);
}

function mealBoyutPopoverOlustur() {
    const pop = document.createElement('div');
    pop.className = 'meal-boyut-popover';
    pop.innerHTML = `
        <span class="boyut-a-kucuk">A</span>
        <input type="range" min="${MEAL_OLCEK_MIN}" max="${MEAL_OLCEK_MAX}" step="0.05" aria-label="Meal yazı boyutu">
        <span class="boyut-a-buyuk">A</span>
        <span class="boyut-yuzde" title="Varsayılana döndür"></span>`;
    document.body.appendChild(pop);

    const slider = pop.querySelector('input');
    const yuzde = pop.querySelector('.boyut-yuzde');
    const guncelleYuzde = () => { yuzde.textContent = Math.round(mealOlcek * 100) + '%'; };

    slider.addEventListener('input', () => {
        mealOlcegiUygula(parseFloat(slider.value), true);
        guncelleYuzde();
    });
    yuzde.addEventListener('click', () => {
        mealOlcegiUygula(1, true);
        slider.value = 1;
        guncelleYuzde();
    });

    // Fare popover üzerindeyken açık kalır; ayrılınca kısa gecikmeyle kapanır
    pop.addEventListener('pointerenter', mealBoyutKapatIptal);
    pop.addEventListener('pointerleave', mealBoyutKapatPlanla);

    // Kaydırıcıyı sürüklerken fare popover dışına çıksa da kapanmasın
    slider.addEventListener('pointerdown', () => { mealBoyutSurukleniyor = true; });
    document.addEventListener('pointerup', () => {
        if (!mealBoyutSurukleniyor) return;
        mealBoyutSurukleniyor = false;
        if (!pop.matches(':hover')) mealBoyutKapatPlanla();
    });

    pop._guncelle = () => { slider.value = mealOlcek; guncelleYuzde(); };
    return pop;
}

// x, y verilirse (fare) popover imlecin tam altında ortalanır; verilmezse düğmenin çevresinde açılır
function mealBoyutPopoverAc(dugme, x, y) {
    if (!mealBoyutPopover) mealBoyutPopover = mealBoyutPopoverOlustur();
    mealBoyutKapatIptal();
    mealBoyutDugme = dugme;
    mealBoyutPopover._guncelle();
    mealBoyutPopover.classList.add('acik');

    const r = dugme.getBoundingClientRect();
    const cx = (x !== undefined) ? x : r.left + r.width / 2;
    const cy = (y !== undefined) ? y : r.bottom + mealBoyutPopover.offsetHeight / 2 + 8;
    const pw = mealBoyutPopover.offsetWidth;
    const ph = mealBoyutPopover.offsetHeight;
    const left = Math.min(Math.max(8, cx - pw / 2), window.innerWidth - pw - 8);
    const top = Math.min(Math.max(8, cy - ph / 2), window.innerHeight - ph - 8);
    mealBoyutPopover.style.left = left + 'px';
    mealBoyutPopover.style.top = top + 'px';
}

function mealBoyutPopoverKapat() {
    mealBoyutKapatIptal();
    if (mealBoyutPopover) mealBoyutPopover.classList.remove('acik');
    mealBoyutDugme = null;
}

function mealBoyutAcikMi() {
    return mealBoyutPopover && mealBoyutPopover.classList.contains('acik');
}

// Dışarı tıklama: kapat (büyüteç düğmesinin kendi tıklaması ayrıca işlenir)
document.addEventListener('pointerdown', (e) => {
    if (!mealBoyutAcikMi() || mealBoyutPopover.contains(e.target)) return;
    if (e.target.closest && e.target.closest('.meal-zoom-btn')) return;
    mealBoyutPopoverKapat();
});
// Sayfa kayarken popover yerinde kalmasın
const mealBoyutKaydirmaKapat = (e) => {
    if (!mealBoyutAcikMi() || mealBoyutPopover.contains(e.target)) return;
    mealBoyutPopoverKapat();
};
document.addEventListener('wheel', mealBoyutKaydirmaKapat, { passive: true, capture: true });
document.addEventListener('touchmove', mealBoyutKaydirmaKapat, { passive: true, capture: true });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') mealBoyutPopoverKapat(); });
window.addEventListener('resize', mealBoyutPopoverKapat);

// Bir ayetin meal kutusunu (aktif meallere göre) oluşturur; gösterilecek bir şey yoksa null döner
function mealKutusuOlustur(ayet) {
    const filtrelenmisMealler = (ayet.mealler || []).filter(m =>
        aktifMealler.length === 0 || aktifMealler.includes(m.yazar_kodu)
    );

    if (filtrelenmisMealler.length > 0) {
        let mealIndex = 0;
        const mealDiv = document.createElement('div');
        mealDiv.className = 'ayet-meal-box';

        const guncelleMealIcerik = () => {
            const m = filtrelenmisMealler[mealIndex];
            mealDiv.innerHTML = `
                <div class="ayet-meal-sol" title="Mealleri seçmek ve filtrelemek için tıklayın">${m.yazar_adi}</div>
                <div class="ayet-meal-orta">${m.meal_metni}</div>
                <div class="ayet-meal-sag">
                    <button class="meal-nav-btn meal-zoom-btn" title="Meal yazı boyutu" aria-label="Meal yazı boyutu">${MEAL_ZOOM_ICON}</button>
                    ${filtrelenmisMealler.length > 1 ? `
                        <button class="meal-nav-btn prev-m">‹</button>
                        <span class="meal-sayac-inline">${mealIndex + 1}/${filtrelenmisMealler.length}</span>
                        <button class="meal-nav-btn next-m">›</button>
                    ` : ''}
                </div>
            `;

            const solYazarEl = mealDiv.querySelector('.ayet-meal-sol');
            solYazarEl.addEventListener('click', (e) => {
                e.stopPropagation();
                acMealSeciciModal();
            });

            const zoomBtn = mealDiv.querySelector('.meal-zoom-btn');
            // Fare: üzerine gelince açılır (kaydırıcı imlecin altında belirir)
            zoomBtn.addEventListener('pointerenter', (e) => {
                if (e.pointerType !== 'mouse') return;
                mealBoyutKapatIptal();
                if (mealBoyutDugme !== zoomBtn) mealBoyutPopoverAc(zoomBtn, e.clientX, e.clientY);
            });
            zoomBtn.addEventListener('pointerleave', (e) => {
                if (e.pointerType === 'mouse') mealBoyutKapatPlanla();
            });
            // Dokunmatik / klavye: tıklayınca aç-kapat
            zoomBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (mealBoyutDugme === zoomBtn && mealBoyutPopover.classList.contains('acik')) {
                    mealBoyutPopoverKapat();
                } else {
                    mealBoyutPopoverAc(zoomBtn);
                }
            });

            if (filtrelenmisMealler.length > 1) {
                mealDiv.querySelector('.prev-m').onclick = (e) => {
                    e.stopPropagation();
                    mealIndex = (mealIndex - 1 + filtrelenmisMealler.length) % filtrelenmisMealler.length;
                    guncelleMealIcerik();
                };
                mealDiv.querySelector('.next-m').onclick = (e) => {
                    e.stopPropagation();
                    mealIndex = (mealIndex + 1) % filtrelenmisMealler.length;
                    guncelleMealIcerik();
                };
            }
        };

        guncelleMealIcerik();
        return mealDiv;
    }

    if (ayet.mealler && ayet.mealler.length > 0) {
        const bosUyari = document.createElement('div');
        bosUyari.className = 'ayet-meal-box';
        bosUyari.innerHTML = `<div class="ayet-meal-orta" style="color:var(--text-muted); font-size:13px; cursor:pointer;" onclick="acMealSeciciModal()">Seçili meal bulunmuyor. Mealleri seçmek için tıklayın.</div>`;
        return bosUyari;
    }

    return null;
}

// Meal seçimi değişince tüm listeyi yeniden kurmak yerine yalnızca meal kutularını değiştirir
// (kartlar, IntersectionObserver ve kaydırma konumu korunur)
function mealKutulariniYenile() {
    mevcutAyetlerVerisi.forEach(ayet => {
        const card = document.getElementById(`ayet-${ayet.ayet_no}`);
        if (!card) return;
        const eski = card.querySelector(':scope > .ayet-meal-box');
        const yeni = mealKutusuOlustur(ayet);
        if (eski && yeni) eski.replaceWith(yeni);
        else if (eski) eski.remove();
        else if (yeni) card.insertBefore(yeni, card.querySelector(':scope > .ayet-floral-divider'));
    });
    document.querySelectorAll('#kok-modal-body .kok-ayet-card').forEach(card => {
        const eski = card.querySelector(':scope > .ayet-meal-box');
        const yeni = mealKutusuOlustur(card._ayet);
        if (eski && yeni) eski.replaceWith(yeni);
        else if (eski) eski.remove();
        else if (yeni) card.insertBefore(yeni, card.querySelector(':scope > .ayet-floral-divider'));
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
                const ayetNo = topmost.target.dataset.ayetNo;
                ayetInput.value = ayetNo;
                // 2. Geliştirme: En son görülen ayeti sakla
                localStorage.setItem('son_ayet_no', ayetNo);
            }

            ayetCards.forEach(c => c.classList.remove('is-active'));
            topmost.target.classList.add('is-active');
        }
    }, {
        root: scrollContainer,
        threshold: [0.2, 0.6]
    });

    ayetCards.forEach(card => observer.observe(card));
}

const bekleyenKelimeIstekleri = {};
let sonIstenenKelimeId = null;

// Aynı kelime için aynı anda yalnızca tek istek atılır; sonuç cache'e yazılır
function kelimeGetir(kelimeId) {
    if (cache[kelimeId]) return Promise.resolve(cache[kelimeId]);
    if (!bekleyenKelimeIstekleri[kelimeId]) {
        bekleyenKelimeIstekleri[kelimeId] = fetch(`/kelime/${kelimeId}`)
            .then(res => {
                if (!res.ok) throw new Error('İstek başarısız');
                return res.json();
            })
            .then(veri => (cache[kelimeId] = veri))
            .finally(() => { delete bekleyenKelimeIstekleri[kelimeId]; });
    }
    return bekleyenKelimeIstekleri[kelimeId];
}

async function gosterMufredat(kelimeId, element) {
    sonIstenenKelimeId = kelimeId;
    document.querySelectorAll('.kelime-token.selected').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');

    const titleEl = document.getElementById('mufredat-title');
    const descEl = document.getElementById('mufredat-desc');

    let data;
    try {
        data = await kelimeGetir(kelimeId);
    } catch (err) {
        if (sonIstenenKelimeId !== kelimeId) return;
        titleEl.textContent = 'Hata';
        descEl.innerHTML = '<span style="color:red;">Kök açıklaması alınamadı.</span>';
        return;
    }

    // Yanıt beklenirken fare başka kelimeye geçtiyse eski yanıtı gösterme
    if (sonIstenenKelimeId !== kelimeId) return;
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

function renderAyetHtmlVurgulu(ayetMetni, vurguluKelimeler) {
    const tokens = ayetMetni.split(/\s+/);
    const vurguSeti = new Set(vurguluKelimeler || []);
    return tokens.map(tok => {
        if (vurguSeti.has(tok)) {
            return `<span class="kok-vurgulu">${tok}</span>`;
        }
        return tok;
    }).join(' ');
}

// Kök penceresindeki bir ayeti, ana paneldeki ayet kartıyla aynı yapıda üretir
function kokAyetKartiOlustur(item) {
    const card = document.createElement('div');
    card.className = 'ayet-card kok-ayet-card';
    card._ayet = item; // meal seçimi değişince yeniden çizmek için

    const sureAdi = item.sure_adi ? `${item.sure_no}. ${item.sure_adi}` : `${item.sure_no}. Sûre`;
    const title = document.createElement('div');
    title.className = 'ayet-title';
    title.textContent = `${sureAdi}, ${item.ayet_no}. Ayet`;
    if (item.adet > 1) {
        const adet = document.createElement('span');
        adet.className = 'adet-badge';
        adet.textContent = `${item.adet} kez`;
        title.appendChild(adet);
    }

    const arabicRow = document.createElement('div');
    arabicRow.className = 'arabic-row';
    const vurguSeti = new Set(item.vurgulu_kelimeler || []);
    item.ayet_metni.split(/\s+/).filter(Boolean).forEach(tok => {
        const span = document.createElement('span');
        span.className = 'kelime-token' + (vurguSeti.has(tok) ? ' kok-eslesen' : '');
        span.textContent = tok;
        arabicRow.appendChild(span);
        arabicRow.appendChild(document.createTextNode(' ')); // iki yana yaslama için kelime boşluğu
    });
    const numBadge = document.createElement('span');
    numBadge.className = 'ayet-num-badge';
    numBadge.textContent = item.ayet_no;
    arabicRow.appendChild(numBadge);

    card.appendChild(title);
    card.appendChild(arabicRow);

    const mealKutusu = mealKutusuOlustur(item);
    if (mealKutusu) card.appendChild(mealKutusu);
    card.insertAdjacentHTML('beforeend', FLORAL_DIVIDER_HTML);

    // Karta tıklayınca ayete git (meal kutusundaki düğmeler stopPropagation yapar)
    card.addEventListener('click', () => kokAyetineGit(item.sure_no, item.ayet_no));
    return card;
}

async function gosterKokAyetleri(kokId, offsetParam) {
    const backdrop = document.getElementById('kok-modal-backdrop');
    const body = document.getElementById('kok-modal-body');
    const baslikEl = document.getElementById('kok-modal-baslik');
    const titleEl = document.getElementById('mufredat-title');

    if (offsetParam === 0) {
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
            body.appendChild(kokAyetKartiOlustur(item));
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

// Kelime hover/click: her kelimeye ayrı dinleyici yerine kapsayıcıda tek dinleyici
const ayetlerKapsayici = document.getElementById('ayetler-container');
let kelimeHoverTimer = null;

function kokTokenBul(target) {
    return target.closest ? target.closest('.kelime-token.has-kok') : null;
}

ayetlerKapsayici.addEventListener('mouseover', (e) => {
    const el = kokTokenBul(e.target);
    if (!el) return;
    clearTimeout(kelimeHoverTimer);
    // Fare kelimelerin üzerinden hızlıca geçerken istek atma (150 ms bekle)
    kelimeHoverTimer = setTimeout(() => gosterMufredat(Number(el.dataset.kelimeId), el), 150);
});

ayetlerKapsayici.addEventListener('mouseout', (e) => {
    if (kokTokenBul(e.target)) clearTimeout(kelimeHoverTimer);
});

ayetlerKapsayici.addEventListener('click', (e) => {
    const el = kokTokenBul(e.target);
    if (!el) return;
    clearTimeout(kelimeHoverTimer);
    gosterMufredat(Number(el.dataset.kelimeId), el);
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        kapatKokModal();
        kapatSureSeciciModal();
        kapatMealSeciciModal();
        kapatNotModal();
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