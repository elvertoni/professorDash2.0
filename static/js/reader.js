/* ──────────────────────────────────────────────────────────────────────────
   Modo Apresentação — Leitura Projetada
   A aula inteira rola em coluna única. Sem fatiar, sem medir, sem escalar:
   o conteúdo só rola, então nunca corta. Setas/Espaço/PageDown rolam ~90%
   da tela por vez e pousam em um landmark próximo quando isso preserva o
   ritmo de leitura para teclado e controle remoto.
   ──────────────────────────────────────────────────────────────────────── */

(function () {
    'use strict';

    const SCROLL_FRACTION = 0.9;
    const LANDMARK_SNAP_FRACTION = 0.22;
    const EDGE_TOLERANCE = 2;

    class ProjectionReader {
        constructor() {
            this.body = document.body;
            this.stage = document.getElementById('reader');
            if (!this.stage) return;

            this.docEl = document.getElementById('reader-doc');
            this.progressEl = document.querySelector('[data-reader-progress]');
            this.progressTrack = this.progressEl
                ? this.progressEl.parentElement
                : null;
            this.controlsEl = document.querySelector('.reader-controls');
            this.contextEl = document.querySelector('[data-reader-context]');
            this.contextCountEl = document.querySelector(
                '[data-reader-section-count]'
            );
            this.contextTitleEl = document.querySelector(
                '[data-reader-section-title]'
            );
            this.blackoutEl = document.getElementById('reader-blackout');
            this.notesEl = document.getElementById('reader-notes');
            this.notesBody = this.notesEl
                ? this.notesEl.querySelector('.reader-notes-body')
                : null;
            this.lightboxEl = document.getElementById('reader-cover-dialog');
            this.lightboxOpenBtn = document.querySelector(
                '[data-reader-lightbox-open]'
            );
            this.upBtn = document.querySelector('[data-reader-up]');
            this.downBtn = document.querySelector('[data-reader-down]');
            this.blackoutBtn = document.querySelector('[data-reader-blackout]');
            this.notesBtn = document.querySelector('[data-reader-notes]');
            this.notesCloseBtn = document.querySelector(
                '[data-reader-notes-close]'
            );
            this.fullscreenBtn = document.querySelector(
                '[data-reader-fullscreen]'
            );
            this.startFullscreenBtn = document.querySelector(
                '[data-reader-start-fullscreen]'
            );
            this.startFullscreenLabel = document.querySelector(
                '[data-reader-start-label]'
            );
            this.revealBtn = document.querySelector('[data-reader-reveal]');
            this.exitEl = document.querySelector('[data-reader-exit]');
            this.hintEl = document.querySelector('[data-reader-hint]');
            this.discoveryEl = document.querySelector(
                '[data-reader-discovery]'
            );

            this.motionQuery = window.matchMedia(
                '(prefers-reduced-motion: reduce)'
            );
            this.landmarks = [];
            this.backgroundInertState = new Map();
            this.managedScrollRegions = new WeakMap();
            this.lightboxReturnFocus = null;
            this.notesReturnFocus = null;
            this.blackoutReturnFocus = null;
            this.lightboxUsesNativeModal = false;
            this.fullscreenActive = false;
            this.idleTimer = null;
            this.helpTimer = null;
            this.discoveryTimer = null;
            this.navigationFeedbackTimer = null;
            this.revealActiveTimer = null;
            this.keyActiveTimers = new WeakMap();
            this.progressScheduled = false;
            this.layoutScheduled = false;
            this.lastIdleResetAt = 0;
            this.lastAnnouncement = '';
            this.lastProgress = -1;
            this.lastLandmarkIndex = -1;
            this.lastAtStart = null;
            this.lastAtEnd = null;

            this.init();
        }

        init() {
            this.prepareAccessibility();
            this.refreshLandmarks();
            this.bindKeys();
            this.bindControls();
            this.bindLightbox();
            this.bindQuizReveal();
            this.bindScroll();
            this.setupIdleDetection();
            this.updateReaderState();
            this.stage.focus({ preventScroll: true });
            if (window.lucide) window.lucide.createIcons();
        }

        prepareAccessibility() {
            this.statusEl = document.createElement('div');
            this.statusEl.className = 'sr-only';
            this.statusEl.setAttribute('role', 'status');
            this.statusEl.setAttribute('aria-live', 'polite');
            this.statusEl.setAttribute('aria-atomic', 'true');
            this.body.appendChild(this.statusEl);

            if (this.progressTrack) {
                this.progressTrack.removeAttribute('aria-hidden');
                this.progressTrack.setAttribute('role', 'progressbar');
                this.progressTrack.setAttribute(
                    'aria-label',
                    'Progresso da apresentação'
                );
                this.progressTrack.setAttribute('aria-valuemin', '0');
                this.progressTrack.setAttribute('aria-valuemax', '100');
            }

            if (this.blackoutEl) {
                this.blackoutEl.setAttribute('role', 'dialog');
                this.blackoutEl.setAttribute('aria-modal', 'true');
                this.blackoutEl.setAttribute(
                    'aria-label',
                    'Pausa pedagógica'
                );
                this.blackoutEl.setAttribute('tabindex', '-1');
            }

            if (this.notesEl) {
                this.notesEl.setAttribute('role', 'dialog');
                this.notesEl.setAttribute('aria-modal', 'false');
                this.notesEl.setAttribute('aria-hidden', 'true');
            }

            if (this.lightboxEl) {
                this.lightboxEl.setAttribute('aria-modal', 'true');
            }

            if (!this.fullscreenRequest()) {
                [this.fullscreenBtn, this.startFullscreenBtn].forEach(
                    (button) => {
                        if (!button) return;
                        button.disabled = true;
                        button.setAttribute(
                            'aria-label',
                            'Tela cheia indisponível neste navegador'
                        );
                        button.setAttribute(
                            'title',
                            'Tela cheia indisponível'
                        );
                    }
                );
            }

            if (this.discoveryEl) {
                this.discoveryTimer = setTimeout(() => {
                    this.dismissDiscovery();
                }, 9000);
            }
        }

        dismissDiscovery() {
            if (!this.discoveryEl || this.discoveryEl.hidden) return;
            clearTimeout(this.discoveryTimer);
            this.discoveryEl.hidden = true;
        }

        landmarkStateText(landmark) {
            if (!landmark) return '';
            if (landmark.kind === 'cover') return 'Introdução';
            if (landmark.kind === 'end') return 'Conclusão';
            return `Seção ${landmark.sectionIndex + 1} de `
                + `${landmark.sectionCount}: ${landmark.label}`;
        }

        updateReaderContext(landmark) {
            if (!this.contextEl) return;
            const isVisible = Boolean(
                landmark && landmark.kind !== 'cover'
            );
            this.contextEl.hidden = !isVisible;
            this.contextEl.setAttribute('aria-hidden', String(!isVisible));
            if (!isVisible) return;

            if (landmark.kind === 'end') {
                if (this.contextCountEl) {
                    this.contextCountEl.textContent = 'Conclusão';
                }
                if (this.contextTitleEl) {
                    this.contextTitleEl.textContent = 'Fim da aula';
                }
                return;
            }

            if (this.contextCountEl) {
                this.contextCountEl.textContent = (
                    `Seção ${landmark.sectionIndex + 1} `
                    + `de ${landmark.sectionCount}`
                );
            }
            if (this.contextTitleEl) {
                this.contextTitleEl.textContent = landmark.label;
            }
        }

        contextOffset() {
            if (this.contextEl && !this.contextEl.hidden) {
                const stageRect = this.stage.getBoundingClientRect();
                const contextRect = this.contextEl.getBoundingClientRect();
                return Math.max(
                    0,
                    contextRect.bottom - stageRect.top + 20
                );
            }
            return Math.max(64, this.stage.clientHeight * 0.08);
        }

        announce(message) {
            if (!this.statusEl || !message) return;
            this.lastAnnouncement = message;
            this.statusEl.textContent = '';
            requestAnimationFrame(() => {
                if (this.lastAnnouncement === message) {
                    this.statusEl.textContent = message;
                }
            });
        }

        isValidFocusTarget(target) {
            return target instanceof HTMLElement
                && target.isConnected
                && !target.closest('[hidden], [inert]')
                && typeof target.focus === 'function';
        }

        restoreFocus(target, fallback) {
            const next = this.isValidFocusTarget(target) ? target : fallback;
            if (this.isValidFocusTarget(next)) {
                next.focus({ preventScroll: true });
            }
        }

        motionOk() {
            return !this.motionQuery.matches;
        }

        elementScrollTop(element) {
            const stageRect = this.stage.getBoundingClientRect();
            const elementRect = element.getBoundingClientRect();
            return Math.max(
                0,
                this.stage.scrollTop + elementRect.top - stageRect.top
            );
        }

        landmarkLabel(element) {
            if (element.classList.contains('reader-cover')) {
                return 'Introdução';
            }
            if (element.classList.contains('reader-end')) return 'Conclusão';
            return element.textContent.trim().replace(/\s+/g, ' ');
        }

        refreshLandmarks() {
            if (!this.docEl) return;

            const selector = '.reader-cover, h2, h3, .conceito-box, .atencao-box, .dica-box, .quiz-card, .tbl-wrap, figure, .reader-end';
            const elements = Array.from(this.docEl.querySelectorAll(selector)).filter((element) => {
                if (!(element instanceof HTMLElement) || element.closest('[hidden], [inert]')) return false;
                // Evitar que filhos de blocos atômicos virem landmarks duplicados
                if (element.parentElement && element.parentElement.closest('.conceito-box, .atencao-box, .dica-box, .quiz-card, .tbl-wrap, figure, article')) {
                    return false;
                }
                return true;
            });

            const sectionCount = elements.filter(
                (element) => element.tagName === 'H2'
            ).length;
            let sectionIndex = 0;

            this.landmarks = elements.map((element) => {
                const isH2 = element.tagName === 'H2';
                const kind = element.classList.contains('reader-cover')
                    ? 'cover'
                    : (
                        element.classList.contains('reader-end')
                            ? 'end'
                            : (isH2 ? 'section' : 'block')
                    );
                const landmark = {
                    element: element,
                    kind: kind,
                    label: this.landmarkLabel(element),
                    sectionCount: sectionCount,
                    sectionIndex: isH2 ? sectionIndex : -1,
                    top: this.elementScrollTop(element)
                };
                if (isH2) sectionIndex += 1;
                return landmark;
            }).sort((first, second) => first.top - second.top);
            this.prepareScrollableRegions();
            this.updateReaderContext(
                this.landmarks[this.activeLandmarkIndex()]
            );
        }

        prepareScrollableRegions() {
            this.docEl.querySelectorAll('.tbl-wrap, table').forEach((region) => {
                const overflows = region.scrollWidth > region.clientWidth + 1;
                if (overflows) {
                    const managed = this.managedScrollRegions.get(region) || {
                        tabindex: false,
                        label: false,
                        role: false
                    };
                    if (!region.hasAttribute('tabindex')) {
                        region.setAttribute('tabindex', '0');
                        managed.tabindex = true;
                    }
                    if (!region.hasAttribute('aria-label')) {
                        region.setAttribute(
                            'aria-label',
                            'Tabela com rolagem horizontal'
                        );
                        managed.label = true;
                    }
                    if (region.matches('.tbl-wrap')
                        && !region.hasAttribute('role')) {
                        region.setAttribute('role', 'region');
                        managed.role = true;
                    }
                    this.managedScrollRegions.set(region, managed);
                } else {
                    const managed = this.managedScrollRegions.get(region);
                    if (!managed) return;
                    if (managed.tabindex) region.removeAttribute('tabindex');
                    if (managed.label) {
                        region.removeAttribute('aria-label');
                    }
                    if (managed.role) region.removeAttribute('role');
                    this.managedScrollRegions.delete(region);
                }
            });
        }

        activeLandmarkIndex(scrollTop = this.stage.scrollTop) {
            if (!this.landmarks.length) return -1;
            const readingLine = scrollTop + (this.stage.clientHeight * 0.2);
            let activeIndex = 0;

            this.landmarks.forEach((landmark, index) => {
                if (landmark.kind === 'section' && landmark.top <= readingLine) {
                    activeIndex = index;
                }
            });
            return activeIndex;
        }

        nearestLandmarkTarget(rawTarget, direction) {
            if (!this.landmarks.length) return null;

            const current = this.stage.scrollTop;
            const offset = this.contextOffset();

            if (direction > 0) {
                // Procura o próximo landmark cujo topo ajustado está ABAIXO da posição atual
                const candidate = this.landmarks.find((lm) => (lm.top - offset) > (current + 24));
                return candidate ? Math.max(0, candidate.top - offset) : null;
            } else {
                // Procura o landmark anterior cujo topo ajustado está ACIMA da posição atual
                const candidates = this.landmarks.filter((lm) => (lm.top - offset) < (current - 24));
                if (candidates.length > 0) {
                    const last = candidates[candidates.length - 1];
                    return Math.max(0, last.top - offset);
                }
                return null;
            }
        }

        maxScrollTop() {
            return Math.max(0, this.stage.scrollHeight - this.stage.clientHeight);
        }

        clampScrollTop(value) {
            return Math.min(this.maxScrollTop(), Math.max(0, value));
        }

        readingViewportHeight() {
            const stageRect = this.stage.getBoundingClientRect();
            const hintRect = this.hintEl && !this.hintEl.hidden
                ? this.hintEl.getBoundingClientRect()
                : null;
            const contextRect = this.contextEl && !this.contextEl.hidden
                ? this.contextEl.getBoundingClientRect()
                : null;
            const controlsRect = this.controlsEl
                ? this.controlsEl.getBoundingClientRect()
                : null;
            const topInset = Math.max(
                hintRect
                    ? Math.max(0, hintRect.bottom - stageRect.top)
                    : 0,
                contextRect
                    ? Math.max(0, contextRect.bottom - stageRect.top)
                    : 0
            );
            const bottomInset = controlsRect
                ? Math.max(0, stageRect.bottom - controlsRect.top)
                : 0;
            return Math.max(
                this.stage.clientHeight * 0.55,
                this.stage.clientHeight - topInset - bottomInset
            );
        }

        scheduleNavigationFeedback(targetTop) {
            clearTimeout(this.navigationFeedbackTimer);
            const delay = this.motionOk() ? 420 : 0;
            this.navigationFeedbackTimer = setTimeout(() => {
                this.updateReaderState();
                const index = this.activeLandmarkIndex(targetTop);
                const landmark = this.landmarks[index];
                if (landmark) {
                    this.announce(`${this.landmarkStateText(landmark)}.`);
                }
            }, delay);
        }

        scrollToPosition(targetTop) {
            const clampedTarget = this.clampScrollTop(targetTop);
            this.stage.scrollTo({
                top: clampedTarget,
                left: 0,
                behavior: this.motionOk() ? 'smooth' : 'auto'
            });
            this.scheduleNavigationFeedback(clampedTarget);
        }

        scrollByScreen(direction) {
            const current = this.stage.scrollTop;
            const max = this.maxScrollTop();
            const atEdge = direction < 0
                ? current <= EDGE_TOLERANCE
                : current >= max - EDGE_TOLERANCE;

            if (atEdge) {
                this.announce(
                    direction < 0 ? 'Início da aula.' : 'Fim da aula.'
                );
                return;
            }

            const target = this.nearestLandmarkTarget(null, direction);
            if (target !== null) {
                this.scrollToPosition(target);
            } else {
                // Fallback: rola 90% da tela se não há mais landmarks
                const rawTarget = this.clampScrollTop(
                    current
                    + (this.readingViewportHeight() * SCROLL_FRACTION * direction)
                );
                this.scrollToPosition(rawTarget);
            }
        }

        scrollToEdge(top) {
            this.scrollToPosition(top ? this.maxScrollTop() : 0);
        }

        pulseControl(control, duration = 220) {
            if (!control) return;

            const previousTimer = this.keyActiveTimers.get(control);
            if (previousTimer) clearTimeout(previousTimer);
            control.classList.add('is-key-active');
            const timer = setTimeout(() => {
                control.classList.remove('is-key-active');
                this.keyActiveTimers.delete(control);
            }, duration);
            this.keyActiveTimers.set(control, timer);
        }

        showHelp() {
            if (!this.hintEl) return;
            clearTimeout(this.helpTimer);
            this.wakeHud(true);
            this.hintEl.hidden = false;
            this.hintEl.classList.add('is-help-visible');
            this.announce('Ajuda de atalhos exibida.');
            this.helpTimer = setTimeout(() => {
                this.hintEl.classList.remove('is-help-visible');
                this.hintEl.hidden = true;
            }, 12000);
        }

        updateNavigationButtons(atStart, atEnd) {
            if (this.upBtn) {
                this.upBtn.disabled = atStart;
                this.upBtn.setAttribute(
                    'aria-label',
                    atStart
                        ? 'Você está no início da aula'
                        : 'Voltar cerca de uma tela'
                );
                this.upBtn.setAttribute(
                    'title',
                    atStart ? 'Início da aula' : 'Voltar (↑ / PgUp)'
                );
            }
            if (this.downBtn) {
                this.downBtn.disabled = atEnd;
                this.downBtn.setAttribute(
                    'aria-label',
                    atEnd
                        ? 'Você está no fim da aula'
                        : 'Avançar cerca de uma tela'
                );
                this.downBtn.setAttribute(
                    'title',
                    atEnd ? 'Fim da aula' : 'Avançar (↓ / PgDown / Espaço)'
                );
            }
        }

        updateReaderState() {
            const max = this.maxScrollTop();
            const scrollTop = this.clampScrollTop(this.stage.scrollTop);
            const ratio = max > EDGE_TOLERANCE ? scrollTop / max : 1;
            const progress = Math.round(
                Math.min(1, Math.max(0, ratio)) * 100
            );
            const atStart = scrollTop <= EDGE_TOLERANCE;
            const atEnd = scrollTop >= max - EDGE_TOLERANCE;
            const landmarkIndex = this.activeLandmarkIndex(scrollTop);
            const landmark = this.landmarks[landmarkIndex];

            if (this.progressEl) {
                this.progressEl.style.transform = `scaleX(${ratio})`;
            }
            if (this.progressTrack
                && (progress !== this.lastProgress
                    || landmarkIndex !== this.lastLandmarkIndex)) {
                this.progressTrack.setAttribute(
                    'aria-valuenow',
                    String(progress)
                );
                this.progressTrack.setAttribute(
                    'aria-valuetext',
                    landmark
                        ? `${progress}% — ${this.landmarkStateText(landmark)}`
                        : `${progress}% da aula`
                );
            }
            if (landmarkIndex !== this.lastLandmarkIndex) {
                this.updateReaderContext(landmark);
            }
            if (atStart !== this.lastAtStart || atEnd !== this.lastAtEnd) {
                this.updateNavigationButtons(atStart, atEnd);
            }
            this.lastProgress = progress;
            this.lastLandmarkIndex = landmarkIndex;
            this.lastAtStart = atStart;
            this.lastAtEnd = atEnd;
        }

        /* ── Pausa Pedagógica ────────────────────────────────────────────── */
        isBlackoutOpen() {
            return Boolean(
                this.blackoutEl
                && !this.blackoutEl.hasAttribute('hidden')
            );
        }

        setBackgroundInert(active) {
            const siblings = Array.from(this.body.children).filter(
                (element) => element !== this.blackoutEl
                    && element !== this.statusEl
                    && element.tagName !== 'SCRIPT'
            );

            if (active) {
                siblings.forEach((element) => {
                    this.backgroundInertState.set(
                        element,
                        element.hasAttribute('inert')
                    );
                    element.setAttribute('inert', '');
                });
                return;
            }

            siblings.forEach((element) => {
                if (!this.backgroundInertState.get(element)) {
                    element.removeAttribute('inert');
                }
            });
            this.backgroundInertState.clear();
        }

        toggleBlackout(force) {
            if (!this.blackoutEl) return;
            const showing = typeof force === 'boolean'
                ? force
                : !this.isBlackoutOpen();
            if (showing === this.isBlackoutOpen()) return;

            if (showing) {
                this.blackoutReturnFocus = document.activeElement;
                this.setBackgroundInert(true);
                this.blackoutEl.removeAttribute('hidden');
                this.blackoutEl.setAttribute('aria-hidden', 'false');
                this.blackoutEl.focus({ preventScroll: true });
                this.announce(
                    'Pausa pedagógica ativada. Pressione B ou Escape para retomar.'
                );
            } else {
                this.blackoutEl.setAttribute('hidden', '');
                this.blackoutEl.setAttribute('aria-hidden', 'true');
                this.setBackgroundInert(false);
                this.restoreFocus(
                    this.blackoutReturnFocus,
                    this.blackoutBtn || this.stage
                );
                this.blackoutReturnFocus = null;
                this.announce('Pausa pedagógica encerrada.');
            }

            if (this.blackoutBtn) {
                this.blackoutBtn.classList.toggle('is-active', showing);
                this.blackoutBtn.setAttribute(
                    'aria-pressed',
                    String(showing)
                );
            }
        }

        /* ── Roteiro no projetor ─────────────────────────────────────────── */
        isNotesOpen() {
            return Boolean(
                this.notesEl
                && this.notesEl.classList.contains('is-open')
            );
        }

        toggleNotes(force) {
            if (!this.notesEl) {
                this.announce('Esta aula não possui roteiro para projeção.');
                return;
            }
            const isOpen = typeof force === 'boolean'
                ? force
                : !this.isNotesOpen();
            if (isOpen === this.isNotesOpen()) return;

            if (isOpen) {
                this.notesReturnFocus = document.activeElement;
                this.notesEl.classList.add('is-open');
                this.notesEl.removeAttribute('inert');
                this.notesEl.setAttribute('aria-hidden', 'false');
                if (this.notesCloseBtn) {
                    this.notesCloseBtn.focus({ preventScroll: true });
                }
                this.announce('Roteiro no projetor aberto.');
            } else {
                this.notesEl.classList.remove('is-open');
                this.notesEl.setAttribute('inert', '');
                this.notesEl.setAttribute('aria-hidden', 'true');
                if (!this.isBlackoutOpen()) {
                    this.restoreFocus(
                        this.notesReturnFocus,
                        this.notesBtn || this.stage
                    );
                }
                this.notesReturnFocus = null;
                this.announce('Roteiro no projetor fechado.');
            }

            if (this.notesBtn) {
                this.notesBtn.classList.toggle('is-active', isOpen);
                this.notesBtn.setAttribute(
                    'aria-expanded',
                    String(isOpen)
                );
                this.notesBtn.setAttribute(
                    'aria-label',
                    isOpen
                        ? 'Fechar roteiro no projetor'
                        : 'Abrir roteiro no projetor'
                );
            }
        }

        scrollNotes(event) {
            if (!this.notesBody || !this.notesEl.contains(event.target)) {
                return false;
            }

            let target = null;
            const page = this.notesBody.clientHeight * 0.85;
            if (event.key === 'ArrowDown' || event.key === 'PageDown') {
                target = this.notesBody.scrollTop + page;
            } else if (event.key === 'ArrowUp' || event.key === 'PageUp') {
                target = this.notesBody.scrollTop - page;
            } else if (event.key === 'Home') {
                target = 0;
            } else if (event.key === 'End') {
                target = this.notesBody.scrollHeight;
            }

            if (target === null) return false;
            event.preventDefault();
            this.notesBody.scrollTo({
                top: target,
                behavior: this.motionOk() ? 'smooth' : 'auto'
            });
            return true;
        }

        /* ── Tela cheia ──────────────────────────────────────────────────── */
        isFullscreen() {
            return Boolean(
                document.fullscreenElement
                || document.webkitFullscreenElement
                || document.msFullscreenElement
            );
        }

        fullscreenRequest() {
            const root = document.documentElement;
            return root.requestFullscreen
                || root.webkitRequestFullscreen
                || root.msRequestFullscreen
                || null;
        }

        async requestFullscreen() {
            const request = this.fullscreenRequest();
            if (!request) return false;
            try {
                await Promise.resolve(request.call(document.documentElement));
                return true;
            } catch (error) {
                return false;
            }
        }

        async exitFullscreen() {
            const exit = document.exitFullscreen
                || document.webkitExitFullscreen
                || document.msExitFullscreen;
            if (!exit) return false;
            try {
                await Promise.resolve(exit.call(document));
                return true;
            } catch (error) {
                return false;
            }
        }

        async toggleFullscreen() {
            if (!this.fullscreenRequest()) {
                this.announce('Tela cheia indisponível neste navegador.');
                return;
            }
            const changed = this.isFullscreen()
                ? await this.exitFullscreen()
                : await this.requestFullscreen();
            if (!changed) {
                this.announce(
                    'Não foi possível alterar o modo de tela cheia.'
                );
            }
        }

        syncFullscreenButton(announceChange = false) {
            const active = this.isFullscreen();
            if (this.fullscreenBtn) {
                if (this.fullscreenRequest()) {
                    this.fullscreenBtn.setAttribute(
                        'aria-pressed',
                        String(active)
                    );
                    this.fullscreenBtn.setAttribute(
                        'aria-label',
                        active ? 'Sair da tela cheia' : 'Entrar em tela cheia'
                    );
                    this.fullscreenBtn.setAttribute(
                        'title',
                        active ? 'Sair da tela cheia (F)' : 'Tela cheia (F)'
                    );
                    this.fullscreenBtn.classList.toggle('is-active', active);
                }
            }
            if (this.startFullscreenBtn && this.fullscreenRequest()) {
                this.startFullscreenBtn.setAttribute(
                    'aria-pressed',
                    String(active)
                );
                this.startFullscreenBtn.setAttribute(
                    'aria-label',
                    active ? 'Sair da tela cheia' : 'Começar em tela cheia'
                );
                this.startFullscreenBtn.setAttribute(
                    'title',
                    active ? 'Sair da tela cheia (F)' : 'Começar em tela cheia (F)'
                );
                this.startFullscreenBtn.classList.toggle('is-active', active);
                if (this.startFullscreenLabel) {
                    this.startFullscreenLabel.textContent = active
                        ? 'Sair da tela cheia'
                        : 'Começar em tela cheia';
                }
            }
            this.body.classList.toggle('is-fullscreen', active);
            if (announceChange && active !== this.fullscreenActive) {
                this.announce(
                    active ? 'Tela cheia ativada.' : 'Tela cheia encerrada.'
                );
            }
            this.fullscreenActive = active;
        }

        /* ── Lightbox da capa ─────────────────────────────────────────────── */
        isLightboxOpen() {
            return Boolean(
                this.lightboxEl
                && (this.lightboxEl.open
                    || this.lightboxEl.hasAttribute('open'))
            );
        }

        openLightbox() {
            if (!this.lightboxEl || this.isLightboxOpen()) return;
            this.lightboxReturnFocus = document.activeElement;
            this.lightboxUsesNativeModal = typeof this.lightboxEl.showModal
                === 'function';

            if (this.lightboxUsesNativeModal) {
                try {
                    this.lightboxEl.showModal();
                } catch (error) {
                    this.lightboxUsesNativeModal = false;
                    this.lightboxEl.setAttribute('open', '');
                }
            } else {
                this.lightboxEl.setAttribute('open', '');
            }
            if (this.lightboxOpenBtn) {
                this.lightboxOpenBtn.setAttribute('aria-expanded', 'true');
            }
            const closeBtn = this.lightboxEl.querySelector(
                '[data-reader-lightbox-close]'
            );
            if (closeBtn) closeBtn.focus({ preventScroll: true });
            this.announce('Capa da aula ampliada.');
        }

        handleLightboxClosed() {
            if (this.lightboxOpenBtn) {
                this.lightboxOpenBtn.setAttribute('aria-expanded', 'false');
            }
            const returnFocus = this.lightboxReturnFocus;
            this.lightboxReturnFocus = null;
            this.restoreFocus(
                returnFocus,
                this.lightboxOpenBtn || this.stage
            );
        }

        closeLightbox() {
            if (!this.lightboxEl || !this.isLightboxOpen()) return;
            if (typeof this.lightboxEl.close === 'function') {
                this.lightboxEl.close();
            } else {
                this.lightboxEl.removeAttribute('open');
                this.handleLightboxClosed();
            }
            this.announce('Capa ampliada fechada.');
        }

        toggleLightbox() {
            if (this.isLightboxOpen()) this.closeLightbox();
            else this.openLightbox();
        }

        trapFallbackLightboxFocus(event) {
            if (this.lightboxUsesNativeModal || event.key !== 'Tab') return;
            const focusable = Array.from(this.lightboxEl.querySelectorAll(
                'button:not(:disabled), [href], [tabindex]:not([tabindex="-1"])'
            )).filter((element) => !element.hasAttribute('hidden'));
            if (!focusable.length) {
                event.preventDefault();
                return;
            }
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }

        bindLightbox() {
            if (!this.lightboxEl) return;

            if (this.lightboxOpenBtn) {
                this.lightboxOpenBtn.addEventListener(
                    'click',
                    () => this.openLightbox()
                );
            }

            const closeBtn = this.lightboxEl.querySelector(
                '[data-reader-lightbox-close]'
            );
            if (closeBtn) {
                closeBtn.addEventListener('click', (event) => {
                    event.stopPropagation();
                    this.closeLightbox();
                });
            }

            this.lightboxEl.addEventListener('click', (event) => {
                if (event.target === this.lightboxEl
                    || event.target.tagName === 'IMG') {
                    this.closeLightbox();
                }
            });
            this.lightboxEl.addEventListener(
                'keydown',
                (event) => this.trapFallbackLightboxFocus(event)
            );
            this.lightboxEl.addEventListener('cancel', (event) => {
                event.preventDefault();
                this.closeLightbox();
            });
            this.lightboxEl.addEventListener(
                'close',
                () => this.handleLightboxClosed()
            );
        }

        handleEscape() {
            if (this.isLightboxOpen()) {
                this.closeLightbox();
                return;
            }
            if (this.isNotesOpen()) {
                this.pulseControl(this.notesBtn);
                this.toggleNotes(false);
                return;
            }
            if (this.isBlackoutOpen()) {
                this.pulseControl(this.blackoutBtn);
                this.toggleBlackout(false);
                return;
            }
            if (this.isFullscreen()) {
                this.pulseControl(this.fullscreenBtn);
                this.toggleFullscreen();
                return;
            }
            if (this.exitEl && this.exitEl.href) {
                this.pulseControl(this.exitEl);
                window.location.assign(this.exitEl.href);
            }
        }

        /* ── Quiz projetado ─────────────────────────────────────────────── */
        revealQuiz(source) {
            window.dispatchEvent(new CustomEvent('reader:reveal-quiz', {
                detail: { source: source }
            }));
        }

        bringQuizIntoContext(target) {
            if (!(target instanceof HTMLElement)) return;
            const stageRect = this.stage.getBoundingClientRect();
            const targetRect = target.getBoundingClientRect();
            const inset = Math.min(64, this.stage.clientHeight * 0.08);
            const isVisible = targetRect.top >= stageRect.top + inset
                && targetRect.bottom <= stageRect.bottom - inset;
            if (isVisible) return;

            const targetTop = this.stage.scrollTop
                + targetRect.top
                - stageRect.top
                - (targetRect.height > this.stage.clientHeight * 0.8
                    ? inset
                    : (this.stage.clientHeight - targetRect.height) / 2);
            this.scrollToPosition(targetTop);
        }

        syncRevealButton(remaining, statusMessage = '') {
            if (!this.revealBtn) return;

            const remainingCount = Number(remaining);
            const hasRemaining = Number.isFinite(remainingCount)
                && remainingCount > 0;
            const actionLabel = hasRemaining
                ? 'Revelar próxima resposta'
                : 'Não há respostas pendentes';
            this.revealBtn.disabled = !hasRemaining;
            this.revealBtn.setAttribute(
                'aria-label',
                statusMessage ? `${statusMessage} ${actionLabel}` : actionLabel
            );
            this.revealBtn.setAttribute(
                'title',
                hasRemaining
                    ? 'Revelar próxima resposta (R)'
                    : 'Não há respostas pendentes'
            );
        }

        handleQuizRevealed(event) {
            const detail = event.detail || {};
            const target = detail.question || detail.quiz;
            const questionNumber = Number(detail.questionNumber);
            const hasQuestionNumber = Number.isInteger(questionNumber)
                && questionNumber > 0;
            const message = hasQuestionNumber
                ? `Resposta da questão ${questionNumber} revelada.`
                : 'Resposta revelada.';

            this.pulseControl(this.revealBtn, 1200);
            if (this.revealBtn) {
                this.syncRevealButton(detail.remaining, message);
                this.revealBtn.classList.add('is-active');
                clearTimeout(this.revealActiveTimer);
                this.revealActiveTimer = setTimeout(() => {
                    this.revealBtn.classList.remove('is-active');
                }, 1600);
            }
            const remaining = Number(detail.remaining) || 0;
            this.announce(
                `${message} ${remaining} `
                + (remaining === 1
                    ? 'resposta pendente.'
                    : 'respostas pendentes.')
            );
            this.bringQuizIntoContext(target);
        }

        handleQuizStateChanged(event) {
            const detail = event.detail || {};
            // Disponibilidade não é resultado: source='answer' nunca recebe
            // texto de "resposta revelada".
            this.syncRevealButton(detail.remaining);
            this.scheduleLayoutRefresh();
        }

        bindQuizReveal() {
            if (this.revealBtn
                && !document.querySelector(
                    '.lesson-quiz--interactive .quiz-option'
                )) {
                this.syncRevealButton(0);
            }
            window.addEventListener(
                'reader:quiz-revealed',
                (event) => this.handleQuizRevealed(event)
            );
            window.addEventListener(
                'reader:quiz-state-changed',
                (event) => this.handleQuizStateChanged(event)
            );
        }

        /* ── Eventos ─────────────────────────────────────────────────────── */
        isEditableTarget(target) {
            return target instanceof HTMLElement
                && (
                    target.matches('input, textarea, select')
                    || target.isContentEditable
                );
        }

        bindKeys() {
            window.addEventListener('keydown', (event) => {
                if (this.isEditableTarget(event.target)) return;
                if (event.ctrlKey || event.metaKey || event.altKey) return;
                if (event.repeat && [
                    'Escape', 'b', 'B', 'n', 'N', 'c', 'C',
                    'f', 'F', 'r', 'R', '?'
                ].includes(event.key)) {
                    return;
                }

                const interactive = event.target.closest
                    && event.target.closest(
                        'button, a[href], select, [role="button"]'
                    );

                if (this.isLightboxOpen()
                    && !['Escape', 'c', 'C'].includes(event.key)) {
                    return;
                }

                if (this.isBlackoutOpen()) {
                    if (event.key === 'Tab') {
                        event.preventDefault();
                        this.blackoutEl.focus({ preventScroll: true });
                        return;
                    }
                    if (!['b', 'B', 'Escape'].includes(event.key)) {
                        if ([
                            ' ', 'ArrowDown', 'PageDown', 'ArrowUp',
                            'PageUp', 'Home', 'End'
                        ].includes(event.key)) {
                            event.preventDefault();
                        }
                        return;
                    }
                }

                if (this.isNotesOpen() && this.scrollNotes(event)) return;

                switch (event.key) {
                    case ' ':
                        // Espaço sobre um controle/opção ativa o próprio elemento.
                        if (interactive) return;
                        event.preventDefault();
                        this.pulseControl(
                            event.shiftKey ? this.upBtn : this.downBtn
                        );
                        this.scrollByScreen(event.shiftKey ? -1 : 1);
                        break;
                    case 'ArrowDown':
                    case 'PageDown':
                        event.preventDefault();
                        this.pulseControl(this.downBtn);
                        this.scrollByScreen(1);
                        break;
                    case 'ArrowUp':
                    case 'PageUp':
                        event.preventDefault();
                        this.pulseControl(this.upBtn);
                        this.scrollByScreen(-1);
                        break;
                    case 'Home':
                        event.preventDefault();
                        this.pulseControl(this.upBtn);
                        this.scrollToEdge(false);
                        break;
                    case 'End':
                        event.preventDefault();
                        this.pulseControl(this.downBtn);
                        this.scrollToEdge(true);
                        break;
                    case 'b':
                    case 'B':
                        event.preventDefault();
                        this.pulseControl(this.blackoutBtn);
                        this.toggleBlackout();
                        break;
                    case 'n':
                    case 'N':
                        event.preventDefault();
                        this.pulseControl(this.notesBtn);
                        this.toggleNotes();
                        break;
                    case 'c':
                    case 'C':
                        event.preventDefault();
                        if (this.lightboxEl) {
                            this.toggleLightbox();
                        } else {
                            this.announce('Esta aula não possui capa ampliável.');
                        }
                        break;
                    case 'f':
                    case 'F':
                        event.preventDefault();
                        this.pulseControl(this.fullscreenBtn);
                        this.toggleFullscreen();
                        break;
                    case 'r':
                    case 'R':
                        event.preventDefault();
                        if (this.revealBtn && !this.revealBtn.disabled) {
                            this.pulseControl(this.revealBtn);
                            this.revealQuiz('shortcut');
                        } else {
                            this.announce('Não há respostas pendentes.');
                        }
                        break;
                    case '?':
                        event.preventDefault();
                        this.showHelp();
                        break;
                    case 'Escape':
                        event.preventDefault();
                        this.handleEscape();
                        break;
                }
            });
        }

        bindControls() {
            const on = (element, handler) => {
                if (element) element.addEventListener('click', handler);
            };

            on(this.downBtn, () => this.scrollByScreen(1));
            on(this.upBtn, () => this.scrollByScreen(-1));
            on(this.blackoutBtn, () => this.toggleBlackout());
            on(this.notesBtn, () => this.toggleNotes());
            on(this.notesCloseBtn, () => this.toggleNotes(false));
            on(this.fullscreenBtn, () => this.toggleFullscreen());
            on(this.startFullscreenBtn, () => this.toggleFullscreen());
            on(this.revealBtn, () => this.revealQuiz('button'));

            if (this.blackoutEl) {
                this.blackoutEl.addEventListener(
                    'click',
                    () => this.toggleBlackout(false)
                );
            }
            const onFullscreenChange = () => {
                this.syncFullscreenButton(true);
            };
            document.addEventListener('fullscreenchange', onFullscreenChange);
            document.addEventListener(
                'webkitfullscreenchange',
                onFullscreenChange
            );
            this.syncFullscreenButton();
        }

        scheduleProgressUpdate() {
            if (this.progressScheduled) return;
            this.progressScheduled = true;
            requestAnimationFrame(() => {
                this.progressScheduled = false;
                this.updateReaderState();
            });
        }

        scheduleLayoutRefresh() {
            if (this.layoutScheduled) return;
            this.layoutScheduled = true;
            requestAnimationFrame(() => {
                this.layoutScheduled = false;
                this.refreshLandmarks();
                this.updateReaderState();
            });
        }

        bindScroll() {
            this.stage.addEventListener(
                'scroll',
                () => this.scheduleProgressUpdate(),
                { passive: true }
            );
            window.addEventListener(
                'resize',
                () => this.scheduleLayoutRefresh(),
                { passive: true }
            );
            window.addEventListener(
                'orientationchange',
                () => this.scheduleLayoutRefresh(),
                { passive: true }
            );

            if ('ResizeObserver' in window && this.docEl) {
                this.resizeObserver = new ResizeObserver(
                    () => this.scheduleLayoutRefresh()
                );
                this.resizeObserver.observe(this.docEl);
            }

            if (document.fonts && document.fonts.ready) {
                document.fonts.ready.then(
                    () => this.scheduleLayoutRefresh()
                );
            }
            this.stage.querySelectorAll('img').forEach((image) => {
                if (!image.complete) {
                    image.addEventListener(
                        'load',
                        () => this.scheduleLayoutRefresh(),
                        { once: true }
                    );
                }
            });
        }

        wakeHud(force = false) {
            const now = performance.now();
            if (!force
                && !this.body.classList.contains('is-idle')
                && now - this.lastIdleResetAt < 180) {
                return;
            }
            this.lastIdleResetAt = now;
            this.body.classList.remove('is-idle');
            clearTimeout(this.idleTimer);
            this.idleTimer = setTimeout(() => {
                this.body.classList.add('is-idle');
                if (this.hintEl
                    && !this.hintEl.classList.contains('is-help-visible')) {
                    this.hintEl.hidden = true;
                }
            }, 3500);
        }

        setupIdleDetection() {
            window.addEventListener(
                'pointermove',
                () => this.wakeHud(),
                { passive: true }
            );
            window.addEventListener(
                'pointerdown',
                () => this.wakeHud(true),
                { passive: true }
            );
            window.addEventListener(
                'keydown',
                () => this.wakeHud(true)
            );
            window.addEventListener(
                'focusin',
                () => this.wakeHud(true)
            );
            this.stage.addEventListener(
                'scroll',
                () => this.wakeHud(),
                { passive: true }
            );
            this.wakeHud(true);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener(
            'DOMContentLoaded',
            () => new ProjectionReader()
        );
    } else {
        new ProjectionReader();
    }
})();
