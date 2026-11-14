// Tagging interface. Talks to the Flask server (tagger.py), or to the
// in-browser fake backend of demo.js when it is active.
const httpApi = {
    get: name => fetch('/api/' + name).then(r => r.json()),
    post: (name, body) => fetch('/api/' + name, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    }).then(async r => ({ ...(await r.json()), status: r.status })),
    imageUrl: key => '/img/' + key.split('/').map(encodeURIComponent).join('/'),
};
const api = window.TaggerDemoApi || httpApi;

const $ = id => document.getElementById(id);
const selectedTags = new Set();
let cfg = { categories: {}, categoryLabels: {}, nsfwTags: [], popularTags: [] };
let lang = 'en';

// ---------- language ----------
function t(key, ...args) {
    const value = (I18N[lang] || I18N.en)[key] ?? I18N.en[key];
    return typeof value === 'function' ? value(...args) : value;
}

function applyLanguage() {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-html]').forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
    const langs = Object.keys(I18N);
    $('langBtn').textContent = langs[(langs.indexOf(lang) + 1) % langs.length].toUpperCase();
}

function switchLanguage() {
    const langs = Object.keys(I18N);
    lang = langs[(langs.indexOf(lang) + 1) % langs.length];
    try { localStorage.setItem('tagger-lang', lang); } catch (e) { /* private mode */ }
    applyLanguage();
    loadTags();
}

// ---------- data ----------
async function updateStats() {
    const data = await api.get('stats');
    $('totalTags').textContent = data.totalTags;
    $('taggedImages').textContent = data.taggedImages;
    $('avgTags').textContent = data.avgTags;
}

function categoryLabel(name) {
    return (cfg.categoryLabels[lang] || {})[name] || name;
}

function addCategory(container, label, tags) {
    const div = document.createElement('div');
    div.className = 'category';
    div.innerHTML = `
        <div class="category-header">
            <span class="category-title"></span>
            <span class="category-count">${tags.length}</span>
        </div>
        <div class="category-tags"></div>`;
    div.querySelector('.category-title').textContent = label;
    div.querySelector('.category-header').onclick = () => div.classList.toggle('collapsed');
    const list = div.querySelector('.category-tags');
    tags.forEach(tag => list.appendChild(createTagButton(tag)));
    container.appendChild(div);
}

async function loadTags() {
    const data = await api.get('tags');
    const container = $('categoriesContainer');
    container.innerHTML = '';

    // Case insensitive lookup: "MHA" in the config matches "mha" in the metadata
    const byLower = new Map(data.tags.map(tag => [tag.toLowerCase(), tag]));
    const placed = new Set();

    Object.entries(cfg.categories).forEach(([name, list]) => {
        const tags = [...new Set(list.map(tag => byLower.get(tag.toLowerCase())).filter(Boolean))];
        if (!tags.length) return;
        tags.forEach(tag => placed.add(tag));
        addCategory(container, categoryLabel(name), tags);
    });

    const others = data.tags.filter(tag => !placed.has(tag));
    if (others.length) addCategory(container, t('other'), others);

    refreshButtons();
    filterTags();
}

function createTagButton(tag) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tag-btn';
    btn.dataset.tag = tag;
    const lower = tag.toLowerCase();
    if (cfg.popularTags.some(p => p.toLowerCase() === lower)) btn.classList.add('popular');
    else if (cfg.nsfwTags.some(n => n.toLowerCase() === lower)) btn.classList.add('nsfw');
    else if (tag[0] !== tag[0].toLowerCase()) btn.classList.add('proper-name');
    btn.textContent = tag;
    btn.onclick = () => toggleTag(tag);
    return btn;
}

function buttonsFor(tag) {
    return [...document.querySelectorAll('.tag-btn')].filter(b => b.dataset.tag === tag);
}

function refreshButtons() {
    document.querySelectorAll('.tag-btn').forEach(b => b.classList.toggle('active', selectedTags.has(b.dataset.tag)));
}

function setSelection(tags) {
    selectedTags.clear();
    tags.forEach(tag => selectedTags.add(tag));
    refreshButtons();
    $('tags').value = [...selectedTags].join(' ');
}

function toggleTag(tag) {
    if (selectedTags.has(tag)) selectedTags.delete(tag);
    else selectedTags.add(tag);
    setSelection([...selectedTags]);
}

// Typing in the field keeps the buttons in sync
function syncFromInput() {
    selectedTags.clear();
    $('tags').value.trim().split(/\s+/).filter(Boolean).forEach(tag => selectedTags.add(tag));
    refreshButtons();
}

