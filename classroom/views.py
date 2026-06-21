import tempfile
from collections import defaultdict
from datetime import timedelta
from io import StringIO

from django.contrib import messages
from django.core.management import call_command
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Prefetch,
    Q,
    Value,
    When,
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import AlunoRequiredMixin, ProfessorRequiredMixin
from accounts.models import User
from catalog.models import Aula
from catalog.parser import render_teacher_notes_html, sanitize_lesson_html
from catalog.services import AcervoDownloadError, download_acervo

from .forms import (
    AulaPublicadaEditForm,
    AulaPublicadaForm,
    StudentCsvImportForm,
    StudentEnrollmentForm,
    TurmaAdminForm,
    TurmaForm,
)
from .models import AulaPublicada, Matricula, ProgressoAula, Turma
from .services import import_students_from_csv


def can_manage_all(user):
    return user.is_superuser or user.role == User.Role.ADMIN


class TurmaQuerysetMixin(ProfessorRequiredMixin):
    model = Turma

    def get_queryset(self):
        queryset = (
            Turma.objects.select_related('disciplina', 'professor')
            .annotate(
                active_students=Count(
                    'matriculas',
                    filter=Q(matriculas__status=Matricula.Status.ATIVA),
                )
            )
            .order_by('-ano_letivo', 'nome')
        )

        if can_manage_all(self.request.user):
            return queryset

        return queryset.filter(professor=self.request.user)


class ProfessorDashboardView(ProfessorRequiredMixin, View):
    template_name = 'classroom/professor_dashboard.html'

    def get(self, request):
        turmas = list(
            Turma.objects.select_related('disciplina')
            .filter(*([] if can_manage_all(request.user) else [Q(professor=request.user)]))
            .order_by('-ano_letivo', 'nome')
        )
        turma_ids = [turma.pk for turma in turmas]

        turma_stats = self.build_turma_stats(turma_ids)
        for turma in turmas:
            turma.stats = turma_stats.get(turma.pk, {})

        turmas_by_serie = defaultdict(list)
        for turma in turmas:
            turmas_by_serie[turma.serie or 'Sem série'].append(turma)

        series_list = [
            {
                'nome': serie,
                'turmas': serie_turmas,
                'total_alunos': sum(t.stats.get('alunos', 0) for t in serie_turmas),
                'total_aulas': sum(t.stats.get('aulas', 0) for t in serie_turmas),
            }
            for serie, serie_turmas in sorted(turmas_by_serie.items())
        ]

        context = {
            'turmas': turmas,
            'series_list': series_list,
            'total_turmas': len(turmas),
            'total_alunos': Matricula.objects.filter(
                turma__in=turma_ids, status=Matricula.Status.ATIVA
            ).count(),
        }
        return render(request, self.template_name, context)

    def build_turma_stats(self, turma_ids):
        if not turma_ids:
            return {}

        stats = {pk: {} for pk in turma_ids}

        students = (
            Matricula.objects.filter(
                turma__in=turma_ids, status=Matricula.Status.ATIVA
            )
            .values('turma')
            .annotate(total=Count('id'))
        )
        for row in students:
            stats[row['turma']]['alunos'] = row['total']

        aulas = (
            AulaPublicada.objects.available()
            .filter(turma__in=turma_ids)
            .values('turma')
            .annotate(total=Count('id'))
        )
        for row in aulas:
            stats[row['turma']]['aulas'] = row['total']

        concluidas = (
            ProgressoAula.objects.filter(
                aula_publicada__turma__in=turma_ids, concluido=True
            )
            .values('aula_publicada__turma')
            .annotate(total=Count('id'))
        )
        for row in concluidas:
            stats[row['aula_publicada__turma']]['concluidas'] = row['total']

        for data in stats.values():
            alunos = data.get('alunos', 0) or 0
            aulas_total = data.get('aulas', 0) or 0
            concluidas_n = data.get('concluidas', 0) or 0
            denominador = alunos * aulas_total
            data['conclusao_pct'] = (
                round(concluidas_n * 100 / denominador) if denominador else 0
            )

        return stats


class TurmaListView(TurmaQuerysetMixin, ListView):
    template_name = 'classroom/turma_list.html'
    context_object_name = 'turmas'
    paginate_by = 12


