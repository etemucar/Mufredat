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
            renderAyetler(mevcutAyetlerVerisi);
        };

        const span = document.createElement('span');
        span.textContent = yazarlarMap[kod];

        label.appendChild(chk);
        label.appendChild(span);
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
    renderAyetler(mevcutAyetlerVerisi);
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

function notuKaydet() {
    if (!duzenlenenAyetKey) return;
    const metin = document.getElementById('not-metin-input').value.trim();

    if (metin) {
        ayetNotlari[duzenlenenAyetKey] = metin;
    } else {
        delete ayetNotlari[duzenlenenAyetKey];
    }
    localStorage.setItem('ayet_notlari', JSON.stringify(ayetNotlari));
    kapatNotModal();
    renderAyetler(mevcutAyetlerVerisi);
}

function notuSil() {
    if (!duzenlenenAyetKey) return;
    delete ayetNotlari[duzenlenenAyetKey];
    localStorage.setItem('ayet_notlari', JSON.stringify(ayetNotlari));
    kapatNotModal();
    renderAyetler(mevcutAyetlerVerisi);
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
        noteBtn.className = 'ayet-note-trigger' + (hasNote ? ' has-note' : '');
        noteBtn.title = hasNote ? 'Notu Görüntüle / Düzenle' : 'Bu Ayete Not Ekle';
        noteBtn.innerHTML = hasNote ? NOTE_ICON_FILLED : NOTE_ICON_EMPTY;
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

        // 3. Türkçe Mealler (Sadece Filtrelenen Mealler Arasında Gezinir)
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
            card.appendChild(mealDiv);
        } else if (ayet.mealler && ayet.mealler.length > 0) {
            const bosUyari = document.createElement('div');
            bosUyari.className = 'ayet-meal-box';
            bosUyari.innerHTML = `<div class="ayet-meal-orta" style="color:var(--text-muted); font-size:13px; cursor:pointer;" onclick="acMealSeciciModal()">Seçili meal bulunmuyor. Mealleri seçmek için tıklayın.</div>`;
            card.appendChild(bosUyari);
        }

        // 4. Çiçekli Ayraç
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
    const tokens = ayetMetni.split(/\s+/);
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

            let modalMealIndex = 0;
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