(function () {
    const root = document.documentElement;
    const body = document.body;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    const storedTheme = localStorage.getItem('professordash-theme');

    if (storedTheme) {
        root.setAttribute('data-theme', storedTheme);
    }

    const setTheme = (theme) => {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('professordash-theme', theme);
    };

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
        button.addEventListener('click', () => {
            const nextTheme = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            if (document.startViewTransition && !reducedMotion.matches) {
                document.startViewTransition(() => setTheme(nextTheme));
            } else {
                setTheme(nextTheme);
            }
        });
    });

    document.querySelectorAll('[data-selected-url-target]').forEach((button) => {
        const select = document.getElementById(button.dataset.selectedUrlTarget);
        if (!select) return;

        button.addEventListener('click', () => {
            if (select.value) {
                window.location.href = select.value;
            }
        });
    });

    const scrollProgress = document.querySelector('.scroll-progress i');
    const header = document.querySelector('.site-header');
    let scrollFrame = null;

    const updateScrollState = () => {
        const scrollable = document.documentElement.scrollHeight - window.innerHeight;
        const progress = scrollable > 0 ? Math.min(window.scrollY / scrollable, 1) : 0;
        if (scrollProgress) {
            scrollProgress.style.transform = `scaleX(${progress})`;
        }
        if (header) {
            header.classList.toggle('is-scrolled', window.scrollY > 12);
        }
        scrollFrame = null;
    };

    const scheduleScrollState = () => {
        if (scrollFrame === null) {
            scrollFrame = window.requestAnimationFrame(updateScrollState);
        }
    };

    window.addEventListener('scroll', scheduleScrollState, { passive: true });
    window.addEventListener('resize', scheduleScrollState, { passive: true });
    updateScrollState();

    /* A luz do ateliê segue a mão apenas em superfícies com ponteiro fino.
       Um único listener global alimenta o shell; não há trabalho de layout
       por movimento e o mobile permanece completamente estático. */
    if (finePointer.matches && !reducedMotion.matches) {
        let pointerFrame = null;
        let pointer = { x: 0, y: 0 };
        window.addEventListener('pointermove', (event) => {
            pointer = { x: event.clientX, y: event.clientY };
            if (pointerFrame !== null) return;
            pointerFrame = window.requestAnimationFrame(() => {
                root.style.setProperty('--cursor-x', `${pointer.x}px`);
                root.style.setProperty('--cursor-y', `${pointer.y}px`);
                pointerFrame = null;
            });
        }, { passive: true });
    }

    const revealTargets = Array.from(new Set(document.querySelectorAll([
        '#conteudo > section',
        '.section-heading',
        '.page-hero',
        '.classroom-header',
        '.kpi',
        '.card',
        '.action-panel',
        '.tbl-wrap',
        '.empty',
        '.journey-step',
        '.dash-collapsible',
        '.atelier',
        '.lesson-nav',
        '.lesson-actionbar',
    ].join(','))));

    const revealAll = () => {
        revealTargets.forEach((element) => {
            element.dataset.motionState = 'in';
        });
    };

    if (!reducedMotion.matches && 'IntersectionObserver' in window) {
        revealTargets.forEach((element, index) => {
            element.dataset.motion = index % 3 === 1 ? 'shift' : 'rise';
            element.dataset.motionState = 'before';
            element.style.setProperty('--motion-order', String(index % 4));
        });

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.dataset.motionState = 'in';
                observer.unobserve(entry.target);
            });
        }, {
            rootMargin: '0px 0px -8% 0px',
            threshold: 0.06,
        });

        window.requestAnimationFrame(() => {
            root.classList.add('motion-ready');
            revealTargets.forEach((element) => observer.observe(element));
        });

        window.setTimeout(revealAll, 2200);
    } else {
        revealAll();
    }

    document.querySelectorAll('.progress i').forEach((bar) => {
        bar.classList.add('progress-fill');
    });

    if (finePointer.matches && !reducedMotion.matches) {
        document.querySelectorAll('.card, .kpi, .action-panel, .journey-step').forEach((surface) => {
            let pointerFrame = null;
            let point = { x: 0, y: 0 };

            surface.addEventListener('pointermove', (event) => {
                const bounds = surface.getBoundingClientRect();
                point = {
                    x: event.clientX - bounds.left,
                    y: event.clientY - bounds.top,
                };
                if (pointerFrame !== null) return;
                pointerFrame = window.requestAnimationFrame(() => {
                    surface.style.setProperty('--pointer-x', `${point.x}px`);
                    surface.style.setProperty('--pointer-y', `${point.y}px`);
                    surface.classList.add('has-pointer');
                    pointerFrame = null;
                });
            }, { passive: true });

            surface.addEventListener('pointerleave', () => {
                surface.classList.remove('has-pointer');
            });
        });
    }

    /* Menus nativos ganham uma classe de estado para que o CSS possa
       desenhar entrada/saída sem depender de um framework de componentes. */
    document.querySelectorAll('details').forEach((details) => {
        details.addEventListener('toggle', () => {
            details.classList.toggle('is-open', details.open);
        });
    });

    const lessonFigures = document.querySelectorAll(
        '.lesson-figure:not(.lesson-figure--missing)'
    );
    const dialogSupported = typeof HTMLDialogElement === 'function'
        && typeof HTMLDialogElement.prototype.showModal === 'function';

    if (lessonFigures.length && dialogSupported) {
        let lightbox = null;
        let lightboxImage = null;
        let lastTrigger = null;

        const ensureLightbox = () => {
            if (lightbox) return lightbox;

            lightbox = document.createElement('dialog');
            lightbox.className = 'lesson-lightbox lesson-figure-lightbox';
            lightbox.setAttribute('aria-label', 'Figura ampliada');

            const closeButton = document.createElement('button');
            closeButton.type = 'button';
            closeButton.className = 'lesson-lightbox-close';
            closeButton.setAttribute('aria-label', 'Fechar figura ampliada');
            closeButton.innerHTML = '&times;';
            closeButton.addEventListener('click', () => lightbox.close());

            lightboxImage = document.createElement('img');

            lightbox.append(closeButton, lightboxImage);
            lightbox.addEventListener('click', (event) => {
                if (event.target === lightbox) lightbox.close();
            });
            lightbox.addEventListener('close', () => {
                if (lastTrigger) lastTrigger.focus();
            });
            document.body.appendChild(lightbox);
            return lightbox;
        };

        lessonFigures.forEach((figure) => {
            const frame = figure.querySelector('.lesson-figure-frame');
            const image = figure.querySelector('.lesson-figure-img');
            if (!frame || !image) return;

            let caption = figure.querySelector('.lesson-figure-caption');
            if (!caption) {
                caption = document.createElement('figcaption');
                caption.className = 'lesson-figure-caption';
                figure.appendChild(caption);
            }

            const zoomButton = document.createElement('button');
            zoomButton.type = 'button';
            zoomButton.className = 'lesson-figure-zoom';
            zoomButton.innerHTML =
                '<i data-lucide="maximize-2" aria-hidden="true"></i>Ampliar';
            caption.appendChild(zoomButton);

            const open = (trigger) => {
                ensureLightbox();
                lightboxImage.src = image.currentSrc || image.src;
                lightboxImage.alt = image.alt;
                lastTrigger = trigger;
                lightbox.showModal();
            };

            zoomButton.addEventListener('click', () => open(zoomButton));
            frame.classList.add('is-zoomable');
            frame.addEventListener('click', () => open(zoomButton));
        });
    }

    body.classList.add('ui-ready');

    if (window.lucide) {
        window.lucide.createIcons();
    }
}());
