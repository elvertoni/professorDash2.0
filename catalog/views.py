import tempfile
from io import StringIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.management import call_command
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.mixins import AdminRequiredMixin
from classroom.models import Matricula

from .models import Aula, Disciplina
from .parser import sanitize_lesson_html
from .services import AcervoDownloadError, download_acervo


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


class AcervoGithubImportView(AdminRequiredMixin, View):
    '''Baixa o acervo PROF-TONI do GitHub e roda o import (admin apenas).'''

    def post(self, request, *args, **kwargs):
        disciplina_slug = (request.POST.get('disciplina') or '').strip()
        redirect_target = request.POST.get('next') or 'catalog:aula_list'

        try:
            with tempfile.TemporaryDirectory(prefix='acervo-') as tmp_dir:
                root = download_acervo(tmp_dir)
                out = StringIO()
                command_kwargs = {
                    'path': str(root),
                    'only_aprovada': True,
                    'force': True,
                    'stdout': out,
                    'stderr': out,
                }
                if disciplina_slug:
                    command_kwargs['disciplina'] = disciplina_slug
                call_command('import_acervo', **command_kwargs)
        except AcervoDownloadError as exc:
            messages.error(request, 'Falha ao importar do GitHub: {0}'.format(exc))
            return self._redirect(redirect_target, disciplina_slug)
        except Exception as exc:  # noqa: BLE001 — surface any import failure to the UI
            messages.error(
                request, 'Erro inesperado na importação: {0}'.format(exc)
            )
            return self._redirect(redirect_target, disciplina_slug)

        summary = out.getvalue().strip().splitlines()
        scope = (
            'matéria "{0}"'.format(disciplina_slug)
            if disciplina_slug
            else 'acervo completo'
        )
        messages.success(
            request,
            'Importação concluída ({0}). {1}'.format(
                scope, summary[-1] if summary else ''
            ),
        )
        return self._redirect(redirect_target, disciplina_slug)

    def _redirect(self, target, disciplina_slug):
        if target == 'catalog:aula_list' and disciplina_slug:
            url = reverse('catalog:aula_list')
            return redirect('{0}?disciplina={1}'.format(url, disciplina_slug))
        if target.startswith('/'):
            return redirect(target)
        return redirect(target)


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
