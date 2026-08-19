(function () {
    const root = document.documentElement;
    const storedTheme = localStorage.getItem('professordash-theme');

    if (storedTheme) {
        root.setAttribute('data-theme', storedTheme);
    }

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
        button.addEventListener('click', () => {
            const nextTheme = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', nextTheme);
            localStorage.setItem('professordash-theme', nextTheme);
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

    /* Zoom das figuras do corpo da aula.

       A arte do acervo é infográfico denso: no celular do aluno o texto
       interno fica ilegível. O controle é criado aqui, e não no parser,
       porque só existe onde o <dialog> realmente abre — em superfícies sem
       este script (modo apresentação) a figura fica estática, sem botão
       morto na tela. O rótulo acessível vive no botão "Ampliar"; a imagem
       nunca é embrulhada no botão para não perder o alt, que no acervo é a
       descrição pedagógica inteira. */
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

    if (window.lucide) {
        window.lucide.createIcons();
    }
}());
