import html
import re
from dataclasses import dataclass

import bleach
import markdown
import yaml
from django.utils.html import escape


FRONTMATTER_RE = re.compile(r'\A---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)\Z', re.S)
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

ALLOWED_LESSON_ATTRIBUTES = {
    '*': ['aria-hidden', 'aria-label', 'class', 'id', 'role', 'title'],
    'a': ['href', 'title'],
    'figure': ['class', 'data-diagram-type'],
    'i': ['aria-hidden', 'class', 'data-lucide'],
    'img': ['alt', 'decoding', 'height', 'loading', 'src', 'title', 'width'],
    'ol': ['class', 'start', 'type'],
    'td': ['align', 'colspan', 'rowspan'],
    'th': ['align', 'colspan', 'rowspan', 'scope'],
}

ALLOWED_LESSON_PROTOCOLS = frozenset({'http', 'https', 'mailto'})


@dataclass(frozen=True)
class ParsedLesson:
    frontmatter: dict
    body: str
    html: str


def parse_lesson_markdown(content):
    frontmatter, body = split_frontmatter(content)
    html_content = render_lesson_html(body)
    return ParsedLesson(frontmatter=frontmatter, body=body, html=html_content)


def split_frontmatter(content):
    match = FRONTMATTER_RE.match(content.strip())
    if not match:
        return {}, content

    data = yaml.safe_load(match.group('yaml')) or {}
    if not isinstance(data, dict):
        data = {}

    return data, match.group('body')


def render_lesson_html(markdown_content):
    prepared = strip_teacher_notes(markdown_content)
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
    return sanitize_lesson_html(rendered)


def strip_teacher_notes(markdown_content):
    return TEACHER_NOTE_RE.sub('', markdown_content or '')


def render_teacher_notes_html(markdown_content):
    notes = [
        match.group('body').strip()
        for match in TEACHER_NOTE_RE.finditer(markdown_content or '')
        if match.group('body').strip()
    ]
    if not notes:
        return ''

    rendered = markdown.markdown(
        '\n\n---\n\n'.join(notes),
        extensions=['extra', 'sane_lists'],
        output_format='html5',
    )
    return sanitize_lesson_html(rendered)


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
                title = escape(str(layer.get('rotulo') or f'Etapa {index}'))
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

        questions = []
        for q_index, question in enumerate(data, start=1):
            if not isinstance(question, dict):
                continue
            prompt = escape(str(question.get('pergunta') or f'Questão {q_index}'))
            alternatives = []
            for alt in question.get('alternativas') or []:
                if not isinstance(alt, dict):
                    continue
                text = escape(str(alt.get('texto') or ''))
                if text:
                    alternatives.append(f'<li>{text}</li>')
            alternatives_html = ''.join(alternatives)
            questions.append(
                '<li class="lesson-quiz-question">'
                f'<p><strong>Questão {q_index}.</strong> {prompt}</p>'
                f'<ol type="A">{alternatives_html}</ol>'
                '</li>'
            )

        if not questions:
            return ''

        return (
            '<section class="lesson-quiz">\n'
            '<div class="lesson-quiz-head">\n'
            '<strong>Quiz</strong>\n'
            '<span>Avaliação formativa</span>\n'
            '</div>\n'
            f'<ol class="lesson-quiz-list">{"".join(questions)}</ol>\n'
            '</section>'
        )

    return QUIZ_FENCE_RE.sub(replace, markdown_content)


def parse_yaml_block(raw_body):
    try:
        return yaml.safe_load(raw_body) or {}
    except yaml.YAMLError:
        return None


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
