from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
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
from catalog.parser import sanitize_lesson_html

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
        from activities.models import Atividade, Entrega

        now = timezone.now()
        turmas = list(
            Turma.objects.select_related('disciplina')
            .filter(*([] if can_manage_all(request.user) else [Q(professor=request.user)]))
            .order_by('-ano_letivo', 'nome')
        )
        turma_ids = [turma.pk for turma in turmas]

        aguardando = (
            Entrega.objects.filter(
                atividade__turma__in=turma_ids,
                checked=False,
                status__in=[Entrega.Status.ENTREGUE, Entrega.Status.ATRASADA],
            )
            .select_related('aluno', 'atividade', 'atividade__turma')
            .order_by('data_entrega')
        )

        turma_stats = self.build_turma_stats(turma_ids, Atividade, Entrega)
        prazos = (
            Atividade.objects.filter(
                turma__in=turma_ids,
                publicada=True,
                prazo__gte=now,
                prazo__lte=now + timedelta(days=7),
            )
            .select_related('turma')
            .order_by('prazo')[:8]
        )

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
            'aguardando': aguardando,
            'prazos': prazos,
            'total_turmas': len(turmas),
            'total_alunos': Matricula.objects.filter(
                turma__in=turma_ids, status=Matricula.Status.ATIVA
            ).count(),
            'total_atividades': Atividade.objects.filter(
                turma__in=turma_ids, publicada=True
            ).count(),
            'total_aguardando': aguardando.count(),
        }
        return render(request, self.template_name, context)

    def build_turma_stats(self, turma_ids, Atividade, Entrega):
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

        nota_norm = Case(
            When(atividade__pontuacao_max=0, then=Value(None)),
            default=ExpressionWrapper(
                F('nota') / F('atividade__pontuacao_max'),
                output_field=DecimalField(max_digits=6, decimal_places=4),
            ),
            output_field=DecimalField(max_digits=6, decimal_places=4),
        )
        entregas = (
            Entrega.objects.filter(atividade__turma__in=turma_ids)
            .values('atividade__turma')
            .annotate(
                total=Count('id'),
                a_corrigir=Count(
                    'id',
                    filter=Q(
                        checked=False,
                        status__in=[Entrega.Status.ENTREGUE, Entrega.Status.ATRASADA],
                    ),
                ),
                media=Avg('nota', filter=Q(checked=True)),
                media_norm=Avg(nota_norm, filter=Q(checked=True)),
            )
        )
        for row in entregas:
            data = stats[row['atividade__turma']]
            data['entregas'] = row['total']
            data['a_corrigir'] = row['a_corrigir']
            data['media'] = row['media']
            data['media_norm'] = row['media_norm']

        max_entregas = max(
            (data.get('entregas', 0) for data in stats.values()), default=0
        )
        for data in stats.values():
            alunos = data.get('alunos', 0) or 0
            aulas_total = data.get('aulas', 0) or 0
            concluidas = data.get('concluidas', 0) or 0
            denominador = alunos * aulas_total
            data['conclusao_pct'] = (
                round(concluidas * 100 / denominador) if denominador else 0
            )
            data['media_pct'] = (
                round(float(data['media_norm']) * 100)
                if data.get('media_norm') is not None
                else 0
            )
            data['entregas_pct'] = (
                round(data.get('entregas', 0) * 100 / max_entregas)
                if max_entregas
                else 0
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
        publicadas = (
            AulaPublicada.objects.filter(turma=turma)
            .select_related('aula', 'aula__disciplina', 'aula__trilha')
            .order_by('ordem_na_turma', 'aula__ordem')
        )
        return render(
            request,
            self.template_name,
            {'turma': turma, 'form': form, 'publicadas': publicadas},
        )


class AulaPublicadaActionMixin(TurmaQuerysetMixin):
    def get_turma(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    def get_publicada(self, turma, pk):
        return get_object_or_404(
            AulaPublicada.objects.select_related('aula'), turma=turma, pk=pk
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
        from activities.models import Atividade, Entrega

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
        total_concluidas = sum(
            1 for p in progressos.values()
            if p.aula_publicada_id in [d.id for d in disponiveis] and p.concluido
        )

        # 1. Para fazer hoje & Prazos próximos
        para_fazer_hoje = []
        prazos_proximos = []

        # Aulas liberadas hoje e pendentes
        for publicada in disponiveis:
            progresso = progressos.get(publicada.id)
            concluido = bool(progresso and progresso.concluido)
            if not concluido:
                local_disp = timezone.localtime(publicada.disponivel_em)
                if today_start <= local_disp < today_end:
                    para_fazer_hoje.append({
                        'tipo': 'aula',
                        'obj': publicada,
                        'data': local_disp,
                        'overdue': False,
                    })

        # Atividades pendentes
        atividades_all = Atividade.objects.filter(turma__in=turmas, publicada=True).select_related('turma', 'aula_publicada', 'aula_publicada__aula')
        entregas_dict = {
            e.atividade_id: e
            for e in Entrega.objects.filter(aluno=request.user, atividade__in=atividades_all)
        }

        for atividade in atividades_all:
            entrega = entregas_dict.get(atividade.id)
            status = entrega.status if entrega else Entrega.Status.PENDENTE
            atividade.minha_entrega = entrega
            atividade.meu_status = status

            if status == Entrega.Status.PENDENTE and atividade.aberta_para_entrega:
                if atividade.prazo:
                    local_prazo = timezone.localtime(atividade.prazo)
                    if local_prazo < today_start:
                        # Vencida mas aceita entrega atrasada
                        para_fazer_hoje.append({
                            'tipo': 'atividade',
                            'obj': atividade,
                            'data': local_prazo,
                            'overdue': True,
                        })
                    elif today_start <= local_prazo < today_end:
                        # Vence hoje
                        para_fazer_hoje.append({
                            'tipo': 'atividade',
                            'obj': atividade,
                            'data': local_prazo,
                            'overdue': False,
                        })
                    elif today_end <= local_prazo < today_end + timedelta(days=7):
                        # Prazos nos próximos 7 dias
                        prazos_proximos.append(atividade)

        # Ordenar itens de hoje por data limite/liberação
        para_fazer_hoje.sort(key=lambda x: x['data'] if x['data'] else now)
        prazos_proximos.sort(key=lambda x: x.prazo if x.prazo else now)

        # 3. Últimos feedbacks e notas
        ultimos_feedbacks = (
            Entrega.objects.filter(aluno=request.user, checked=True)
            .select_related('atividade', 'atividade__turma')
            .order_by('-corrigido_em')[:5]
        )

        # Obter as próximas 6 aulas não concluídas (geral) para manter o bloco existente do dashboard
        proximas = []
        for publicada in disponiveis:
            progresso = progressos.get(publicada.id)
            concluida = bool(progresso and progresso.concluido)
            if not concluida and len(proximas) < 6:
                publicada.concluida = False
                proximas.append(publicada)

        context = {
            'turmas': turmas,
            'proximas': proximas,
            'para_fazer_hoje': para_fazer_hoje,
            'prazos_proximos': prazos_proximos,
            'ultimos_feedbacks': ultimos_feedbacks,
            'total_turmas': len(turmas),
            'total_disponiveis': total_disponiveis,
            'total_concluidas': total_concluidas,
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
