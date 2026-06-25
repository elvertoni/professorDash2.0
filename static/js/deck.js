/* ──────────────────────────────────────────────────────────────────────────
   deck.js — Modo Apresentação das aulas.
   Fatia o conteúdo da aula (.prose) por <h2> em slides, monta capa +
   encerramento e controla navegação por teclado/clique/controle remoto.
   Sem dependências além do lucide (ícones). Vanilla JS, zero build.
   ──────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    const body = document.body;
    const stage = document.getElementById('deck-stage');
    const source = document.getElementById('deck-source');
    if (!stage || !source) return;

    /* ── Monta os slides ──────────────────────────────────────────────────── */
    function buildSectionSlides() {
        const slides = [];
        let current = null;

        Array.from(source.children).forEach((node) => {
            const isHeading = node.tagName === 'H2';
            if (isHeading || current === null) {
                current = document.createElement('div');
                current.className = 'deck-slide-content';
                slides.push(current);
            }
            current.appendChild(node.cloneNode(true));
        });

        return slides;
    }

    function wrap(contentEl) {
        const slide = document.createElement('section');
        slide.className = 'deck-slide';
        slide.appendChild(contentEl);
        return slide;
    }

    function fromTemplate(id) {
        const tpl = document.getElementById(id);
        if (!tpl) return null;
        return tpl.content.firstElementChild.cloneNode(true);
    }

    const slideEls = [];
    const capa = fromTemplate('deck-capa');
    if (capa) slideEls.push(wrap(capa));
    buildSectionSlides().forEach((content) => slideEls.push(wrap(content)));
    const fim = fromTemplate('deck-fim');
    if (fim) slideEls.push(wrap(fim));

    slideEls.forEach((el) => stage.appendChild(el));
    source.remove();

    const total = slideEls.length;
    let index = 0;

    /* ── Elementos de UI ──────────────────────────────────────────────────── */
    const elCurrent = document.querySelector('[data-deck-current]');
    const elTotal = document.querySelector('[data-deck-total]');
    const elProgress = document.querySelector('[data-deck-progress]');
    const notes = document.getElementById('deck-notes');
    const hint = document.querySelector('[data-deck-hint]');

    if (elTotal) elTotal.textContent = String(total);

    function render() {
        slideEls.forEach((el, i) => {
            el.classList.toggle('is-active', i === index);
            el.classList.toggle('is-prev', i < index);
            if (i === index) el.scrollTop = 0;
        });
        if (elCurrent) elCurrent.textContent = String(index + 1);
        if (elProgress) {
            const ratio = total > 1 ? index / (total - 1) : 1;
            elProgress.style.transform = 'scaleX(' + ratio + ')';
        }
    }

    function go(next) {
        const clamped = Math.max(0, Math.min(total - 1, next));
        if (clamped === index) return;
        index = clamped;
        render();
    }

    /* ── Navegação ────────────────────────────────────────────────────────── */
    function next() { go(index + 1); }
    function prev() { go(index - 1); }

    document.querySelectorAll('[data-deck-next]').forEach((b) =>
        b.addEventListener('click', next));
    document.querySelectorAll('[data-deck-prev]').forEach((b) =>
        b.addEventListener('click', prev));

    /* ── Roteiro docente (overlay) ────────────────────────────────────────── */
    function toggleNotes(force) {
        if (!notes) return;
        const open = typeof force === 'boolean' ? force : notes.hasAttribute('hidden');
        if (open) notes.removeAttribute('hidden');
        else notes.setAttribute('hidden', '');
    }
    document.querySelectorAll('[data-deck-notes]').forEach((b) =>
        b.addEventListener('click', () => toggleNotes()));
    document.querySelectorAll('[data-deck-notes-close]').forEach((b) =>
        b.addEventListener('click', () => toggleNotes(false)));

    /* ── Tela cheia ───────────────────────────────────────────────────────── */
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

    /* ── Teclado / controle remoto ────────────────────────────────────────── */
    document.addEventListener('keydown', (e) => {
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
            case 'n':
            case 'N':
                toggleNotes(); break;
            case 'Escape':
                if (notes && !notes.hasAttribute('hidden')) {
                    toggleNotes(false);
                } else if (document.fullscreenElement) {
                    toggleFullscreen();
                } else {
                    const exit = document.querySelector('.deck-controls a[href]');
                    if (exit) window.location.href = exit.href;
                }
                break;
            default:
                break;
        }
    });

    /* ── Auto-hide de controles (ocioso) ──────────────────────────────────── */
    let idleTimer = null;
    function poke() {
        body.classList.remove('is-idle');
        if (idleTimer) clearTimeout(idleTimer);
        idleTimer = setTimeout(() => body.classList.add('is-idle'), 3500);
    }
    ['mousemove', 'mousedown', 'keydown', 'touchstart'].forEach((evt) =>
        document.addEventListener(evt, poke, { passive: true }));
    poke();

    /* Dica de teclado some após alguns segundos. */
    if (hint) setTimeout(() => hint.classList.add('is-gone'), 6000);

    /* ── Início ───────────────────────────────────────────────────────────── */
    render();
    if (window.lucide) window.lucide.createIcons();
}());
