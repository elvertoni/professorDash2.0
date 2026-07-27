import html
import json
import logging
import re
from dataclasses import dataclass

import bleach
import markdown
import yaml
from django.utils.html import escape


logger = logging.getLogger(__name__)


FRONTMATTER_RE = re.compile(r'\A---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)\Z', re.S)
WIKILINK_RE = re.compile(r'\[\[(?P<slug>[^\]|\n]+?)(?:\|(?P<label>[^\]\n]+?))?\]\]')
STEP_NUMBER_PREFIX_RE = re.compile(r'^\s*\d{1,2}\s*[.)\-–]\s+')
DIAGRAM_FENCE_RE = re.compile(r'```(?P<kind>diagrama[\w-]*)\n(?P<body>.*?)\n```', re.S)
QUIZ_FENCE_RE = re.compile(r'```quiz\n(?P<body>.*?)\n```', re.S)
TEACHER_NOTE_RE = re.compile(
    r'(?P<block>:::roteiro[^\n]*\n(?P<body>.*?)\n:::\s*)',
    re.S,
)
BLOCK_RE = re.compile(
    (
        r':::(?P<kind>conceito|atencao|atenção|dica|exemplo|importante|curiosidade)'
        r'(?P<title>[^\n]*)\n(?P<body>.*?)\n:::\s*'
    ),
    re.S,
)
DANGEROUS_HTML_BLOCK_RE = re.compile(
    r'<\s*(script|style|iframe|object|embed|template)\b.*?<\s*/\s*\1\s*>',
    re.I | re.S,
)
THEAD_RE = re.compile(
    r'(?P<open><thead\b[^>]*>)(?P<body>.*?)(?P<close></thead\s*>)',
    re.I | re.S,
)
TH_WITHOUT_SCOPE_RE = re.compile(
    r'<th\b(?![^>]*\bscope\s*=)(?P<attributes>[^>]*)>',
    re.I,
)

CALLOUT_LABELS = {
    'conceito': 'Conceito',
    'atencao': 'Atenção',
    'atenção': 'Atenção',
    'dica': 'Dica',
    'exemplo': 'Exemplo',
    'importante': 'Importante',
    'curiosidade': 'Curiosidade',
}

CALLOUT_ICONS = {
    'conceito': 'lightbulb',
    'atencao': 'alert-triangle',
    'dica': 'sparkle',
    'exemplo': 'book-open',
    'importante': 'star',
    'curiosidade': 'compass',
}

ALLOWED_LESSON_TAGS = frozenset(
    {
        'a',
        'abbr',
        'article',
        'b',
        'blockquote',
        'br',
        'button',
        'caption',
        'code',
        'dd',
        'del',
        'details',
        'div',
        'dl',
        'dt',
        'em',
        'figcaption',
        'figure',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'hr',
        'i',
        'img',
        'ins',
        'kbd',
        'li',
        'mark',
        'ol',
        'p',
        'pre',
        's',
        'samp',
        'section',
        'small',
        'span',
        'strong',
        'sub',
        'summary',
        'sup',
        'table',
        'tbody',
        'td',
        'tfoot',
        'th',
        'thead',
        'tr',
        'u',
        'ul',
        'var',
    }
)

_BASE_ATTRIBUTES = {
    '*': ['aria-hidden', 'aria-label', 'class', 'id', 'role', 'title'],
    'a': ['href', 'title'],
    'button': ['type', 'disabled'],
    'figure': ['class', 'data-diagram-type'],
    'i': ['aria-hidden', 'class', 'data-lucide'],
    'img': ['alt', 'decoding', 'height', 'loading', 'src', 'title', 'width'],
    'ol': ['class', 'start', 'type'],
    'section': ['data-quiz-total'],
    'td': ['align', 'colspan', 'rowspan'],
    'th': ['align', 'colspan', 'rowspan', 'scope'],
}


def _allowed_attributes_filter(tag, name, value):
    """Allow standard attributes + Alpine.js directives (x-*, @*, :*)."""
    if name.startswith(('x-', '@', ':')):
        return True
    allowed = _BASE_ATTRIBUTES.get(tag, [])
    if name in allowed:
        return True
    wildcard = _BASE_ATTRIBUTES.get('*', [])
    return name in wildcard


ALLOWED_LESSON_ATTRIBUTES = _allowed_attributes_filter

ALLOWED_LESSON_PROTOCOLS = frozenset({'http', 'https', 'mailto'})


