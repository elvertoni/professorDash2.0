import html
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import bleach
import markdown

COLLECTIONS = {
    'estudar': 'Estudar',
    'preparar-aulas': 'Preparar aulas',
    'projetos': 'Projetos e negócios',
}


def normalize(value):
    return ''.join(
        c
        for c in unicodedata.normalize('NFKD', value.casefold())
        if not unicodedata.combining(c)
    )


def plain_text(body):
    return html.unescape(bleach.clean(markdown.markdown(body), tags=[], strip=True))


def excerpt(body, query):
    text = ' '.join(plain_text(body).split())
    terms = normalize(query).split()
    positions = [normalize(text).find(term) for term in terms]
    found = [position for position in positions if position >= 0]
    start = max(0, min(found) - 70) if found else 0
    return (
        ('…' if start else '')
        + text[start : start + 260]
        + ('…' if len(text) > start + 260 else '')
    )


def resolve_note(target, note, notes):
    target = target.split('#', 1)[0].strip().removesuffix('.md')
    relative = str(PurePosixPath(note.path).parent / target)
    exact = [n for n in notes if n.path.removesuffix('.md') in (target, relative)]
    if len(exact) == 1:
        return exact[0]
    matches = [n for n in notes if target in (n.slug, n.title)]
    return matches[0] if len(matches) == 1 else None


class LinkPolicy(HTMLParser):
    def __init__(self, allowed_links):
        super().__init__(convert_charrefs=False)
        self.allowed_links = allowed_links
        self.parts = []

    def handle_starttag(self, tag, attrs):
        clean = []
        for key, value in attrs:
            if key == 'href':
                try:
                    url = urlsplit(value)
                except ValueError:
                    continue
                if value not in self.allowed_links and not (
                    url.scheme in ('http', 'https') and url.netloc
                ):
                    continue
            clean.append(f' {key}="{html.escape(value or "", quote=True)}"')
        if tag == 'a':
            clean.append(' rel="noreferrer noopener"')
        if tag == 'th':
            clean.append(' scope="col"')
        self.parts.append(f'<{tag}{"".join(clean)}>')

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')


def render_note(note, notes):
    related = {}
    unresolved = set()

    def replace(match):
        target, _, label = match.group(1).partition('|')
        label = label or target
        found = resolve_note(target, note, notes)
        if found and found.pk != note.pk:
            related[found.pk] = found
            return f'<a href="{found.get_absolute_url()}">{html.escape(label)}</a>'
        if not found:
            unresolved.add(target)
        return html.escape(label)

    # Do not reinterpret wiki syntax inside fenced or inline code.
    blocks = re.split(r'(```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`)', note.body)
    body = ''.join(
        part if index % 2 else re.sub(r'\[\[([^\]\n]+)\]\]', replace, part)
        for index, part in enumerate(blocks)
    )
    rendered = markdown.markdown(
        body, extensions=['fenced_code', 'tables', 'sane_lists']
    )
    clean = bleach.clean(
        rendered,
        tags=[
            'p',
            'br',
            'h1',
            'h2',
            'h3',
            'h4',
            'h5',
            'h6',
            'ul',
            'ol',
            'li',
            'strong',
            'em',
            'blockquote',
            'code',
            'pre',
            'a',
            'hr',
            'table',
            'thead',
            'tbody',
            'tr',
            'th',
            'td',
            'del',
        ],
        attributes={'a': ['href', 'title']},
        protocols=['http', 'https'],
        strip=True,
    )
    policy = LinkPolicy({n.get_absolute_url() for n in related.values()})
    policy.feed(clean)
    return ''.join(policy.parts), list(related.values()), sorted(unresolved)
