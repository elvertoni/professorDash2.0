/* ──────────────────────────────────────────────────────────────────────────
   quiz.js — Quiz interativo (avaliação formativa client-side).
   Registra componente Alpine.js `quizQuestion()` que gerencia:
   - Seleção de alternativa
   - Feedback visual certo/errado
   - Travamento após resposta
   Usado tanto nas páginas normais (base.html + Alpine) quanto no modo apresentação
   (aula_presentation.html, onde Alpine é carregado explicitamente).
   ──────────────────────────────────────────────────────────────────────── */
document.addEventListener('alpine:init', function () {
    'use strict';

    var questionSequence = 0;
    var handledRevealEvents = new WeakSet();

    function pendingProjectionQuestions() {
        return Array.from(document.querySelectorAll(
            '.lesson-quiz-question[data-reader-quiz-resolved="false"]'
        ));
    }

    function nextProjectionQuestion() {
        var pending = pendingProjectionQuestions();
        var stage = document.getElementById('reader')
            || document.querySelector('.reader-stage');
        var stageRect = stage
            ? stage.getBoundingClientRect()
            : { top: 0, bottom: window.innerHeight };
        var viewportTop = Math.max(0, stageRect.top);
        var viewportBottom = Math.min(window.innerHeight, stageRect.bottom);
        var visible = pending.map(function (question) {
            var rect = question.getBoundingClientRect();
            var intersection = Math.max(
                0,
                Math.min(rect.bottom, viewportBottom)
                    - Math.max(rect.top, viewportTop)
            );
            var center = rect.top + (rect.height / 2);
            var viewportCenter = viewportTop
                + ((viewportBottom - viewportTop) / 2);

            return {
                question: question,
                intersection: intersection,
                centerDistance: Math.abs(center - viewportCenter),
            };
        }).filter(function (candidate) {
            return candidate.intersection > 0;
        }).sort(function (first, second) {
            return second.intersection - first.intersection
                || first.centerDistance - second.centerDistance;
        });
        var belowViewport = pending.find(function (question) {
            return question.getBoundingClientRect().top >= viewportBottom;
        });

        return visible.length
            ? visible[0].question
            : belowViewport || pending[0] || null;
    }

    Alpine.data('quizQuestion', function () {
        var questionId = ++questionSequence;
        var questionEl = null;
        var revealButton = null;
        var revealStatus = null;
        var revealButtonHandler = null;
        var revealEventHandler = null;

        return {
            answered: false,
            selectedIndex: -1,
            isCorrect: false,
            resolved: false,
            revealed: false,
            correctIndex: -1,
            projectionMode: document.documentElement.classList.contains('reader-html'),

            init: function () {
                questionEl = this.$el;
                if (!this.projectionMode) return;

                questionEl.dataset.readerQuizResolved = 'false';
                questionEl.dataset.readerQuizRevealed = 'false';

                revealButton = document.createElement('button');
                revealButton.type = 'button';
                revealButton.className = 'reader-quiz-reveal';
                revealButton.textContent = 'Revelar resposta';
                revealButton.setAttribute('aria-pressed', 'false');
                revealButton.setAttribute('aria-keyshortcuts', 'R');

                revealStatus = document.createElement('p');
                revealStatus.id = 'reader-quiz-reveal-status-' + questionId;
                revealStatus.className = 'reader-quiz-reveal-status';
                revealStatus.setAttribute('role', 'status');
                revealStatus.setAttribute('aria-live', 'polite');
                revealStatus.setAttribute('aria-atomic', 'true');

                revealButton.setAttribute('aria-controls', revealStatus.id);

                var feedback = questionEl.querySelector('.quiz-feedback');
                questionEl.insertBefore(revealButton, feedback);
                questionEl.insertBefore(revealStatus, feedback);

                revealButtonHandler = function () {
                    this.reveal('button');
                }.bind(this);
                revealButton.addEventListener('click', revealButtonHandler);

                revealEventHandler = function (event) {
                    if (handledRevealEvents.has(event) || this.resolved) return;
                    if (nextProjectionQuestion() !== questionEl) return;

                    handledRevealEvents.add(event);
                    var source = event.detail && event.detail.source
                        ? event.detail.source
                        : 'shortcut';
                    this.reveal(source);
                }.bind(this);
                window.addEventListener('reader:reveal-quiz', revealEventHandler);
            },

            destroy: function () {
                if (revealButton && revealButtonHandler) {
                    revealButton.removeEventListener('click', revealButtonHandler);
                }
                if (revealEventHandler) {
                    window.removeEventListener('reader:reveal-quiz', revealEventHandler);
                }
            },

            choose: function (index, correct) {
                if (this.answered) return;
                this.answered = true;
                this.resolved = true;
                this.selectedIndex = index;
                this.isCorrect = correct;

                if (this.projectionMode) {
                    if (questionEl) {
                        questionEl.dataset.readerQuizResolved = 'true';
                    }
                    if (revealButton) {
                        revealButton.disabled = true;
                        revealButton.hidden = true;
                        revealButton.setAttribute('aria-pressed', 'false');
                    }
                    this.$nextTick(function () {
                        this.emitStateChanged('answer');
                    }.bind(this));
                }
            },

            emitStateChanged: function (source) {
                window.dispatchEvent(new CustomEvent('reader:quiz-state-changed', {
                    detail: {
                        remaining: pendingProjectionQuestions().length,
                        source: source,
                    },
                }));
            },

            reveal: function (source) {
                if (!this.projectionMode
                    || !questionEl
                    || this.resolved
                    || this.answered) {
                    return false;
                }

                this.answered = true;
                this.resolved = true;
                this.revealed = true;
                this.selectedIndex = -1;
                this.isCorrect = false;
                questionEl.dataset.readerQuizResolved = 'true';
                questionEl.dataset.readerQuizRevealed = 'true';

                var feedback = questionEl.querySelector('.quiz-feedback');
                if (feedback) {
                    feedback.hidden = true;
                    feedback.setAttribute('aria-hidden', 'true');
                }

                if (revealButton) {
                    revealButton.disabled = true;
                    revealButton.textContent = 'Resposta revelada';
                    revealButton.setAttribute('aria-pressed', 'true');
                }

                var correctOption = questionEl.querySelectorAll('.quiz-option')[
                    this.correctIndex
                ];
                var correctLetter = correctOption
                    ? correctOption.querySelector('.quiz-option-letter')
                    : null;
                var announcement = correctLetter
                    ? 'Resposta revelada. A alternativa '
                        + correctLetter.textContent.trim()
                        + ' está destacada.'
                    : 'Resposta revelada. A alternativa correta está destacada.';

                if (revealStatus) revealStatus.textContent = announcement;

                this.$nextTick(function () {
                    var questionLabel = questionEl.querySelector('p strong');
                    var questionNumberMatch = questionLabel
                        ? questionLabel.textContent.match(/\d+/)
                        : null;

                    this.emitStateChanged('reveal');
                    window.dispatchEvent(new CustomEvent('reader:quiz-revealed', {
                        detail: {
                            question: questionEl,
                            quiz: questionEl.closest('.lesson-quiz'),
                            questionNumber: questionNumberMatch
                                ? parseInt(questionNumberMatch[0], 10)
                                : null,
                            correctIndex: this.correctIndex,
                            remaining: pendingProjectionQuestions().length,
                            source: source || 'button',
                        },
                    }));
                }.bind(this));

                return true;
            },

            optionClass: function (index, correct) {
                if (correct && this.correctIndex === -1) {
                    this.correctIndex = index;
                }
                if (this.revealed) {
                    return correct ? 'is-revealed' : 'is-dimmed';
                }
                if (!this.answered) return '';
                if (index === this.selectedIndex) {
                    return correct ? 'is-correct' : 'is-wrong';
                }
                if (!this.isCorrect && correct) {
                    return 'is-revealed';
                }
                return 'is-dimmed';
            },
        };
    });

    Alpine.data('quizSection', function () {
        return {
            total: 0,
            correct: 0,
            answeredCount: 0,

            init: function () {
                var el = this.$el;
                this.total = parseInt(el.dataset.quizTotal || '0', 10);
            },

            registerAnswer: function (isCorrect) {
                this.answeredCount++;
                if (isCorrect) this.correct++;
            },

            get allAnswered() {
                return this.answeredCount >= this.total;
            },

            get resultText() {
                if (!this.allAnswered) return '';
                if (this.correct === this.total) return 'Parabéns! Todas corretas!';
                return this.correct + ' de ' + this.total + ' corretas';
            },

            get resultClass() {
                if (!this.allAnswered) return '';
                if (this.correct === this.total) return 'quiz-result--perfect';
                if (this.correct >= this.total / 2) return 'quiz-result--good';
                return 'quiz-result--needs-review';
            },
        };
    });
});
