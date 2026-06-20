from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import DetailView, ListView

from classroom.models import Matricula

from .models import Aula, Disciplina
from .parser import sanitize_lesson_html


def user_can_view_full_catalog(user):
    return user.is_superuser or user.role in ('admin', 'professor')


def visible_aulas_for_user(user):
    queryset = Aula.objects.filter(status=Aula.Status.APROVADA)

    if user_can_view_full_catalog(user):
        return queryset

    if user.is_aluno:
        return queryset.filter(
            publicacoes__publicada=True,
            publicacoes__disponivel_em__lte=timezone.now(),
            publicacoes__turma__ativa=True,
            publicacoes__turma__matriculas__aluno=user,
            publicacoes__turma__matriculas__status=Matricula.Status.ATIVA,
        ).distinct()

    return queryset.none()


class AulaListView(LoginRequiredMixin, ListView):
    model = Aula
    template_name = 'catalog/aula_list.html'
    context_object_name = 'aulas'
    paginate_by = 24

    def get_queryset(self):
        queryset = (
            visible_aulas_for_user(self.request.user)
            .select_related('disciplina', 'trilha')
            .order_by('disciplina__label', 'trilha__label', 'ordem')
        )

        disciplina_slug = self.request.GET.get('disciplina')
        trilha_slug = self.request.GET.get('trilha')

        if disciplina_slug:
            queryset = queryset.filter(disciplina__slug=disciplina_slug)
        if trilha_slug:
            queryset = queryset.filter(trilha__slug=trilha_slug)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        disciplinas = Disciplina.objects.prefetch_related('trilhas').order_by('label')
        if not user_can_view_full_catalog(self.request.user):
            visible_aulas = visible_aulas_for_user(self.request.user)
            disciplinas = disciplinas.filter(aulas__in=visible_aulas).distinct()
        context['disciplinas'] = disciplinas
        context['selected_disciplina'] = self.request.GET.get('disciplina', '')
        context['selected_trilha'] = self.request.GET.get('trilha', '')

        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_params'] = query_params.urlencode()

        return context


class AulaDetailView(LoginRequiredMixin, DetailView):
    model = Aula
    template_name = 'catalog/aula_detail.html'
    context_object_name = 'aula'

    def get_queryset(self):
        return (
            visible_aulas_for_user(self.request.user)
            .select_related('disciplina', 'trilha')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aula = self.object
        base_queryset = visible_aulas_for_user(self.request.user).filter(
            disciplina=aula.disciplina,
            trilha=aula.trilha,
        )
        context['lesson_html'] = sanitize_lesson_html(aula.conteudo_html)
        context['previous_aula'] = (
            base_queryset.filter(ordem__lt=aula.ordem).order_by('-ordem').first()
        )
        context['next_aula'] = (
            base_queryset.filter(ordem__gt=aula.ordem).order_by('ordem').first()
        )

        if self.request.user.is_authenticated and self.request.user.role in ('admin', 'professor'):
            from classroom.models import Turma
            from classroom.views import can_manage_all

            queryset = Turma.objects.filter(ativa=True)
            if not can_manage_all(self.request.user):
                queryset = queryset.filter(professor=self.request.user)
            context['minhas_turmas'] = queryset.order_by('nome')

        return context
