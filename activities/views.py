from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from accounts.mixins import AlunoRequiredMixin, ProfessorRequiredMixin
from classroom.models import Matricula, Turma
from classroom.views import can_manage_all

from .forms import AtividadeForm, CorrecaoForm, EntregaForm
from .models import Atividade, Entrega, EntregaArquivo


# --- Professor ---


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


class AtividadeListView(ProfessorTurmaMixin, View):
    template_name = 'activities/atividade_list.html'

    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        atividades = (
            Atividade.objects.filter(turma=turma)
            .select_related('aula_publicada', 'aula_publicada__aula')
            .prefetch_related('entregas')
            .order_by('-created_at')
        )
        return render(
            request,
            self.template_name,
            {'turma': turma, 'atividades': atividades},
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
            form.save()
            messages.success(request, 'Atividade criada com sucesso.')
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
            messages.success(request, 'Atividade atualizada com sucesso.')
            return redirect('activities:atividade_list', turma_pk=atividade.turma.pk)
        return self.render_form(request, atividade.turma, form, atividade)


class AtividadeDeleteView(ProfessorTurmaMixin, View):
    template_name = 'activities/atividade_confirm_delete.html'

    def get(self, request, pk):
        atividade = self.get_atividade(pk)
        return render(
            request, self.template_name, {'atividade': atividade, 'turma': atividade.turma}
        )

    def post(self, request, pk):
        atividade = self.get_atividade(pk)
        turma_pk = atividade.turma.pk
        atividade.delete()
        messages.success(request, 'Atividade excluída com sucesso.')
        return redirect('activities:atividade_list', turma_pk=turma_pk)


class AtividadeEntregasView(ProfessorTurmaMixin, View):
    template_name = 'activities/atividade_entregas.html'

    def get(self, request, pk):
        atividade = self.get_atividade(pk)
        entregas = {
            entrega.aluno_id: entrega
            for entrega in atividade.entregas.select_related('aluno').prefetch_related(
                'arquivos'
            )
        }
        matriculas = (
            Matricula.objects.filter(
                turma=atividade.turma, status=Matricula.Status.ATIVA
            )
            .select_related('aluno')
            .order_by('aluno__nome_completo')
        )
        linhas = []
        for matricula in matriculas:
            entrega = entregas.get(matricula.aluno_id)
            linhas.append(
                {
                    'aluno': matricula.aluno,
                    'entrega': entrega,
                    'status': entrega.status if entrega else Entrega.Status.PENDENTE,
                    'arquivos': list(entrega.arquivos.all()) if entrega else [],
                }
            )
        return render(
            request,
            self.template_name,
            {'turma': atividade.turma, 'atividade': atividade, 'linhas': linhas},
        )


class CorrecaoView(ProfessorTurmaMixin, View):
    template_name = 'activities/correcao.html'

    def get_entrega(self, pk):
        return get_object_or_404(
            Entrega.objects.filter(atividade__turma__in=self.get_turma_queryset())
            .select_related('atividade', 'atividade__turma', 'aluno')
            .prefetch_related('arquivos'),
            pk=pk,
        )

    def get_queue_data(self, entrega):
        pending_deliveries = list(
            Entrega.objects.filter(
                atividade=entrega.atividade,
                checked=False,
                status__in=[Entrega.Status.ENTREGUE, Entrega.Status.ATRASADA],
            ).order_by('data_entrega', 'pk')
        )
        total_pending = len(pending_deliveries)
        current_index = -1
        for i, item in enumerate(pending_deliveries):
            if item.pk == entrega.pk:
                current_index = i
                break

        position = current_index + 1 if current_index != -1 else 0
        next_entrega = None
        if current_index != -1 and current_index + 1 < total_pending:
            next_entrega = pending_deliveries[current_index + 1]

        return {
            'total_pending': total_pending,
            'position': position,
            'next_entrega': next_entrega,
        }

    def get(self, request, pk):
        entrega = self.get_entrega(pk)
        form = CorrecaoForm(instance=entrega, atividade=entrega.atividade)
        queue_data = self.get_queue_data(entrega)
        return self.render_page(
            request,
            entrega,
            form,
            next_entrega=queue_data['next_entrega'],
            position=queue_data['position'],
            total_pending=queue_data['total_pending'],
        )

    def post(self, request, pk):
        entrega = self.get_entrega(pk)
        if entrega.data_entrega is None:
            messages.error(request, 'Este aluno ainda não fez a entrega.')
            return redirect('activities:atividade_entregas', pk=entrega.atividade.pk)

        queue_data = self.get_queue_data(entrega)
        next_entrega = queue_data['next_entrega']

        form = CorrecaoForm(request.POST, instance=entrega, atividade=entrega.atividade)
        if form.is_valid():
            entrega.mark_checked(
                request.user,
                form.cleaned_data['nota'],
                form.cleaned_data['feedback'],
            )
            messages.success(request, 'Entrega corrigida com sucesso.')

            action = request.POST.get('action')
            if action == 'save_next' and next_entrega:
                return redirect('activities:correcao', pk=next_entrega.pk)

            return redirect('activities:atividade_entregas', pk=entrega.atividade.pk)

        return self.render_page(
            request,
            entrega,
            form,
            next_entrega=next_entrega,
            position=queue_data['position'],
            total_pending=queue_data['total_pending'],
        )

    def render_page(self, request, entrega, form, next_entrega=None, position=0, total_pending=0):
        return render(
            request,
            self.template_name,
            {
                'turma': entrega.atividade.turma,
                'atividade': entrega.atividade,
                'entrega': entrega,
                'form': form,
                'next_entrega': next_entrega,
                'position': position,
                'total_pending': total_pending,
            },
        )


class EntregaArquivoDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        arquivo = get_object_or_404(
            EntregaArquivo.objects.select_related(
                'entrega', 'entrega__atividade__turma', 'entrega__aluno'
            ),
            pk=pk,
        )
        if not self.user_can_access(request.user, arquivo.entrega):
            raise PermissionDenied('Você não tem permissão para baixar este arquivo.')
        return FileResponse(
            arquivo.arquivo.open('rb'),
            as_attachment=True,
            filename=arquivo.nome,
        )

    def user_can_access(self, user, entrega):
        if can_manage_all(user):
            return True
        if user.is_professor and entrega.atividade.turma.professor_id == user.id:
            return True
        if user.is_aluno and entrega.aluno_id == user.id:
            return Matricula.objects.filter(
                turma=entrega.atividade.turma,
                aluno=user,
                status=Matricula.Status.ATIVA,
            ).exists()
        return False


# --- Aluno ---


class AlunoAtividadesMixin(AlunoRequiredMixin):
    def get_turma_for_aluno(self, turma_pk):
        return get_object_or_404(
            Turma.objects.filter(
                pk=turma_pk,
                matriculas__aluno=self.request.user,
                matriculas__status=Matricula.Status.ATIVA,
            ).select_related('disciplina', 'professor')
        )

    def get_atividade_for_aluno(self, pk):
        return get_object_or_404(
            Atividade.objects.filter(
                pk=pk,
                publicada=True,
                turma__matriculas__aluno=self.request.user,
                turma__matriculas__status=Matricula.Status.ATIVA,
            ).select_related('turma', 'turma__disciplina')
        )


class AlunoAtividadeListView(AlunoAtividadesMixin, View):
    template_name = 'activities/aluno_atividade_list.html'

    def get(self, request, turma_pk):
        turma = self.get_turma_for_aluno(turma_pk)
        entregas = {
            entrega.atividade_id: entrega
            for entrega in Entrega.objects.filter(
                aluno=request.user, atividade__turma=turma
            )
        }
        atividades = list(
            Atividade.objects.filter(turma=turma, publicada=True)
            .select_related('aula_publicada', 'aula_publicada__aula')
            .order_by('prazo', '-created_at')
        )
        for atividade in atividades:
            entrega = entregas.get(atividade.id)
            atividade.minha_entrega = entrega
            atividade.meu_status = (
                entrega.status if entrega else Entrega.Status.PENDENTE
            )
        return render(
            request,
            self.template_name,
            {'turma': turma, 'atividades': atividades},
        )


class AlunoEntregaView(AlunoAtividadesMixin, View):
    template_name = 'activities/aluno_entrega.html'

    def get(self, request, pk):
        atividade = self.get_atividade_for_aluno(pk)
        entrega = Entrega.objects.filter(
            atividade=atividade, aluno=request.user
        ).prefetch_related('arquivos').first()
        return self.render_page(request, atividade, entrega, EntregaForm())

    def post(self, request, pk):
        atividade = self.get_atividade_for_aluno(pk)
        entrega = Entrega.objects.filter(
            atividade=atividade, aluno=request.user
        ).first()

        if entrega and entrega.status == Entrega.Status.CORRIGIDA:
            messages.error(request, 'Esta entrega já foi corrigida e não pode ser alterada.')
            return redirect('activities:aluno_entrega', pk=atividade.pk)

        if not atividade.aberta_para_entrega:
            messages.error(request, 'O prazo encerrou e esta atividade não aceita entrega atrasada.')
            return redirect('activities:aluno_entrega', pk=atividade.pk)

        form = EntregaForm(request.POST, request.FILES)
        if form.is_valid():
            arquivos_novos = form.cleaned_data['arquivos']
            with transaction.atomic():
                if entrega is None:
                    entrega = Entrega(atividade=atividade, aluno=request.user)
                else:
                    entrega.arquivos.all().delete()
                entrega.texto_resposta = form.cleaned_data['texto_resposta']
                entrega.submit()
                entrega.save()
                for arquivo in arquivos_novos:
                    EntregaArquivo.objects.create(entrega=entrega, arquivo=arquivo)
            messages.success(request, 'Entrega registrada com sucesso.')
            return redirect('activities:aluno_entrega', pk=atividade.pk)

        return self.render_page(request, atividade, entrega, form)

    def render_page(self, request, atividade, entrega, form):
        return render(
            request,
            self.template_name,
            {
                'turma': atividade.turma,
                'atividade': atividade,
                'entrega': entrega,
                'form': form,
            },
        )
