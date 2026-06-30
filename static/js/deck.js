/* ──────────────────────────────────────────────────────────────────────────
   deck.js — Modo Apresentação (slides) das aulas.
   Motor DETERMINÍSTICO: fatiamento estrutural (capa · seções · blocos
   destaque · encerramento) + ajuste fit-to-stage por slide (escala única
   medida, sem rebalanceamento iterativo, sem corte no meio de frase).
   ──────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    const body = document.body;
    const stage = document.getElementById('deck-stage');
    const source = document.getElementById('deck-source');
    if (!stage || !source) return;

    // Tipos de slide
    const COVER = 'cover';
    const PROSE = 'prose';
    const POINT = 'point';
    const STEPS = 'steps';
    const CALLOUT = 'callout';
    const MEDIA = 'media';
    const QUIZ = 'quiz';
    const TABLE = 'table';
    const CODE = 'code';
    const END = 'end';

    // Piso de legibilidade ao encolher um slide para caber no palco da TV.
    const MIN_SCALE = 0.62;

    // Palco oculto para medir a altura real de um slide antes de exibi-lo.
    let measureStage = document.getElementById('deck-stage-measure');
    if (!measureStage) {
        measureStage = document.createElement('div');
        measureStage.id = 'deck-stage-measure';
        measureStage.className = 'deck-stage-measure';
        document.body.appendChild(measureStage);
    }

    // Estado do deck
    let slides = []; // { el, steps, title, notesHTML, items[] }
    let totalSlides = 0;
    let currentIndex = 0;
    let currentStep = 0;
    let resizeObserver = null;

    /* ── Auxiliares de criação DOM ───────────────────────────────────────── */
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

    /* ── FASE 1: Classificação semântica de blocos ───────────────────────── */
    function classifyBlock(node) {
        const tag = node.tagName;
        const cls = node.classList || { contains: () => false };
        if (tag === 'H2') return 'h2';
        if (tag === 'H3') return 'h3';
        if (cls.contains('callout') || cls.contains('lesson-callout')) return CALLOUT;
        if (cls.contains('lesson-quiz')) return QUIZ;
        if (cls.contains('lesson-steps')) return STEPS;
        if (cls.contains('lesson-diagram') || tag === 'FIGURE' || tag === 'IMG') return MEDIA;
        if (tag === 'TABLE' || cls.contains('tbl-wrap') || node.querySelector('table')) return TABLE;
        if (tag === 'PRE' || node.querySelector('pre')) return CODE;
        if (tag === 'OL' || tag === 'UL') return POINT;
        if (tag === 'P') return 'p';
        return 'other';
    }

    // Blocos visualmente pesados e autocontidos: cada um ocupa o seu slide.
    const FEATURE = { [CALLOUT]: 1, [QUIZ]: 1, [TABLE]: 1, [CODE]: 1, [MEDIA]: 1 };

    /* ── FASE 2: Fatiamento determinístico em specs de slide ─────────────── */
    function buildSpecs(sourceEl) {
        const specs = [];
        let section = '';          // título h2 corrente
        let sub = '';              // subtítulo h3 corrente
        let headingShown = false;  // o cabeçalho da seção já apareceu?
        let current = null;        // spec de conteúdo em acumulação

        function startContent(want) {
            const wantsHeading = !headingShown && (section || sub);
            const spec = {
                type: want,
                section: section,
                sub: sub,
                lead: !section && !sub,
                heading: wantsHeading ? (sub || section) : '',
                eyebrow: (!wantsHeading && (section || sub)) ? (sub || section) : '',
                blocks: [],
            };
            if (wantsHeading) headingShown = true;
            specs.push(spec);
            current = spec;
            return spec;
        }

        Array.from(sourceEl.children).forEach((node) => {
            const type = classifyBlock(node);

            if (type === 'h2') {
                section = node.textContent.trim();
                sub = '';
                headingShown = false;
                current = null;
                return;
            }
            if (type === 'h3') {
                sub = node.textContent.trim();
                headingShown = false;
                current = null;
                return;
            }

            if (FEATURE[type]) {
                specs.push({
                    type: type,
                    section: section,
                    sub: sub,
                    lead: false,
                    heading: '',
                    eyebrow: sub || section || '',
                    blocks: [node.cloneNode(true)],
                });
                current = null; // prosa após destaque recomeça num slide novo
                return;
            }

            // Prosa, listas e passos acumulam no slide de conteúdo corrente.
            const want = (type === STEPS) ? STEPS : (type === POINT ? POINT : PROSE);
            if (!current) startContent(want);
            else if (current.type !== want) current.type = PROSE; // mistura → prosa
            current.blocks.push(node.cloneNode(true));
        });

        return specs;
    }

    /* ── FASE 3: Renderização de um spec em elemento de slide ────────────── */
    function renderSlide(spec, index) {
        const sec = el('section', 'deck-slide deck-slide--' + spec.type);
        sec.dataset.index = String(index);
        if (spec.lead) sec.classList.add('deck-slide--lead');
        const inner = el('div', 'deck-slide-inner');

        if (spec.type === COVER || spec.type === END) {
            inner.classList.add('deck-slide-inner--bleed');
            inner.appendChild(spec.node || el('div'));
            sec.appendChild(inner);
            return sec;
        }

        if (FEATURE[spec.type]) inner.classList.add('deck-slide-inner--center');

        if (spec.eyebrow) {
            const eb = el('span', 'deck-eyebrow-section');
            eb.textContent = spec.eyebrow;
            inner.appendChild(eb);
        }
        if (spec.heading) {
            const h = el('h2', 'deck-heading');
            h.textContent = spec.heading;
            inner.appendChild(h);
        }

        if (spec.type === POINT || spec.type === STEPS) {
            const listTag = spec.type === STEPS ? 'ol' : 'ul';
            const listClass = spec.type === STEPS ? 'deck-steps' : 'deck-points';
            const list = el(listTag, listClass);
            spec.blocks.forEach((block) => {
                if (block.tagName === 'LI') {
                    list.appendChild(block.cloneNode(true));
                } else if (block.tagName === 'UL' || block.tagName === 'OL') {
                    Array.from(block.children).forEach(li => list.appendChild(li.cloneNode(true)));
                } else {
                    const li = el('li');
                    li.appendChild(block.cloneNode(true));
                    list.appendChild(li);
                }
            });
            Array.from(list.children).forEach((li, i) => {
                li.classList.add('deck-build');
                li.dataset.step = String(i);
            });
            inner.appendChild(list);
        } else if (FEATURE[spec.type]) {
            spec.blocks.forEach(block => inner.appendChild(block.cloneNode(true)));
        } else { // PROSE
            const bodyWrap = el('div', 'deck-prose-body');
            spec.blocks.forEach(block => bodyWrap.appendChild(block.cloneNode(true)));
            inner.appendChild(bodyWrap);
        }

        sec.appendChild(inner);
        return sec;
    }

    /* ── FASE 4: Paginação por fronteira de bloco (caso raro de excesso) ──── */
    // Mede a razão conteúdo/altura útil de um spec usando o palco oculto.
    function measureRatio(spec, index) {
        const probe = renderSlide(spec, index);
        measureStage.innerHTML = '';
        measureStage.appendChild(probe);
        const inner = probe.querySelector('.deck-slide-inner');
        const style = window.getComputedStyle(probe);
        const padY = (parseFloat(style.paddingTop) || 0) + (parseFloat(style.paddingBottom) || 0);
        const slideH = probe.clientHeight || measureStage.clientHeight || 1;
        const avail = Math.max(1, slideH - padY);
        const contentH = inner ? inner.scrollHeight : probe.scrollHeight;
        measureStage.innerHTML = '';
        return contentH / avail;
    }

    function continuationOf(spec, blocks) {
        return {
            type: spec.type,
            section: spec.section,
            sub: spec.sub,
            lead: spec.lead,
            heading: '',
            eyebrow: spec.section || spec.sub || '',
            blocks: blocks,
        };
    }

    function paginateSpecs(specs) {
        const MAX = 1 / MIN_SCALE; // acima disso não cabe nem no piso de escala
        let guard = 60;
        for (let i = 0; i < specs.length && guard > 0; i++) {
            const spec = specs[i];
            if (spec.type !== PROSE && spec.type !== POINT && spec.type !== STEPS) continue;
            if (measureRatio(spec, i) <= MAX) continue;
            guard -= 1;

            if (spec.blocks.length > 1) {
                // Divide em fronteira de bloco — nunca no meio de uma frase.
                const mid = Math.ceil(spec.blocks.length / 2);
                const tail = spec.blocks.splice(mid);
                specs.splice(i + 1, 0, continuationOf(spec, tail));
                i -= 1; // remede o slide encurtado
            } else if (spec.type === POINT || spec.type === STEPS) {
                // Lista única longa: divide os itens entre dois slides.
                const listEl = spec.blocks[0];
                const items = listEl && listEl.children ? Array.from(listEl.children) : [];
                if (items.length > 1) {
                    const mid = Math.ceil(items.length / 2);
                    const firstEl = el(listEl.tagName, listEl.className);
                    const secondEl = el(listEl.tagName, listEl.className);
                    items.forEach((li, k) => (k < mid ? firstEl : secondEl).appendChild(li.cloneNode(true)));
                    spec.blocks = [firstEl];
                    specs.splice(i + 1, 0, continuationOf(spec, [secondEl]));
                    i -= 1;
                }
            }
            // Bloco único indivisível (ex.: parágrafo gigante): escala até o piso.
        }
    }

    /* ── FASE 5: Ajuste fit-to-stage por slide (escala única, sem loop) ───── */
    function fitAll() {
        slides.forEach(({ el: s }) => {
            const inner = s.querySelector('.deck-slide-inner');
            if (!inner) return;
            inner.style.removeProperty('--slide-scale');
            const style = window.getComputedStyle(s);
            const padY = (parseFloat(style.paddingTop) || 0) + (parseFloat(style.paddingBottom) || 0);
            const padX = (parseFloat(style.paddingLeft) || 0) + (parseFloat(style.paddingRight) || 0);
            const availH = Math.max(1, s.clientHeight - padY);
            const availW = Math.max(1, s.clientWidth - padX);
            const contentH = inner.scrollHeight;
            const contentW = inner.scrollWidth;
            let k = 1;
            if (contentH > availH) k = Math.min(k, availH / contentH);
            if (contentW > availW) k = Math.min(k, availW / contentW);
            if (k > 1) k = 1;
            if (k < MIN_SCALE) k = MIN_SCALE;
            inner.style.setProperty('--slide-scale', k.toFixed(4));
        });
    }

    /* ── Carregamento de Recursos Visuais ────────────────────────────────── */
    function waitForAssets(callback) {
        const images = Array.from(source.querySelectorAll('img'));
        let loadedCount = 0;
        const totalImages = images.length;

        function checkDone() {
            loadedCount += 1;
            if (loadedCount >= totalImages) {
                if (document.fonts && document.fonts.ready) {
                    document.fonts.ready.then(callback);
                } else {
                    callback();
                }
            }
        }

        if (totalImages === 0) {
            if (document.fonts && document.fonts.ready) {
                document.fonts.ready.then(callback);
            } else {
                callback();
            }
            return;
        }

        images.forEach(img => {
            if (img.complete) {
                checkDone();
            } else {
                img.addEventListener('load', checkDone);
                img.addEventListener('error', checkDone); // progride mesmo se falhar
            }
        });
    }

    /* ── COMPOSIÇÃO FINAL E INICIALIZAÇÃO DO DECK ─────────────────────────── */
    function buildDeck() {
        // 1. Fatiamento determinístico do conteúdo da aula.
        const specs = buildSpecs(source);

        // 2. Paginação só onde o conteúdo realmente não cabe (fronteira de bloco).
        paginateSpecs(specs);

        // 3. Capa e encerramento a partir dos templates.
        const coverEl = fromTemplate('deck-cover');
        const endEl = fromTemplate('deck-end');
        const roteiroEl = document.getElementById('deck-roteiro');

        const finalSpecs = [];

        if (coverEl) {
            const notes = [];
            if (roteiroEl && roteiroEl.children.length) {
                Array.from(roteiroEl.children).forEach(n => notes.push(n.cloneNode(true)));
            }
            finalSpecs.push({ type: COVER, node: coverEl, title: 'Capa', notes: notes, blocks: [] });
        }

        specs.forEach(spec => finalSpecs.push(spec));

        if (endEl) {
            finalSpecs.push({ type: END, node: endEl, title: 'Fim da aula', notes: [], blocks: [] });
        }

        // 4. Montagem no palco real.
        stage.innerHTML = '';
        slides = [];

        finalSpecs.forEach((spec, idx) => {
            const slideEl = renderSlide(spec, idx);
            stage.appendChild(slideEl);

            let slideTitle = spec.title || spec.section || spec.sub || 'Slide';
            if (spec.type === QUIZ) slideTitle = 'Quiz';
            else if (spec.type === CALLOUT) slideTitle = 'Destaque';
            else if (spec.type === TABLE) slideTitle = 'Tabela';
            else if (spec.type === CODE) slideTitle = 'Código';
            else if (spec.type === MEDIA) slideTitle = 'Imagem';

            let notesHTML = '';
            if (spec.notes && spec.notes.length) {
                const holder = el('div');
                spec.notes.forEach(n => holder.appendChild(n));
                notesHTML = holder.innerHTML;
            }

            const items = Array.from(slideEl.querySelectorAll('.deck-build'));

            slides.push({
                el: slideEl,
                steps: items.length || 1,
                title: slideTitle,
                notesHTML: notesHTML,
                items: items,
            });
        });

        // Limpeza dos containers de origem.
        source.remove();
        if (roteiroEl) roteiroEl.remove();

        totalSlides = slides.length;

        // 5. UI, ajuste de escala e posição inicial.
        initUI();
        fitAll();

        // Re-ajusta o slide quando o conteúdo muda de altura (ex.: o quiz revela
        // o feedback após a resposta) — mantém tudo dentro do palco.
        if (window.ResizeObserver) {
            if (resizeObserver) resizeObserver.disconnect();
            resizeObserver = new ResizeObserver(() => scheduleFit());
            slides.forEach(s => {
                const inner = s.el.querySelector('.deck-slide-inner');
                if (inner) resizeObserver.observe(inner);
            });
        }

        goTo(0, false);

        if (window.lucide) window.lucide.createIcons();

        // Revela o palco (some o splash de carregamento).
        body.classList.remove('is-deck-loading');

        // Suite de teste visual sob demanda: ?test=true
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('test') === 'true') {
            runIntegratedTests();
        }
    }

    /* ── INTERFACE GRÁFICA E NAVEGAÇÃO ───────────────────────────────────── */
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

    const dots = [];

    function initUI() {
        if (elTotal) elTotal.textContent = String(totalSlides);

        if (rail) {
            rail.innerHTML = '';
            dots.length = 0;
            slides.forEach((slide, i) => {
                const dot = el('button', 'deck-rail-dot');
                dot.type = 'button';
                dot.setAttribute('aria-label', slide.title || ('Slide ' + (i + 1)));
                dot.addEventListener('click', () => goTo(i, false));
                rail.appendChild(dot);
                dots.push(dot);
            });
        }
    }

    function showSteps(slide, upto) {
        slide.items.forEach((item) => {
            item.classList.toggle('is-shown', Number(item.dataset.step) <= upto);
        });
    }

    function goTo(i, landAtEnd) {
        const clamped = Math.max(0, Math.min(totalSlides - 1, i));
        if (clamped === currentIndex && currentIndex >= 0) return;

        if (currentIndex >= 0 && slides[currentIndex]) {
            slides[currentIndex].el.classList.remove('is-active');
        }

        currentIndex = clamped;
        const slide = slides[currentIndex];
        if (slide) {
            slide.el.classList.add('is-active');
            currentStep = landAtEnd ? slide.steps - 1 : 0;
            showSteps(slide, currentStep);
            updateUI();
        }
    }

    function next() {
        const slide = slides[currentIndex];
        if (!slide) return;

        if (currentStep < slide.steps - 1) {
            currentStep += 1;
            showSteps(slide, currentStep);
        } else if (currentIndex < totalSlides - 1) {
            goTo(currentIndex + 1, false);
        }
    }

    function previous() {
        const slide = slides[currentIndex];
        if (!slide) return;

        if (currentStep > 0) {
            currentStep -= 1;
            showSteps(slide, currentStep);
        } else if (currentIndex > 0) {
            goTo(currentIndex - 1, true);
        }
    }

    function updateUI() {
        const slide = slides[currentIndex];
        if (!slide) return;

        if (elCurrent) elCurrent.textContent = String(currentIndex + 1);
        if (elCurrentTitle) elCurrentTitle.textContent = slide.title || 'Slide';
        if (elProgress) elProgress.style.transform = 'scaleX(' + ((currentIndex + 1) / totalSlides) + ')';

        previousButtons.forEach(b => { b.disabled = currentIndex === 0; });
        nextButtons.forEach(b => { b.disabled = currentIndex === totalSlides - 1; });

        dots.forEach((dot, d) => {
            const current = d === currentIndex;
            dot.classList.toggle('is-current', current);
            if (current) dot.setAttribute('aria-current', 'step');
            else dot.removeAttribute('aria-current');
        });

        // Roteiro do professor
        if (notesBody) {
            notesBody.innerHTML = slide.notesHTML ||
                '<p class="deck-notes-empty">Sem roteiro para este slide. Você conduz a fala.</p>';
        }

        // Acessibilidade
        if (elLive) {
            elLive.textContent = 'Slide ' + (currentIndex + 1) + ' de ' + totalSlides + (slide.title ? ': ' + slide.title : '');
        }
    }

    /* ── Painel de Roteiro Docente (Acessibilidade e Teclado) ─────────────── */
    let notesReturnFocus = null;
    const SUPPORTS_INERT = 'inert' in HTMLElement.prototype;

    function notesOpen() {
        return notes && notes.classList.contains('is-open');
    }

    function toggleNotes(force) {
        if (!notes) return;
        const open = typeof force === 'boolean' ? force : !notesOpen();
        notes.classList.toggle('is-open', open);
        document.querySelectorAll('[data-deck-notes]').forEach(b => b.setAttribute('aria-expanded', String(open)));

        if (!SUPPORTS_INERT) notes.setAttribute('aria-hidden', open ? 'false' : 'true');

        if (open) {
            notes.removeAttribute('inert');
            notesReturnFocus = document.activeElement;
            const closeBtn = notes.querySelector('[data-deck-notes-close]');
            if (closeBtn) closeBtn.focus();
        } else {
            notes.setAttribute('inert', '');
            if (notesReturnFocus && notesReturnFocus.focus) notesReturnFocus.focus();
            notesReturnFocus = null;
        }
    }

    document.querySelectorAll('[data-deck-notes]').forEach(b => b.addEventListener('click', () => toggleNotes()));
    document.querySelectorAll('[data-deck-notes-close]').forEach(b => b.addEventListener('click', () => toggleNotes(false)));

    /* ── Capa Ampliada (Dialog) ──────────────────────────────────────────── */
    document.addEventListener('click', (event) => {
        const openBtn = event.target.closest('[data-deck-lightbox-open]');
        if (openBtn && lightbox && !lightbox.open) lightbox.showModal();

        const closeBtn = event.target.closest('[data-deck-lightbox-close]');
        if (closeBtn && lightbox && lightbox.open) lightbox.close();
    });
    if (lightbox) {
        lightbox.addEventListener('click', (event) => {
            if (event.target === lightbox) lightbox.close();
        });
    }

    /* ── Tela Cheia ──────────────────────────────────────────────────────── */
    function toggleFullscreen() {
        const root = document.documentElement;
        if (!document.fullscreenElement) {
            (root.requestFullscreen || root.webkitRequestFullscreen || function () {}).call(root);
        } else {
            (document.exitFullscreen || document.webkitExitFullscreen || function () {}).call(document);
        }
    }

    document.querySelectorAll('[data-deck-fullscreen]').forEach(b => b.addEventListener('click', toggleFullscreen));

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

    /* ── Eventos de Teclado e Navegação ──────────────────────────────────── */
    nextButtons.forEach(b => b.addEventListener('click', next));
    previousButtons.forEach(b => b.addEventListener('click', previous));

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
            case 'End': e.preventDefault(); goTo(totalSlides - 1, false); break;
            case 'f': case 'F': toggleFullscreen(); break;
            case 'n': case 'N': e.preventDefault(); toggleNotes(); break;
            case 'Escape':
                if (lightbox && lightbox.open) lightbox.close();
                else if (notesOpen()) toggleNotes(false);
                else if (document.fullscreenElement) toggleFullscreen();
                else {
                    const exit = document.querySelector('[data-deck-exit]');
                    if (exit) window.location.href = exit.href;
                }
                break;
            default: break;
        }
    });

    /* ── Auto-hide ocioso dos controles ───────────────────────────────────── */
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
    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'focusin'].forEach(evt =>
        document.addEventListener(evt, poke, { passive: true }));
    poke();
    if (hint) setTimeout(() => hint.classList.add('is-gone'), 6000);

    /* ── Escuta de redimensionamento de Viewport ─────────────────────────── */
    let fitRAF = 0;
    function scheduleFit() {
        cancelAnimationFrame(fitRAF);
        fitRAF = requestAnimationFrame(fitAll);
    }
    window.addEventListener('resize', scheduleFit, { passive: true });

    /* ── SUITE DE TESTE VISUAL INTEGRADO (NAVEGADOR): ?test=true ──────────── */
    function runIntegratedTests() {
        console.log('%c[TEST SUITE] Iniciando testes de validação visual do deck...', 'color: #2DD4BF; font-weight: bold;');

        const testContainer = el('div');
        testContainer.style.position = 'fixed';
        testContainer.style.top = '12px';
        testContainer.style.left = '50%';
        testContainer.style.transform = 'translateX(-50%)';
        testContainer.style.zIndex = '99999';
        testContainer.style.background = '#0F172A';
        testContainer.style.border = '2px solid #2DD4BF';
        testContainer.style.borderRadius = '8px';
        testContainer.style.padding = '12px 20px';
        testContainer.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
        testContainer.style.fontFamily = 'monospace';
        testContainer.style.fontSize = '13px';
        testContainer.style.color = '#F8FAFC';
        testContainer.style.maxWidth = '90vw';
        testContainer.style.maxHeight = '240px';
        testContainer.style.overflowY = 'auto';

        const testHeader = el('div');
        testHeader.style.fontWeight = 'bold';
        testHeader.style.borderBottom = '1px solid #334155';
        testHeader.style.paddingBottom = '6px';
        testHeader.style.marginBottom = '8px';
        testHeader.style.display = 'flex';
        testHeader.style.justifyContent = 'space-between';
        testHeader.textContent = 'Suite de Teste Visual do Deck';

        const closeBtn = el('button');
        closeBtn.textContent = '[X]';
        closeBtn.style.background = 'none';
        closeBtn.style.border = 'none';
        closeBtn.style.color = '#EF4444';
        closeBtn.style.cursor = 'pointer';
        closeBtn.addEventListener('click', () => testContainer.remove());
        testHeader.appendChild(closeBtn);
        testContainer.appendChild(testHeader);

        const testBody = el('div');
        testContainer.appendChild(testBody);
        document.body.appendChild(testContainer);

        let errors = 0;
        let originalIndex = currentIndex;

        let jsConsoleErrors = [];
        const originalOnError = window.onerror;
        window.onerror = function (message, source, lineno, colno, error) {
            jsConsoleErrors.push({ message, line: lineno });
            if (originalOnError) originalOnError.apply(this, arguments);
            return false;
        };

        let sIdx = 0;
        function testNextSlide() {
            if (sIdx < totalSlides) {
                goTo(sIdx, false);
                setTimeout(() => {
                    const slide = slides[sIdx];
                    const innerEl = slide.el.querySelector('.deck-slide-inner');
                    const style = window.getComputedStyle(slide.el);
                    const paddingTop = parseFloat(style.paddingTop) || 0;
                    const paddingBottom = parseFloat(style.paddingBottom) || 0;
                    const paddingY = paddingTop + paddingBottom;

                    const clientH = slide.el.clientHeight || 1;
                    const availableH = Math.max(1, clientH - paddingY);
                    // Altura visual real (já considerando a escala fit-to-stage).
                    const rect = innerEl ? innerEl.getBoundingClientRect() : null;
                    const contentH = rect ? rect.height : (slide.el.scrollHeight - paddingY);

                    const isOverflow = contentH > availableH + 2;
                    const isTooEmpty = (contentH / availableH) < 0.30 &&
                        !slide.el.className.includes('deck-slide--cover') &&
                        !slide.el.className.includes('deck-slide--end') &&
                        !slide.el.className.includes('deck-slide--media') &&
                        !slide.el.className.includes('deck-slide--quiz') &&
                        !slide.el.className.includes('deck-slide--lead');

                    let status = 'OK';
                    let color = '#10B981';

                    if (isOverflow) {
                        status = 'FALHA (Overflow detectado!)';
                        color = '#EF4444';
                        errors += 1;
                    } else if (isTooEmpty) {
                        status = 'AVISO (Muito vazio)';
                        color = '#F59E0B';
                    }

                    const itemLine = el('div');
                    itemLine.style.marginBottom = '4px';
                    itemLine.innerHTML = `Slide ${sIdx + 1} (${slide.title}): <span style="color: ${color}; font-weight: bold;">${status}</span> (Ocupação: ${Math.round(contentH * 100 / availableH)}%)`;
                    testBody.appendChild(itemLine);
                    testContainer.scrollTop = testContainer.scrollHeight;

                    sIdx += 1;
                    testNextSlide();
                }, 150);
            } else {
                let jsStatus = 'Zero Erros no Console JS';
                let jsColor = '#10B981';
                if (jsConsoleErrors.length > 0) {
                    jsStatus = `${jsConsoleErrors.length} Erro(s) de JS detectado(s)!`;
                    jsColor = '#EF4444';
                    errors += jsConsoleErrors.length;
                }

                const jsLine = el('div');
                jsLine.style.marginTop = '8px';
                jsLine.style.borderTop = '1px dashed #334155';
                jsLine.style.paddingTop = '6px';
                jsLine.innerHTML = `Console JS: <span style="color: ${jsColor}; font-weight: bold;">${jsStatus}</span>`;
                testBody.appendChild(jsLine);

                const summaryLine = el('div');
                summaryLine.style.marginTop = '10px';
                summaryLine.style.fontWeight = 'bold';
                summaryLine.style.fontSize = '14px';

                if (errors === 0) {
                    summaryLine.innerHTML = `<span style="color: #10B981;">STATUS: PASSED (Tudo verde!)</span>`;
                    console.log('%c[TEST SUITE] PASSED. Todos os slides válidos.', 'color: #10B981; font-weight: bold;');
                } else {
                    summaryLine.innerHTML = `<span style="color: #EF4444;">STATUS: FAILED (${errors} erros detectados)</span>`;
                    console.error(`[TEST SUITE] FAILED. ${errors} problemas detectados.`);
                }
                testBody.appendChild(summaryLine);
                testContainer.scrollTop = testContainer.scrollHeight;

                window.onerror = originalOnError;
                goTo(originalIndex, false);
            }
        }

        setTimeout(testNextSlide, 600);
    }

    /* ── INÍCIO ───────────────────────────────────────────────────────────── */
    // Aguarda fontes e imagens carregarem, depois constrói o deck.
    waitForAssets(() => {
        buildDeck();
    });
}());
