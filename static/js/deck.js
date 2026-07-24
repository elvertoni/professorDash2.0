/* ──────────────────────────────────────────────────────────────────────────
   AtelierDeck v2 — Engine de Apresentação Cinematográfica
   Projeção em sala de aula (Educatron / TV / Lousa Digital).
   ──────────────────────────────────────────────────────────────────────── */

(function () {
    'use strict';

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

    class AtelierDeck {
        constructor() {
            this.body = document.body;
            this.stage = document.getElementById('deck-stage');
            this.source = document.getElementById('deck-source');
            if (!this.stage || !this.source) return;

            // Elementos DOM
            this.progressEl = document.querySelector('[data-deck-progress]');
            this.railEl = document.querySelector('[data-deck-rail]');
            this.currentTitleEl = document.querySelector('[data-deck-current-title]');
            this.currentCounterEl = document.querySelector('[data-deck-current]');
            this.totalCounterEl = document.querySelector('[data-deck-total]');
            this.prevBtns = document.querySelectorAll('[data-deck-previous]');
            this.nextBtns = document.querySelectorAll('[data-deck-next]');

            // Overlays & Ferramentas
            this.notesEl = document.getElementById('deck-notes');
            this.notesBodyEl = document.querySelector('[data-deck-notes-body]');
            this.notesBadgeEl = document.querySelector('[data-deck-notes-badge]');
            this.blackoutEl = document.getElementById('deck-blackout');
            this.overviewDialog = document.getElementById('deck-overview');
            this.overviewGrid = document.querySelector('[data-deck-overview-grid]');
            this.spotlightCanvas = document.getElementById('deck-spotlight');

            // Estado interno
            this.slides = []; // Array de { el, title, notesHTML, builds: [] }
            this.currentIndex = 0;
            this.currentBuildIndex = -1;
            this.isLaserActive = false;
            this.laserTrail = [];
            this.idleTimer = null;

            this.init();
        }

        init() {
            const fallback = document.getElementById('deck-fallback');
            if (fallback) {
                fallback.style.display = 'none';
                fallback.hidden = true;
            }
            this.body.classList.remove('is-deck-loading');

            this.buildDeckStructure();
            this.bindEvents();
            this.initSpotlightCanvas();
            this.setupIdleDetection();
            this.goToSlide(0);
        }

        /* ── FASE 1: Classificação e Fatiamento de Conteúdo ──────────────── */
        classifyBlock(node) {
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
            return PROSE;
        }

        buildDeckStructure() {
            const specs = [];
            let currentSection = '';
            let currentSub = '';
            let currentSpec = null;

            // 1. Cover Slide Spec
            const coverNode = this.fromTemplate('deck-cover');
            if (coverNode) {
                specs.push({ type: COVER, node: coverNode, title: 'Capa' });
            }

            // 2. Fatiar o HTML da aula
            const blocks = Array.from(this.source.children);

            blocks.forEach((node) => {
                const type = this.classifyBlock(node);

                if (type === 'h2') {
                    currentSection = node.textContent.trim();
                    currentSub = '';
                    currentSpec = null;
                    return;
                }
                if (type === 'h3') {
                    currentSub = node.textContent.trim();
                    currentSpec = null;
                    return;
                }

                // Blocos pesados ganham slides próprios
                if ([CALLOUT, QUIZ, TABLE, CODE, MEDIA].includes(type)) {
                    specs.push({
                        type: type,
                        section: currentSection,
                        sub: currentSub,
                        heading: '',
                        eyebrow: currentSub || currentSection || '',
                        blocks: [node.cloneNode(true)],
                        title: currentSub || currentSection || 'Destaque'
                    });
                    currentSpec = null;
                    return;
                }

                // Agrupamento de prosa e pontos
                if (!currentSpec) {
                    currentSpec = {
                        type: type === STEPS ? STEPS : (type === POINT ? POINT : PROSE),
                        section: currentSection,
                        sub: currentSub,
                        heading: currentSub || currentSection || '',
                        eyebrow: (currentSub && currentSection) ? currentSection : '',
                        blocks: [],
                        title: currentSub || currentSection || 'Conteúdo'
                    };
                    specs.push(currentSpec);
                }
                currentSpec.blocks.push(node.cloneNode(true));
            });

            // 3. End Slide Spec
            const endNode = this.fromTemplate('deck-end');
            if (endNode) {
                specs.push({ type: END, node: endNode, title: 'Encerramento' });
            }

            // 4. Renderizar Elementos DOM no Stage
            this.stage.innerHTML = '';
            this.slides = specs.map((spec, index) => this.renderSlideSpec(spec, index));
            this.totalCounterEl.textContent = String(this.slides.length);

            // Re-inicializar Lucide icons nos slides renderizados
            if (window.lucide) {
                window.lucide.createIcons();
            }
        }

        fromTemplate(id) {
            const tpl = document.getElementById(id);
            if (!tpl) return null;
            return tpl.content.firstElementChild.cloneNode(true);
        }

        renderSlideSpec(spec, index) {
            const sec = document.createElement('section');
            sec.className = `deck-slide deck-slide--${spec.type}`;
            sec.dataset.index = String(index);

            const inner = document.createElement('div');
            inner.className = 'deck-slide-inner';

            if (spec.type === COVER || spec.type === END) {
                inner.appendChild(spec.node);
                sec.appendChild(inner);
                this.stage.appendChild(sec);
                return { el: sec, title: spec.title, builds: [] };
            }

            if (spec.eyebrow) {
                const eb = document.createElement('span');
                eb.className = 'deck-eyebrow-section';
                eb.textContent = spec.eyebrow;
                inner.appendChild(eb);
            }
            if (spec.heading) {
                const h = document.createElement('h2');
                h.className = 'deck-heading';
                h.textContent = spec.heading;
                inner.appendChild(h);
            }

            const builds = [];

            if (spec.type === POINT || spec.type === STEPS) {
                const listTag = spec.type === STEPS ? 'ol' : 'ul';
                const listClass = spec.type === STEPS ? 'deck-steps' : 'deck-points';
                const list = document.createElement(listTag);
                list.className = listClass;

                spec.blocks.forEach((block) => {
                    const appendLi = (liNode) => {
                        const li = liNode.cloneNode(true);
                        li.classList.add('deck-build');
                        list.appendChild(li);
                        builds.push(li);
                    };

                    if (block.tagName === 'LI') {
                        appendLi(block);
                    } else if (block.tagName === 'UL' || block.tagName === 'OL') {
                        Array.from(block.children).forEach(li => appendLi(li));
                    } else {
                        const li = document.createElement('li');
                        li.appendChild(block.cloneNode(true));
                        li.classList.add('deck-build');
                        list.appendChild(li);
                        builds.push(li);
                    }
                });

                inner.appendChild(list);
            } else {
                const bodyWrap = document.createElement('div');
                bodyWrap.className = 'deck-prose-body';
                spec.blocks.forEach(block => bodyWrap.appendChild(block.cloneNode(true)));
                inner.appendChild(bodyWrap);
            }

            sec.appendChild(inner);
            this.stage.appendChild(sec);

            return {
                el: sec,
                title: spec.title,
                builds: builds
            };
        }

        /* ── FASE 2: Navegação & Estado de Slides ───────────────────────── */
        goToSlide(index, buildIndex = -1) {
            if (index < 0 || index >= this.slides.length) return;

            const prevSlide = this.slides[this.currentIndex];
            const nextSlide = this.slides[index];

            if (prevSlide) {
                prevSlide.el.classList.remove('is-active', 'is-prev');
                if (index > this.currentIndex) prevSlide.el.classList.add('is-prev');
            }

            this.currentIndex = index;
            nextSlide.el.classList.add('is-active');

            // Atualizar animação de builds internos
            this.currentBuildIndex = buildIndex;
            nextSlide.builds.forEach((item, idx) => {
                if (idx <= buildIndex) {
                    item.classList.add('is-revealed');
                } else {
                    item.classList.remove('is-revealed');
                }
            });

            // Atualizar HUD e Progresso
            this.updateHUD();
        }

        next() {
            const current = this.slides[this.currentIndex];
            if (current && current.builds.length > 0 && this.currentBuildIndex < current.builds.length - 1) {
                this.currentBuildIndex += 1;
                current.builds[this.currentBuildIndex].classList.add('is-revealed');
                return;
            }

            if (this.currentIndex < this.slides.length - 1) {
                this.goToSlide(this.currentIndex + 1, -1);
            }
        }

        previous() {
            const current = this.slides[this.currentIndex];
            if (current && current.builds.length > 0 && this.currentBuildIndex >= 0) {
                current.builds[this.currentBuildIndex].classList.remove('is-revealed');
                this.currentBuildIndex -= 1;
                return;
            }

            if (this.currentIndex > 0) {
                const prevSlideSpec = this.slides[this.currentIndex - 1];
                const lastBuildIndex = prevSlideSpec.builds.length > 0 ? prevSlideSpec.builds.length - 1 : -1;
                this.goToSlide(this.currentIndex - 1, lastBuildIndex);
            }
        }

        updateHUD() {
            const current = this.slides[this.currentIndex];

            // Contador e Título
            if (this.currentCounterEl) this.currentCounterEl.textContent = String(this.currentIndex + 1);
            if (this.currentTitleEl) this.currentTitleEl.textContent = current.title;

            // Barra de Progresso
            if (this.progressEl) {
                const pct = ((this.currentIndex + 1) / this.slides.length) * 100;
                this.progressEl.style.width = `${pct}%`;
            }

            // Habilitar/Desabilitar Botões
            this.prevBtns.forEach(btn => btn.disabled = (this.currentIndex === 0 && this.currentBuildIndex < 0));
            this.nextBtns.forEach(btn => btn.disabled = (this.currentIndex === this.slides.length - 1 && (current.builds.length === 0 || this.currentBuildIndex === current.builds.length - 1)));

            // Atualizar Notas do Professor se o painel estiver aberto
            if (this.notesBadgeEl) this.notesBadgeEl.textContent = `Slide ${this.currentIndex + 1}`;
        }

        /* ── FASE 3: Ponteiro Laser (Spotlight Canvas) ──────────────────── */
        initSpotlightCanvas() {
            if (!this.spotlightCanvas) return;
            const ctx = this.spotlightCanvas.getContext('2d');

            const resizeCanvas = () => {
                this.spotlightCanvas.width = window.innerWidth;
                this.spotlightCanvas.height = window.innerHeight;
            };
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);

            const renderLaser = () => {
                ctx.clearRect(0, 0, this.spotlightCanvas.width, this.spotlightCanvas.height);

                if (this.isLaserActive && this.laserTrail.length > 0) {
                    const head = this.laserTrail[this.laserTrail.length - 1];

                    // Halo brilhante verde/ciano
                    const grad = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 24);
                    grad.addColorStop(0, 'rgba(0, 242, 254, 1)');
                    grad.addColorStop(0.4, 'rgba(16, 185, 129, 0.6)');
                    grad.addColorStop(1, 'rgba(16, 185, 129, 0)');

                    ctx.fillStyle = grad;
                    ctx.beginPath();
                    ctx.arc(head.x, head.y, 24, 0, Math.PI * 2);
                    ctx.fill();

                    // Ponto focal central
                    ctx.fillStyle = '#ffffff';
                    ctx.beginPath();
                    ctx.arc(head.x, head.y, 4, 0, Math.PI * 2);
                    ctx.fill();
                }
                requestAnimationFrame(renderLaser);
            };
            requestAnimationFrame(renderLaser);

            window.addEventListener('mousemove', (e) => {
                if (this.isLaserActive) {
                    this.laserTrail = [{ x: e.clientX, y: e.clientY }];
                }
            });
        }

        toggleLaserPointer() {
            this.isLaserActive = !this.isLaserActive;
            this.body.classList.toggle('is-laser-active', this.isLaserActive);
            const btn = document.querySelector('[data-deck-laser]');
            if (btn) btn.classList.toggle('is-active', this.isLaserActive);
        }

        /* ── FASE 4: Pausa Pedagógica, Roteiro & Matriz ──────────────────── */
        toggleBlackout() {
            if (!this.blackoutEl) return;
            const hidden = this.blackoutEl.hasAttribute('hidden');
            if (hidden) {
                this.blackoutEl.removeAttribute('hidden');
            } else {
                this.blackoutEl.setAttribute('hidden', '');
            }
        }

        toggleNotes() {
            if (!this.notesEl) return;
            const isOpen = this.notesEl.classList.toggle('is-open');
            this.notesEl.removeAttribute('inert');
            if (!isOpen) this.notesEl.setAttribute('inert', '');

            const btn = document.querySelector('[data-deck-notes]');
            if (btn) btn.classList.toggle('is-active', isOpen);
        }

        openOverview() {
            if (!this.overviewDialog || !this.overviewGrid) return;
            this.overviewGrid.innerHTML = '';

            this.slides.forEach((slide, idx) => {
                const thumb = document.createElement('div');
                thumb.className = `deck-thumb${idx === this.currentIndex ? ' is-current' : ''}`;
                thumb.innerHTML = `
                    <span style="font-size:0.75rem; font-weight:700; color:var(--accent);">Slide ${idx + 1}</span>
                    <strong style="font-size:0.9rem; margin-top:4px;">${slide.title}</strong>
                `;
                thumb.addEventListener('click', () => {
                    this.goToSlide(idx);
                    this.overviewDialog.close();
                });
                this.overviewGrid.appendChild(thumb);
            });

            this.overviewDialog.showModal();
        }

        /* ── FASE 5: Detecção de Inatividade & Eventos ──────────────────── */
        setupIdleDetection() {
            const resetIdle = () => {
                this.body.classList.remove('is-idle');
                clearTimeout(this.idleTimer);
                this.idleTimer = setTimeout(() => {
                    this.body.classList.add('is-idle');
                }, 3500);
            };

            window.addEventListener('mousemove', resetIdle);
            window.addEventListener('keydown', resetIdle);
            window.addEventListener('touchstart', resetIdle);
            resetIdle();
        }

        bindEvents() {
            // Teclas de Atalho
            window.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

                switch (e.key) {
                    case 'ArrowRight':
                    case 'ArrowDown':
                    case 'PageDown':
                    case ' ':
                        e.preventDefault();
                        this.next();
                        break;
                    case 'ArrowLeft':
                    case 'ArrowUp':
                    case 'PageUp':
                        e.preventDefault();
                        this.previous();
                        break;
                    case 'Home':
                        e.preventDefault();
                        this.goToSlide(0);
                        break;
                    case 'End':
                        e.preventDefault();
                        this.goToSlide(this.slides.length - 1);
                        break;
                    case 'l':
                    case 'L':
                        this.toggleLaserPointer();
                        break;
                    case 'b':
                    case 'B':
                        this.toggleBlackout();
                        break;
                    case 'n':
                    case 'N':
                        this.toggleNotes();
                        break;
                    case 'o':
                    case 'O':
                        this.openOverview();
                        break;
                    case 'f':
                    case 'F':
                        this.toggleFullscreen();
                        break;
                    case 'Escape':
                        if (this.overviewDialog && this.overviewDialog.open) {
                            this.overviewDialog.close();
                        } else if (this.blackoutEl && !this.blackoutEl.hasAttribute('hidden')) {
                            this.toggleBlackout();
                        }
                        break;
                }
            });

            // Botões de Ação
            this.prevBtns.forEach(btn => btn.addEventListener('click', () => this.previous()));
            this.nextBtns.forEach(btn => btn.addEventListener('click', () => this.next()));

            const laserBtn = document.querySelector('[data-deck-laser]');
            if (laserBtn) laserBtn.addEventListener('click', () => this.toggleLaserPointer());

            const blackoutBtn = document.querySelector('[data-deck-blackout]');
            if (blackoutBtn) blackoutBtn.addEventListener('click', () => this.toggleBlackout());
            if (this.blackoutEl) this.blackoutEl.addEventListener('click', () => this.toggleBlackout());

            const notesBtn = document.querySelector('[data-deck-notes]');
            if (notesBtn) notesBtn.addEventListener('click', () => this.toggleNotes());

            const notesCloseBtn = document.querySelector('[data-deck-notes-close]');
            if (notesCloseBtn) notesCloseBtn.addEventListener('click', () => this.toggleNotes());

            const overviewToggleBtn = document.querySelector('[data-deck-overview-toggle]');
            if (overviewToggleBtn) overviewToggleBtn.addEventListener('click', () => this.openOverview());

            const overviewCloseBtn = document.querySelector('[data-deck-overview-close]');
            if (overviewCloseBtn) overviewCloseBtn.addEventListener('click', () => this.overviewDialog.close());

            const fsBtn = document.querySelector('[data-deck-fullscreen]');
            if (fsBtn) fsBtn.addEventListener('click', () => this.toggleFullscreen());

            // Gesture Swipe no Palco para Smartboards
            let touchStartX = 0;
            this.stage.addEventListener('touchstart', (e) => {
                touchStartX = e.touches[0].clientX;
            }, { passive: true });

            this.stage.addEventListener('touchend', (e) => {
                const diffX = e.changedTouches[0].clientX - touchStartX;
                if (Math.abs(diffX) > 50) {
                    if (diffX < 0) this.next();
                    else this.previous();
                }
            }, { passive: true });
        }

        toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(() => {});
            } else {
                document.exitFullscreen().catch(() => {});
            }
        }
    }

    // Inicializa quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new AtelierDeck());
    } else {
        new AtelierDeck();
    }
})();
