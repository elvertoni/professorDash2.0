/* ──────────────────────────────────────────────────────────────────────────
   deck.js — Modo Apresentação das aulas.
   Fatia o conteúdo da aula (.prose) em slides legíveis, monta capa +
   encerramento e controla navegação por teclado/clique/controle remoto.
   Recursos de apresentador: visão geral (O), roteiro docente (N), tela
   preta (B), tela cheia (F). Vanilla JS, sem build, sem dependência além
   do lucide (ícones).
   ──────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    const body = document.body;
    const stage = document.getElementById('deck-stage');
    const source = document.getElementById('deck-source');
    if (!stage || !source) return;

    /* ── Monta os slides ──────────────────────────────────────────────────── */
    const MAX_SLIDE_WEIGHT = 7;

    function makeSlideContent() {
        const content = document.createElement('div');
        content.className = 'deck-slide-content prose';
        return content;
    }

    function isStandaloneBlock(node) {
        return node.matches && node.matches(
            'figure, table, pre, iframe, img, svg, .callout, .lesson-diagram, ' +
            '.lesson-quiz, .lesson-steps'
        );
    }

    function nodeWeight(node) {
        if (isStandaloneBlock(node)) return 4;
        if (node.tagName === 'H2') return 3;
        if (node.tagName === 'H3') return 2;
        if (node.tagName === 'UL' || node.tagName === 'OL') {
            return Math.min(5, Math.max(2, node.children.length));
        }
        return 1;
    }

    function addSectionHeading(content, heading, continuation) {
        if (!heading) return 0;
        const clone = heading.cloneNode(true);
        if (continuation) clone.classList.add('deck-repeat-heading');
        content.appendChild(clone);
        return nodeWeight(clone);
    }

    function splitSection(section) {
        const slides = [];
        let content = makeSlideContent();
        let weight = addSectionHeading(content, section.heading, false);
        let hasBody = false;

        function pushCurrent() {
            if (content.children.length) slides.push(content);
        }

        function startNext() {
            pushCurrent();
            content = makeSlideContent();
            weight = addSectionHeading(content, section.heading, true);
            hasBody = false;
        }

        section.nodes.forEach((node) => {
            const standalone = isStandaloneBlock(node);
            const startsFresh = node.tagName === 'H3' || standalone;
            const nextWeight = nodeWeight(node);

            if (
                hasBody &&
                (startsFresh || weight + nextWeight > MAX_SLIDE_WEIGHT)
            ) {
                startNext();
            }

            content.appendChild(node.cloneNode(true));
            weight += nextWeight;
            hasBody = true;
        });

        pushCurrent();
        return slides;
    }

    function buildSectionSlides() {
        const sections = [];
        let current = null;

        Array.from(source.children).forEach((node) => {
            if (node.tagName === 'H2' || current === null) {
                current = {
                    heading: node.tagName === 'H2' ? node.cloneNode(true) : null,
                    nodes: [],
                };
                sections.push(current);
                if (node.tagName === 'H2') return;
            }
            current.nodes.push(node);
        });

        const slides = [];
        sections.forEach((section) => {
            splitSection(section).forEach((slide) => slides.push(slide));
        });
        return slides;
    }

    function wrap(contentEl, title) {
        const slide = document.createElement('section');
        slide.className = 'deck-slide';
        slide.setAttribute('aria-hidden', 'true');
        slide.appendChild(contentEl);
        slide.dataset.title = title || '';
        return slide;
    }

    function fromTemplate(id) {
        const tpl = document.getElementById(id);
        if (!tpl) return null;
        return tpl.content.firstElementChild.cloneNode(true);
    }

    function titleOf(contentEl, fallback) {
        const h = contentEl.querySelector('h1, h2, h3');
        const text = h ? h.textContent.trim() : '';
        return text || fallback;
    }

    const slideEls = [];
    const capa = fromTemplate('deck-capa');
    if (capa) {
        const capaSlide = wrap(capa, titleOf(capa, 'Capa'));
        capaSlide.classList.add('deck-slide--capa');
        slideEls.push(capaSlide);
    }
    buildSectionSlides().forEach((content, i) =>
        slideEls.push(wrap(content, titleOf(content, 'Seção ' + (i + 1)))));
    const fim = fromTemplate('deck-fim');
    if (fim) slideEls.push(wrap(fim, 'Fim da aula'));

    slideEls.forEach((el) => stage.appendChild(el));
    source.remove();

    const total = slideEls.length;
    let index = 0;

    /* ── Elementos de UI ──────────────────────────────────────────────────── */
    const elCurrent = document.querySelector('[data-deck-current]');
    const elTotal = document.querySelector('[data-deck-total]');
    const elProgress = document.querySelector('[data-deck-progress]');
    const elLive = document.querySelector('[data-deck-live]');
    const prevBtn = document.querySelector('[data-deck-prev-btn]');
    const nextBtn = document.querySelector('[data-deck-next-btn]');
    const prevZone = document.querySelector('.deck-zone-prev');
    const nextZone = document.querySelector('.deck-zone-next');
    const notes = document.getElementById('deck-notes');
    const notesHasContent = notes && !notes.querySelector('.deck-notes-empty');
    const overview = document.getElementById('deck-overview');
    const overviewGrid = document.querySelector('[data-deck-overview-grid]');
    const blackEl = document.querySelector('[data-deck-black]');
    const hint = document.querySelector('[data-deck-hint]');
    const fsBtn = document.querySelector('[data-deck-fullscreen]');

    if (elTotal) elTotal.textContent = String(total);

    /* ── Auto-ajuste: correção fina; paginação evita texto pequeno na TV. ─── */
    const FIT_MIN = 0.84;

    function fitSlide(slide) {
        const content = slide.firstElementChild;
        if (!content) return;
        slide.style.removeProperty('--deck-fit');
        const cs = getComputedStyle(slide);
        const padY = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
        const avail = slide.clientHeight - padY;
        const needed = content.scrollHeight;
        if (avail <= 0 || needed <= avail) return;
        let scale = Math.max(FIT_MIN, avail / needed);
        slide.style.setProperty('--deck-fit', String(scale));
        // Imagens/min-heights não escalam linearmente → uma passada de correção.
        if (content.scrollHeight > avail && scale > FIT_MIN) {
            scale = Math.max(FIT_MIN, scale * (avail / content.scrollHeight));
            slide.style.setProperty('--deck-fit', String(scale));
        }
    }

    let refitRAF = 0;
    function refit() {
        cancelAnimationFrame(refitRAF);
        refitRAF = requestAnimationFrame(() => {
            const active = slideEls[index];
            if (active) fitSlide(active);
        });
    }
    window.addEventListener('resize', refit);
    window.addEventListener('orientationchange', refit);
    // Imagens carregam tarde (async) → re-ajusta quando a altura real chega.
    stage.querySelectorAll('img').forEach((img) => {
        if (!img.complete) img.addEventListener('load', refit, { once: true });
    });

    function render() {
        slideEls.forEach((el, i) => {
            const active = i === index;
            el.classList.toggle('is-active', active);
            el.classList.toggle('is-prev', i < index);
            el.setAttribute('aria-hidden', active ? 'false' : 'true');
            if (active) { el.scrollTop = 0; fitSlide(el); }
        });
        if (elCurrent) elCurrent.textContent = String(index + 1);
        if (elProgress) {
            const ratio = total > 1 ? index / (total - 1) : 1;
            elProgress.style.transform = 'scaleX(' + ratio + ')';
        }
        // Limites do deck: zona/botão correspondente fica inerte.
        toggleBound(prevBtn, prevZone, index === 0);
        toggleBound(nextBtn, nextZone, index === total - 1);
        announce();
        markOverviewCurrent();
    }

    function toggleBound(btn, zone, atBound) {
        if (btn) btn.setAttribute('aria-disabled', atBound ? 'true' : 'false');
        if (zone) zone.classList.toggle('is-disabled', atBound);
    }

    function announce() {
        if (!elLive) return;
        const title = slideEls[index].dataset.title;
        elLive.textContent = 'Slide ' + (index + 1) + ' de ' + total +
            (title ? ': ' + title : '');
    }

    function go(next) {
        const clamped = Math.max(0, Math.min(total - 1, next));
        if (clamped === index) {
            nudge();
            return;
        }
        index = clamped;
        render();
    }

    function nudge() {
        stage.classList.remove('is-nudge');
        // reflow para reiniciar a animação
        void stage.offsetWidth;
        stage.classList.add('is-nudge');
    }

    function next() { go(index + 1); }
    function prev() { go(index - 1); }

    document.querySelectorAll('[data-deck-next]').forEach((b) =>
        b.addEventListener('click', next));
    document.querySelectorAll('[data-deck-prev]').forEach((b) =>
        b.addEventListener('click', prev));

    /* ── Roteiro docente (painel lateral, não-modal) ──────────────────────── */
    let notesReturnFocus = null;
    const SUPPORTS_INERT = 'inert' in HTMLElement.prototype;

    function notesOpen() { return notes && notes.classList.contains('is-open'); }

    function toggleNotes(force) {
        if (!notes || !notesHasContent) return;
        const open = typeof force === 'boolean' ? force : !notesOpen();
        notes.classList.toggle('is-open', open);
        // Fallback p/ browsers de TV sem suporte a `inert`.
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
    document.querySelectorAll('[data-deck-notes]').forEach((b) =>
        b.addEventListener('click', () => toggleNotes()));
    document.querySelectorAll('[data-deck-notes-close]').forEach((b) =>
        b.addEventListener('click', () => toggleNotes(false)));

    /* ── Visão geral / pular para seção ───────────────────────────────────── */
    function buildOverview() {
        if (!overviewGrid) return;
        slideEls.forEach((el, i) => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'deck-ov-item';
            item.dataset.go = String(i);
            const num = document.createElement('span');
            num.className = 'deck-ov-num';
            num.textContent = String(i + 1).padStart(2, '0');
            const title = document.createElement('span');
            title.className = 'deck-ov-title';
            title.textContent = el.dataset.title || ('Slide ' + (i + 1));
            item.append(num, title);
            item.addEventListener('click', () => {
                go(i);
                toggleOverview(false);
            });
            overviewGrid.appendChild(item);
        });
    }

    function markOverviewCurrent() {
        if (!overviewGrid) return;
        overviewGrid.querySelectorAll('.deck-ov-item').forEach((item, i) =>
            item.classList.toggle('is-current', i === index));
    }

    function overviewOpen() { return overview && !overview.hasAttribute('hidden'); }

    let overviewReturnFocus = null;
    function toggleOverview(force) {
        if (!overview) return;
        const open = typeof force === 'boolean' ? force : !overviewOpen();
        if (open) {
            overview.removeAttribute('hidden');
            overviewReturnFocus = document.activeElement;
            const current = overviewGrid.querySelector('.deck-ov-item.is-current')
                || overviewGrid.querySelector('.deck-ov-item');
            if (current) current.focus();
        } else {
            overview.setAttribute('hidden', '');
            if (overviewReturnFocus && overviewReturnFocus.focus) overviewReturnFocus.focus();
            overviewReturnFocus = null;
        }
    }
    document.querySelectorAll('[data-deck-overview]').forEach((b) =>
        b.addEventListener('click', () => toggleOverview()));
    document.querySelectorAll('[data-deck-overview-close]').forEach((b) =>
        b.addEventListener('click', () => toggleOverview(false)));
    buildOverview();

    /* ── Tela preta ───────────────────────────────────────────────────────── */
    function blackOn() { return blackEl && blackEl.classList.contains('is-on'); }
    function toggleBlack(force) {
        if (!blackEl) return;
        const on = typeof force === 'boolean' ? force : !blackOn();
        blackEl.classList.toggle('is-on', on);
        blackEl.setAttribute('aria-hidden', on ? 'false' : 'true');
    }
    if (blackEl) blackEl.addEventListener('click', () => toggleBlack(false));

    /* ── Tela cheia (ícone sincronizado) ──────────────────────────────────── */
    function toggleFullscreen() {
        const root = document.documentElement;
        if (!document.fullscreenElement) {
            (root.requestFullscreen || root.webkitRequestFullscreen || function () {}).call(root);
        } else {
            (document.exitFullscreen || document.webkitExitFullscreen || function () {}).call(document);
        }
    }
    document.querySelectorAll('[data-deck-fullscreen]').forEach((b) =>
        b.addEventListener('click', toggleFullscreen));

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
        refit();
    });

    /* ── Teclado / controle remoto ────────────────────────────────────────── */
    document.addEventListener('keydown', (e) => {
        // Overlays modais (visão geral) capturam o essencial.
        if (overviewOpen()) {
            if (e.key === 'Escape' || e.key === 'o' || e.key === 'O') {
                e.preventDefault();
                toggleOverview(false);
            }
            return;
        }
        if (blackOn() && e.key !== 'F11') {
            e.preventDefault();
            toggleBlack(false);
            return;
        }

        switch (e.key) {
            case 'ArrowRight':
            case 'PageDown':
            case ' ':
                e.preventDefault(); next(); break;
            case 'ArrowLeft':
            case 'PageUp':
                e.preventDefault(); prev(); break;
            case 'Home':
                e.preventDefault(); go(0); break;
            case 'End':
                e.preventDefault(); go(total - 1); break;
            case 'f':
            case 'F':
                toggleFullscreen(); break;
            case 'o':
            case 'O':
                e.preventDefault(); toggleOverview(); break;
            case 'b':
            case 'B':
            case '.':
                e.preventDefault(); toggleBlack(); break;
            case 'n':
            case 'N':
                if (notesHasContent) { e.preventDefault(); toggleNotes(); }
                break;
            case 'Escape':
                if (notesOpen()) toggleNotes(false);
                else if (document.fullscreenElement) toggleFullscreen();
                else {
                    const exit = document.querySelector('.deck-controls a[href]');
                    if (exit) window.location.href = exit.href;
                }
                break;
            default:
                break;
        }
    });

    /* ── Auto-hide de controles (ocioso, com throttle) ────────────────────── */
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
    ['mousemove', 'mousedown', 'keydown', 'touchstart'].forEach((evt) =>
        document.addEventListener(evt, poke, { passive: true }));
    poke();

    /* Dica de teclado some após alguns segundos; reaparece ao sair do ocioso. */
    if (hint) setTimeout(() => hint.classList.add('is-gone'), 4500);

    /* ── Início ───────────────────────────────────────────────────────────── */
    render();
    if (window.lucide) window.lucide.createIcons();
}());