class TurmaDetailView(TurmaQuerysetMixin, DetailView):
    template_name = 'classroom/turma_detail.html'
    context_object_name = 'turma'

    def get_queryset(self):
        matriculas = Matricula.objects.select_related(
            'aluno',
            'aluno__aluno_profile',
        ).order_by('status', 'aluno__nome_completo')
        return super().get_queryset().prefetch_related(
            Prefetch('matriculas', queryset=matriculas)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        matriculas = list(self.object.matriculas.all())
        context['active_matriculas'] = [
            item for item in matriculas if item.status == Matricula.Status.ATIVA
        ]
        context['inactive_matriculas'] = [
            item for item in matriculas if item.status == Matricula.Status.INATIVA
        ]
        return context


class TurmaFormMixin(TurmaQuerysetMixin):
    template_name = 'classroom/turma_form.html'

    def get_form_class(self):
        if can_manage_all(self.request.user):
            return TurmaAdminForm
        return TurmaForm

    def form_valid(self, form):
        if not can_manage_all(self.request.user):
            form.instance.professor = self.request.user
        messages.success(self.request, 'Turma salva com sucesso.')
        return super().form_valid(form)


class TurmaCreateView(TurmaFormMixin, CreateView):
    pass


class TurmaUpdateView(TurmaFormMixin, UpdateView):
    pass


class TurmaDeleteView(TurmaQuerysetMixin, DeleteView):
    template_name = 'classroom/turma_confirm_delete.html'

    def get_success_url(self):
        return reverse('classroom:turma_list')

    def form_valid(self, form):
        messages.success(self.request, 'Turma excluída com sucesso.')
        return super().form_valid(form)


class RegenerateInviteCodeView(TurmaQuerysetMixin, View):
    def post(self, request, pk):
        turma = get_object_or_404(self.get_queryset(), pk=pk)
        turma.regenerate_invite_code()
        messages.success(request, 'Código de convite renovado com sucesso.')
        return redirect(turma)


class MatriculaCreateView(TurmaQuerysetMixin, View):
    template_name = 'classroom/matricula_form.html'

    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        form = StudentEnrollmentForm(turma=turma)
        return self.render_form(request, turma, form)

    def post(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        form = StudentEnrollmentForm(request.POST, turma=turma)

        if form.is_valid():
            matricula, created = form.save()
            if created:
                messages.success(request, 'Aluno matriculado com sucesso.')
            else:
                messages.success(request, 'Aluno atualizado e matrícula reativada.')
            return redirect(matricula.turma)

        return self.render_form(request, turma, form)

    def get_turma(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def render_form(self, request, turma, form):
        return render(
            request,
            self.template_name,
            {
                'turma': turma,
                'form': form,
                'title': 'Matricular aluno',
                'submit_label': 'Salvar matrícula',
            },
        )


class MatriculaUpdateView(TurmaQuerysetMixin, View):
    template_name = 'classroom/matricula_form.html'

    def get(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        matricula = self.get_matricula(turma, pk)
        form = StudentEnrollmentForm(turma=turma, instance=matricula)
        return self.render_form(request, turma, matricula, form)

    def post(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        matricula = self.get_matricula(turma, pk)
        form = StudentEnrollmentForm(request.POST, turma=turma, instance=matricula)

        if form.is_valid():
            form.save()
            messages.success(request, 'Aluno atualizado com sucesso.')
            return redirect(turma)

        return self.render_form(request, turma, matricula, form)

    def get_turma(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_matricula(self, turma, pk):
        return get_object_or_404(Matricula.objects.select_related('aluno'), turma=turma, pk=pk)

    def render_form(self, request, turma, matricula, form):
        return render(
            request,
            self.template_name,
            {
                'turma': turma,
                'matricula': matricula,
                'form': form,
                'title': 'Editar aluno',
                'submit_label': 'Salvar aluno',
            },
        )


class MatriculaDeleteView(TurmaQuerysetMixin, View):
    template_name = 'classroom/matricula_confirm_delete.html'

    def get(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        matricula = self.get_matricula(turma, pk)
        return render(
            request,
            self.template_name,
            {'turma': turma, 'matricula': matricula},
        )

    def post(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        matricula = self.get_matricula(turma, pk)
        matricula.deactivate()
        messages.success(request, 'Aluno desmatriculado da turma.')
        return redirect(turma)

    def get_turma(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_matricula(self, turma, pk):
        return get_object_or_404(Matricula.objects.select_related('aluno'), turma=turma, pk=pk)


class StudentCsvImportView(TurmaQuerysetMixin, View):
    template_name = 'classroom/matricula_import.html'

    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        form = StudentCsvImportForm()
        return self.render_form(request, turma, form)

    def post(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        form = StudentCsvImportForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                report = import_students_from_csv(turma, form.cleaned_data['file'])
            except UnicodeDecodeError:
                form.add_error('file', 'Envie um CSV em UTF-8.')
                return self.render_form(request, turma, form)

            if report['errors']:
                messages.error(
                    request,
                    'Importação concluída com erros. Revise as linhas indicadas.',
                )
                return self.render_form(request, turma, form, report)

            messages.success(
                request,
                (
                    f'Importação concluída: {report["created"]} alunos criados, '
                    f'{report["updated"]} atualizados.'
                ),
            )
            return redirect(turma)

        return self.render_form(request, turma, form)

    def get_turma(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def render_form(self, request, turma, form, report=None):
        return render(
            request,
            self.template_name,
            {
                'turma': turma,
                'form': form,
                'report': report,
            },
        )


# --- Sprint 4: publicação de aulas por turma (professor) ---


class AulaPublicadaManageView(TurmaQuerysetMixin, View):
    template_name = 'classroom/aula_publicada_manage.html'

    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        aula_id = request.GET.get('aula')
        initial = {}
        if aula_id:
            initial['aula'] = aula_id
        return self.render_page(request, turma, AulaPublicadaForm(turma=turma, initial=initial))

    def post(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        form = AulaPublicadaForm(request.POST, turma=turma)
        if form.is_valid():
            form.save()
            messages.success(request, 'Aula publicada na turma.')
            return redirect('classroom:turma_aulas', turma_pk=turma.pk)
        return self.render_page(request, turma, form)

    def get_turma(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def render_page(self, request, turma, form):
        publicadas = list(
            AulaPublicada.objects.filter(turma=turma)
            .select_related('aula', 'aula__disciplina', 'aula__trilha')
            .order_by('ordem_na_turma', 'aula__ordem')
        )
        now = timezone.now()
        stats = {
            'total': len(publicadas),
            'visiveis': sum(
                1
                for item in publicadas
                if item.publicada and item.disponivel_em <= now
            ),
            'agendadas': sum(
                1
                for item in publicadas
                if item.publicada and item.disponivel_em > now
            ),
            'ocultas': sum(1 for item in publicadas if not item.publicada),
            'catalogo_disponivel': form.fields['aula'].queryset.count(),
        }
        return render(
            request,
            self.template_name,
            {
                'turma': turma,
                'form': form,
                'publicadas': publicadas,
                'stats': stats,
            },
        )


class TurmaSyncAulasView(TurmaQuerysetMixin, View):
    '''Sincroniza as aulas da disciplina da turma com o head e publica todas.'''

    def post(self, request, turma_pk):
        turma = get_object_or_404(self.get_queryset(), pk=turma_pk)
        disciplina = turma.disciplina
        import_error = None

        try:
            with tempfile.TemporaryDirectory(prefix='acervo-') as tmp_dir:
                root = download_acervo(tmp_dir)
                out = StringIO()
                call_command(
                    'import_acervo',
                    path=str(root),
                    only_aprovada=True,
                    disciplina=disciplina.slug,
                    stdout=out,
                    stderr=out,
                )
        except AcervoDownloadError as exc:
            import_error = 'Falha ao atualizar do GitHub: {0}'.format(exc)
        except Exception as exc:  # noqa: BLE001 — surfacing import failures to the UI
            import_error = 'Erro inesperado ao atualizar do GitHub: {0}'.format(exc)

        now = timezone.now()
        aulas = Aula.objects.filter(
            disciplina=disciplina, status=Aula.Status.APROVADA
        )
        if not aulas.exists():
            if import_error:
                messages.error(request, import_error)
            messages.error(
                request,
                'Nenhuma aula aprovada encontrada para {0}.'.format(
                    disciplina.label
                ),
            )
            return redirect('classroom:turma_aulas', turma_pk=turma.pk)

        novas = 0
        atualizadas = 0
        for aula in aulas:
            publicada, created = AulaPublicada.objects.get_or_create(
                turma=turma,
                aula=aula,
                defaults={
                    'disponivel_em': now,
                    'ordem_na_turma': aula.ordem,
                    'publicada': True,
                },
            )
            if created:
                novas += 1
                continue

            fields = []
            if not publicada.publicada:
                publicada.publicada = True
                fields.append('publicada')
            if publicada.disponivel_em > now:
                publicada.disponivel_em = now
                fields.append('disponivel_em')
            if fields:
                publicada.save(update_fields=[*fields, 'updated_at'])
                atualizadas += 1

        if import_error:
            messages.warning(
                request,
                '{0} A publicação usou as aulas já importadas no catálogo.'.format(
                    import_error
                ),
            )

        messages.success(
            request,
            (
                'Aulas sincronizadas: {0} disponíveis na turma '
                '({1} novas, {2} reativadas/agora liberadas).'
            ).format(
                aulas.count(), novas, atualizadas
            ),
        )
        return redirect('classroom:turma_aulas', turma_pk=turma.pk)


class AulaPublicadaActionMixin(TurmaQuerysetMixin):
    def get_turma(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_publicada(self, turma, pk):
        return get_object_or_404(
            AulaPublicada.objects.select_related(
                'aula',
                'aula__disciplina',
                'aula__trilha',
                'turma',
            ),
            turma=turma,
            pk=pk,
        )


class AulaPublicadaPreviewView(AulaPublicadaActionMixin, View):
    template_name = 'classroom/aula_publicada_preview.html'

    def get(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        publicada = self.get_publicada(turma, pk)
        ordered = list(
            AulaPublicada.objects.filter(turma=turma)
            .select_related('aula')
            .order_by('ordem_na_turma', 'aula__ordem')
        )
        index = next((i for i, item in enumerate(ordered) if item.pk == pk), None)
        previous_aula = ordered[index - 1] if index not in (None, 0) else None
        next_aula = (
            ordered[index + 1]
            if index is not None and index < len(ordered) - 1
            else None
        )
        aula = publicada.aula
        return render(
            request,
            self.template_name,
            {
                'turma': turma,
                'publicada': publicada,
                'aula': aula,
                'lesson_html': sanitize_lesson_html(aula.conteudo_html),
                'teacher_notes_html': render_teacher_notes_html(aula.conteudo_md),
                'previous_aula': previous_aula,
                'next_aula': next_aula,
            },
        )


class AulaPublicadaUpdateView(AulaPublicadaActionMixin, View):
    template_name = 'classroom/aula_publicada_form.html'

    def get(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        publicada = self.get_publicada(turma, pk)
        form = AulaPublicadaEditForm(instance=publicada)
        return self.render_form(request, turma, publicada, form)

    def post(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        publicada = self.get_publicada(turma, pk)
        form = AulaPublicadaEditForm(request.POST, instance=publicada)
        if form.is_valid():
            form.save()
            messages.success(request, 'Publicação atualizada.')
            return redirect('classroom:turma_aulas', turma_pk=turma.pk)
        return self.render_form(request, turma, publicada, form)

    def render_form(self, request, turma, publicada, form):
        return render(
            request,
            self.template_name,
            {'turma': turma, 'publicada': publicada, 'form': form},
        )


class AulaPublicadaToggleView(AulaPublicadaActionMixin, View):
    def get(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        publicada = self.get_publicada(turma, pk)
        if publicada.publicada:
            return render(
                request,
                'classroom/aula_publicada_confirm_toggle.html',
                {'turma': turma, 'publicada': publicada},
            )
        return redirect('classroom:turma_aulas', turma_pk=turma.pk)

    def post(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        publicada = self.get_publicada(turma, pk)
        publicada.publicada = not publicada.publicada
        publicada.save(update_fields=['publicada', 'updated_at'])
        if publicada.publicada:
            messages.success(request, 'Aula publicada para a turma.')
        else:
            messages.success(request, 'Aula despublicada da turma.')
        return redirect('classroom:turma_aulas', turma_pk=turma.pk)


class AulaPublicadaDeleteView(AulaPublicadaActionMixin, View):
    def get(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        publicada = self.get_publicada(turma, pk)
        return render(
            request,
            'classroom/aula_publicada_confirm_delete.html',
            {'turma': turma, 'publicada': publicada},
        )

    def post(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        publicada = self.get_publicada(turma, pk)
        publicada.delete()
        messages.success(request, 'Aula removida da turma.')
        return redirect('classroom:turma_aulas', turma_pk=turma.pk)


class AulaPublicadaReorderView(AulaPublicadaActionMixin, View):
    def post(self, request, turma_pk, pk):
        turma = self.get_turma(turma_pk)
        direction = request.POST.get('direction')
        items = list(
            AulaPublicada.objects.filter(turma=turma).order_by(
                'ordem_na_turma', 'aula__ordem'
            )
        )
        index = next((i for i, item in enumerate(items) if item.pk == pk), None)
        if index is not None:
            if direction == 'up' and index > 0:
                items[index - 1], items[index] = items[index], items[index - 1]
            elif direction == 'down' and index < len(items) - 1:
                items[index + 1], items[index] = items[index], items[index + 1]
            for position, item in enumerate(items, start=1):
                if item.ordem_na_turma != position:
                    item.ordem_na_turma = position
                    item.save(update_fields=['ordem_na_turma', 'updated_at'])
        return redirect('classroom:turma_aulas', turma_pk=turma.pk)


# --- Sprints 4 e 5: experiência do aluno ---


class AlunoTurmasMixin(AlunoRequiredMixin):
    def get_active_turmas(self):
        return (
            Turma.objects.filter(
                matriculas__aluno=self.request.user,
                matriculas__status=Matricula.Status.ATIVA,
            )
            .select_related('disciplina', 'professor')
            .distinct()
            .order_by('-ano_letivo', 'nome')
        )

    def get_turma_for_aluno(self, turma_pk):
        return get_object_or_404(self.get_active_turmas(), pk=turma_pk)


class AlunoDashboardView(AlunoTurmasMixin, View):
    template_name = 'classroom/aluno_dashboard.html'

    def get(self, request):
        turmas = list(self.get_active_turmas())
        now = timezone.now()
        local_now = timezone.localtime(now)
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        progressos = {
            progresso.aula_publicada_id: progresso
            for progresso in ProgressoAula.objects.filter(aluno=request.user)
        }
        disponiveis = list(
            AulaPublicada.objects.available(now)
            .filter(turma__in=turmas)
            .select_related('aula', 'turma', 'aula__disciplina')
            .order_by('-disponivel_em')
        )

        total_disponiveis = len(disponiveis)
        disponivel_ids = {d.id for d in disponiveis}
        total_concluidas = sum(
            1 for p in progressos.values()
            if p.aula_publicada_id in disponivel_ids and p.concluido
        )

        para_fazer_hoje = []
        proximas = []
        for publicada in disponiveis:
            progresso = progressos.get(publicada.id)
            if progresso and progresso.concluido:
                continue
            local_disp = timezone.localtime(publicada.disponivel_em)
            if today_start <= local_disp < today_end:
                para_fazer_hoje.append({
                    'tipo': 'aula',
                    'obj': publicada,
                    'data': local_disp,
                })
            if len(proximas) < 6:
                publicada.concluida = False
                proximas.append(publicada)

        para_fazer_hoje.sort(key=lambda x: x['data'] if x['data'] else now)

        progresso_pct = (
            round(total_concluidas * 100 / total_disponiveis)
            if total_disponiveis else 0
        )

        context = {
            'turmas': turmas,
            'proximas': proximas,
            'para_fazer_hoje': para_fazer_hoje,
            'total_turmas': len(turmas),
            'total_disponiveis': total_disponiveis,
            'total_concluidas': total_concluidas,
            'progresso_pct': progresso_pct,
        }
        return render(request, self.template_name, context)


class AlunoTurmaAulasView(AlunoTurmasMixin, View):
    template_name = 'classroom/aluno_turma_aulas.html'

    def get(self, request, turma_pk):
        turma = self.get_turma_for_aluno(turma_pk)
        progressos = {
            progresso.aula_publicada_id: progresso
            for progresso in ProgressoAula.objects.filter(aluno=request.user)
        }
        publicadas = list(
            AulaPublicada.objects.available()
            .filter(turma=turma)
            .select_related('aula', 'aula__disciplina', 'aula__trilha')
            .order_by('ordem_na_turma', 'aula__ordem')
        )
        for publicada in publicadas:
            progresso = progressos.get(publicada.id)
            publicada.concluida = bool(progresso and progresso.concluido)
        concluidas = sum(1 for item in publicadas if item.concluida)
        context = {
            'turma': turma,
            'publicadas': publicadas,
            'total': len(publicadas),
            'concluidas': concluidas,
        }
        return render(request, self.template_name, context)


class AlunoAulaDetailView(AlunoTurmasMixin, View):
    template_name = 'classroom/aluno_aula_detail.html'

    def get(self, request, pk):
        publicada = self.get_publicada(pk)
        turma = publicada.turma
        ordered = list(
            AulaPublicada.objects.available()
            .filter(turma=turma)
            .select_related('aula')
            .order_by('ordem_na_turma', 'aula__ordem')
        )
        index = next((i for i, item in enumerate(ordered) if item.pk == pk), None)
        previous_aula = ordered[index - 1] if index not in (None, 0) else None
        next_aula = (
            ordered[index + 1]
            if index is not None and index < len(ordered) - 1
            else None
        )
        progresso, _ = ProgressoAula.objects.get_or_create(
            aluno=request.user, aula_publicada=publicada
        )
        context = {
            'turma': turma,
            'publicada': publicada,
            'aula': publicada.aula,
            'lesson_html': sanitize_lesson_html(publicada.aula.conteudo_html),
            'progresso': progresso,
            'previous_aula': previous_aula,
            'next_aula': next_aula,
        }
        return render(request, self.template_name, context)

    def get_publicada(self, pk):
        turmas = self.get_active_turmas()
        return get_object_or_404(
            AulaPublicada.objects.available()
            .filter(turma__in=turmas)
            .select_related('aula', 'aula__disciplina', 'aula__trilha', 'turma'),
            pk=pk,
        )


class ProgressoToggleView(AlunoTurmasMixin, View):
    def post(self, request, pk):
        turmas = self.get_active_turmas()
        publicada = get_object_or_404(
            AulaPublicada.objects.available().filter(turma__in=turmas), pk=pk
        )
        progresso, _ = ProgressoAula.objects.get_or_create(
            aluno=request.user, aula_publicada=publicada
        )
        if progresso.concluido:
            progresso.mark_undone()
            messages.success(request, 'Aula marcada como não concluída.')
        else:
            progresso.mark_done()
            messages.success(request, 'Aula marcada como concluída.')
        return redirect('classroom:aluno_aula_detail', pk=publicada.pk)


# --- Sprint 10: relatórios (PDF/CSV) ---


def _pdf_response(content, filename):
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


class TurmaRelatorioPdfView(TurmaQuerysetMixin, View):
    def get(self, request, pk):
        from .reports import build_turma_report_pdf

        turma = get_object_or_404(self.get_queryset(), pk=pk)
        content = build_turma_report_pdf(turma)
        return _pdf_response(content, f'relatorio-{slugify(turma.nome)}.pdf')


class TurmaRelatorioCsvView(TurmaQuerysetMixin, View):
    def get(self, request, pk):
        from .reports import build_turma_report_csv

        turma = get_object_or_404(self.get_queryset(), pk=pk)
        content = build_turma_report_csv(turma)
        response = HttpResponse(
            '﻿' + content, content_type='text/csv; charset=utf-8'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="relatorio-{slugify(turma.nome)}.csv"'
        )
        return response


class TurmaBoletimPdfView(TurmaQuerysetMixin, View):
    def get(self, request, turma_pk, pk):
        from .reports import build_boletim_pdf

        turma = get_object_or_404(self.get_queryset(), pk=turma_pk)
        matricula = get_object_or_404(
            Matricula.objects.select_related('aluno'), turma=turma, pk=pk
        )
        content = build_boletim_pdf(turma, matricula.aluno)
        return _pdf_response(
            content, f'boletim-{slugify(matricula.aluno.nome_completo)}.pdf'
        )


class AlunoBoletimPdfView(AlunoTurmasMixin, View):
    def get(self, request, turma_pk):
        from .reports import build_boletim_pdf

        turma = self.get_turma_for_aluno(turma_pk)
        content = build_boletim_pdf(turma, request.user)
        return _pdf_response(content, f'boletim-{slugify(turma.nome)}.pdf')
