/* ──────────────────────────────────────────────────────────────────────────
   quiz.js — Quiz interativo (avaliação formativa client-side).
   Registra componente Alpine.js `quizQuestion()` que gerencia:
   - Seleção de alternativa
   - Feedback visual certo/errado
   - Travamento após resposta
   Usado tanto nas páginas normais (base.html + Alpine) quanto no deck
   (aula_presentation.html, onde Alpine é carregado explicitamente).
   ──────────────────────────────────────────────────────────────────────── */
document.addEventListener('alpine:init', function () {
    'use strict';

    Alpine.data('quizQuestion', function () {
        return {
            answered: false,
            selectedIndex: -1,
            isCorrect: false,

            choose: function (index, correct) {
                if (this.answered) return;
                this.answered = true;
                this.selectedIndex = index;
                this.isCorrect = correct;
            },

            optionClass: function (index, correct) {
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
