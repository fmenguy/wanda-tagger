// In-browser fake backend for the online demo (GitHub Pages).
// Active on *.github.io or with ?demo in the URL. It mirrors the Flask API
// with the placeholder images of ../demo/, keeps everything in memory, and
// returns precomputed tags instead of calling Claude.
(function () {
    const params = new URLSearchParams(location.search);
    const active = location.hostname.endsWith('github.io') || params.has('demo');
    if (!active) return;

    const BASE = '../demo/';
    const load = name => fetch(BASE + name).then(r => r.json());
    const sleep = ms => new Promise(res => setTimeout(res, ms));
    const ready = Promise.all([load('config.json'), load('metadata.json'), load('suggestions.json')])
        .then(([config, metadata, suggestions]) => {
            const queue = Object.keys(suggestions).filter(k => !(metadata[k] && metadata[k].tags && metadata[k].tags.length));
            return { config, metadata, suggestions, queue, index: 0, lastTags: [] };
        });

    function allTags(s) {
        const tags = new Set();
        Object.values(s.metadata).forEach(e => (e.tags || []).forEach(t => tags.add(t)));
        Object.values(s.config.categories || {}).forEach(list => list.forEach(t => tags.add(t)));
        return [...tags].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
    }

    function stats(s) {
        const tagged = Object.values(s.metadata).filter(e => e.tags && e.tags.length);
        const unique = new Set(tagged.flatMap(e => e.tags));
        const total = tagged.reduce((n, e) => n + e.tags.length, 0);
        return {
            totalTags: unique.size,
            taggedImages: tagged.length,
            avgTags: tagged.length ? Math.round(total / tagged.length * 10) / 10 : 0,
        };
    }

    const routes = {
        config: s => ({
            language: s.config.language || 'en',
            categories: s.config.categories || {},
            categoryLabels: s.config.category_labels || {},
            nsfwTags: s.config.nsfw_tags || [],
            popularTags: s.config.popular_tags || [],
            allowDelete: false,
            review: false,
            demo: true,
        }),
        stats,
        tags: s => ({ tags: allTags(s) }),
        current: s => {
            const key = s.queue[s.index];
            if (!key) return { done: true, total: s.queue.length };
            return { key, index: s.index, total: s.queue.length, tags: (s.metadata[key] || {}).tags || [] };
        },
        'last-tags': s => ({ tags: s.lastTags }),
        save: (s, body) => {
            const key = s.queue[s.index];
            if (!key || !body.tags.length) return { success: false };
            s.metadata[key] = { tags: body.tags };
            s.lastTags = body.tags;
            s.index++;
            return { success: true };
        },
        skip: s => { if (s.index < s.queue.length) s.index++; return { success: true }; },
        back: s => { if (s.index > 0) s.index--; return { success: true }; },
        suggest: async s => {
            await sleep(700); // feels like a real call
            return { tags: s.suggestions[s.queue[s.index]] || [] };
        },
    };

    window.TaggerDemoApi = {
        async get(name) { return routes[name](await ready); },
        async post(name, body) { return routes[name](await ready, body || {}); },
        imageUrl: key => BASE + key,
    };
})();
