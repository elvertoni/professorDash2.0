from django.contrib import messages
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
        total_alunos = self.active_matriculas(turma).count()
        atividades = list(
            Atividade.objects.filter(turma=turma).order_by('-data', '-created_at')
        )
        feitos = {
            row['atividade']: row['n']
            for row in AtividadeCheck.objects.filter(
                atividade__in=atividades, feito=True
            )
            .values('atividade')
            .annotate(n=Count('id'))
        }
        for atividade in atividades:
            atividade.feitos = feitos.get(atividade.pk, 0)
            atividade.total_alunos = total_alunos
        return render(
            request,
            self.template_name,
            {
                'turma': turma,
                'atividades': atividades,
                'total_alunos': total_alunos,
            },
        )


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
            messages.success(request, 'Atividade criada. Marque os alunos.')
            return redirect('activities:atividade_checks', pk=atividade.pk)
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
    '''Grade alunos × checkbox (controle do professor, estilo Notion).'''

    template_name = 'activities/atividade_check.html'

    def get(self, request, pk):
        atividade = self.get_atividade(pk)
        return render(
            request,
            self.template_name,
            {
                'turma': atividade.turma,
                'atividade': atividade,
                'linhas': self.build_rows(atividade),
            },
        )

    def post(self, request, pk):
        atividade = self.get_atividade(pk)
        now = timezone.now()
        for matricula in self.active_matriculas(atividade.turma):
            aluno = matricula.aluno
            feito = request.POST.get('feito_{0}'.format(aluno.id)) == 'on'
            observacao = (request.POST.get('obs_{0}'.format(aluno.id)) or '').strip()[:280]
            check, _ = AtividadeCheck.objects.get_or_create(
                atividade=atividade, aluno=aluno
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
        messages.success(request, 'Checks salvos.')
        return redirect('activities:atividade_checks', pk=atividade.pk)

    def build_rows(self, atividade):
        checks = {
            check.aluno_id: check
            for check in AtividadeCheck.objects.filter(atividade=atividade)
        }
        return [
            {'aluno': matricula.aluno, 'check': checks.get(matricula.aluno_id)}
            for matricula in self.active_matriculas(atividade.turma)
        ]
