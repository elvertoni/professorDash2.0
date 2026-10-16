import re

from django.db.models import Case, IntegerField, Value, When
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import DetailView, ListView

from catalog.models import Aula
from .access import LibraryOwnerMixin
from .content import COLLECTIONS, excerpt, normalize, render_note
from .models import Note, Source


@method_decorator(never_cache, name='dispatch')
class NoteListView(LibraryOwnerMixin, ListView):
    model = Note
    template_name = 'library/note_list.html'
    context_object_name = 'notes'
    paginate_by = 20

    def get_queryset(self):
        queryset = Note.objects.filter(source__owner=self.request.user).select_related(
            'source'
        )
        query = self.request.GET.get('q', '').strip()[:200]
        for token in normalize(query).split()[:12]:
            queryset = queryset.filter(search_text__contains=token)
        for parameter, field in [
            ('source', 'source__key'),
            ('topic', 'topic'),
            ('status', 'status'),
        ]:
            value = self.request.GET.get(parameter, '').strip()
            if value:
                queryset = queryset.filter(**{field: value})
        if not self.request.GET.get('status'):
            queryset = queryset.exclude(status='obsoleto')
        collection = self.request.GET.get('collection', '')
        if collection:
            queryset = queryset.filter(collections__contains=[collection])
        if query:
            queryset = queryset.annotate(
                priority=Case(
                    When(search_title=normalize(query), then=Value(0)),
                    When(search_title__contains=normalize(query), then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            ).order_by('priority', 'title', 'pk')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        owned = Note.objects.filter(source__owner=self.request.user)
        context.update(
            query=self.request.GET.get('q', '')[:200],
            sources=Source.objects.filter(owner=self.request.user).order_by('label'),
            topics=owned.order_by('topic').values_list('topic', flat=True).distinct(),
            statuses=owned.order_by('status')
            .values_list('status', flat=True)
            .distinct(),
            collections=COLLECTIONS,
            selected=self.request.GET,
            has_notes=owned.exists(),
        )
        for note in context['notes']:
            note.excerpt = excerpt(note.body, context['query'])
        return context


@method_decorator(never_cache, name='dispatch')
class NoteDetailView(LibraryOwnerMixin, DetailView):
    model = Note
    template_name = 'library/note_detail.html'
    context_object_name = 'note'

    def get_queryset(self):
        return Note.objects.filter(source__owner=self.request.user).select_related(
            'source'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        note = self.object
        peers = list(Note.objects.filter(source=note.source))
        rendered, related, unresolved = render_note(note, peers)
        # Number-only references are ambiguous across tracks and must not be guessed.
        paths = set(
            re.findall(
                r'aulas/([\w-]+)/([\w-]+)/(\d+)-([\w-]+)/canonica\.md', note.body
            )
        )
        lessons = []
        if note.source.key == 'prof-toni':
            for discipline, track, order, slug in sorted(paths):
                lesson = Aula.objects.filter(
                    disciplina__slug=discipline,
                    trilha__slug=track,
                    ordem=int(order),
                    slug=slug,
                    status=Aula.Status.APROVADA,
                ).first()
                if lesson:
                    lessons.append(lesson)
        context.update(
            note_html=rendered,
            related=related,
            unresolved=unresolved,
            lessons=lessons,
            reference=f'{note.title} — {note.source.label} — {note.path}',
        )
        return context
