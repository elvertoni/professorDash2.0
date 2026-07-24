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
    const DEFAULT_SCALE_FLOOR = 0.88;
    const SCALE_PRECISION = 1000;
    const MEASURE_TOLERANCE = 1;
    const SPARSE_HEIGHT_RATIO = 0.38;
    const SPARSE_CENTER_RATIO = 0.6;
    const AUDIT_EMPTY_OCCUPANCY = 35;
    const AUDIT_EMPTY_EXEMPT = Object.freeze([COVER, END, MEDIA, QUIZ, CALLOUT, TABLE, CODE]);
    const ATOMIC_TYPES = Object.freeze([CALLOUT, MEDIA, QUIZ, TABLE, CODE]);

    class AtelierDeck {
        constructor() {
            this.body = document.body;
            this.stage = document.getElementById('deck-stage');
            this.source = document.getElementById('deck-source');
            this.fallback = document.getElementById('deck-fallback');
            this.measurementStage = null;

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
            this.liveEl = document.querySelector('[data-deck-live]');
            this.blackoutEl = document.getElementById('deck-blackout');
            this.overviewDialog = document.getElementById('deck-overview');
            this.overviewGrid = document.querySelector('[data-deck-overview-grid]');
            this.spotlightCanvas = document.getElementById('deck-spotlight');

            // Estado interno
            this.notesMap = {};
            this.railButtons = [];
            this.specs = Object.freeze([]);

            // Modo de auditoria visual (?test=true).
            this.testMode = new URLSearchParams(window.location.search).get('test') === 'true';
            this.testErrors = [];
            if (this.testMode) {
                window.addEventListener('error', (e) => {
                    this.testErrors.push(e.message || String(e.error || 'erro'));
                });
            }
            this.slides = []; // Array de { el, title, notesHTML, builds: [] }
            this.scaleFloor = DEFAULT_SCALE_FLOOR;
            this.currentIndex = 0;
            this.currentBuildIndex = -1;
            this.isLaserActive = false;
            this.laserTrail = [];
            this.idleTimer = null;

            this.initializeDeck();
        }

        async initializeDeck() {
            this.showFallback();

            try {
                if (!this.stage || !this.source) {
                    throw new Error('Palco ou fonte da aula não encontrado.');
                }

                this.createMeasurementStage();
                await this.waitForAssets();

                this.notesMap = this.parseNotesData();
                const specs = this.buildSpecs();
                this.specs = this.paginateSpecs(specs);
                this.renderDeck(this.specs);
                this.buildRail();
                this.bindEvents();
                this.initSpotlightCanvas();
                this.setupIdleDetection();
                this.setupResizeObserver();
                this.goToSlide(0);

                this.hideFallback();
                this.body.classList.remove('is-deck-loading');

                // Sucesso: remove a fonte original para evitar IDs duplicados e
                // dupla inicialização de Alpine/quiz sobre o conteúdo clonado.
                if (this.source && this.source.parentNode) {
                    this.source.remove();
                }

                if (this.testMode) {
                    // Aguarda um frame para o layout do slide ativo assentar.
                    requestAnimationFrame(() => this.runIntegratedTests());
                }
            } catch (error) {
                this.restoreFallback(error);
            }
        }

        showFallback() {
            if (!this.fallback) return;
            this.fallback.hidden = false;
            this.fallback.style.setProperty('display', 'block', 'important');
        }

        hideFallback() {
            if (!this.fallback) return;
            this.fallback.hidden = true;
            this.fallback.style.setProperty('display', 'none', 'important');
        }

        restoreFallback(error) {
            console.error('[AtelierDeck] Falha ao preparar a apresentação.', error);
            this.teardownResizeObserver();
            if (this.stage) this.stage.innerHTML = '';
            this.body.classList.remove('is-deck-loading');
            this.body.classList.add('is-deck-failed');
            this.body.style.overflow = 'auto';
            this.body.style.userSelect = 'text';
            this.showFallback();
        }

        async waitForAssets() {
            const assetPromises = [];

            if (document.fonts && document.fonts.ready) {
                assetPromises.push(document.fonts.ready);
            }

            const images = new Set(document.querySelectorAll('img'));
            document.querySelectorAll('template').forEach((template) => {
                template.content.querySelectorAll('img').forEach((image) => images.add(image));
            });
            images.forEach((image) => {
                if (typeof image.decode === 'function') {
                    assetPromises.push(Promise.resolve().then(() => image.decode()));
                }
            });

            await Promise.allSettled(assetPromises);
        }

        createMeasurementStage() {
            if (this.measurementStage) return this.measurementStage;

            const measurementStage = document.createElement('div');
            measurementStage.className = 'deck-stage deck-stage--measure';
            measurementStage.setAttribute('aria-hidden', 'true');
            measurementStage.setAttribute('inert', '');
            measurementStage.style.visibility = 'hidden';
            measurementStage.style.pointerEvents = 'none';
            measurementStage.style.zIndex = '-1';
            this.body.appendChild(measurementStage);
            this.measurementStage = measurementStage;
            return measurementStage;
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

        createSpec(data) {
            const segments = Array.from(data.segments || []).map((segment) => Object.freeze({
                type: segment.type,
                heading: segment.heading || '',
                blocks: Object.freeze(Array.from(segment.blocks || []))
            }));

            return Object.freeze({
                semanticKey: data.semanticKey,
                originSemanticKey: data.originSemanticKey || data.semanticKey,
                sectionIndex: Number.isInteger(data.sectionIndex) ? data.sectionIndex : null,
                subIndex: Number.isInteger(data.subIndex) ? data.subIndex : null,
                section: data.section || '',
                sub: data.sub || '',
                type: data.type,
                blocks: Object.freeze(Array.from(data.blocks || [])),
                segments: Object.freeze(segments),
                continuation: Boolean(data.continuation),
                heading: data.heading || '',
                eyebrow: data.eyebrow || '',
                title: data.title || 'Conteúdo',
                node: data.node || null,
                scale: Number.isFinite(data.scale) ? data.scale : 1,
                requiredScale: Number.isFinite(data.requiredScale) ? data.requiredScale : 1,
                heightRatio: Number.isFinite(data.heightRatio) ? data.heightRatio : 0,
                widthRatio: Number.isFinite(data.widthRatio) ? data.widthRatio : 0,
                scrollable: Boolean(data.scrollable),
                overflowing: Boolean(data.overflowing),
                sparse: Boolean(data.sparse),
                scrollMaxHeight: Number.isFinite(data.scrollMaxHeight) ? data.scrollMaxHeight : null,
                scrollMaxWidth: Number.isFinite(data.scrollMaxWidth) ? data.scrollMaxWidth : null
            });
        }

        copySpec(spec, overrides = {}) {
            return this.createSpec({
                ...spec,
                blocks: spec.blocks,
                segments: spec.segments,
                ...overrides
            });
        }

        buildSpecs() {
            const specs = [];
            let currentSection = '';
            let currentSub = '';
            let sectionIndex = 0;
            let subIndex = 0;
            let blockOrdinal = 0;
            let currentSegment = null;

            const semanticKey = (ordinal) => (
                `section-${sectionIndex}-sub-${subIndex}-block-${ordinal}`
            );

            const flushSegment = () => {
                if (!currentSegment) return;
                specs.push(this.createSpec(currentSegment));
                currentSegment = null;
            };

            // 1. Cover Slide Spec
            const coverNode = this.fromTemplate('deck-cover');
            if (coverNode) {
                specs.push(this.createSpec({
                    semanticKey: 'cover',
                    sectionIndex: 0,
                    subIndex: 0,
                    type: COVER,
                    node: coverNode,
                    title: 'Capa'
                }));
            }

            // 2. Fatiar o HTML da aula
            const blocks = Array.from(this.source.children);

            blocks.forEach((node) => {
                const type = this.classifyBlock(node);

                if (type === 'h2') {
                    flushSegment();
                    currentSection = node.textContent.trim();
                    currentSub = '';
                    sectionIndex += 1;
                    subIndex = 0;
                    blockOrdinal = 0;
                    return;
                }
                if (type === 'h3') {
                    flushSegment();
                    currentSub = node.textContent.trim();
                    subIndex += 1;
                    blockOrdinal = 0;
                    return;
                }

                // Blocos pesados ganham slides próprios
                if ([CALLOUT, QUIZ, TABLE, CODE, MEDIA].includes(type)) {
                    flushSegment();
                    specs.push(this.createSpec({
                        semanticKey: semanticKey(blockOrdinal),
                        sectionIndex: sectionIndex,
                        subIndex: subIndex,
                        type: type,
                        section: currentSection,
                        sub: currentSub,
                        heading: '',
                        eyebrow: currentSub || currentSection || '',
                        blocks: [node.cloneNode(true)],
                        title: currentSub || currentSection || 'Destaque'
                    }));
                    blockOrdinal += 1;
                    return;
                }

                // Cada mudança de fluxo inicia um segmento próprio.
                const flowType = type === STEPS ? STEPS : (type === POINT ? POINT : PROSE);
                if (!currentSegment || currentSegment.type !== flowType) {
                    flushSegment();
                    currentSegment = {
                        semanticKey: semanticKey(blockOrdinal),
                        sectionIndex: sectionIndex,
                        subIndex: subIndex,
                        type: flowType,
                        section: currentSection,
                        sub: currentSub,
                        heading: currentSub || currentSection || '',
                        eyebrow: (currentSub && currentSection) ? currentSection : '',
                        blocks: [],
                        title: currentSub || currentSection || 'Conteúdo'
                    };
                }
                currentSegment.blocks.push(node.cloneNode(true));
                blockOrdinal += 1;
            });
            flushSegment();

            // 3. End Slide Spec
            const endNode = this.fromTemplate('deck-end');
            if (endNode) {
                specs.push(this.createSpec({
                    semanticKey: 'end',
                    sectionIndex: sectionIndex + 1,
                    subIndex: 0,
                    type: END,
                    node: endNode,
                    title: 'Encerramento'
                }));
            }

            return Object.freeze(specs);
        }

        paginateSpecs(specs) {
            this.scaleFloor = this.readScaleFloor();
            const fittedSpecs = [];

            specs.forEach((spec) => {
                const measurement = this.measureSpec(spec);

                if (measurement.fitsAtFullScale || measurement.requiredScale >= this.scaleFloor) {
                    fittedSpecs.push(this.createFittedSpec(spec, measurement));
                    return;
                }

                if (this.isAtomicSpec(spec) || !this.isSplittableSpec(spec)) {
                    fittedSpecs.push(this.createFittedSpec(spec, measurement, true));
                    return;
                }

                fittedSpecs.push(...this.paginateOverflowingSpec(spec));
            });

            return Object.freeze(this.mergeSparseSubsections(fittedSpecs));
        }

        readScaleFloor() {
            const cssValue = window.getComputedStyle(this.body)
                .getPropertyValue('--deck-scale-floor');
            const floor = Number.parseFloat(cssValue);
            if (!Number.isFinite(floor) || floor <= 0 || floor > 1) {
                return DEFAULT_SCALE_FLOOR;
            }
            return floor;
        }

        roundScale(scale) {
            const bounded = Math.min(1, Math.max(this.scaleFloor, scale));
            return Math.floor((bounded + Number.EPSILON) * SCALE_PRECISION) / SCALE_PRECISION;
        }

        measureContentExtent(container) {
            const containerRect = container.getBoundingClientRect();
            let width = Math.max(1, container.scrollWidth);
            let height = Math.max(1, container.scrollHeight);

            container.querySelectorAll('*').forEach((element) => {
                const style = window.getComputedStyle(element);
                if (style.position === 'fixed' || style.position === 'absolute') return;

                const rect = element.getBoundingClientRect();
                const offsetX = Math.max(0, rect.left - containerRect.left);
                const offsetY = Math.max(0, rect.top - containerRect.top);
                width = Math.max(width, offsetX + element.scrollWidth);
                height = Math.max(height, offsetY + element.scrollHeight);
            });

            return Object.freeze({ width: width, height: height });
        }

        measureSpec(spec) {
            if (!this.measurementStage) {
                throw new Error('Palco de medição não encontrado.');
            }

            this.measurementStage.innerHTML = '';

            try {
                const rendered = this.renderSlideSpec(spec, -1, {
                    targetStage: this.measurementStage,
                    measurement: true
                });
                const slide = rendered.el;
                const inner = rendered.inner;
                const slideStyle = window.getComputedStyle(slide);
                const horizontalPadding = (
                    Number.parseFloat(slideStyle.paddingLeft)
                    + Number.parseFloat(slideStyle.paddingRight)
                );
                const verticalPadding = (
                    Number.parseFloat(slideStyle.paddingTop)
                    + Number.parseFloat(slideStyle.paddingBottom)
                );
                const stageWidth = Math.max(1, slide.clientWidth - horizontalPadding);
                const stageHeight = Math.max(1, slide.clientHeight - verticalPadding);
                const availableWidth = Math.max(
                    1,
                    Math.min(stageWidth, inner.clientWidth || stageWidth)
                );
                const availableHeight = stageHeight;
                const contentExtent = this.measureContentExtent(inner);
                const contentWidth = contentExtent.width;
                const contentHeight = contentExtent.height;
                const scrollTarget = inner.querySelector('.deck-prose-body');
                const scrollTargetHeight = scrollTarget
                    ? this.measureContentExtent(scrollTarget).height
                    : contentHeight;
                const fixedContentHeight = Math.max(0, contentHeight - scrollTargetHeight);
                const widthRatio = contentWidth / availableWidth;
                const heightRatio = contentHeight / availableHeight;
                const fitsWidth = contentWidth <= availableWidth + MEASURE_TOLERANCE;
                const fitsHeight = contentHeight <= availableHeight + MEASURE_TOLERANCE;
                const requiredScale = Math.min(
                    1,
                    availableWidth / contentWidth,
                    availableHeight / contentHeight
                );

                return Object.freeze({
                    availableWidth: availableWidth,
                    availableHeight: availableHeight,
                    contentWidth: contentWidth,
                    contentHeight: contentHeight,
                    fixedContentHeight: fixedContentHeight,
                    widthRatio: widthRatio,
                    heightRatio: heightRatio,
                    fitsAtFullScale: fitsWidth && fitsHeight,
                    requiredScale: requiredScale
                });
            } finally {
                this.measurementStage.innerHTML = '';
            }
        }

        createFittedSpec(spec, measurement, forceScroll = false) {
            const fitsAtFullScale = measurement.fitsAtFullScale;
            const fitsAtFloor = measurement.requiredScale >= this.scaleFloor;
            const scrollable = forceScroll && !fitsAtFullScale && !fitsAtFloor;
            const scale = fitsAtFullScale
                ? 1
                : this.roundScale(fitsAtFloor ? measurement.requiredScale : this.scaleFloor);
            const sparse = scale === 1
                && !scrollable
                && spec.type !== COVER
                && spec.type !== END
                && measurement.heightRatio <= SPARSE_CENTER_RATIO;

            return this.copySpec(spec, {
                scale: scale,
                sparse: sparse,
                requiredScale: measurement.requiredScale,
                heightRatio: measurement.heightRatio,
                widthRatio: measurement.widthRatio,
                scrollable: scrollable,
                overflowing: scrollable,
                scrollMaxHeight: scrollable
                    ? Math.max(
                        1,
                        Math.floor(
                            (measurement.availableHeight / this.scaleFloor)
                            - measurement.fixedContentHeight
                        )
                    )
                    : null,
                scrollMaxWidth: scrollable
                    ? Math.floor(measurement.availableWidth / this.scaleFloor)
                    : null
            });
        }

        isAtomicSpec(spec) {
            return ATOMIC_TYPES.includes(spec.type);
        }

        isSplittableSpec(spec) {
            return [PROSE, POINT, STEPS].includes(spec.type) && spec.blocks.length > 0;
        }

        fitsAtFloor(measurement) {
            return (
                measurement.fitsAtFullScale
                || measurement.requiredScale + Number.EPSILON >= this.scaleFloor
            );
        }

        createPaginationUnits(spec) {
            if (spec.type === PROSE) {
                return spec.blocks.map((block, index) => ({
                    kind: 'block',
                    id: `block-${index}`,
                    node: block
                }));
            }

            const units = [];
            spec.blocks.forEach((block, blockIndex) => {
                if (block.tagName === 'UL' || block.tagName === 'OL') {
                    const baseStart = block.tagName === 'OL'
                        ? Number.parseInt(block.getAttribute('start') || '1', 10)
                        : 1;
                    Array.from(block.children).forEach((item, itemIndex) => {
                        units.push({
                            kind: 'list-item',
                            id: `list-${blockIndex}`,
                            node: item,
                            listRoot: block,
                            baseStart: Number.isFinite(baseStart) ? baseStart : 1,
                            itemIndex: itemIndex
                        });
                    });
                    return;
                }

                units.push({
                    kind: 'list-item',
                    id: `list-${blockIndex}`,
                    node: block,
                    listRoot: null,
                    baseStart: 1,
                    itemIndex: 0
                });
            });
            return units;
        }

        buildBlocksFromUnits(spec, units) {
            if (spec.type === PROSE) {
                return units.map(unit => unit.node.cloneNode(true));
            }

            const blocks = [];
            let activeList = null;
            let activeListId = null;

            units.forEach((unit) => {
                if (unit.id !== activeListId) {
                    activeList = unit.listRoot
                        ? unit.listRoot.cloneNode(false)
                        : document.createElement(spec.type === STEPS ? 'ol' : 'ul');
                    if (activeList.tagName === 'OL') {
                        activeList.setAttribute('start', String(unit.baseStart + unit.itemIndex));
                    }
                    blocks.push(activeList);
                    activeListId = unit.id;
                }

                const item = unit.node.tagName === 'LI'
                    ? unit.node.cloneNode(true)
                    : document.createElement('li');
                if (unit.node.tagName !== 'LI') {
                    item.appendChild(unit.node.cloneNode(true));
                }
                activeList.appendChild(item);
            });

            return blocks;
        }

        createContinuationSpec(spec, units, pageIndex) {
            const originSemanticKey = spec.originSemanticKey || spec.semanticKey;
            const semanticKey = pageIndex === 0
                ? spec.semanticKey
                : `${originSemanticKey}-cont-${pageIndex}`;

            return this.createSpec({
                semanticKey: semanticKey,
                originSemanticKey: originSemanticKey,
                sectionIndex: spec.sectionIndex,
                subIndex: spec.subIndex,
                section: spec.section,
                sub: spec.sub,
                type: spec.type,
                blocks: this.buildBlocksFromUnits(spec, units),
                continuation: spec.continuation || pageIndex > 0,
                heading: spec.heading,
                eyebrow: spec.eyebrow,
                title: spec.title
            });
        }

        paginateOverflowingSpec(spec) {
            const units = this.createPaginationUnits(spec);
            if (units.length === 0) {
                return [this.createFittedSpec(spec, this.measureSpec(spec), true)];
            }

            const pages = [];
            let currentUnits = [];

            units.forEach((unit) => {
                const candidateUnits = [...currentUnits, unit];
                const candidate = this.createContinuationSpec(
                    spec,
                    candidateUnits,
                    pages.length
                );
                const measurement = this.measureSpec(candidate);

                if (currentUnits.length > 0 && !this.fitsAtFloor(measurement)) {
                    pages.push(currentUnits);
                    currentUnits = [unit];
                    return;
                }

                currentUnits = candidateUnits;
            });

            if (currentUnits.length > 0) {
                pages.push(currentUnits);
            }

            return pages.map((pageUnits, pageIndex) => {
                const pageSpec = this.createContinuationSpec(spec, pageUnits, pageIndex);
                const measurement = this.measureSpec(pageSpec);
                return this.createFittedSpec(
                    pageSpec,
                    measurement,
                    !this.fitsAtFloor(measurement)
                );
            });
        }

        isSparseSubsection(specs, index) {
            const spec = specs[index];
            if (
                !spec
                || spec.continuation
                || !spec.section
                || !spec.sub
                || ![PROSE, POINT, STEPS].includes(spec.type)
                || spec.scrollable
                || spec.scale !== 1
                || spec.heightRatio > SPARSE_HEIGHT_RATIO
            ) {
                return false;
            }

            const sharesSubsection = (candidate) => (
                candidate
                && candidate.sectionIndex === spec.sectionIndex
                && candidate.subIndex === spec.subIndex
            );
            return !sharesSubsection(specs[index - 1]) && !sharesSubsection(specs[index + 1]);
        }

        createMergedSubsectionSpec(specs) {
            const first = specs[0];
            const last = specs[specs.length - 1];
            return this.createSpec({
                semanticKey: `${first.semanticKey}-merge-${last.semanticKey}`,
                originSemanticKey: first.originSemanticKey,
                sectionIndex: first.sectionIndex,
                subIndex: first.subIndex,
                section: first.section,
                sub: first.sub,
                type: PROSE,
                blocks: specs.flatMap(spec => spec.blocks),
                segments: specs.map((spec) => ({
                    type: spec.type,
                    heading: spec.heading,
                    blocks: spec.blocks
                })),
                heading: '',
                eyebrow: first.section,
                title: first.section
            });
        }

        mergeSparseSubsections(specs) {
            const merged = [];
            let index = 0;

            while (index < specs.length) {
                const first = specs[index];
                if (!this.isSparseSubsection(specs, index)) {
                    merged.push(first);
                    index += 1;
                    continue;
                }

                const group = [first];
                let nextIndex = index + 1;

                while (nextIndex < specs.length) {
                    const candidate = specs[nextIndex];
                    if (
                        !this.isSparseSubsection(specs, nextIndex)
                        || candidate.sectionIndex !== first.sectionIndex
                        || candidate.subIndex === group[group.length - 1].subIndex
                    ) {
                        break;
                    }

                    const candidateGroup = [...group, candidate];
                    const candidateSpec = this.createMergedSubsectionSpec(candidateGroup);
                    if (!this.fitsAtFloor(this.measureSpec(candidateSpec))) {
                        break;
                    }

                    group.push(candidate);
                    nextIndex += 1;
                }

                if (group.length === 1) {
                    merged.push(first);
                    index += 1;
                    continue;
                }

                const mergedSpec = this.createMergedSubsectionSpec(group);
                merged.push(this.createFittedSpec(mergedSpec, this.measureSpec(mergedSpec)));
                index += group.length;
            }

            return merged;
        }

        renderDeck(specs) {
            this.stage.innerHTML = '';
            this.slides = specs.map((spec, index) => this.renderSlideSpec(spec, index));
            if (this.totalCounterEl) {
                this.totalCounterEl.textContent = String(this.slides.length);
            }

            // Re-inicializar Lucide icons nos slides renderizados
            if (window.lucide) {
                window.lucide.createIcons();
            }
        }

        fromTemplate(id) {
            const tpl = document.getElementById(id);
            if (!tpl) return null;
            return tpl.content.cloneNode(true);
        }

        appendSlideHeading(container, text) {
            if (!text) return;
            const heading = document.createElement('h2');
            heading.className = 'deck-heading';
            heading.textContent = text;
            container.appendChild(heading);
        }

        appendListItem(list, node, builds) {
            const item = node.tagName === 'LI'
                ? node.cloneNode(true)
                : document.createElement('li');
            if (node.tagName !== 'LI') {
                item.appendChild(node.cloneNode(true));
            }
            item.classList.add('deck-build');
            list.appendChild(item);
            builds.push(item);
        }

        prepareDeckList(list) {
            const isOrdered = list.tagName === 'OL';
            list.classList.add(isOrdered ? 'deck-steps' : 'deck-points');
            if (isOrdered) {
                const start = Number.parseInt(list.getAttribute('start') || '1', 10);
                list.style.setProperty(
                    '--deck-list-start',
                    String((Number.isFinite(start) ? start : 1) - 1)
                );
            }
            return list;
        }

        appendFlowContent(container, content, builds, scrollable = false) {
            if (content.type === POINT || content.type === STEPS) {
                let fallbackList = null;

                content.blocks.forEach((block) => {
                    if (block.tagName === 'UL' || block.tagName === 'OL') {
                        const list = this.prepareDeckList(block.cloneNode(false));
                        if (scrollable) {
                            list.classList.add('is-scrollable');
                            list.tabIndex = 0;
                            list.setAttribute('role', 'region');
                            list.setAttribute('aria-label', 'Conteúdo extenso do slide');
                        }
                        Array.from(block.children).forEach((item) => {
                            this.appendListItem(list, item, builds);
                        });
                        container.appendChild(list);
                        fallbackList = null;
                        return;
                    }

                    if (!fallbackList) {
                        fallbackList = this.prepareDeckList(
                            document.createElement(content.type === STEPS ? 'ol' : 'ul')
                        );
                        if (scrollable) {
                            fallbackList.classList.add('is-scrollable');
                            fallbackList.tabIndex = 0;
                            fallbackList.setAttribute('role', 'region');
                            fallbackList.setAttribute('aria-label', 'Conteúdo extenso do slide');
                        }
                        container.appendChild(fallbackList);
                    }
                    this.appendListItem(fallbackList, block, builds);
                });
                return;
            }

            const bodyWrap = document.createElement('div');
            bodyWrap.className = 'deck-prose-body';
            if (scrollable) {
                bodyWrap.classList.add('is-scrollable');
                bodyWrap.tabIndex = 0;
                bodyWrap.setAttribute('role', 'region');
                bodyWrap.setAttribute('aria-label', 'Conteúdo extenso do slide');
            }
            content.blocks.forEach(block => bodyWrap.appendChild(block.cloneNode(true)));
            container.appendChild(bodyWrap);
        }

        renderSlideSpec(spec, index, options = {}) {
            const targetStage = options.targetStage || this.stage;
            const isMeasurement = Boolean(options.measurement);
            const scale = isMeasurement ? 1 : spec.scale;
            const sec = document.createElement('section');
            sec.className = `deck-slide deck-slide--${spec.type}`;
            sec.dataset.index = String(index);
            sec.dataset.semanticKey = spec.semanticKey;
            if (!isMeasurement) {
                sec.setAttribute('role', 'group');
                sec.setAttribute('aria-roledescription', 'slide');
                sec.setAttribute('aria-label', spec.title);
            }
            const noteKey = this.noteKeyForSpec(spec);
            if (!isMeasurement && spec.overflowing) {
                sec.classList.add('is-overflowing');
            }
            if (!isMeasurement && spec.sparse) {
                sec.classList.add('is-sparse');
            }

            const inner = document.createElement('div');
            inner.className = 'deck-slide-inner';
            inner.style.setProperty('--slide-scale', String(scale));
            if (!isMeasurement && spec.scrollMaxHeight) {
                inner.style.setProperty('--deck-scroll-max-height', `${spec.scrollMaxHeight}px`);
            }
            if (!isMeasurement && spec.scrollMaxWidth) {
                inner.style.setProperty('--deck-scroll-max-width', `${spec.scrollMaxWidth}px`);
            }

            const builds = [];

            if (spec.type === COVER || spec.type === END) {
                inner.appendChild(spec.node.cloneNode(true));
                if (!isMeasurement && spec.scrollable) {
                    inner.classList.add('is-scrollable');
                    inner.tabIndex = 0;
                    inner.setAttribute('role', 'region');
                    inner.setAttribute('aria-label', 'Conteúdo extenso do slide');
                }
                sec.appendChild(inner);
                targetStage.appendChild(sec);
                return {
                    el: sec,
                    inner: inner,
                    semanticKey: spec.semanticKey,
                    title: spec.title,
                    builds: builds,
                    scale: scale,
                    noteKey: noteKey,
                    builtScrollable: !isMeasurement && Boolean(spec.scrollable),
                    fitSignature: `${scale}:${!isMeasurement && Boolean(spec.scrollable)}`
                };
            }

            if (spec.eyebrow) {
                const eb = document.createElement('span');
                eb.className = 'deck-eyebrow-section';
                eb.textContent = spec.eyebrow;
                inner.appendChild(eb);
            }

            if (spec.segments.length > 0) {
                spec.segments.forEach((segment) => {
                    const segmentWrap = document.createElement('div');
                    segmentWrap.className = 'deck-slide-segment';
                    this.appendSlideHeading(segmentWrap, segment.heading);
                    this.appendFlowContent(segmentWrap, segment, builds);
                    inner.appendChild(segmentWrap);
                });
            } else {
                this.appendSlideHeading(inner, spec.heading);
                this.appendFlowContent(
                    inner,
                    spec,
                    builds,
                    !isMeasurement && spec.scrollable
                );
            }

            sec.appendChild(inner);
            targetStage.appendChild(sec);

            return {
                el: sec,
                inner: inner,
                semanticKey: spec.semanticKey,
                title: spec.title,
                builds: builds,
                scale: scale,
                noteKey: noteKey,
                builtScrollable: !isMeasurement && Boolean(spec.scrollable),
                fitSignature: `${scale}:${!isMeasurement && Boolean(spec.scrollable)}`
            };
        }

        applySlideScale(slide) {
            if (!slide || !slide.inner) return;
            slide.inner.style.setProperty('--slide-scale', String(slide.scale));
        }

        /* ── FASE 4: Roteiro docente, trilho e anúncios ──────────────────── */
        parseNotesData() {
            const el = document.getElementById('deck-notes-data');
            if (!el) return {};
            try {
                return JSON.parse(el.textContent || '{}') || {};
            } catch (error) {
                console.warn('[AtelierDeck] Roteiro docente inválido.', error);
                return {};
            }
        }

        normalizeHeadingKey(text) {
            return (text || '').replace(/\s+/g, ' ').trim().toLowerCase();
        }

        noteKeyForSpec(spec) {
            if (spec.type === END) return null;
            if (spec.type === COVER) return '';
            return this.normalizeHeadingKey(spec.sub || spec.section || '');
        }

        buildRail() {
            if (!this.railEl) return;
            this.railEl.innerHTML = '';
            this.railButtons = this.slides.map((slide, index) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'deck-rail-dot';
                btn.setAttribute('aria-label', `Ir para o slide ${index + 1}: ${slide.title}`);
                btn.addEventListener('click', () => this.goToSlide(index));
                this.railEl.appendChild(btn);
                return btn;
            });
        }

        /* ── FASE 3: Refit dinâmico (resize, quiz-reveal, fullscreen) ─────── */
        setupResizeObserver() {
            if (!window.ResizeObserver) return;

            this.resizeObserver = new ResizeObserver(() => this.scheduleRefit());
            this.resizeObserver.observe(this.stage);

            // Fullscreen muda a geometria do palco sem disparar resize de layout.
            this.onFullscreenChange = () => this.scheduleRefit();
            document.addEventListener('fullscreenchange', this.onFullscreenChange);
        }

        teardownResizeObserver() {
            if (this.resizeObserver) {
                this.resizeObserver.disconnect();
                this.resizeObserver = null;
            }
            this.observedInner = null;
            if (this.onFullscreenChange) {
                document.removeEventListener('fullscreenchange', this.onFullscreenChange);
                this.onFullscreenChange = null;
            }
        }

        scheduleRefit() {
            if (this.refitScheduled) return;
            this.refitScheduled = true;
            requestAnimationFrame(() => {
                this.refitScheduled = false;
                this.refitCurrent();
            });
        }

        observeActiveContent(slide) {
            if (!this.resizeObserver || !slide || !slide.inner) return;
            if (this.observedInner && this.observedInner !== slide.inner) {
                this.resizeObserver.unobserve(this.observedInner);
            }
            this.observedInner = slide.inner;
            this.resizeObserver.observe(this.observedInner);
        }

        refitCurrent() {
            this.refitSlide(this.slides[this.currentIndex]);
        }

        refitSlide(slide) {
            if (!slide || !slide.inner || !slide.el) return;

            const sec = slide.el;
            const inner = slide.inner;
            const secStyle = window.getComputedStyle(sec);
            const padY = (
                Number.parseFloat(secStyle.paddingTop)
                + Number.parseFloat(secStyle.paddingBottom)
            );
            const availableHeight = Math.max(1, sec.clientHeight - padY);
            const availableWidth = Math.max(1, inner.clientWidth);
            // scrollWidth/scrollHeight são medidas de layout — imunes ao transform aplicado.
            const contentWidth = Math.max(1, inner.scrollWidth);
            const contentHeight = Math.max(1, inner.scrollHeight);
            const requiredScale = Math.min(
                1,
                availableWidth / contentWidth,
                availableHeight / contentHeight
            );

            const fitsAtFloor = requiredScale + Number.EPSILON >= this.scaleFloor;
            const scale = fitsAtFloor ? this.roundScale(requiredScale) : this.scaleFloor;
            // Blocos atômicos já trazem rolagem própria do build; refit só reescala.
            const scrollable = !slide.builtScrollable && !fitsAtFloor;

            const signature = `${scale}:${scrollable}`;
            if (slide.fitSignature === signature) return;
            slide.fitSignature = signature;

            slide.scale = scale;
            inner.style.setProperty('--slide-scale', String(scale));

            if (slide.builtScrollable) return;

            if (scrollable) {
                sec.classList.add('is-overflowing');
                inner.classList.add('is-scrollable');
                inner.tabIndex = 0;
                inner.setAttribute('role', 'region');
                inner.setAttribute('aria-label', 'Conteúdo extenso do slide');
                inner.style.setProperty(
                    '--deck-scroll-max-height',
                    `${Math.floor(availableHeight / this.scaleFloor)}px`
                );
            } else {
                sec.classList.remove('is-overflowing');
                inner.classList.remove('is-scrollable');
                inner.style.removeProperty('--deck-scroll-max-height');
            }
        }

        /* ── FASE 6: Suíte de auditoria visual (?test=true) ──────────────── */
        auditSlide(slide, index) {
            const sec = slide.el;
            const inner = slide.inner;
            const secStyle = window.getComputedStyle(sec);
            const padY = (
                Number.parseFloat(secStyle.paddingTop)
                + Number.parseFloat(secStyle.paddingBottom)
            );
            const stageHeight = Math.max(1, sec.clientHeight);
            const availableHeight = Math.max(1, stageHeight - padY);
            const availableWidth = Math.max(1, inner.clientWidth);
            const scale = slide.scale || 1;
            const contentHeight = inner.scrollHeight;
            const contentWidth = inner.scrollWidth;
            const scaledHeight = Math.round(contentHeight * scale);
            const scaledWidth = Math.round(contentWidth * scale);
            const overflowV = Math.max(0, scaledHeight - Math.round(availableHeight));
            const overflowH = Math.max(0, scaledWidth - Math.round(availableWidth));
            const occupancy = Math.round((scaledHeight / stageHeight) * 100);
            const type = (
                [...sec.classList].find(c => c.startsWith('deck-slide--')) || ''
            ).replace('deck-slide--', '');
            const scrollable = (
                inner.classList.contains('is-scrollable')
                || Boolean(inner.querySelector('.is-scrollable'))
            );
            const sample = inner.querySelector('.deck-prose-body p, .deck-points li, .deck-heading');
            const fontPx = sample
                ? Math.round(Number.parseFloat(window.getComputedStyle(sample).fontSize) * scale)
                : null;

            const floorViolation = scale + Number.EPSILON < this.scaleFloor;
            const overflowFail = (overflowV > MEASURE_TOLERANCE || overflowH > MEASURE_TOLERANCE) && !scrollable;
            const emptyWarn = (
                occupancy < AUDIT_EMPTY_OCCUPANCY
                && !AUDIT_EMPTY_EXEMPT.includes(type)
                && !sec.classList.contains('is-sparse')
            );

            return {
                i: index,
                type: type,
                scale: scale,
                occ: `${occupancy}%`,
                overflowV: overflowV,
                overflowH: overflowH,
                fontPx: fontPx,
                scrollable: scrollable,
                floorViolation: floorViolation,
                overflowFail: overflowFail,
                emptyWarn: emptyWarn
            };
        }

        runIntegratedTests() {
            const rows = this.slides.map((slide, index) => this.auditSlide(slide, index));
            const activeCount = this.stage.querySelectorAll('.deck-slide.is-active').length;
            const activeIsPrev = Boolean(this.stage.querySelector('.deck-slide.is-active.is-prev'));
            const summary = {
                total: this.slides.length,
                exactlyOneActive: activeCount === 1,
                noActiveIsPrev: !activeIsPrev,
                railMatches: this.railButtons.length === this.slides.length,
                overflowFailures: rows.filter(r => r.overflowFail).length,
                floorViolations: rows.filter(r => r.floorViolation).length,
                emptyWarnings: rows.filter(r => r.emptyWarn).length,
                jsErrors: this.testErrors.length
            };
            summary.pass = (
                summary.exactlyOneActive
                && summary.noActiveIsPrev
                && summary.railMatches
                && summary.overflowFailures === 0
                && summary.floorViolations === 0
                && summary.jsErrors === 0
            );

            const report = { summary: summary, slides: rows, errors: this.testErrors.slice() };
            window.__deckAudit = report;
            if (window.console) {
                console.log(`[DeckAudit] ${summary.pass ? 'PASS' : 'FAIL'}`, summary);
                if (console.table) console.table(rows);
            }
            this.renderAuditBadge(summary);
            return report;
        }

        renderAuditBadge(summary) {
            let badge = document.getElementById('deck-audit-badge');
            if (!badge) {
                badge = document.createElement('div');
                badge.id = 'deck-audit-badge';
                badge.className = 'deck-audit-badge';
                document.body.appendChild(badge);
            }
            badge.classList.toggle('is-pass', summary.pass);
            badge.classList.toggle('is-fail', !summary.pass);
            badge.innerHTML = (
                `<strong>${summary.pass ? 'AUDIT PASS' : 'AUDIT FAIL'}</strong>`
                + `<span>${summary.total} slides · overflow ${summary.overflowFailures}`
                + ` · piso ${summary.floorViolations} · vazio ${summary.emptyWarnings}`
                + ` · erros ${summary.jsErrors}</span>`
            );
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
            this.applySlideScale(nextSlide);
            nextSlide.el.classList.remove('is-prev');
            nextSlide.el.classList.add('is-active');
            this.observeActiveContent(nextSlide);
            this.refitSlide(nextSlide);

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

            // Trilho de navegação: marca o ponto atual.
            this.railButtons.forEach((btn, idx) => {
                const active = idx === this.currentIndex;
                btn.classList.toggle('is-active', active);
                if (active) {
                    btn.setAttribute('aria-current', 'step');
                } else {
                    btn.removeAttribute('aria-current');
                }
            });

            // Anúncio para leitores de tela.
            if (this.liveEl) {
                this.liveEl.textContent = (
                    `Slide ${this.currentIndex + 1} de ${this.slides.length}: ${current.title}`
                );
            }

            // Roteiro docente do slide atual.
            if (this.notesBadgeEl) this.notesBadgeEl.textContent = `Slide ${this.currentIndex + 1}`;
            if (this.notesBodyEl) {
                const noteHTML = current.noteKey != null ? this.notesMap[current.noteKey] : '';
                if (noteHTML) {
                    this.notesBodyEl.innerHTML = noteHTML;
                    this.notesBodyEl.classList.remove('is-empty');
                } else {
                    this.notesBodyEl.innerHTML = (
                        '<p class="deck-notes-empty">Sem roteiro para este slide.</p>'
                    );
                    this.notesBodyEl.classList.add('is-empty');
                }
            }
        }

        /* ── FASE 3: Ponteiro Laser (Spotlight Canvas) ──────────────────── */
        initSpotlightCanvas() {
            if (!this.spotlightCanvas) return;
            this.laserCtx = this.spotlightCanvas.getContext('2d');
            this.laserRAF = null;

            const resizeCanvas = () => {
                this.spotlightCanvas.width = window.innerWidth;
                this.spotlightCanvas.height = window.innerHeight;
            };
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);

            window.addEventListener('mousemove', (e) => {
                if (this.isLaserActive) {
                    this.laserTrail = [{ x: e.clientX, y: e.clientY }];
                }
            });

            // Pausa o loop quando a aba não está visível para poupar CPU.
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    this.stopLaserLoop();
                } else if (this.isLaserActive) {
                    this.startLaserLoop();
                }
            });
        }

        renderLaserFrame() {
            const ctx = this.laserCtx;
            if (!ctx) return;
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
        }

        startLaserLoop() {
            if (this.laserRAF || !this.laserCtx) return;
            const loop = () => {
                this.renderLaserFrame();
                this.laserRAF = requestAnimationFrame(loop);
            };
            this.laserRAF = requestAnimationFrame(loop);
        }

        stopLaserLoop() {
            if (this.laserRAF) {
                cancelAnimationFrame(this.laserRAF);
                this.laserRAF = null;
            }
            if (this.laserCtx) {
                this.laserCtx.clearRect(0, 0, this.spotlightCanvas.width, this.spotlightCanvas.height);
            }
        }

        toggleLaserPointer() {
            this.isLaserActive = !this.isLaserActive;
            this.body.classList.toggle('is-laser-active', this.isLaserActive);
            const btn = document.querySelector('[data-deck-laser]');
            if (btn) {
                btn.classList.toggle('is-active', this.isLaserActive);
                btn.setAttribute('aria-pressed', String(this.isLaserActive));
            }
            if (this.isLaserActive) {
                this.startLaserLoop();
            } else {
                this.stopLaserLoop();
            }
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
            if (isOpen) {
                this.notesEl.removeAttribute('inert');
            } else {
                this.notesEl.setAttribute('inert', '');
            }

            const btn = document.querySelector('[data-deck-notes]');
            if (btn) {
                btn.classList.toggle('is-active', isOpen);
                btn.setAttribute('aria-expanded', String(isOpen));
            }
        }

        openOverview() {
            if (!this.overviewDialog || !this.overviewGrid) return;
            this.overviewGrid.innerHTML = '';

            this.slides.forEach((slide, idx) => {
                const thumb = document.createElement('button');
                thumb.type = 'button';
                thumb.className = `deck-thumb${idx === this.currentIndex ? ' is-current' : ''}`;
                thumb.setAttribute('aria-label', `Ir para o slide ${idx + 1}: ${slide.title}`);
                if (idx === this.currentIndex) thumb.setAttribute('aria-current', 'true');
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

        handleEscape() {
            if (this.overviewDialog && this.overviewDialog.open) {
                this.overviewDialog.close();
                return;
            }
            if (this.blackoutEl && !this.blackoutEl.hasAttribute('hidden')) {
                this.toggleBlackout();
                return;
            }
            if (this.notesEl && this.notesEl.classList.contains('is-open')) {
                this.toggleNotes();
                return;
            }
            if (document.fullscreenElement) {
                document.exitFullscreen().catch(() => {});
                return;
            }
            // Sem overlays abertos: sair da apresentação de volta à aula.
            const exit = document.querySelector('[data-deck-exit]');
            if (exit && exit.href) window.location.href = exit.href;
        }

        bindEvents() {
            // Teclas de Atalho
            window.addEventListener('keydown', (e) => {
                // Campos editáveis nunca têm atalhos sequestrados.
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
                        this.next();
                        break;
                    case 'ArrowRight':
                    case 'ArrowDown':
                    case 'PageDown':
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
                        e.preventDefault();
                        this.handleEscape();
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
            document.addEventListener('fullscreenchange', () => this.syncFullscreenButton());

            // Lightbox da Capa Ampliada
            const lightboxDialog = document.querySelector('[data-deck-lightbox]');
            if (lightboxDialog) {
                document.addEventListener('click', (e) => {
                    const trigger = e.target.closest('[data-deck-lightbox-open]');
                    const closeBtn = e.target.closest('[data-deck-lightbox-close]');
                    if (trigger) {
                        e.preventDefault();
                        lightboxDialog.showModal();
                    } else if (closeBtn || (e.target === lightboxDialog)) {
                        e.preventDefault();
                        lightboxDialog.close();
                    }
                });
            }

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

        syncFullscreenButton() {
            const btn = document.querySelector('[data-deck-fullscreen]');
            if (!btn) return;
            const active = Boolean(document.fullscreenElement);
            const label = active ? 'Sair da tela cheia' : 'Entrar em tela cheia';
            btn.setAttribute('aria-label', label);
            btn.setAttribute('title', active ? 'Sair da tela cheia (F)' : 'Tela cheia (F)');
            btn.setAttribute('aria-pressed', String(active));
            btn.classList.toggle('is-active', active);
        }
    }

    // Inicializa quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new AtelierDeck());
    } else {
        new AtelierDeck();
    }
})();
