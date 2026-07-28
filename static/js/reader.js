/* ──────────────────────────────────────────────────────────────────────────
   Modo Apresentação — Leitura Projetada
   A aula inteira rola em coluna única. Sem fatiar, sem medir, sem escalar:
   o conteúdo só rola, então nunca corta. Setas/Espaço/PageDown rolam ~90%
   da tela por vez (sensação de "virar página" para o controle remoto).
   ──────────────────────────────────────────────────────────────────────── */

(function () {
    'use strict';

    const SCROLL_FRACTION = 0.9;

    class ProjectionReader {
        constructor() {
            this.body = document.body;
            this.stage = document.getElementById('reader');
            if (!this.stage) return;

            this.progressEl = document.querySelector('[data-reader-progress]');
            this.blackoutEl = document.getElementById('reader-blackout');
            this.notesEl = document.getElementById('reader-notes');
            this.lightboxEl = document.getElementById('reader-cover-dialog');
            this.lightboxOpenBtn = document.querySelector('[data-reader-lightbox-open]');
            this.hintEl = document.querySelector('[data-reader-hint]');
            this.revealBtn = document.querySelector('[data-reader-reveal]');
            this.lightboxReturnFocus = null;
            this.idleTimer = null;
            this.helpTimer = null;
            this.keyActiveTimers = new WeakMap();
            this.progressScheduled = false;

            this.init();
        }

        init() {
            this.bindKeys();
            this.bindControls();
            this.bindLightbox();
            this.bindQuizReveal();
            this.bindScroll();
            this.setupIdleDetection();
            this.updateProgress();
            this.stage.focus({ preventScroll: true });
            if (window.lucide) window.lucide.createIcons();
        }

        isLightboxOpen() {
            return Boolean(this.lightboxEl && this.lightboxEl.open);
        }

        motionOk() {
            return !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        }

        scrollByScreen(direction) {
            const amount = this.stage.clientHeight * SCROLL_FRACTION * direction;
            this.stage.scrollBy({
                top: amount,
                left: 0,
                behavior: this.motionOk() ? 'smooth' : 'auto'
            });
        }

        scrollToEdge(top) {
            this.stage.scrollTo({
                top: top,
                behavior: this.motionOk() ? 'smooth' : 'auto'
            });
        }

        pulseControl(selector, duration = 220) {
            const control = document.querySelector(selector);
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
            this.body.classList.remove('is-idle');
            this.hintEl.classList.add('is-help-visible');
            this.helpTimer = setTimeout(() => {
                this.hintEl.classList.remove('is-help-visible');
            }, 12000);
        }

        updateProgress() {
            if (!this.progressEl) return;
            const max = this.stage.scrollHeight - this.stage.clientHeight;
            const pct = max > 0 ? (this.stage.scrollTop / max) * 100 : 0;
            this.progressEl.style.transform = `scaleX(${Math.min(1, Math.max(0, pct / 100))})`;
        }

        /* ── Pausa Pedagógica ────────────────────────────────────────────── */
        toggleBlackout() {
            if (!this.blackoutEl) return;
            const showing = this.blackoutEl.hasAttribute('hidden');
            if (showing) {
                this.blackoutEl.removeAttribute('hidden');
                this.blackoutEl.setAttribute('aria-hidden', 'false');
            } else {
                this.blackoutEl.setAttribute('hidden', '');
                this.blackoutEl.setAttribute('aria-hidden', 'true');
            }
            const btn = document.querySelector('[data-reader-blackout]');
            if (btn) {
                btn.classList.toggle('is-active', showing);
                btn.setAttribute('aria-pressed', String(showing));
            }
        }

        /* ── Roteiro docente ─────────────────────────────────────────────── */
        toggleNotes() {
            if (!this.notesEl) return;
            const isOpen = this.notesEl.classList.toggle('is-open');
            if (isOpen) {
                this.notesEl.removeAttribute('inert');
            } else {
                this.notesEl.setAttribute('inert', '');
            }
            const btn = document.querySelector('[data-reader-notes]');
            if (btn) {
                btn.classList.toggle('is-active', isOpen);
                btn.setAttribute('aria-expanded', String(isOpen));
            }
        }

        /* ── Tela cheia ──────────────────────────────────────────────────── */
        isFullscreen() {
            return Boolean(
                document.fullscreenElement
                || document.webkitFullscreenElement
                || document.msFullscreenElement
            );
        }

        requestFullscreen() {
            const root = document.documentElement;
            const req = root.requestFullscreen
                || root.webkitRequestFullscreen
                || root.msRequestFullscreen;
            if (!req) return Promise.resolve();
            return Promise.resolve(req.call(root)).catch(() => {});
        }

        exitFullscreen() {
            const exit = document.exitFullscreen
                || document.webkitExitFullscreen
                || document.msExitFullscreen;
            if (!exit) return Promise.resolve();
            return Promise.resolve(exit.call(document)).catch(() => {});
        }

        toggleFullscreen() {
            if (!this.isFullscreen()) {
                this.requestFullscreen();
            } else {
                this.exitFullscreen();
            }
        }

        syncFullscreenButton() {
            const btn = document.querySelector('[data-reader-fullscreen]');
            if (!btn) return;
            const active = this.isFullscreen();
            btn.setAttribute('aria-pressed', String(active));
            btn.setAttribute('aria-label', active ? 'Sair da tela cheia' : 'Entrar em tela cheia');
            btn.setAttribute('title', active ? 'Sair da tela cheia (F)' : 'Tela cheia (F)');
            btn.classList.toggle('is-active', active);
            this.body.classList.toggle('is-fullscreen', active);
        }

        /* ── Lightbox da capa ─────────────────────────────────────────────── */
        openLightbox() {
            if (!this.lightboxEl || this.lightboxEl.open) return;
            this.lightboxReturnFocus = document.activeElement;
            if (typeof this.lightboxEl.showModal === 'function') {
                this.lightboxEl.showModal();
            } else {
                this.lightboxEl.setAttribute('open', '');
            }
            if (this.lightboxOpenBtn) {
                this.lightboxOpenBtn.setAttribute('aria-expanded', 'true');
            }
            const closeBtn = this.lightboxEl.querySelector('[data-reader-lightbox-close]');
            if (closeBtn) closeBtn.focus({ preventScroll: true });
        }

        closeLightbox() {
            if (!this.lightboxEl || !this.lightboxEl.open) return;
            if (typeof this.lightboxEl.close === 'function') {
                this.lightboxEl.close();
            } else {
                this.lightboxEl.removeAttribute('open');
            }
            if (this.lightboxOpenBtn) {
                this.lightboxOpenBtn.setAttribute('aria-expanded', 'false');
            }
            const back = this.lightboxReturnFocus || this.lightboxOpenBtn || this.stage;
            if (back && typeof back.focus === 'function') {
                back.focus({ preventScroll: true });
            }
            this.lightboxReturnFocus = null;
        }

        toggleLightbox() {
            if (this.isLightboxOpen()) this.closeLightbox();
            else this.openLightbox();
        }

        bindLightbox() {
            if (!this.lightboxEl) return;

            if (this.lightboxOpenBtn) {
                this.lightboxOpenBtn.addEventListener('click', () => this.openLightbox());
            }

            const closeBtn = this.lightboxEl.querySelector('[data-reader-lightbox-close]');
            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.closeLightbox();
                });
            }

            this.lightboxEl.addEventListener('click', (e) => {
                if (e.target === this.lightboxEl || e.target.tagName === 'IMG') {
                    this.closeLightbox();
                }
            });

            this.lightboxEl.addEventListener('cancel', (e) => {
                e.preventDefault();
                this.closeLightbox();
            });

            this.lightboxEl.addEventListener('close', () => {
                if (this.lightboxOpenBtn) {
                    this.lightboxOpenBtn.setAttribute('aria-expanded', 'false');
                }
            });
        }

        handleEscape() {
            if (this.isLightboxOpen()) {
                this.closeLightbox();
                return;
            }
            if (this.notesEl && this.notesEl.classList.contains('is-open')) {
                this.pulseControl('[data-reader-notes]');
                this.toggleNotes();
                return;
            }
            if (this.blackoutEl && !this.blackoutEl.hasAttribute('hidden')) {
                this.pulseControl('[data-reader-blackout]');
                this.toggleBlackout();
                return;
            }
            if (this.isFullscreen()) {
                this.pulseControl('[data-reader-fullscreen]');
                this.exitFullscreen();
                return;
            }
            const exit = document.querySelector('[data-reader-exit]');
            if (exit && exit.href) {
                this.pulseControl('[data-reader-exit]');
                window.location.href = exit.href;
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

            target.scrollIntoView({
                block: targetRect.height > this.stage.clientHeight * 0.8
                    ? 'start'
                    : 'center',
                inline: 'nearest',
                behavior: this.motionOk() ? 'smooth' : 'auto'
            });
        }

        syncRevealButton(remaining, statusMessage = '') {
            if (!this.revealBtn) return;

            const hasRemaining = Number(remaining) > 0;
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

            this.pulseControl('[data-reader-reveal]', 1200);
            if (this.revealBtn) {
                this.syncRevealButton(detail.remaining, message);
                this.revealBtn.classList.add('is-active');
                setTimeout(() => {
                    this.revealBtn.classList.remove('is-active');
                }, 1600);
            }
            this.bringQuizIntoContext(target);
        }

        handleQuizStateChanged(event) {
            const detail = event.detail || {};
            // Disponibilidade não é resultado: source='answer' nunca recebe
            // texto de "resposta revelada".
            this.syncRevealButton(detail.remaining);
        }

        bindQuizReveal() {
            if (this.revealBtn
                && !document.querySelector('.lesson-quiz--interactive .quiz-option')) {
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
        bindKeys() {
            window.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT'
                    || e.target.tagName === 'TEXTAREA'
                    || e.target.isContentEditable) {
                    return;
                }
                if (e.ctrlKey || e.metaKey || e.altKey) return;
                if (e.repeat && [
                    'Escape', 'b', 'B', 'n', 'N', 'c', 'C',
                    'f', 'F', 'r', 'R', '?'
                ].includes(e.key)) {
                    return;
                }
                const interactive = e.target.closest
                    && e.target.closest('button, a[href], select, [role="button"]');

                if (this.isLightboxOpen() && e.key !== 'Escape') {
                    return;
                }

                switch (e.key) {
                    case ' ':
                        // Espaço sobre um controle/opção ativa o próprio elemento.
                        if (interactive) return;
                        e.preventDefault();
                        this.pulseControl(
                            e.shiftKey ? '[data-reader-up]' : '[data-reader-down]'
                        );
                        this.scrollByScreen(e.shiftKey ? -1 : 1);
                        break;
                    case 'ArrowDown':
                    case 'PageDown':
                        if (interactive) return;
                        e.preventDefault();
                        this.pulseControl('[data-reader-down]');
                        this.scrollByScreen(1);
                        break;
                    case 'ArrowUp':
                    case 'PageUp':
                        if (interactive) return;
                        e.preventDefault();
                        this.pulseControl('[data-reader-up]');
                        this.scrollByScreen(-1);
                        break;
                    case 'Home':
                        if (interactive) return;
                        e.preventDefault();
                        this.pulseControl('[data-reader-up]');
                        this.scrollToEdge(0);
                        break;
                    case 'End':
                        if (interactive) return;
                        e.preventDefault();
                        this.pulseControl('[data-reader-down]');
                        this.scrollToEdge(this.stage.scrollHeight);
                        break;
                    case 'b':
                    case 'B':
                        this.pulseControl('[data-reader-blackout]');
                        this.toggleBlackout();
                        break;
                    case 'n':
                    case 'N':
                        this.pulseControl('[data-reader-notes]');
                        this.toggleNotes();
                        break;
                    case 'c':
                    case 'C':
                        if (this.lightboxEl) this.toggleLightbox();
                        break;
                    case 'f':
                    case 'F':
                        this.pulseControl('[data-reader-fullscreen]');
                        this.toggleFullscreen();
                        break;
                    case 'r':
                    case 'R':
                        if (this.revealBtn && !this.revealBtn.disabled) {
                            e.preventDefault();
                            this.pulseControl('[data-reader-reveal]');
                            this.revealQuiz('shortcut');
                        }
                        break;
                    case '?':
                        e.preventDefault();
                        this.showHelp();
                        break;
                    case 'Escape':
                        e.preventDefault();
                        this.handleEscape();
                        break;
                }
            });
        }

        bindControls() {
            const on = (selector, handler) => {
                const el = document.querySelector(selector);
                if (el) el.addEventListener('click', handler);
            };

            on('[data-reader-down]', () => this.scrollByScreen(1));
            on('[data-reader-up]', () => this.scrollByScreen(-1));
            on('[data-reader-blackout]', () => this.toggleBlackout());
            on('[data-reader-notes]', () => this.toggleNotes());
            on('[data-reader-notes-close]', () => this.toggleNotes());
            on('[data-reader-fullscreen]', () => this.toggleFullscreen());
            on('[data-reader-reveal]', () => this.revealQuiz('button'));

            if (this.blackoutEl) {
                this.blackoutEl.addEventListener('click', () => this.toggleBlackout());
            }
            const onFs = () => this.syncFullscreenButton();
            document.addEventListener('fullscreenchange', onFs);
            document.addEventListener('webkitfullscreenchange', onFs);
            this.syncFullscreenButton();
        }

        bindScroll() {
            this.stage.addEventListener('scroll', () => {
                if (this.progressScheduled) return;
                this.progressScheduled = true;
                requestAnimationFrame(() => {
                    this.progressScheduled = false;
                    this.updateProgress();
                });
            }, { passive: true });
            window.addEventListener('resize', () => this.updateProgress());
        }

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
            window.addEventListener('touchstart', resetIdle, { passive: true });
            this.stage.addEventListener('scroll', resetIdle, { passive: true });
            resetIdle();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new ProjectionReader());
    } else {
        new ProjectionReader();
    }
})();