@dataclass(frozen=True)
class ParsedLesson:
    frontmatter: dict
    body: str
    html: str


def parse_lesson_markdown(content, concept_labels=None):
    frontmatter, body = split_frontmatter(content)
    html_content = render_lesson_html(body, concept_labels=concept_labels)
    return ParsedLesson(frontmatter=frontmatter, body=body, html=html_content)


def resolve_wikilinks(markdown_content, concept_labels=None):
    '''Troca `[[slug]]` / `[[slug|rótulo]]` do acervo pelo nome de exibição.

    Os conceitos vivem no grafo do acervo e não têm página no portal — um link
    apontaria para lugar nenhum, e o destaque seria redundante porque o autor
    já marca esses termos em negrito. Fica só o texto.

    Sem rótulo explícito, o nome sai de `manifesto.json` (`conceitos[]`), que
    carrega a grafia correta. O último recurso troca hífen por espaço, e é aí
    que aparece "aprendizado de maquina" sem acento — por isso o mapa vem do
    acervo em vez de ser derivado aqui.
    '''
    labels = concept_labels or {}

    def replace(match):
        label = (match.group('label') or '').strip()
        if label:
            return label
        slug = match.group('slug').strip()
        return labels.get(slug) or slug.replace('-', ' ')

    return WIKILINK_RE.sub(replace, markdown_content or '')


def split_frontmatter(content):
    match = FRONTMATTER_RE.match(content.strip())
    if not match:
        return {}, content

    data = yaml.safe_load(match.group('yaml')) or {}
    if not isinstance(data, dict):
        data = {}

    return data, match.group('body')


def render_lesson_html(markdown_content, concept_labels=None):
    prepared = strip_teacher_notes(markdown_content)
    prepared = resolve_wikilinks(prepared, concept_labels)
    prepared = render_quiz_fences(prepared)
    prepared = render_diagram_fences(prepared)
    prepared = render_custom_blocks(prepared)

    rendered = markdown.markdown(
        prepared,
        extensions=[
            'extra',
            'sane_lists',
            'toc',
            'md_in_html',
        ],
        output_format='html5',
    )
    rendered = normalize_table_header_scopes(rendered)
    return sanitize_lesson_html(rendered)


def strip_teacher_notes(markdown_content):
    return TEACHER_NOTE_RE.sub('', markdown_content or '')


def render_teacher_notes_html(markdown_content, concept_labels=None):
    notes = [
        match.group('body').strip()
        for match in TEACHER_NOTE_RE.finditer(markdown_content or '')
        if match.group('body').strip()
    ]
    if not notes:
        return ''

    rendered = markdown.markdown(
        resolve_wikilinks('\n\n---\n\n'.join(notes), concept_labels),
        extensions=['extra', 'sane_lists'],
        output_format='html5',
    )
    rendered = normalize_table_header_scopes(rendered)
    return sanitize_lesson_html(rendered)


def normalize_table_header_scopes(html_content):
    def replace_thead(match):
        body = TH_WITHOUT_SCOPE_RE.sub(
            r'<th scope="col"\g<attributes>>',
            match.group('body'),
        )
        return ''.join((match.group('open'), body, match.group('close')))

    return THEAD_RE.sub(replace_thead, html_content or '')


