import html
import re
from dataclasses import dataclass

import bleach
import markdown
import yaml
from django.utils.html import escape


FRONTMATTER_RE = re.compile(r'\A---\s*\n(?P<yaml>.*?)\n---\s*\n(?P<body>.*)\Z', re.S)
FENCE_RE = re.compile(r'```(?P<kind>diagrama[\w-]*)\n(?P<body>.*?)\n```', re.S)
BLOCK_RE = re.compile(
    r':::(?P<kind>conceito|atencao|atenção|dica)\s*\n(?P<body>.*?)\n:::\s*',
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
    'img': ['alt', 'decoding', 'height', 'loading', 'src', 'title', 'width'],
    'ol': ['start', 'type'],
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
    prepared = render_diagram_fences(markdown_content)
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


def sanitize_lesson_html(html_content):
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
        body = html.escape(match.group('body').strip())
        label = kind.replace('-', ' ').title()
        return (
            f'<figure class="lesson-diagram" data-diagram-type="{kind}">\n'
            f'<figcaption>{label}</figcaption>\n'
            f'<pre><code>{body}</code></pre>\n'
            f'</figure>'
        )

    return FENCE_RE.sub(replace, markdown_content)


def render_custom_blocks(markdown_content):
    def replace(match):
        kind = match.group('kind').lower()
        normalized_kind = 'atencao' if kind == 'atenção' else kind
        label = CALLOUT_LABELS[kind]
        body = match.group('body').strip()
        return (
            f'<section class="lesson-callout lesson-callout-{normalized_kind}" markdown="1">\n'
            f'<p class="lesson-callout-title">{label}</p>\n\n'
            f'{body}\n'
            f'</section>'
        )

    return BLOCK_RE.sub(replace, markdown_content)
