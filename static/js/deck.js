/* ──────────────────────────────────────────────────────────────────────────
   deck.js — Modo Apresentação (slides) das aulas.
   Motor de paginação e renderização dinâmico baseado em medição real do DOM
   e rebalanceamento iterativo de slides.
   ──────────────────────────────────────────────────────────────────────── */
(function () {
    'use strict';

    const body = document.body;
    const stage = document.getElementById('deck-stage');
    const source = document.getElementById('deck-source');
    if (!stage || !source) return;

    // Constantes de tipos de slide e orçamentos
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

    // Orçamento visual estimado inicial (unidades de linha de conteúdo)
    const SLIDE_WEIGHT_LIMIT = 15;

    // Palco de medição temporário
    let measureStage = document.getElementById('deck-stage-measure');
    if (!measureStage) {
        measureStage = document.createElement('div');
        measureStage.id = 'deck-stage-measure';
        measureStage.className = 'deck-stage-measure';
        document.body.appendChild(measureStage);
    }

    // Variável para armazenar os slides processados
    let slides = []; // { el, steps, title, notesHTML, items[] }
    let totalSlides = 0;
    let currentIndex = 0;
    let currentStep = 0;

    /* ── Auxiliares de criação DOM ────────────────────────────────────────── */
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

    /* ── FASE 1: Segmentação Semântica ───────────────────────────────────── */
    function parseLessonContent(sourceEl) {
        const blocks = [];
        Array.from(sourceEl.children).forEach((node) => {
            const tag = node.tagName;
            const cls = node.classList || { contains: () => false };
            let type = 'other';

            if (tag === 'H2') type = 'h2';
            else if (tag === 'H3') type = 'h3';
            else if (cls.contains('callout') || cls.contains('lesson-callout')) type = CALLOUT;
            else if (cls.contains('lesson-steps')) type = STEPS;
            else if (cls.contains('lesson-diagram') || tag === 'FIGURE' || tag === 'IMG') type = MEDIA;
            else if (cls.contains('lesson-quiz')) type = QUIZ;
            else if (tag === 'UL' || tag === 'OL') type = POINT;
            else if (tag === 'TABLE' || cls.contains('tbl-wrap') || node.querySelector('table')) type = TABLE;
            else if (tag === 'PRE' || node.querySelector('pre')) type = CODE;
            else if (tag === 'P') type = 'p';

            blocks.push({
                element: node.cloneNode(true),
                type: type,
                weight: 0 // preenchido na Fase 2
            });
        });
        return blocks;
    }

    /* ── FASE 2: Estimativa de Peso Visual ───────────────────────────────── */
    function estimateVisualWeight(block) {
        const text = block.element.textContent.trim();
        const html = block.element.innerHTML || '';
        
        switch (block.type) {
            case 'h2':
                return 4;
            case 'h3':
                return 3;
            case 'p': {
                // Linhas estimadas baseadas em ~45 caracteres por linha + margens
                const charWeight = Math.ceil(text.length / 45);
                const formattingBonus = (html.includes('<strong>') || html.includes('<code>')) ? 1 : 0;
                return Math.max(2, charWeight + formattingBonus + 1);
            }
            case POINT:
            case STEPS: {
                // Soma do peso de cada item da lista
                let listWeight = 0;
                const items = Array.from(block.element.querySelectorAll('li'));
                items.forEach(li => {
                    const liText = li.textContent.trim();
                    listWeight += Math.max(1.5, Math.ceil(liText.length / 40) + 1);
                });
                return Math.max(3, listWeight);
            }
            case CALLOUT: {
                const calloutText = block.element.querySelector('.ct')?.textContent || text;
                return Math.max(5, Math.ceil(calloutText.length / 50) + 3);
            }
            case TABLE: {
                const rows = block.element.querySelectorAll('tr').length || 3;
                const cols = block.element.querySelectorAll('th, td').length / rows || 3;
                return Math.max(6, rows * 1.8 + cols * 0.5);
            }
            case CODE: {
                const lines = text.split('\n').length || 4;
                return Math.max(5, lines + 2);
            }
            case MEDIA:
                return 12; // Mídia grande tem peso alto
            case QUIZ:
                return 15; // Quiz interativo consome o slide inteiro
            default:
                return 5;
        }
    }

    /* ── FASE 3: Composição Inicial dos Slides ────────────────────────────── */
    function composeInitialSlides(blocks) {
        const specs = [];
        let currentSectionTitle = '';
        let currentSubTitle = '';
        let sectionNo = 0;

        let activeSpec = null;
        let accumulatedWeight = 0;

        function startNewSlide(type) {
            if (activeSpec) {
                specs.push(activeSpec);
            }
            activeSpec = {
                type: type,
                sectionNo: sectionNo,
                sectionTitle: currentSectionTitle,
                subTitle: currentSubTitle,
                blocks: [],
                page: 0,
                pages: 1
            };
            accumulatedWeight = 0;
        }

        blocks.forEach((block) => {
            if (block.type === 'h2') {
                sectionNo += 1;
                currentSectionTitle = block.element.textContent.trim();
                currentSubTitle = '';
                startNewSlide(PROSE);
                return;
            }
            if (block.type === 'h3') {
                currentSubTitle = block.element.textContent.trim();
                startNewSlide(PROSE);
                return;
            }

            // Elementos gigantes ou isolados ganham slides próprios
            if (block.type === QUIZ || block.type === MEDIA || block.type === TABLE || block.type === CODE) {
                startNewSlide(block.type);
                activeSpec.blocks.push(block);
                activeSpec.weight = block.weight;
                startNewSlide(PROSE); // Próximo slide volta a ser prosa comum
                return;
            }

            // Se não há slide ativo, inicia um de prosa
            if (!activeSpec) {
                startNewSlide(PROSE);
            }

            // Determina se cabe no slide atual
            const blockWeight = block.weight;
            const wouldOverflow = (accumulatedWeight + blockWeight) > SLIDE_WEIGHT_LIMIT;

            if (wouldOverflow && activeSpec.blocks.length > 0) {
                // Começa novo slide de continuação da seção
                const prevType = activeSpec.type;
                startNewSlide(prevType);
            }

            activeSpec.blocks.push(block);
            accumulatedWeight += blockWeight;
            
            // Se o tipo do slide ainda é genérico (PROSE), mas adicionamos uma lista,
            // podemos alterar o tipo para representar melhor a estrutura se ela for dominante
            if (activeSpec.type === PROSE && (block.type === POINT || block.type === STEPS)) {
                if (activeSpec.blocks.length === 1) {
                    activeSpec.type = block.type;
                }
            }
        });

        if (activeSpec && activeSpec.blocks.length > 0) {
            specs.push(activeSpec);
        }

        // Calcula paginação para cada subseção de slides consecutivos
        let currentGroup = [];
        let currentGroupKey = '';

        function flushGroupPagination() {
            if (currentGroup.length > 1) {
                currentGroup.forEach((spec, i) => {
                    spec.page = i;
                    spec.pages = currentGroup.length;
                });
            }
            currentGroup = [];
        }

        specs.forEach((spec) => {
            const key = spec.sectionTitle + '||' + spec.subTitle;
            if (key !== currentGroupKey) {
                flushGroupPagination();
                currentGroupKey = key;
            }
            // Apenas slides de conteúdo comum (prosa, ponto, passos) entram na paginação da seção
            if (spec.type === PROSE || spec.type === POINT || spec.type === STEPS) {
                currentGroup.push(spec);
            } else {
                flushGroupPagination();
            }
        });
        flushGroupPagination();

        return specs;
    }

    /* ── Fracionamento de blocos de texto e lista para rebalanceamento ────── */
    function splitParagraphHTML(htmlContent) {
        // Divide o HTML por sentenças de forma segura sem quebrar tags inline
        const sentences = htmlContent.trim().split(/(?<=[.!?…])\s+(?![^<>]*>)/);
        return sentences.filter(s => s.trim().length > 0);
    }

    /* ── FASE 4 & 5: Medição e Rebalanceamento Iterativo ──────────────────── */
    function measureSlideReal(slideEl) {
        measureStage.innerHTML = '';
        measureStage.appendChild(slideEl);
        
        // Medição baseada na altura física do conteúdo interno em relação à altura útil disponível
        const innerEl = slideEl.querySelector('.deck-slide-inner');
        const style = window.getComputedStyle(slideEl);
        const paddingTop = parseFloat(style.paddingTop) || 0;
        const paddingBottom = parseFloat(style.paddingBottom) || 0;
        const paddingY = paddingTop + paddingBottom;
        
        const clientH = slideEl.clientHeight || 1;
        const availableH = Math.max(1, clientH - paddingY);
        const contentH = innerEl ? innerEl.offsetHeight : slideEl.scrollHeight - paddingY;
        
        measureStage.innerHTML = '';
        return {
            scrollHeight: slideEl.scrollHeight,
            clientHeight: clientH,
            contentHeight: contentH,
            availableHeight: availableH,
            ocupacao: contentH / availableH,
            overflow: contentH > availableH || slideEl.scrollHeight > clientH
        };
    }

    function rebalanceDeck(slideSpecs) {
        let maxIterations = 20;
        let changed = true;

        while (changed && maxIterations > 0) {
            changed = false;
            maxIterations -= 1;

            for (let i = 0; i < slideSpecs.length; i++) {
                const spec = slideSpecs[i];
                if (spec.type === COVER || spec.type === END || spec.type === QUIZ || spec.type === MEDIA) {
                    continue; // Pula capas, encerramentos e mídias dedicadas
                }

                // Renderiza temporariamente para medição real
                const tempEl = renderSlideElement(spec, i);
                const measurement = measureSlideReal(tempEl);

                // Cenário A: O slide transborda (ocupação > 0.90 ou overflow real)
                if (measurement.overflow || measurement.ocupacao > 0.90) {
                    // 1. Se tem múltiplos blocos, move o último para o próximo
                    if (spec.blocks.length > 1) {
                        const lastBlock = spec.blocks.pop();
                        
                        // Garante que existe um slide seguinte compatível ou cria um
                        let nextSpec = slideSpecs[i + 1];
                        const isNextCompatible = nextSpec && 
                            (nextSpec.type === spec.type || nextSpec.type === PROSE) &&
                            nextSpec.sectionTitle === spec.sectionTitle &&
                            nextSpec.subTitle === spec.subTitle;

                        if (!isNextCompatible) {
                            // Inserir novo slide
                            nextSpec = {
                                type: spec.type,
                                sectionNo: spec.sectionNo,
                                sectionTitle: spec.sectionTitle,
                                subTitle: spec.subTitle,
                                blocks: [],
                                page: spec.page + 1,
                                pages: spec.pages + 1
                            };
                            slideSpecs.splice(i + 1, 0, nextSpec);
                        }
                        
                        nextSpec.blocks.unshift(lastBlock);
                        changed = true;
                        break; // Recomeça a varredura após alteração estrutural
                    }
                    
                    // 2. Se tem um único bloco e ele é uma Lista/Passos, divide os itens
                    const singleBlock = spec.blocks[0];
                    if (singleBlock && (singleBlock.type === POINT || singleBlock.type === STEPS)) {
                        const listItems = Array.from(singleBlock.element.children);
                        if (listItems.length > 1) {
                            // Divide a lista ao meio
                            const mid = Math.ceil(listItems.length / 2);
                            const firstHalf = listItems.slice(0, mid);
                            const secondHalf = listItems.slice(mid);

                            // Atualiza bloco atual
                            singleBlock.element.innerHTML = '';
                            firstHalf.forEach(li => singleBlock.element.appendChild(li.cloneNode(true)));

                            // Cria novo bloco de lista para o excesso
                            const newListEl = el(singleBlock.element.tagName, singleBlock.element.className);
                            secondHalf.forEach(li => newListEl.appendChild(li.cloneNode(true)));
                            const newBlock = {
                                element: newListEl,
                                type: singleBlock.type,
                                weight: 0
                            };

                            // Insere no próximo slide
                            let nextSpec = slideSpecs[i + 1];
                            const isNextCompatible = nextSpec && 
                                (nextSpec.type === spec.type || nextSpec.type === PROSE) &&
                                nextSpec.sectionTitle === spec.sectionTitle &&
                                nextSpec.subTitle === spec.subTitle;

                            if (!isNextCompatible) {
                                nextSpec = {
                                    type: spec.type,
                                    sectionNo: spec.sectionNo,
                                    sectionTitle: spec.sectionTitle,
                                    subTitle: spec.subTitle,
                                    blocks: [],
                                    page: spec.page + 1,
                                    pages: spec.pages + 1
                                };
                                slideSpecs.splice(i + 1, 0, nextSpec);
                            }

                            nextSpec.blocks.unshift(newBlock);
                            changed = true;
                            break;
                        }
                    }

                    // 3. Se tem um único parágrafo longo, divide-o por frases
                    if (singleBlock && singleBlock.type === 'p') {
                        const sentences = splitParagraphHTML(singleBlock.element.innerHTML);
                        if (sentences.length > 1) {
                            const mid = Math.ceil(sentences.length / 2);
                            const firstSentences = sentences.slice(0, mid);
                            const secondSentences = sentences.slice(mid);

                            // Atualiza parágrafo atual
                            singleBlock.element.innerHTML = firstSentences.join(' ');

                            // Cria novo bloco para frases excedentes
                            const newPEl = el('p', singleBlock.element.className);
                            newPEl.innerHTML = secondSentences.join(' ');
                            const newBlock = {
                                element: newPEl,
                                type: 'p',
                                weight: 0
                            };

                            let nextSpec = slideSpecs[i + 1];
                            const isNextCompatible = nextSpec && 
                                (nextSpec.type === spec.type || nextSpec.type === PROSE) &&
                                nextSpec.sectionTitle === spec.sectionTitle &&
                                nextSpec.subTitle === spec.subTitle;

                            if (!isNextCompatible) {
                                nextSpec = {
                                    type: PROSE,
                                    sectionNo: spec.sectionNo,
                                    sectionTitle: spec.sectionTitle,
                                    subTitle: spec.subTitle,
                                    blocks: [],
                                    page: spec.page + 1,
                                    pages: spec.pages + 1
                                };
                                slideSpecs.splice(i + 1, 0, nextSpec);
                            }

                            nextSpec.blocks.unshift(newBlock);
                            changed = true;
                            break;
                        }
                    }
                }

                // Cenário B: Slide excessivamente vazio (ocupação < 0.35)
                if (measurement.ocupacao < 0.35 && i < slideSpecs.length - 1) {
                    const nextSpec = slideSpecs[i + 1];
                    const isNextCompatible = nextSpec &&
                        (nextSpec.type === spec.type || nextSpec.type === PROSE) &&
                        nextSpec.sectionTitle === spec.sectionTitle &&
                        nextSpec.subTitle === spec.subTitle;

                    if (isNextCompatible && nextSpec.blocks.length > 0) {
                        // Tenta mover o primeiro bloco do próximo slide para este
                        const firstBlockOfNext = nextSpec.blocks[0];
                        
                        // Cria spec temporária simulando a união
                        const tempSpec = {
                            type: spec.type,
                            sectionTitle: spec.sectionTitle,
                            subTitle: spec.subTitle,
                            blocks: [...spec.blocks, firstBlockOfNext],
                            page: spec.page,
                            pages: spec.pages
                        };
                        const unionEl = renderSlideElement(tempSpec, i);
                        const unionMeasurement = measureSlideReal(unionEl);

                        // Se couber perfeitamente sem estourar, realiza a fusão do bloco
                        if (!unionMeasurement.overflow && unionMeasurement.ocupacao <= 0.85) {
                            spec.blocks.push(nextSpec.blocks.shift());
                            if (nextSpec.blocks.length === 0) {
                                // Se o próximo slide ficou vazio, remove ele do spec
                                slideSpecs.splice(i + 1, 1);
                            }
                            changed = true;
                            break;
                        }
                    }
                }
            }
        }

        // Recalcula a paginação final após o rebalanceamento
        let currentGroup = [];
        let currentGroupKey = '';

        function flushGroupPagination() {
            if (currentGroup.length > 0) {
                currentGroup.forEach((spec, i) => {
                    spec.page = i;
                    spec.pages = currentGroup.length;
                });
            }
            currentGroup = [];
        }

        slideSpecs.forEach((spec) => {
            const key = spec.sectionTitle + '||' + spec.subTitle;
            if (key !== currentGroupKey) {
                flushGroupPagination();
                currentGroupKey = key;
            }
            if (spec.type === PROSE || spec.type === POINT || spec.type === STEPS) {
                currentGroup.push(spec);
            } else {
                flushGroupPagination();
            }
        });
        flushGroupPagination();
    }

    /* ── Renderizador de Elemento Slide ──────────────────────────────────── */
    function renderSlideElement(spec, index) {
        const sec = el('section', 'deck-slide deck-slide--' + spec.type);
        sec.dataset.index = String(index);
        const inner = el('div', 'deck-slide-inner');

        if (spec.type === COVER || spec.type === END) {
            inner.classList.add('deck-slide-inner--bleed');
            inner.appendChild(spec.node || el('div'));
            sec.appendChild(inner);
            return sec;
        }

        // Títulos de seção/subtítulo
        const hasHeader = spec.page === 0;
        const sectionText = spec.subTitle || spec.sectionTitle;
        
        if (sectionText) {
            const h = el('h2', 'deck-heading');
            if (hasHeader) {
                h.textContent = sectionText;
            } else {
                h.innerHTML = sectionText + ' <span class="deck-page-mark" style="margin-top:0; font-size:0.5em; vertical-align:middle;">(continuação)</span>';
            }
            inner.appendChild(h);
        } else if (!spec.sectionTitle && !spec.subTitle) {
            inner.classList.add('deck-slide--lead');
        }

        // Renderização dos blocos internos
        if (spec.type === PROSE) {
            const bodyWrap = el('div', 'deck-prose-body');
            spec.blocks.forEach(block => {
                bodyWrap.appendChild(block.element.cloneNode(true));
            });
            inner.appendChild(bodyWrap);
        } else if (spec.type === POINT || spec.type === STEPS) {
            const listTag = spec.type === STEPS ? 'ol' : 'ul';
            const listClass = spec.type === STEPS ? 'deck-steps' : 'deck-points';
            const list = el(listTag, listClass);

            spec.blocks.forEach(block => {
                if (block.element.tagName === 'LI') {
                    list.appendChild(block.element.cloneNode(true));
                } else if (block.element.tagName === 'UL' || block.element.tagName === 'OL') {
                    Array.from(block.element.children).forEach(li => {
                        list.appendChild(li.cloneNode(true));
                    });
                } else {
                    const li = el('li');
                    li.appendChild(block.element.cloneNode(true));
                    list.appendChild(li);
                }
            });
            
            // Adiciona classe de build-in nos itens
            Array.from(list.children).forEach((li, itemIndex) => {
                li.classList.add('deck-build');
                li.dataset.step = String(itemIndex);
            });

            inner.appendChild(list);
        } else if (spec.type === CALLOUT || spec.type === MEDIA || spec.type === QUIZ || spec.type === TABLE || spec.type === CODE) {
            inner.classList.add('deck-slide-inner--center');
            spec.blocks.forEach(block => {
                inner.appendChild(block.element.cloneNode(true));
            });
        }

        // Indicador de paginação discreto
        if (spec.pages > 1) {
            const pg = el('span', 'deck-page-mark');
            pg.textContent = (spec.page + 1) + ' / ' + spec.pages;
            inner.appendChild(pg);
        }

        sec.appendChild(inner);
        return sec;
    }

    /* ── FASE 6: Escalonamento Tipográfico Global ─────────────────────────── */
    function calculateWorstOverflow() {
        let maxOverflow = 0;
        slides.forEach(({ el: s }) => {
            const o = s.scrollHeight - s.clientHeight;
            if (o > maxOverflow) maxOverflow = o;
        });
        return maxOverflow;
    }

    function fitAll() {
        body.style.removeProperty('--deck-fs'); // restaura padrão CSS
        const baseFs = parseFloat(getComputedStyle(body).fontSize) || 32;
        let fs = baseFs;
        let iterations = 0;

        // Diminui a fonte progressivamente em 4% por vez se houver estouro real
        while (calculateWorstOverflow() > 2 && iterations < 12) {
            fs *= 0.96;
            if (fs < 14) break; // limite mínimo absoluto de legibilidade
            body.style.setProperty('--deck-fs', fs + 'px');
            iterations += 1;
        }
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
                img.addEventListener('error', checkDone); // Garante progresso se imagem falhar
            }
        });
    }

    /* ── COMPOSIÇÃO FINAL E INICIALIZAÇÃO DO DECK ─────────────────────────── */
    function buildDeck() {
        // 1. Extração do conteúdo
        const rawBlocks = parseLessonContent(source);
        
        // 2. Estimativa de pesos
        rawBlocks.forEach(block => {
            block.weight = estimateVisualWeight(block);
        });

        // 3. Composição preliminar
        const slideSpecs = composeInitialSlides(rawBlocks);

        // 4. Inserção de Capa e Encerramento
        const coverEl = fromTemplate('deck-cover');
        const endEl = fromTemplate('deck-end');
        const roteiroEl = document.getElementById('deck-roteiro');

        const finalSpecs = [];
        
        if (coverEl) {
            const notes = [];
            if (roteiroEl && roteiroEl.children.length) {
                Array.from(roteiroEl.children).forEach(n => notes.push(n.cloneNode(true)));
            }
            finalSpecs.push({
                type: COVER,
                node: coverEl,
                title: 'Capa',
                notes: notes,
                page: 0,
                pages: 1,
                blocks: []
            });
        }

        slideSpecs.forEach(spec => finalSpecs.push(spec));

        if (endEl) {
            finalSpecs.push({
                type: END,
                node: endEl,
                title: 'Fim da aula',
                notes: [],
                page: 0,
                pages: 1,
                blocks: []
            });
        }

        // 5. Rebalanceamento baseado em medição DOM real
        rebalanceDeck(finalSpecs);

        // 6. Renderização definitiva no palco real
        stage.innerHTML = '';
        slides = [];

        finalSpecs.forEach((spec, idx) => {
            const slideEl = renderSlideElement(spec, idx);
            stage.appendChild(slideEl);

            // Título para Dots e controles
            let slideTitle = spec.title || spec.sectionTitle || 'Slide';
            if (spec.type === QUIZ) slideTitle = 'Quiz';
            else if (spec.type === CALLOUT) slideTitle = 'Destaque';
            else if (spec.type === TABLE) slideTitle = 'Tabela';
            else if (spec.type === CODE) slideTitle = 'Código';

            // Notas do professor
            let notesHTML = '';
            if (spec.notes && spec.notes.length) {
                const holder = el('div');
                spec.notes.forEach(n => holder.appendChild(n));
                notesHTML = holder.innerHTML;
            } else if (spec.blocks && spec.blocks.length) {
                // Se o bloco tiver notas internas (ex: roteiro específico)
                const holder = el('div');
                spec.blocks.forEach(block => {
                    const blockNotes = block.element.querySelector('.teacher-note');
                    if (blockNotes) holder.appendChild(blockNotes.cloneNode(true));
                });
                notesHTML = holder.innerHTML;
            }

            // Itens de build-in
            const items = Array.from(slideEl.querySelectorAll('.deck-build'));
            const steps = items.length || 1;

            slides.push({
                el: slideEl,
                steps: steps,
                title: slideTitle,
                notesHTML: notesHTML,
                items: items
            });
        });

        // Limpeza dos containers originais
        source.remove();
        if (roteiroEl) roteiroEl.remove();

        totalSlides = slides.length;

        // Atualização da UI (dots, total)
        initUI();

        // 7. Escalonamento tipográfico final
        fitAll();

        // Posição inicial
        goTo(0, false);

        // Ícones Lucide
        if (window.lucide) window.lucide.createIcons();

        // Executa testes automatizados integrados se solicitado na URL
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

    /* ── EXECUÇÃO DA AUTOMAÇÃO DE TESTES INTEGRADOS (NAVEGADOR) ───────────── */
    function runIntegratedTests() {
        console.log('%c[TEST SUITE] Iniciando testes de validação visual do deck...', 'color: #2DD4BF; font-weight: bold;');
        
        // Cria container visual da suite de testes
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

        // Monitor de Erros Globais no Console
        let jsConsoleErrors = [];
        const originalOnError = window.onerror;
        window.onerror = function(message, source, lineno, colno, error) {
            jsConsoleErrors.push({ message, line: lineno });
            if (originalOnError) originalOnError.apply(this, arguments);
            return false;
        };

        // Passa slide por slide de forma assíncrona para medir e auditar
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
                    const contentH = innerEl ? innerEl.offsetHeight : slide.el.scrollHeight - paddingY;
                    
                    const isOverflow = contentH > availableH || slide.el.scrollHeight > clientH;
                    // Evita alertar sobre slides vazios para Cover, End, Media ou Quiz
                    const isTooEmpty = (contentH / availableH) < 0.35 && 
                        !slide.el.className.includes('deck-slide--cover') && 
                        !slide.el.className.includes('deck-slide--end') && 
                        !slide.el.className.includes('deck-slide--media') && 
                        !slide.el.className.includes('deck-slide--quiz');
                    
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
                // Finalizou a verificação dos slides
                // Valida erros no console JS
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

                // Resultado Geral
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

                // Restaura o monitor e volta ao slide inicial
                window.onerror = originalOnError;
                goTo(originalIndex, false);
            }
        }

        // Aguarda assets iniciais antes de rodar os testes
        setTimeout(testNextSlide, 600);
    }

    /* ── INÍCIO ───────────────────────────────────────────────────────────── */
    // Aguarda fontes e imagens carregarem, depois constrói o deck
    waitForAssets(() => {
        buildDeck();
    });
}());