def sanitize_lesson_html(html_content):
    html_content = TEACHER_NOTE_RE.sub('', html_content or '')
    html_content = DANGEROUS_HTML_BLOCK_RE.sub('', html_content or '')
    cleaner = bleach.Cleaner(
        tags=ALLOWED_LESSON_TAGS,
        attributes=ALLOWED_LESSON_ATTRIBUTES,
        protocols=ALLOWED_LESSON_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
    return cleaner.clean(html_content)


def render_diagram_fences(markdown_content):
    def replace(match):
        kind = escape(match.group('kind'))
        raw_body = match.group('body').strip()
        data = parse_yaml_block(raw_body)
        label = escape(
            data.get('titulo') if isinstance(data, dict) and data.get('titulo')
            else kind.replace('-', ' ').title()
        )

        if isinstance(data, dict) and isinstance(data.get('camadas'), list):
            items = []
            for index, layer in enumerate(data['camadas'], start=1):
                if not isinstance(layer, dict):
                    continue
                # O componente já mostra o índice na bolinha: "1. LGPD" viraria
                # "1 · 1. LGPD".
                raw_title = str(layer.get('rotulo') or f'Etapa {index}')
                title = escape(STEP_NUMBER_PREFIX_RE.sub('', raw_title, count=1))
                content = escape(str(layer.get('conteudo') or ''))
                items.append(
                    '<li>'
                    f'<span class="lesson-step-index">{index}</span>'
                    '<div>'
                    f'<strong>{title}</strong>'
                    f'<p>{content}</p>'
                    '</div>'
                    '</li>'
                )
            if items:
                return (
                    f'<figure class="lesson-diagram lesson-diagram-progressive" data-diagram-type="{kind}">\n'
                    f'<figcaption>{label}</figcaption>\n'
                    f'<ol class="lesson-steps">{"".join(items)}</ol>\n'
                    f'</figure>'
                )

        body = html.escape(raw_body)
        return (
            f'<figure class="lesson-diagram" data-diagram-type="{kind}">\n'
            f'<figcaption>{label}</figcaption>\n'
            f'<pre><code>{body}</code></pre>\n'
            f'</figure>'
        )

    return DIAGRAM_FENCE_RE.sub(replace, markdown_content)


def render_quiz_fences(markdown_content):
    """Render ```quiz fences into HTML.

    When at least one alternative has ``correta: true``, generates
    interactive Alpine.js HTML with clickable option buttons and
    correct/wrong feedback.  Otherwise, keeps the original static
    ``<ol>`` layout (backward compatible).
    """

    def replace(match):
        raw_body = match.group('body').strip()
        data = parse_yaml_block(raw_body)
        if not isinstance(data, list):
            return (
                '<section class="lesson-quiz">\n'
                '<div class="lesson-quiz-head"><strong>Quiz</strong></div>\n'
                f'<pre><code>{html.escape(raw_body)}</code></pre>\n'
                '</section>'
            )

        questions_static = []
        questions_interactive = []
        has_any_correct = False

        for q_index, question in enumerate(data, start=1):
            if not isinstance(question, dict):
                continue
            prompt = escape(str(question.get('pergunta') or f'Questão {q_index}'))
            alts_raw = question.get('alternativas') or []
            q_has_correct = any(
                isinstance(a, dict) and a.get('correta')
                for a in alts_raw
            )
            if q_has_correct:
                has_any_correct = True

            # --- static alternative list (fallback) ---
            static_items = []
            # --- interactive alternative buttons ---
            interactive_items = []
            for alt_index, alt in enumerate(alts_raw):
                if not isinstance(alt, dict):
                    continue
                text = escape(str(alt.get('texto') or ''))
                if not text:
                    continue
                is_correct = bool(alt.get('correta'))
                letter = chr(65 + alt_index)  # A, B, C, D…
                static_items.append(f'<li>{text}</li>')
                correct_js = 'true' if is_correct else 'false'
                interactive_items.append(
                    f'<button type="button" class="quiz-option"'
                    f' :class="optionClass({alt_index}, {correct_js})"'
                    f' :disabled="answered"'
                    f' @click="choose({alt_index}, {correct_js});'
                    f' $dispatch(\'quiz-answered\', {{ correct: {correct_js} }})">'
                    f'<span class="quiz-option-letter">{letter}</span>'
                    f'<span class="quiz-option-text">{text}</span>'
                    f'<span class="quiz-option-icon" aria-hidden="true"></span>'
                    f'</button>'
                )

            static_html = ''.join(static_items)
            interactive_html = ''.join(interactive_items)

            questions_static.append(
                '<li class="lesson-quiz-question">'
                f'<p><strong>Questão {q_index}.</strong> {prompt}</p>'
                f'<ol type="A">{static_html}</ol>'
                '</li>'
            )

            questions_interactive.append(
                f'<li class="lesson-quiz-question" x-data="quizQuestion()"'
                f' @quiz-answered.stop="$dispatch(\'quiz-answer-registered\','
                f' {{ correct: $event.detail.correct }})">'
                f'<p><strong>Questão {q_index}.</strong> {prompt}</p>'
                f'<div class="quiz-options">{interactive_html}</div>'
                f'<p class="quiz-feedback" x-show="answered" x-cloak>'
                f'<span x-show="isCorrect" class="quiz-feedback--correct">'
                f'✓ Correto!</span>'
                f'<span x-show="!isCorrect" class="quiz-feedback--wrong">'
                f'✗ Incorreta — veja a resposta destacada.</span>'
                f'</p>'
                f'</li>'
            )

        if not questions_static and not questions_interactive:
            return ''

        # Interactive path: at least one question has `correta`.
        if has_any_correct:
            total_q = len(questions_interactive)
            return (
                f'<section class="lesson-quiz lesson-quiz--interactive"'
                f' x-data="quizSection()" data-quiz-total="{total_q}"'
                f' @quiz-answer-registered.stop='
                f'"registerAnswer($event.detail.correct)">\n'
                '<div class="lesson-quiz-head">\n'
                '<strong>Quiz</strong>\n'
                '<span>Avaliação formativa</span>\n'
                '</div>\n'
                f'<ol class="lesson-quiz-list">'
                f'{"".join(questions_interactive)}</ol>\n'
                '<div class="quiz-result" x-show="allAnswered"'
                ' x-transition x-cloak :class="resultClass">\n'
                '<span x-text="resultText"></span>\n'
                '</div>\n'
                '</section>'
            )

        # Static path: no question has `correta`.
        return (
            '<section class="lesson-quiz">\n'
            '<div class="lesson-quiz-head">\n'
            '<strong>Quiz</strong>\n'
            '<span>Avaliação formativa</span>\n'
            '</div>\n'
            f'<ol class="lesson-quiz-list">{"".join(questions_static)}</ol>\n'
            '</section>'
        )

    return QUIZ_FENCE_RE.sub(replace, markdown_content)


SCALAR_LINE_RE = re.compile(
    r'^(?P<prefix>\s*(?:-\s+)?)(?P<key>[A-Za-z_][\w-]*):[ \t]+(?P<value>\S.*?)\s*$'
)
YAML_INDICATORS = ('|', '>', '[', '{', '&', '*', '!', '#', '%', '@', '`')


def needs_quoting(value):
    '''Diz se um escalar YAML quebraria o parse sem aspas.

    Os dois casos que aparecem no acervo: dois-pontos no meio da frase
    ("A ideia central (inspirada na lei europeia): quanto maior o risco")
    e aspas abrindo o valor sem fechá-lo ('"Quanto?" é a resposta').
    '''
    if value[:1] in YAML_INDICATORS:
        return False
    if value[:1] in ('"', "'"):
        return not (len(value) > 1 and value.endswith(value[0]))
    return ': ' in value or value.endswith(':')


def repair_yaml_block(raw_body):
    '''Cita escalares que o autor escreveu sem aspas.

    Aulas são escritas à mão em Markdown; exigir YAML impecável do professor
    faria o aluno pagar o erro com um bloco cru na tela. Só toca em linhas
    `chave: valor` cujo valor quebraria o parse — números e booleanos (o
    índice da alternativa correta, por exemplo) passam intactos.
    '''
    repaired = []
    for line in (raw_body or '').splitlines():
        match = SCALAR_LINE_RE.match(line)
        if match and needs_quoting(match.group('value')):
            value = json.dumps(match.group('value'), ensure_ascii=False)
            repaired.append(f'{match.group("prefix")}{match.group("key")}: {value}')
        else:
            repaired.append(line)
    return '\n'.join(repaired)


def parse_yaml_block(raw_body):
    try:
        return yaml.safe_load(raw_body) or {}
    except yaml.YAMLError:
        pass

    try:
        parsed = yaml.safe_load(repair_yaml_block(raw_body)) or {}
    except yaml.YAMLError:
        logger.warning(
            'Bloco YAML da aula não parseia nem após reparo; será exibido cru. '
            'Trecho: %s',
            (raw_body or '')[:120].replace('\n', ' '),
        )
        return None

    logger.info(
        'Bloco YAML da aula precisou de reparo (escalar sem aspas). Trecho: %s',
        (raw_body or '')[:120].replace('\n', ' '),
    )
    return parsed


def render_custom_blocks(markdown_content):
    def replace(match):
        kind = match.group('kind').lower()
        normalized_kind = 'atencao' if kind == 'atenção' else kind
        title = match.group('title').strip()
        base_label = CALLOUT_LABELS[kind]
        label = escape(f'{base_label} · {title}' if title else base_label)
        icon = CALLOUT_ICONS[normalized_kind]
        body = match.group('body').strip()
        return (
            f'<section class="callout {normalized_kind}" markdown="1">\n'
            f'<div class="ic" aria-hidden="true"><i data-lucide="{icon}"></i></div>\n'
            f'<div class="ct" markdown="1">\n'
            f'<b>{label}</b>\n\n'
            f'{body}\n'
            f'</div>\n'
            f'</section>'
        )

    return BLOCK_RE.sub(replace, markdown_content)
