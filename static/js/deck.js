/* ──────────────────────────────────────────────────────────────────────────
   deck.js — Modo Apresentação (slides) das aulas.
   Transforma o conteúdo da aula (.prose) em SLIDES discretos e glanceáveis
   para projetar na sala/TV (42", 4-6 m). Modelo "substância paginada":
   cada seção (<h2>) vira um ou mais slides com cabeçalho da seção + conteúdo
   real (prosa curta paginada, bullets, passos, callout, mídia, quiz). A prosa
   longa é fatiada em páginas que NUNCA estouram a tela; o professor expande
   falando. O roteiro (:::roteiro) fica no painel lateral (tecla N).
   Avança por clique/seta; build-in por step. Quiz usa Alpine (no template).
   ──────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    const body = document.body;
    const stage = document.getElementById('deck-stage');
    const source = document.getElementById('deck-source');
    if (!stage || !source) return;

    const COVER = 'cover';
    const PROSE = 'prose';
    const POINT = 'point';
    const STEPS = 'steps';
    const CALLOUT = 'callout';
    const MEDIA = 'media';
    const QUIZ = 'quiz';
    const END = 'end';

    const PROSE_BUDGET = 380; // ~caracteres por página de prosa (glanceável)

    function el(tag, cls) {
        const node = document.createElement(tag);
        if (cls) node.className = cls;
        return node;
    }

    function fromTemplate(id) {
        const tpl = document.getElementById(id);
        if (!tpl) return null;
        return tpl.content.firstElementChild.cloneNode(true);
    }

    /* ── Paginação de prosa ───────────────────────────────────────────────── */
    function splitParagraph(p) {
        // Divide um parágrafo longo em pedaços (<p>) por frases, sob o budget.
        const text = p.textContent.trim();
        if (text.length <= PROSE_BUDGET) return [p];
        const sentences = text.split(/(?<=[.!?…])\s+/);
        const chunks = [];
        let buf = '';
        sentences.forEach((s) => {
            if (buf && (buf.length + s.length) > PROSE_BUDGET) {
                chunks.push(buf.trim());
                buf = '';
            }
            buf += (buf ? ' ' : '') + s;
        });
        if (buf.trim()) chunks.push(buf.trim());
        return chunks.map((c) => {
            const np = el('p');
            np.textContent = c;
            return np;
        });
    }

    function paginate(paragraphs) {
        // Recebe nós <p>; devolve páginas (cada uma = array de <p>) sob o budget.
        const flat = [];
        paragraphs.forEach((p) => splitParagraph(p).forEach((x) => flat.push(x)));
        const pages = [];
        let page = [];
        let len = 0;
        flat.forEach((p) => {
            const l = p.textContent.length;
            if (page.length && (len + l) > PROSE_BUDGET) {
                pages.push(page);
                page = [];
                len = 0;
            }
            page.push(p);
            len += l;
        });
        if (page.length) pages.push(page);
        return pages;
    }

    /* ── 1) Percorre o .prose montando especificações de slide ────────────── */
    const specs = [];
    let sectionNo = 0;
    let section = null;          // { num, title } da seção corrente (<h2>)
    let subTitle = null;         // <h3> corrente (subtítulo dentro da seção)
    let proseBuf = [];           // <p> acumulados aguardando flush
    let openPoint = null;        // slide de bullets em acumulação

    function sectionCtx() {
        return section
            ? { sectionNo: section.num, sectionTitle: section.title }
            : { sectionNo: null, sectionTitle: '' };
    }

    function flushProse() {
        if (!proseBuf.length) return;
        const pages = paginate(proseBuf);
        const ctx = sectionCtx();
        pages.forEach((pageNodes, i) => {
            specs.push(Object.assign({
                type: PROSE,
                subTitle: subTitle,
                body: pageNodes,
                page: i,
                pages: pages.length,
                notes: [],
            }, ctx));
        });
        proseBuf = [];
    }

    function pushList(type, build, sub, ctx) {
        // Fatia listas longas em páginas para nunca estourar a tela na TV.
        const MAX = type === STEPS ? 4 : 3;
        const pages = Math.max(1, Math.ceil(build.length / MAX));
        for (let p = 0; p < pages; p += 1) {
            specs.push(Object.assign({
                type: type,
                subTitle: sub,
                build: build.slice(p * MAX, (p + 1) * MAX),
                page: p,
                pages: pages,
                notes: [],
            }, ctx));
        }
    }

    function flushPoint() {
        if (openPoint && openPoint.build.length) {
            pushList(POINT, openPoint.build, openPoint.subTitle, {
                sectionNo: openPoint.sectionNo,
                sectionTitle: openPoint.sectionTitle,
            });
        }
        openPoint = null;
    }

    function flushAll() { flushProse(); flushPoint(); }

    Array.from(source.children).forEach((node) => {
        const tag = node.tagName;
        const cls = node.classList || { contains: () => false };

        if (tag === 'H2') {
            flushAll();
            sectionNo += 1;
            section = { num: sectionNo, title: node.textContent.trim() };
            subTitle = null;
            return;
        }
        if (tag === 'H3') {
            flushAll();
            subTitle = node.textContent.trim();
            return;
        }
        // Blocos especiais → slide próprio, com contexto da seção.
        if (cls.contains('callout') || cls.contains('lesson-callout')) {
            flushAll();
            const label = node.querySelector('.ct b, b, strong');
            specs.push(Object.assign({
                type: CALLOUT,
                blockTitle: (label && label.textContent.trim()) || 'Destaque',
                node: node.cloneNode(true), notes: [],
            }, sectionCtx()));
            return;
        }
        if (cls.contains('lesson-steps')) {
            flushAll();
            const items = Array.from(node.children).map((li) => li.cloneNode(true));
            pushList(STEPS, items, subTitle, sectionCtx());
            return;
        }
        if (cls.contains('lesson-diagram') || tag === 'FIGURE') {
            flushAll();
            specs.push(Object.assign({ type: MEDIA, node: node.cloneNode(true), notes: [] }, sectionCtx()));
            return;
        }
        if (cls.contains('lesson-quiz')) {
            flushAll();
            specs.push(Object.assign({ type: QUIZ, node: node.cloneNode(true), notes: [] }, sectionCtx()));
            return;
        }
        if (tag === 'UL' || tag === 'OL') {
            flushProse();
            if (!openPoint) openPoint = Object.assign({ type: POINT, subTitle: subTitle, build: [], notes: [] }, sectionCtx());
            Array.from(node.children).forEach((li) => openPoint.build.push(li.cloneNode(true)));
            return;
        }
        if (tag === 'P') {
            if (node.textContent.trim()) {
                flushPoint();
                proseBuf.push(node.cloneNode(true));
            }
            return;
        }
        if (tag === 'IMG') {
            flushAll();
            const fig = el('figure', 'lesson-diagram');
            fig.appendChild(node.cloneNode(true));
            specs.push(Object.assign({ type: MEDIA, node: fig, notes: [] }, sectionCtx()));
            return;
        }
        // Fallback (tabela, pre…) entra como item de ponto.
        flushProse();
        if (!openPoint) openPoint = Object.assign({ type: POINT, subTitle: subTitle, build: [], notes: [] }, sectionCtx());
        openPoint.build.push(node.cloneNode(true));
    });
    flushAll();

    /* ── 2) Capa + Encerramento ───────────────────────────────────────────── */
    const coverEl = fromTemplate('deck-cover');
    const endEl = fromTemplate('deck-end');
    const roteiroEl = document.getElementById('deck-roteiro');

    const slideSpecs = [];
    if (coverEl) {
        const notes = [];
        if (roteiroEl && roteiroEl.children.length) {
            Array.from(roteiroEl.children).forEach((n) => notes.push(n.cloneNode(true)));
        }
        slideSpecs.push({ type: COVER, node: coverEl, title: 'Capa', notes: notes });
    }
    specs.forEach((s) => slideSpecs.push(s));
    if (endEl) slideSpecs.push({ type: END, node: endEl, title: 'Fim da aula', notes: [] });

    if (!slideSpecs.length) return;

    /* ── 3) Renderização ──────────────────────────────────────────────────── */
    function markBuilds(items) {
        items.forEach((item, i) => {
            item.classList.add('deck-build');
            item.dataset.step = String(i);
        });
        return items.length;
    }

    function sectionHeading(text) {
        // Título da seção como cabeçalho real (sem número/eyebrow — bans do DS).
        if (!text) return null;
        const h = el('h2', 'deck-heading');
        h.textContent = text;
        return h;
    }

    const slides = []; // { el, steps, title, notesHTML, items[] }

    slideSpecs.forEach((spec, index) => {
        const sec = el('section', 'deck-slide deck-slide--' + spec.type);
        sec.dataset.index = String(index);
        const inner = el('div', 'deck-slide-inner');
        let steps = 1;
        let items = [];
        let title = spec.title || spec.sectionTitle || spec.blockTitle || 'Slide';

        if (spec.type === COVER || spec.type === END) {
            inner.classList.add('deck-slide-inner--bleed');
            inner.appendChild(spec.node);
        } else if (spec.type === PROSE) {
            const head = spec.page === 0 ? sectionHeading(spec.subTitle || spec.sectionTitle) : null;
            if (head) inner.appendChild(head);
            else if (!spec.sectionTitle && !spec.subTitle) inner.classList.add('deck-slide--lead'); // abertura
            const bodyWrap = el('div', 'deck-prose-body');
            spec.body.forEach((p) => bodyWrap.appendChild(p));
            // Prosa aparece inteira (fluxo de leitura) — sem build por parágrafo.
            // Só listas/passos constroem item a item.
            inner.appendChild(bodyWrap);
            if (spec.pages > 1) {
                const pg = el('span', 'deck-page-mark');
                pg.textContent = (spec.page + 1) + ' / ' + spec.pages;
                inner.appendChild(pg);
            }
            title = spec.sectionTitle || 'Abertura';
        } else if (spec.type === POINT || spec.type === STEPS) {
            const head = spec.page === 0 ? sectionHeading(spec.subTitle || spec.sectionTitle) : null;
            if (head) inner.appendChild(head);
            const list = el(spec.type === STEPS ? 'ol' : 'ul', spec.type === STEPS ? 'deck-steps' : 'deck-points');
            spec.build.forEach((node) => {
                if (node.tagName === 'LI') list.appendChild(node);
                else { const li = el('li'); li.appendChild(node); list.appendChild(li); }
            });
            items = Array.from(list.children);
            steps = markBuilds(items) || 1;
            inner.appendChild(list);
            if (spec.pages > 1) {
                const pg = el('span', 'deck-page-mark');
                pg.textContent = (spec.page + 1) + ' / ' + spec.pages;
                inner.appendChild(pg);
            }
            title = spec.subTitle || spec.sectionTitle || 'Tópico';
        } else if (spec.type === CALLOUT || spec.type === MEDIA || spec.type === QUIZ) {
            // Blocos têm identidade própria (Conceito/Quiz/legenda) — sem eyebrow.
            inner.classList.add('deck-slide-inner--center');
            inner.appendChild(spec.node);
            if (spec.type === QUIZ) title = 'Quiz';
            else if (spec.type === CALLOUT) title = spec.blockTitle || 'Destaque';
            else title = spec.sectionTitle || 'Imagem';
        }

        sec.appendChild(inner);

        let notesHTML = '';
        if (spec.notes && spec.notes.length) {
            const holder = el('div');
            spec.notes.forEach((n) => holder.appendChild(n));
            notesHTML = holder.innerHTML;
        }

        stage.appendChild(sec);
        slides.push({ el: sec, steps: steps, title: title, notesHTML: notesHTML, items: items });
    });

    source.remove();
    if (roteiroEl) roteiroEl.remove();

    const total = slides.length;

    /* ── 4) UI ────────────────────────────────────────────────────────────── */
    const elCurrent = document.querySelector('[data-deck-current]');
    const elTotal = document.querySelector('[data-deck-total]');
    const elProgress = document.querySelector('[data-deck-progress]');
    const elLive = document.querySelector('[data-deck-live]');
    const elCurrentTitle = document.querySelector('[data-deck-current-title]');
    const rail = document.querySelector('[data-deck-rail]');
    const notes = document.getElementById('deck-notes');
    const notesBody = document.querySelector('[data-deck-notes-body]');
    const hint = document.querySelector('[data-deck-hint]');
    const fsBtn = document.querySelector('[data-deck-fullscreen]');
    const previousButtons = Array.from(document.querySelectorAll('[data-deck-previous]'));
    const nextButtons = Array.from(document.querySelectorAll('[data-deck-next]'));
    const lightbox = document.querySelector('[data-deck-lightbox]');

    if (elTotal) elTotal.textContent = String(total);

    const dots = [];
    if (rail) {
        slides.forEach((slide, i) => {
            const dot = el('button', 'deck-rail-dot');
            dot.type = 'button';
            dot.setAttribute('aria-label', slide.title || ('Slide ' + (i + 1)));
            dot.addEventListener('click', () => goTo(i, false));
            rail.appendChild(dot);
            dots.push(dot);
        });
    }

    /* ── 5) Navegação (slide + step) ──────────────────────────────────────── */
    let index = -1;
    let step = 0;

    function showSteps(slide, upto) {
        slide.items.forEach((item) => {
            item.classList.toggle('is-shown', Number(item.dataset.step) <= upto);
        });
    }

    function goTo(i, landAtEnd) {
        const clamped = Math.max(0, Math.min(total - 1, i));
        if (clamped === index) return;
        if (index >= 0) slides[index].el.classList.remove('is-active');
        index = clamped;
        const slide = slides[index];
        slide.el.classList.add('is-active');
        step = landAtEnd ? slide.steps - 1 : 0;
        showSteps(slide, step);
        update();
    }

    function next() {
        const slide = slides[index];
        if (step < slide.steps - 1) { step += 1; showSteps(slide, step); }
        else if (index < total - 1) goTo(index + 1, false);
    }

    function previous() {
        const slide = slides[index];
        if (step > 0) { step -= 1; showSteps(slide, step); }
        else if (index > 0) goTo(index - 1, true);
    }

    function update() {
        const slide = slides[index];
        if (elCurrent) elCurrent.textContent = String(index + 1);
        if (elCurrentTitle) elCurrentTitle.textContent = slide.title || 'Slide';
        if (elProgress) elProgress.style.transform = 'scaleX(' + ((index + 1) / total) + ')';
        previousButtons.forEach((b) => { b.disabled = index === 0; });
        nextButtons.forEach((b) => { b.disabled = index === total - 1; });
        dots.forEach((dot, d) => {
            const current = d === index;
            dot.classList.toggle('is-current', current);
            if (current) dot.setAttribute('aria-current', 'step');
            else dot.removeAttribute('aria-current');
        });
        renderNotes(slide);
        announce(slide);
    }

    function announce(slide) {
        if (!elLive) return;
        elLive.textContent = 'Slide ' + (index + 1) + ' de ' + total + (slide.title ? ': ' + slide.title : '');
    }

    /* ── 6) Roteiro do professor (por slide) ──────────────────────────────── */
    function renderNotes(slide) {
        if (!notesBody) return;
        notesBody.innerHTML = slide.notesHTML ||
            '<p class="deck-notes-empty">Sem roteiro para este slide. Você conduz a fala.</p>';
    }

    let notesReturnFocus = null;
    const SUPPORTS_INERT = 'inert' in HTMLElement.prototype;
    function notesOpen() { return notes && notes.classList.contains('is-open'); }
    function toggleNotes(force) {
        if (!notes) return;
        const open = typeof force === 'boolean' ? force : !notesOpen();
        notes.classList.toggle('is-open', open);
        document.querySelectorAll('[data-deck-notes]').forEach((b) => b.setAttribute('aria-expanded', String(open)));
        if (!SUPPORTS_INERT) notes.setAttribute('aria-hidden', open ? 'false' : 'true');
        if (open) {
            notes.removeAttribute('inert');
            notesReturnFocus = document.activeElement;
            const close = notes.querySelector('[data-deck-notes-close]');
            if (close) close.focus();
        } else {
            notes.setAttribute('inert', '');
            if (notesReturnFocus && notesReturnFocus.focus) notesReturnFocus.focus();
            notesReturnFocus = null;
        }
    }
    document.querySelectorAll('[data-deck-notes]').forEach((b) => b.addEventListener('click', () => toggleNotes()));
    document.querySelectorAll('[data-deck-notes-close]').forEach((b) => b.addEventListener('click', () => toggleNotes(false)));

    /* ── 7) Capa ampliada ─────────────────────────────────────────────────── */
    document.addEventListener('click', (event) => {
        const open = event.target.closest('[data-deck-lightbox-open]');
        if (open && lightbox && !lightbox.open) lightbox.showModal();
        const close = event.target.closest('[data-deck-lightbox-close]');
        if (close && lightbox && lightbox.open) lightbox.close();
    });
    if (lightbox) {
        lightbox.addEventListener('click', (event) => { if (event.target === lightbox) lightbox.close(); });
    }

    /* ── 8) Tela cheia ────────────────────────────────────────────────────── */
    function toggleFullscreen() {
        const root = document.documentElement;
        if (!document.fullscreenElement) {
            (root.requestFullscreen || root.webkitRequestFullscreen || function () {}).call(root);
        } else {
            (document.exitFullscreen || document.webkitExitFullscreen || function () {}).call(document);
        }
    }
    document.querySelectorAll('[data-deck-fullscreen]').forEach((b) => b.addEventListener('click', toggleFullscreen));
    document.addEventListener('fullscreenchange', () => {
        if (!fsBtn) return;
        const on = !!document.fullscreenElement;
        const icon = fsBtn.querySelector('i');
        if (icon) {
            icon.setAttribute('data-lucide', on ? 'minimize' : 'maximize');
            if (window.lucide) window.lucide.createIcons();
        }
        const label = on ? 'Sair da tela cheia' : 'Entrar em tela cheia';
        fsBtn.setAttribute('aria-label', label);
        fsBtn.setAttribute('title', label + ' (F)');
    });

    /* ── 9) Botões e teclado ──────────────────────────────────────────────── */
    nextButtons.forEach((b) => b.addEventListener('click', next));
    previousButtons.forEach((b) => b.addEventListener('click', previous));

    document.addEventListener('keydown', (e) => {
        const interactive = e.target && e.target.closest('input, textarea, select, button, a, [contenteditable="true"]');
        if (interactive && (e.key === ' ' || e.key === 'Enter')) return;
        if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
        switch (e.key) {
            case 'ArrowRight': case 'ArrowDown': case 'PageDown': case ' ':
                e.preventDefault(); next(); break;
            case 'ArrowLeft': case 'ArrowUp': case 'PageUp':
                e.preventDefault(); previous(); break;
            case 'Home': e.preventDefault(); goTo(0, false); break;
            case 'End': e.preventDefault(); goTo(total - 1, false); break;
            case 'f': case 'F': toggleFullscreen(); break;
            case 'n': case 'N': e.preventDefault(); toggleNotes(); break;
            case 'Escape':
                if (lightbox && lightbox.open) lightbox.close();
                else if (notesOpen()) toggleNotes(false);
                else if (document.fullscreenElement) toggleFullscreen();
                else { const exit = document.querySelector('[data-deck-exit]'); if (exit) window.location.href = exit.href; }
                break;
            default: break;
        }
    });

    /* ── 10) Auto-hide ocioso ─────────────────────────────────────────────── */
    let idleTimer = null;
    let lastPoke = 0;
    function poke() {
        const now = Date.now();
        if (body.classList.contains('is-idle')) body.classList.remove('is-idle');
        if (now - lastPoke < 120 && idleTimer) return;
        lastPoke = now;
        if (idleTimer) clearTimeout(idleTimer);
        idleTimer = setTimeout(() => body.classList.add('is-idle'), 3500);
    }
    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'focusin'].forEach((evt) =>
        document.addEventListener(evt, poke, { passive: true }));
    poke();
    if (hint) setTimeout(() => hint.classList.add('is-gone'), 6000);

    /* ── 11) Auto-fit GLOBAL: uma escala única pro deck inteiro ────────────── */
    /* Filosofia: todos os slides no MESMO tamanho (como deck profissional).
       Em vez de encolher slide a slide (gera tamanhos diferentes na projeção),
       achamos a única escala que faz o slide MAIS cheio caber e aplicamos a
       TODOS. A paginação (PROSE_BUDGET + listas cap) já evita que algo precise
       encolher muito; o auto-fit é só a rede de segurança final (TV não rola). */
    function worstOverflow() {
        let max = 0;
        slides.forEach(({ el: s }) => {
            const o = s.scrollHeight - s.clientHeight;
            if (o > max) max = o;
        });
        return max;
    }

    function fitAll() {
        body.style.removeProperty('--deck-fs'); // volta ao clamp do CSS
        const baseFs = parseFloat(getComputedStyle(body).fontSize) || 32;
        let fs = baseFs;
        let guard = 0;
        while (worstOverflow() > 2 && guard < 14) {
            fs *= 0.95;
            if (fs < 14) break; // piso de legibilidade na sala
            body.style.setProperty('--deck-fs', fs + 'px');
            guard += 1;
        }
    }

    let fitRAF = 0;
    function scheduleFit() {
        cancelAnimationFrame(fitRAF);
        fitRAF = requestAnimationFrame(fitAll);
    }
    window.addEventListener('resize', scheduleFit, { passive: true });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitAll);

    /* ── 12) Início ───────────────────────────────────────────────────────── */
    goTo(0, false);
    if (window.lucide) window.lucide.createIcons();
    fitAll();
}());
