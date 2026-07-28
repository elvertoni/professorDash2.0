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
            this.idleTimer = null;
            this.progressScheduled = false;

            this.init();
        }

        init() {
            this.bindKeys();
            this.bindControls();
            this.bindScroll();
            this.setupIdleDetection();
            this.updateProgress();
            this.stage.focus({ preventScroll: true });
            if (window.lucide) window.lucide.createIcons();
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
            } else {
                this.blackoutEl.setAttribute('hidden', '');
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

        handleEscape() {
            if (this.notesEl && this.notesEl.classList.contains('is-open')) {
                this.toggleNotes();
                return;
            }
            if (this.blackoutEl && !this.blackoutEl.hasAttribute('hidden')) {
                this.toggleBlackout();
                return;
            }
            if (this.isFullscreen()) {
                this.exitFullscreen();
                return;
            }
            const exit = document.querySelector('[data-reader-exit]');
            if (exit && exit.href) window.location.href = exit.href;
        }

        /* ── Eventos ─────────────────────────────────────────────────────── */
        bindKeys() {
            window.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT'
                    || e.target.tagName === 'TEXTAREA'
                    || e.target.isContentEditable) {
                    return;
                }
                const interactive = e.target.closest
                    && e.target.closest('button, a[href], select, [role="button"]');

                switch (e.key) {
                    case ' ':
                        // Espaço sobre um controle/opção ativa o próprio elemento.
                        if (interactive) return;
                        e.preventDefault();
                        this.scrollByScreen(e.shiftKey ? -1 : 1);
                        break;
                    case 'ArrowDown':
                    case 'PageDown':
                        e.preventDefault();
                        this.scrollByScreen(1);
                        break;
                    case 'ArrowUp':
                    case 'PageUp':
                        e.preventDefault();
                        this.scrollByScreen(-1);
                        break;
                    case 'Home':
                        e.preventDefault();
                        this.scrollToEdge(0);
                        break;
                    case 'End':
                        e.preventDefault();
                        this.scrollToEdge(this.stage.scrollHeight);
                        break;
                    case 'b':
                    case 'B':
                        this.toggleBlackout();
                        break;
                    case 'n':
                    case 'N':
                        this.toggleNotes();
                        break;
                    case 'f':
                    case 'F':
                        this.toggleFullscreen();
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