function filterTags() {
    const search = $('searchTags').value.toLowerCase();
    document.querySelectorAll('.tag-btn').forEach(btn => {
        btn.classList.toggle('hidden', !btn.dataset.tag.toLowerCase().includes(search));
    });
    document.querySelectorAll('.category').forEach(cat => {
        const visible = cat.querySelectorAll('.tag-btn:not(.hidden)').length;
        cat.style.display = visible ? '' : 'none';
        cat.querySelector('.category-count').textContent = visible;
    });
}

async function loadCurrent() {
    const data = await api.get('current');
    document.querySelectorAll('.tag-btn.suggested').forEach(b => b.classList.remove('suggested'));
    if (data.done) {
        $('image').src = '';
        $('doneMessage').hidden = false;
        $('counter').textContent = $('counterMini').textContent = `${data.total}/${data.total}`;
        $('filename').textContent = '';
        setSelection([]);
        return;
    }
    $('doneMessage').hidden = true;
    $('image').src = api.imageUrl(data.key);
    $('image').alt = data.key;
    $('counter').textContent = $('counterMini').textContent = `${data.index + 1}/${data.total}`;
    $('filename').textContent = data.key;
    setSelection(data.tags || []);
    $('tags').focus();
}

// ---------- actions ----------
async function saveTags() {
    syncFromInput();
    const tags = [...selectedTags];
    if (!tags.length) { alert(t('needTag')); return; }
    await api.post('save', { tags });
    await Promise.all([loadTags(), updateStats()]);
    await loadCurrent();
}

async function skip() { await api.post('skip'); loadCurrent(); }
async function back() { await api.post('back'); loadCurrent(); }

async function reuseLastTags() {
    const data = await api.get('last-tags');
    if (data.tags && data.tags.length) setSelection([...new Set([...selectedTags, ...data.tags])]);
}

async function suggestTags() {
    const btn = $('suggestBtn');
    const label = btn.innerHTML;
    btn.textContent = t('analysing');
    btn.disabled = true;
    document.querySelectorAll('.tag-btn.suggested').forEach(b => b.classList.remove('suggested'));

    let message;
    try {
        const data = await api.post('suggest');
        if (data.error === 'auth') message = t('noKey');
        else if (data.error) message = t('error');
        else if (data.tags && data.tags.length) {
            setSelection([...new Set([...selectedTags, ...data.tags])]);
            data.tags.forEach(tag => buttonsFor(tag).forEach(b => {
                b.classList.add('suggested');
                b.closest('.category').classList.remove('collapsed');
            }));
            message = t('suggestions', data.tags.length);
        } else message = t('noSuggestion');
    } catch (e) {
        message = t('error');
    }
    btn.textContent = message;
    btn.disabled = false;
    setTimeout(() => { btn.innerHTML = label; applyLanguage(); }, 3000);
}

async function deleteImage() {
    if (!cfg.allowDelete || !confirm(t('confirmDelete'))) return;
    const data = await api.post('delete');
    if (!data.success) { alert(t('error')); return; }
    await updateStats();
    await loadCurrent();
}

// ---------- events ----------
$('backBtn').onclick = back;
$('skipBtn').onclick = skip;
$('saveBtn').onclick = saveTags;
$('reuseBtn').onclick = reuseLastTags;
$('suggestBtn').onclick = suggestTags;
$('deleteBtn').onclick = deleteImage;
$('langBtn').onclick = switchLanguage;
$('searchTags').oninput = filterTags;
$('tags').oninput = syncFromInput;

$('tags').addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    if (e.shiftKey) skip(); else saveTags();
});

document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    if (e.key === 'ArrowRight') { e.preventDefault(); skip(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); back(); }
    else if (e.key === 'Delete' && cfg.allowDelete) { e.preventDefault(); deleteImage(); }
});

// ---------- start ----------
(async function init() {
    cfg = { ...cfg, ...(await api.get('config')) };
    let saved = null;
    try { saved = localStorage.getItem('tagger-lang'); } catch (e) { /* private mode */ }
    const fromUrl = new URLSearchParams(location.search).get('lang');
    lang = [fromUrl, saved, cfg.language].find(l => l && I18N[l]) || 'en';

    $('demoBanner').hidden = !cfg.demo;
    $('modeBadge').hidden = !cfg.review;
    $('deleteBtn').hidden = !cfg.allowDelete;
    applyLanguage();
    await Promise.all([loadTags(), updateStats()]);
    await loadCurrent();
    // ?demo&suggest shows the AI suggestion right away (used for the README screenshot)
    if (cfg.demo && new URLSearchParams(location.search).has('suggest')) suggestTags();
})();
