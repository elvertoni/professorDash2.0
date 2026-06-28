/* ──────────────────────────────────────────────────────────────────────────
   deck.js — Modo Apresentação (slides) das aulas.
   Transforma o conteúdo da aula (.prose) em SLIDES DISCRETOS e glanceáveis
   para projetar na sala/TV (42", 4-6 m). Cada slide carrega UMA ideia:
   divisor de seção, ponto (bullets que constroem no clique), destaque
   (callout), passos, mídia, quiz interativo. Texto corrido NÃO vai para a
   tela — é roteado para o roteiro do professor (tecla N), slide a slide.
   Avança por clique/seta; sem rolagem de navegação. Build-in por step.
   Vanilla JS; o quiz interativo usa Alpine (carregado no template).
   ──────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    const body = document.body;
    const stage = document.getElementById('deck-stage');
    const source = document.getElementById('deck-source');
    if (!stage || !source) return;

    /* ── Tipos de slide ───────────────────────────────────────────────────── */
    const COVER = 'cover';
    const DIVIDER = 'divider';
    const POINT = 'point';
    const STEPS = 'steps';
    const CALLOUT = 'callout';
    const MEDIA = 'media';
    const QUIZ = 'quiz';
    const END = 'end';

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

    /* ── 1) Percorre o .prose montando a lista de slides ──────────────────── */
    const specs = [];
    let sectionNo = 0;
    let lastSectionTitle = '';
    let openPoint = null; // slide de pontos em acumulação

    function flushPoint() {
        if (openPoint && openPoint.build.length) specs.push(openPoint);
        openPoint = null;
    }

    function ensurePoint() {
        if (!openPoint) openPoint = { type: POINT, title: lastSectionTitle, build: [], notes: [] };
        return openPoint;
    }

    function routeNote(node) {
        const target = openPoint || specs[specs.length - 1];
        if (!target) return;
        if (!target.notes) target.notes = [];
        target.notes.push(node.cloneNode(true));
    }

    Array.from(source.children).forEach((node) => {
        const tag = node.tagName;
        const cls = node.classList || { contains: () => false };

        if (tag === 'H2') {
            flushPoint();
            sectionNo += 1;
            lastSectionTitle = node.textContent.trim();
            specs.push({ type: DIVIDER, title: lastSectionTitle, sectionNo: sectionNo, notes: [] });
            return;
        }
        if (tag === 'H3') {
            flushPoint();
            openPoint = { type: POINT, title: node.textContent.trim(), build: [], notes: [] };
            return;
        }
        // Blocos especiais primeiro (têm classe própria e viram slide isolado).
        if (cls.contains('callout') || cls.contains('lesson-callout')) {
            flushPoint();
            const label = node.querySelector('.ct b, b, strong');
            specs.push({
                type: CALLOUT,
                title: (label && label.textContent.trim()) || 'Destaque',
                node: node.cloneNode(true),
                notes: [],
            });
            return;
        }
        if (cls.contains('lesson-steps')) {
            flushPoint();
            const items = Array.from(node.children).map((li) => li.cloneNode(true));
            specs.push({ type: STEPS, title: lastSectionTitle, build: items, notes: [] });
            return;
        }
        if (cls.contains('lesson-diagram') || tag === 'FIGURE') {
            flushPoint();
            specs.push({ type: MEDIA, title: lastSectionTitle || 'Imagem', node: node.cloneNode(true), notes: [] });
            return;
        }
        if (cls.contains('lesson-quiz')) {
            flushPoint();
            specs.push({ type: QUIZ, title: 'Quiz', node: node.cloneNode(true), notes: [] });
            return;
        }
        // Listas comuns → bullets que constroem no ponto aberto.
        if (tag === 'UL' || tag === 'OL') {
            const point = ensurePoint();
            Array.from(node.children).forEach((li) => point.build.push(li.cloneNode(true)));
            return;
        }
        if (tag === 'IMG') {
            flushPoint();
            const fig = el('figure', 'lesson-diagram');
            fig.appendChild(node.cloneNode(true));
            specs.push({ type: MEDIA, title: lastSectionTitle || 'Imagem', node: fig, notes: [] });
            return;
        }
        if (tag === 'P') {
            // Texto corrido → roteiro do professor, nunca na TV.
            if (node.textContent.trim()) routeNote(node);
            return;
        }
        // Qualquer outra coisa (tabela, pre…) entra como item visível do ponto.
        ensurePoint().build.push(node.cloneNode(true));
    });
    flushPoint();

    /* ── 2) Capa (início) e Encerramento (fim) ────────────────────────────── */
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

    /* ── 3) Renderiza cada slide para o palco ─────────────────────────────── */
    function markBuilds(items) {
        items.forEach((item, i) => {
            item.classList.add('deck-build');
            item.dataset.step = String(i);
        });
        return items.length;
    }

    function buildTitle(text, sectionNo) {
        const head = el('div', 'deck-slide-head');
        if (sectionNo) {
            const num = el('span', 'deck-sec-num');
            num.textContent = String(sectionNo).padStart(2, '0');
            head.appendChild(num);
        }
        const h = el('h2', 'deck-slide-title');
        h.textContent = text;
        head.appendChild(h);
        return head;
    }

    const slides = []; // { el, steps, title, notesHTML, items[] }

    slideSpecs.forEach((spec, index) => {
        const section = el('section', 'deck-slide deck-slide--' + spec.type);
        section.dataset.index = String(index);
        const inner = el('div', 'deck-slide-inner');
        let steps = 1;
        let items = [];
        let title = spec.title || 'Slide';

        if (spec.type === COVER || spec.type === END) {
            inner.classList.add('deck-slide-inner--bleed');
            inner.appendChild(spec.node);
        } else if (spec.type === DIVIDER) {
            const wrap = el('div', 'deck-divider-wrap');
            const num = el('span', 'deck-divider-num');
            num.textContent = String(spec.sectionNo).padStart(2, '0');
            const h = el('h2', 'deck-divider-title');
            h.textContent = spec.title;
            wrap.append(num, h);
            inner.appendChild(wrap);
            section.setAttribute('aria-label', 'Seção ' + spec.sectionNo + ': ' + spec.title);
        } else if (spec.type === POINT || spec.type === STEPS) {
            inner.appendChild(buildTitle(spec.title, spec.type === STEPS ? null : null));
            const list = el(spec.type === STEPS ? 'ol' : 'ul',
                spec.type === STEPS ? 'deck-steps' : 'deck-points');
            spec.build.forEach((node) => {
                // node já é um <li> (ou outro bloco) clonado.
                if (node.tagName === 'LI') {
                    list.appendChild(node);
                } else {
                    const li = el('li');
                    li.appendChild(node);
                    list.appendChild(li);
                }
            });
            items = Array.from(list.children);
            steps = markBuilds(items) || 1;
            inner.appendChild(list);
            section.setAttribute('aria-label', spec.title);
        } else if (spec.type === CALLOUT || spec.type === MEDIA || spec.type === QUIZ) {
            inner.classList.add('deck-slide-inner--center');
            inner.appendChild(spec.node);
        }

        section.appendChild(inner);

        // Roteiro do slide (texto corrido roteado). Guardado p/ painel de notas.
        let notesHTML = '';
        if (spec.notes && spec.notes.length) {
            const holder = el('div');
            spec.notes.forEach((n) => holder.appendChild(n));
            notesHTML = holder.innerHTML;
        }

        stage.appendChild(section);
        slides.push({ el: section, steps: steps, title: title, notesHTML: notesHTML, items: items });
    });

    source.remove();
    if (roteiroEl) roteiroEl.remove();

    const total = slides.length;

    /* ── 4) Elementos de UI ───────────────────────────────────────────────── */
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

    /* ── Trilho de pontos (saltar para um slide) ──────────────────────────── */
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

    function prefersReducedMotion() {
        return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    /* ── 5) Estado de navegação (slide + step) ────────────────────────────── */
    let index = -1;
    let step = 0;

    function showSteps(slide, upto) {
        slide.items.forEach((item) => {
            const s = Number(item.dataset.step);
            item.classList.toggle('is-shown', s <= upto);
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
        if (step < slide.steps - 1) {
            step += 1;
            showSteps(slide, step);
        } else if (index < total - 1) {
            goTo(index + 1, false);
        }
    }

    function previous() {
        const slide = slides[index];
        if (step > 0) {
            step -= 1;
            showSteps(slide, step);
        } else if (index > 0) {
            goTo(index - 1, true);
        }
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
        elLive.textContent = 'Slide ' + (index + 1) + ' de ' + total +
            (slide.title ? ': ' + slide.title : '');
    }

    /* ── 6) Roteiro do professor (painel lateral, por slide) ──────────────── */
    function hasNotes() {
        return slides.some((s) => s.notesHTML);
    }

    function renderNotes(slide) {
        if (!notesBody) return;
        if (slide.notesHTML) {
            notesBody.innerHTML = slide.notesHTML;
        } else {
            notesBody.innerHTML = '<p class="deck-notes-empty">Sem roteiro para este slide. Você conduz a fala.</p>';
        }
    }

    let notesReturnFocus = null;
    const SUPPORTS_INERT = 'inert' in HTMLElement.prototype;

    function notesOpen() { return notes && notes.classList.contains('is-open'); }

    function toggleNotes(force) {
        if (!notes) return;
        const open = typeof force === 'boolean' ? force : !notesOpen();
        notes.classList.toggle('is-open', open);
        document.querySelectorAll('[data-deck-notes]').forEach((b) =>
            b.setAttribute('aria-expanded', String(open)));
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

    /* ── 7) Capa ampliada (dialog nativo) ─────────────────────────────────── */
    document.addEventListener('click', (event) => {
        const open = event.target.closest('[data-deck-lightbox-open]');
        if (open && lightbox && !lightbox.open) lightbox.showModal();
        const close = event.target.closest('[data-deck-lightbox-close]');
        if (close && lightbox && lightbox.open) lightbox.close();
    });
    if (lightbox) {
        lightbox.addEventListener('click', (event) => {
            if (event.target === lightbox) lightbox.close();
        });
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

    /* ── 9) Cliques nas zonas laterais e botões ───────────────────────────── */
    nextButtons.forEach((b) => b.addEventListener('click', next));
    previousButtons.forEach((b) => b.addEventListener('click', previous));

    /* ── 10) Teclado / controle remoto ────────────────────────────────────── */
    document.addEventListener('keydown', (e) => {
        const interactive = e.target && e.target.closest(
            'input, textarea, select, button, a, [contenteditable="true"]'
        );
        if (interactive && (e.key === ' ' || e.key === 'Enter')) return;
        if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;

        switch (e.key) {
            case 'ArrowRight':
            case 'ArrowDown':
            case 'PageDown':
            case ' ':
                e.preventDefault(); next(); break;
            case 'ArrowLeft':
            case 'ArrowUp':
            case 'PageUp':
                e.preventDefault(); previous(); break;
            case 'Home':
                e.preventDefault(); goTo(0, false); break;
            case 'End':
                e.preventDefault(); goTo(total - 1, false); break;
            case 'f':
            case 'F':
                toggleFullscreen(); break;
            case 'n':
            case 'N':
                e.preventDefault(); toggleNotes(); break;
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

    /* ── 11) Auto-hide de controles (ocioso) ──────────────────────────────── */
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

    /* ── 12) Início ───────────────────────────────────────────────────────── */
    goTo(0, false);
    if (window.lucide) window.lucide.createIcons();
}());
