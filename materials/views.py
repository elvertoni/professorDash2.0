from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from accounts.mixins import AlunoRequiredMixin, ProfessorRequiredMixin
from classroom.models import Matricula, Turma
from classroom.views import can_manage_all

from .forms import MaterialForm
from .models import Material


# --- Professor ---


class ProfessorTurmaMixin(ProfessorRequiredMixin):
    def get_turma_queryset(self):
        queryset = Turma.objects.select_related('disciplina', 'professor')
        if can_manage_all(self.request.user):
            return queryset
        return queryset.filter(professor=self.request.user)

    def get_turma(self, turma_pk):
        return get_object_or_404(self.get_turma_queryset(), pk=turma_pk)

    def get_material_queryset(self):
        return Material.objects.filter(turma__in=self.get_turma_queryset())

    def get_material(self, pk):
        return get_object_or_404(
            self.get_material_queryset().select_related('turma'), pk=pk
        )


class MaterialListView(ProfessorTurmaMixin, View):
    template_name = 'materials/material_list.html'

    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        materiais = (
            Material.objects.filter(turma=turma)
            .select_related('aula_publicada', 'aula_publicada__aula')
            .order_by('-created_at')
        )
        return render(
            request,
            self.template_name,
            {'turma': turma, 'materiais': materiais},
        )


class MaterialFormMixin(ProfessorTurmaMixin):
    template_name = 'materials/material_form.html'

    def render_form(self, request, turma, form, material=None):
        return render(
            request,
            self.template_name,
            {'turma': turma, 'form': form, 'material': material},
        )


class MaterialCreateView(MaterialFormMixin, View):
    def get(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        return self.render_form(request, turma, MaterialForm(turma=turma))

    def post(self, request, turma_pk):
        turma = self.get_turma(turma_pk)
        form = MaterialForm(request.POST, request.FILES, turma=turma)
        if form.is_valid():
            material = form.save(commit=False)
            material.turma = turma
            material.enviado_por = request.user
            material.save()
            messages.success(request, 'Material adicionado com sucesso.')
            return redirect('materials:material_list', turma_pk=turma.pk)
        return self.render_form(request, turma, form)


class MaterialUpdateView(MaterialFormMixin, View):
    def get(self, request, pk):
        material = self.get_material(pk)
        form = MaterialForm(instance=material, turma=material.turma)
        return self.render_form(request, material.turma, form, material)

    def post(self, request, pk):
        material = self.get_material(pk)
        form = MaterialForm(
            request.POST, request.FILES, instance=material, turma=material.turma
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Material atualizado com sucesso.')
            return redirect('materials:material_list', turma_pk=material.turma.pk)
        return self.render_form(request, material.turma, form, material)


class MaterialDeleteView(ProfessorTurmaMixin, View):
    template_name = 'materials/material_confirm_delete.html'

    def get(self, request, pk):
        material = self.get_material(pk)
        return render(
            request, self.template_name, {'material': material, 'turma': material.turma}
        )

    def post(self, request, pk):
        material = self.get_material(pk)
        turma_pk = material.turma.pk
        material.delete()
        messages.success(request, 'Material removido com sucesso.')
        return redirect('materials:material_list', turma_pk=turma_pk)


# --- Download protegido (professor ou aluno da turma) ---


class MaterialDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        material = get_object_or_404(
            Material.objects.select_related('turma', 'aula_publicada'), pk=pk
        )
        if not material.arquivo:
            raise PermissionDenied('Este material não possui arquivo para download.')
        if not self.user_can_access(request.user, material):
            raise PermissionDenied('Você não tem permissão para baixar este material.')
        return FileResponse(
            material.arquivo.open('rb'),
            as_attachment=True,
            filename=material.nome_arquivo,
        )

    def user_can_access(self, user, material):
        if can_manage_all(user):
            return True
        turma = material.turma
        if turma is None:
            return False
        if user.is_professor and turma.professor_id == user.id:
            return True
        if user.is_aluno:
            matriculado = Matricula.objects.filter(
                turma=turma, aluno=user, status=Matricula.Status.ATIVA
            ).exists()
            if not matriculado:
                return False
            ap = material.aula_publicada
            if ap is not None and not ap.is_available:
                return False
            return True
        return False


# --- Aluno ---


class AlunoMaterialListView(AlunoRequiredMixin, View):
    template_name = 'materials/aluno_material_list.html'

    def get(self, request, turma_pk):
        turma = get_object_or_404(
            Turma.objects.filter(
                pk=turma_pk,
                matriculas__aluno=request.user,
                matriculas__status=Matricula.Status.ATIVA,
            ).select_related('disciplina', 'professor')
        )
        now = timezone.now()
        materiais = [
            material
            for material in Material.objects.filter(turma=turma)
            .select_related('aula_publicada', 'aula_publicada__aula')
            .order_by('-created_at')
            if material.aula_publicada is None
            or (
                material.aula_publicada.publicada
                and material.aula_publicada.disponivel_em <= now
            )
        ]
        return render(
            request,
            self.template_name,
            {'turma': turma, 'materiais': materiais},
        )
