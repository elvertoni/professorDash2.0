from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from accounts.mixins import ProfessorRequiredMixin
from classroom.models import Matricula, Turma
from classroom.views import can_manage_all

from .forms import AtividadeForm
from .models import Atividade, AtividadeCheck


class ProfessorTurmaMixin(ProfessorRequiredMixin):
    def get_turma_queryset(self):
        queryset = Turma.objects.select_related('disciplina', 'professor')
        if can_manage_all(self.request.user):
            return queryset
        return queryset.filter(professor=self.request.user)

    def get_turma(self, turma_pk):
        return get_object_or_404(self.get_turma_queryset(), pk=turma_pk)

    def get_atividade_queryset(self):
        return Atividade.objects.filter(turma__in=self.get_turma_queryset())

    def get_atividade(self, pk):
        return get_object_or_404(
            self.get_atividade_queryset().select_related('turma'), pk=pk
        )

    def active_matriculas(self, turma):
        return (
            Matricula.objects.filter(turma=turma, status=Matricula.Status.ATIVA)
            .select_related('aluno')
            .order_by('aluno__nome_completo')
        )


class AtividadeListView(ProfessorTurmaMixin, View):
    template_name = 'activities/atividade_list.html'

    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        active_students = self.active_matriculas(turma)
        atividades = list(Atividade.objects.filter(turma=turma).order_by('data', 'created_at'))

        # Fetch all checks for these activities
        checks = AtividadeCheck.objects.filter(atividade__in=atividades)
        # Create a mapping: (aluno_id, atividade_id) -> check
        checks_map = {
            (check.aluno_id, check.atividade_id): check
            for check in checks
        }

        # Build grid rows
        grid_rows = []
        for idx, matricula in enumerate(active_students, start=1):
            student = matricula.aluno
            student_checks = []
            for act in atividades:
                check = checks_map.get((student.id, act.id))
                student_checks.append({
                    'atividade': act,
                    'check': check,
                })
            grid_rows.append({
                'counter': f'{idx:02d}',
                'aluno': student,
                'checks': student_checks,
            })

        return render(
            request,
            self.template_name,
            {
                'turma': turma,
                'atividades': atividades,
                'grid_rows': grid_rows,
                'total_alunos': len(active_students),
            },
        )

    def post(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        active_students = self.active_matriculas(turma)
        atividades = Atividade.objects.filter(turma=turma)
        now = timezone.now()

        with transaction.atomic():
            for matricula in active_students:
                aluno = matricula.aluno
                for act in atividades:
                    # Check if checkbox was submitted (check_<aluno_id>_<atividade_id>)
                    checkbox_name = f'check_{aluno.id}_{act.id}'
                    feito = request.POST.get(checkbox_name) == 'on'

                    # Fetch observation
                    obs_name = f'obs_{aluno.id}_{act.id}'
                    observacao = (request.POST.get(obs_name) or '').strip()[:280]

                    check, _ = AtividadeCheck.objects.get_or_create(
                        atividade=act, aluno=aluno
                    )

                    campos = []
                    if check.feito != feito:
                        check.feito = feito
                        check.feito_em = now if feito else None
                        campos += ['feito', 'feito_em']
                    if check.observacao != observacao:
                        check.observacao = observacao
                        campos.append('observacao')

                    if campos:
                        check.save(update_fields=[*campos, 'updated_at'])

        messages.success(request, 'Controle de atividades atualizado com sucesso.')
        return redirect('activities:atividade_list', turma_pk=turma.pk)


class AtividadeFormMixin(ProfessorTurmaMixin):
    template_name = 'activities/atividade_form.html'

    def render_form(self, request, turma, form, atividade=None):
        return render(
            request,
            self.template_name,
            {'turma': turma, 'form': form, 'atividade': atividade},
        )


class AtividadeCreateView(AtividadeFormMixin, View):
    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        return self.render_form(request, turma, AtividadeForm(turma=turma))

    def post(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        form = AtividadeForm(request.POST, turma=turma)
        if form.is_valid():
            atividade = form.save()
            messages.success(request, 'Atividade criada. Marque os alunos na grade.')
            return redirect('activities:atividade_list', turma_pk=turma.pk)
        return self.render_form(request, turma, form)


class AtividadeUpdateView(AtividadeFormMixin, View):
    def get(self, request, pk):
        atividade = self.get_atividade(pk)
        form = AtividadeForm(instance=atividade, turma=atividade.turma)
        return self.render_form(request, atividade.turma, form, atividade)

    def post(self, request, pk):
        atividade = self.get_atividade(pk)
        form = AtividadeForm(request.POST, instance=atividade, turma=atividade.turma)
        if form.is_valid():
            form.save()
            messages.success(request, 'Atividade atualizada.')
            return redirect('activities:atividade_list', turma_pk=atividade.turma.pk)
        return self.render_form(request, atividade.turma, form, atividade)


class AtividadeDeleteView(ProfessorTurmaMixin, View):
    template_name = 'activities/atividade_confirm_delete.html'

    def get(self, request, pk):
        atividade = self.get_atividade(pk)
        return render(
            request,
            self.template_name,
            {'atividade': atividade, 'turma': atividade.turma},
        )

    def post(self, request, pk):
        atividade = self.get_atividade(pk)
        turma_pk = atividade.turma.pk
        atividade.delete()
        messages.success(request, 'Atividade excluída.')
        return redirect('activities:atividade_list', turma_pk=turma_pk)


class AtividadeChecksView(ProfessorTurmaMixin, View):
    '''Redireciona para a tela de grade consolidated de atividades da turma.'''

    def get(self, request, pk):
        atividade = self.get_atividade(pk)
        return redirect('activities:atividade_list', turma_pk=atividade.turma.pk)
