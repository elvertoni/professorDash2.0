from django import forms

from accounts.forms import StyledFormMixin
from classroom.models import AulaPublicada

from .models import Material, validate_material_file


class MaterialForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Material
        fields = (
            'titulo',
            'tipo',
            'aula_publicada',
            'descricao',
            'arquivo',
            'link_externo',
        )
        labels = {
            'titulo': 'Título',
            'tipo': 'Tipo',
            'aula_publicada': 'Aula relacionada (opcional)',
            'descricao': 'Descrição',
            'arquivo': 'Arquivo',
            'link_externo': 'Link externo',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, turma=None, **kwargs):
        self.turma = turma
        super().__init__(*args, **kwargs)
        self.fields['aula_publicada'].required = False
        self.fields['aula_publicada'].queryset = (
            AulaPublicada.objects.filter(turma=turma)
            .select_related('aula')
            .order_by('ordem_na_turma', 'aula__ordem')
        )
        self.apply_design_system_classes()

    def _post_clean(self):
        self.instance.turma = self.turma
        super()._post_clean()

    def clean(self):
        cleaned = super().clean()
        aula_publicada = cleaned.get('aula_publicada')
        if (
            aula_publicada is not None
            and self.turma is not None
            and aula_publicada.turma_id != self.turma.pk
        ):
            self.add_error(
                'aula_publicada',
                'A aula relacionada precisa pertencer à turma do material.',
            )

        arquivo = cleaned.get('arquivo')
        if arquivo:
            validate_material_file(arquivo)

        if not cleaned.get('arquivo') and not cleaned.get('link_externo'):
            raise forms.ValidationError(
                'Anexe um arquivo ou informe um link externo.'
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.turma = self.turma
        if commit:
            instance.save()
        return instance
