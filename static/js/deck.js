/* ──────────────────────────────────────────────────────────────────────────
   deck.js — Modo Apresentação (cinema) das aulas.
   Fatia o conteúdo da aula (.prose) em ATOS verticais (1 por <h2>), monta
   capa + encerramento e conduz a leitura por ROLAGEM: cada ato revela ao
   entrar na tela (IntersectionObserver), com barra de progresso, trilho de
   pontos para saltar, roteiro docente (N), tela cheia (F) e saída (Esc).
   Vanilla JS, sem build, só depende do lucide (ícones).
   ──────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    const body = document.body;
    const scroll = document.getElementById('deck-scroll');
    const source = document.getElementById('deck-source');
    if (!scroll || !source) return;

    /* ── Agrupa o conteúdo do .prose em seções por <h2> ───────────────────── */
    function buildSections() {
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
        // Remove seção-fantasma inicial (sem heading e sem corpo).
        return sections.filter((s) => s.heading || s.nodes.length);
    }

    function fromTemplate(id) {
        const tpl = document.getElementById(id);
        if (!tpl) return null;
        return tpl.content.firstElementChild.cloneNode(true);
    }

    function headingText(node, fallback) {
        if (!node) return fallback;
        const text = node.textContent.trim();
        return text || fallback;
    }

    /* ── Monta um ato (<section> full-bleed) ──────────────────────────────── */
    function makeAct(className, title) {
        const act = document.createElement('section');
        act.className = 'deck-act ' + className;
        act.dataset.title = title || '';
        act.setAttribute('aria-label', title || 'Seção da aula');
        return act;
    }

    const acts = [];
    // Contêineres que revelam ao rolar (.deck-reveal). 1 por ato; o stagger
    // anima os filhos DIRETOS deste contêiner (--i define o atraso no CSS).
    const revealEls = [];

    function registerReveal(act, container) {
        container.classList.add('deck-reveal');
        revealEls.push(container);
        Array.from(container.children).forEach((child, i) => {
            child.style.setProperty('--i', String(i));
        });
        acts.push(act);
    }

    // 1) Capa (hero).
    const cover = fromTemplate('deck-cover');
    if (cover) {
        const act = makeAct('deck-act--cover', 'Capa');
        act.appendChild(cover);
        registerReveal(act, cover);
    }

    // 2) Seções da aula.
    const sections = buildSections();
    let sectionNo = 0;
    sections.forEach((section) => {
        sectionNo += 1;
        const title = headingText(section.heading, 'Seção ' + sectionNo);
        const act = makeAct('deck-act--section', title);

        const inner = document.createElement('div');
        inner.className = 'deck-act-body prose';

        if (section.heading) {
            const head = document.createElement('div');
            head.className = 'deck-act-head';
            const num = document.createElement('span');
            num.className = 'deck-act-num';
            num.textContent = String(sectionNo).padStart(2, '0');
            section.heading.id = 'deck-section-' + sectionNo;
            head.append(num, section.heading); // section.heading já é clone
            inner.appendChild(head);
            act.setAttribute('aria-labelledby', section.heading.id);
            act.removeAttribute('aria-label');
        }
        section.nodes.forEach((node) => inner.appendChild(node.cloneNode(true)));

        act.appendChild(inner);
        registerReveal(act, inner);
    });

    // 3) Encerramento.
    const end = fromTemplate('deck-end');
    if (end) {
        const act = makeAct('deck-act--end', 'Fim da aula');
        act.appendChild(end);
        registerReveal(act, end);
    }

    acts.forEach((act) => scroll.appendChild(act));
    source.remove();

    const total = acts.length;
    if (!total) return; // aula vazia: nada a apresentar (capa/fim sempre criam ≥2).

    /* ── Elementos de UI ──────────────────────────────────────────────────── */
    const elCurrent = document.querySelector('[data-deck-current]');
    const elTotal = document.querySelector('[data-deck-total]');
    const elProgress = document.querySelector('[data-deck-progress]');
    const elLive = document.querySelector('[data-deck-live]');
    const rail = document.querySelector('[data-deck-rail]');
    const notes = document.getElementById('deck-notes');
    const notesHasContent = notes && !notes.querySelector('.deck-notes-empty');
    const hint = document.querySelector('[data-deck-hint]');
    const fsBtn = document.querySelector('[data-deck-fullscreen]');
    const elCurrentTitle = document.querySelector('[data-deck-current-title]');
    const previousButtons = Array.from(document.querySelectorAll('[data-deck-previous]'));
    const nextButtons = Array.from(document.querySelectorAll('[data-deck-next]'));
    const notesButtons = Array.from(document.querySelectorAll('[data-deck-notes]'));
    const lightbox = document.querySelector('[data-deck-lightbox]');

    if (elTotal) elTotal.textContent = String(total);

    /* ── Trilho de pontos (saltar para um ato) ────────────────────────────── */
    const dots = [];
    if (rail) {
        acts.forEach((act, i) => {
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'deck-rail-dot';
            dot.setAttribute('aria-label', act.dataset.title || ('Seção ' + (i + 1)));
            dot.addEventListener('click', () => scrollToAct(act));
            rail.appendChild(dot);
            dots.push(dot);
        });
    }

    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function scrollToAct(act) {
        scroll.scrollTo({
            top: act.offsetTop,
            behavior: prefersReducedMotion() ? 'auto' : 'smooth',
        });
    }

    /* ── Reveal ao entrar na tela ─────────────────────────────────────────── */
    let activeIndex = 0;

    const io = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-in');
                io.unobserve(entry.target); // revela uma vez, não re-esconde
            }
        });
    }, { root: scroll, rootMargin: '0px 0px -12% 0px', threshold: 0.15 });

    revealEls.forEach((el) => io.observe(el));

    /* ── Ato corrente (qual está mais centrado) → trilho + contador + a11y ── */
    const centerIO = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            const i = acts.indexOf(entry.target);
            if (i === -1 || i === activeIndex) return;
            setActive(i);
        });
    }, { root: scroll, rootMargin: '-45% 0px -45% 0px', threshold: 0 });

    acts.forEach((act) => centerIO.observe(act));

    function setActive(i) {
        activeIndex = i;
        if (elCurrent) elCurrent.textContent = String(i + 1);
        if (elCurrentTitle) elCurrentTitle.textContent = acts[i].dataset.title || 'Seção da aula';
        previousButtons.forEach((button) => { button.disabled = i === 0; });
        nextButtons.forEach((button) => { button.disabled = i === total - 1; });
        dots.forEach((dot, d) => {
            const current = d === i;
            dot.classList.toggle('is-current', current);
            if (current) dot.setAttribute('aria-current', 'step');
            else dot.removeAttribute('aria-current');
        });
        announce(i);
    }

    function announce(i) {
        if (!elLive) return;
        const title = acts[i].dataset.title;
        elLive.textContent = 'Seção ' + (i + 1) + ' de ' + total +
            (title ? ': ' + title : '');
    }

    /* ── Barra de progresso (proporção rolada) ────────────────────────────── */
    let progressRAF = 0;
    function updateProgress() {
        cancelAnimationFrame(progressRAF);
        progressRAF = requestAnimationFrame(() => {
            const max = scroll.scrollHeight - scroll.clientHeight;
            const ratio = max > 0 ? Math.min(1, scroll.scrollTop / max) : 1;
            if (elProgress) elProgress.style.transform = 'scaleX(' + ratio + ')';

            const marker = scroll.scrollTop + (scroll.clientHeight * 0.45);
            let visibleIndex = 0;
            acts.forEach((act, i) => {
                if (act.offsetTop <= marker) visibleIndex = i;
            });
            if (visibleIndex !== activeIndex) setActive(visibleIndex);
        });
    }
    scroll.addEventListener('scroll', updateProgress, { passive: true });

    /* ── Navegação por teclado (além do scroll nativo) ────────────────────── */
    function go(i) {
        if (!total) return;
        const clamped = Math.max(0, Math.min(total - 1, i));
        scrollToAct(acts[clamped]);
    }

    previousButtons.forEach((button) =>
        button.addEventListener('click', () => go(activeIndex - 1)));
    nextButtons.forEach((button) =>
        button.addEventListener('click', () => go(activeIndex + 1)));

    /* ── Roteiro docente (painel lateral, não-modal) ──────────────────────── */
    let notesReturnFocus = null;
    const SUPPORTS_INERT = 'inert' in HTMLElement.prototype;

    function notesOpen() { return notes && notes.classList.contains('is-open'); }

    function toggleNotes(force) {
        if (!notes || !notesHasContent) return;
        const open = typeof force === 'boolean' ? force : !notesOpen();
        notes.classList.toggle('is-open', open);
        notesButtons.forEach((button) => button.setAttribute('aria-expanded', String(open)));
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

    /* ── Capa ampliada (dialog nativo, foco e Esc do navegador) ──────────── */
    document.querySelectorAll('[data-deck-lightbox-open]').forEach((button) =>
        button.addEventListener('click', () => {
            if (lightbox && !lightbox.open) lightbox.showModal();
        }));
    document.querySelectorAll('[data-deck-lightbox-close]').forEach((button) =>
        button.addEventListener('click', () => {
            if (lightbox && lightbox.open) lightbox.close();
        }));
    if (lightbox) {
        lightbox.addEventListener('click', (event) => {
            if (event.target === lightbox) lightbox.close();
        });
    }

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
    });

    /* ── Teclado / controle remoto ────────────────────────────────────────── */
    document.addEventListener('keydown', (e) => {
        // Preserva edição e ativação nativa de controles com Espaço/Enter.
        const interactive = e.target && e.target.closest(
            'input, textarea, select, button, a, [contenteditable="true"]'
        );
        if (interactive && (e.key === ' ' || e.key === 'Enter')) return;
        if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;

        switch (e.key) {
            case 'ArrowDown':
            case 'ArrowRight':
            case 'PageDown':
            case ' ':
                e.preventDefault(); go(activeIndex + 1); break;
            case 'ArrowUp':
            case 'ArrowLeft':
            case 'PageUp':
                e.preventDefault(); go(activeIndex - 1); break;
            case 'Home':
                e.preventDefault(); go(0); break;
            case 'End':
                e.preventDefault(); go(total - 1); break;
            case 'f':
            case 'F':
                toggleFullscreen(); break;
            case 'n':
            case 'N':
                if (notesHasContent) { e.preventDefault(); toggleNotes(); }
                break;
            case 'Escape':
                if (lightbox && lightbox.open) lightbox.close();
                else if (notesOpen()) toggleNotes(false);
                else if (document.fullscreenElement) toggleFullscreen();
                else {
                    const exit = document.querySelector('[data-deck-exit]');
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
    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'wheel', 'focusin'].forEach((evt) =>
        document.addEventListener(evt, poke, { passive: true }));
    poke();

    /* Dica de teclado some após alguns segundos. */
    if (hint) setTimeout(() => hint.classList.add('is-gone'), 5000);

    /* ── Início ───────────────────────────────────────────────────────────── */
    // 1º ato visível imediatamente (sem esperar o observer disparar).
    if (revealEls[0]) {
        revealEls[0].classList.add('is-in');
        io.unobserve(revealEls[0]);
    }
    setActive(0);
    updateProgress();
    if (window.lucide) window.lucide.createIcons();
}());
