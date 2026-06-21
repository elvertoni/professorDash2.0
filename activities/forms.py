from django import forms

from accounts.forms import StyledFormMixin

from .models import Atividade


class AtividadeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Atividade
        fields = ('titulo', 'descricao', 'data')
        labels = {
            'titulo': 'Título',
            'descricao': 'Descrição (opcional)',
            'data': 'Data (opcional)',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'data': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }

    def __init__(self, *args, turma=None, **kwargs):
        self.turma = turma
        super().__init__(*args, **kwargs)
        self.fields['data'].input_formats = ['%Y-%m-%d']
        self.apply_design_system_classes()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.turma is not None:
            instance.turma = self.turma
        if commit:
            instance.save()
        return instance
