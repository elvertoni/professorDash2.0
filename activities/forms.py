from django import forms

from accounts.forms import StyledFormMixin
from classroom.models import AulaPublicada
from materials.models import Material

from .models import Atividade, Entrega, validate_submission_file


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        if data in self.empty_values:
            return []
        return [single_clean(data, initial)]


class AtividadeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Atividade
        fields = (
            'titulo',
            'aula_publicada',
            'enunciado',
            'anexos',
            'prazo',
            'pontuacao_max',
            'permite_entrega_atrasada',
            'publicada',
        )
        labels = {
            'titulo': 'Título',
            'aula_publicada': 'Aula relacionada (opcional)',
            'enunciado': 'Enunciado',
            'anexos': 'Materiais anexados',
            'prazo': 'Prazo',
            'pontuacao_max': 'Pontuação máxima',
            'permite_entrega_atrasada': 'Permite entrega atrasada',
            'publicada': 'Publicar para a turma',
        }
        widgets = {
            'enunciado': forms.Textarea(attrs={'rows': 6}),
            'anexos': forms.CheckboxSelectMultiple(),
            'prazo': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, turma=None, **kwargs):
        self.turma = turma
        super().__init__(*args, **kwargs)
        self.fields['prazo'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['aula_publicada'].required = False
        self.fields['aula_publicada'].queryset = (
            AulaPublicada.objects.filter(turma=turma)
            .select_related('aula')
            .order_by('ordem_na_turma', 'aula__ordem')
        )
        self.fields['anexos'].required = False
        self.fields['anexos'].queryset = Material.objects.filter(
            turma=turma
        ).order_by('-created_at')
        self.apply_design_system_classes()

    def clean_aula_publicada(self):
        aula_publicada = self.cleaned_data.get('aula_publicada')
        if (
            aula_publicada is not None
            and self.turma is not None
            and aula_publicada.turma_id != self.turma.pk
        ):
            raise forms.ValidationError(
                'A aula relacionada precisa pertencer à turma da atividade.'
            )
        return aula_publicada

    def clean_anexos(self):
        anexos = self.cleaned_data.get('anexos')
        if self.turma is None or not anexos:
            return anexos

        invalid = [anexo for anexo in anexos if anexo.turma_id != self.turma.pk]
        if invalid:
            raise forms.ValidationError(
                'Todos os materiais anexados precisam pertencer à turma da atividade.'
            )
        return anexos

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.turma = self.turma
        if commit:
            instance.save()
            self.save_m2m()
            instance.validate_anexos_turma()
        return instance


class CorrecaoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Entrega
        fields = ('nota', 'feedback')
        labels = {
            'nota': 'Nota',
            'feedback': 'Feedback',
        }
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, atividade=None, **kwargs):
        self.atividade = atividade
        super().__init__(*args, **kwargs)
        self.fields['nota'].required = True
        if atividade is not None:
            self.fields['nota'].help_text = (
                f'Pontuação máxima: {atividade.pontuacao_max}.'
            )
        self.apply_design_system_classes()

    def clean_nota(self):
        nota = self.cleaned_data.get('nota')
        if nota is None:
            return nota
        if nota < 0:
            raise forms.ValidationError('A nota não pode ser negativa.')
        if self.atividade and nota > self.atividade.pontuacao_max:
            raise forms.ValidationError(
                f'A nota não pode exceder {self.atividade.pontuacao_max}.'
            )
        return nota


class EntregaForm(StyledFormMixin, forms.Form):
    texto_resposta = forms.CharField(
        label='Sua resposta',
        required=False,
        widget=forms.Textarea(attrs={'rows': 6}),
    )
    arquivos = MultipleFileField(
        label='Anexos (opcional)',
        required=False,
        validators=[validate_submission_file],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_design_system_classes()

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('texto_resposta') and not cleaned.get('arquivos'):
            raise forms.ValidationError(
                'Escreva uma resposta ou anexe ao menos um arquivo.'
            )
        return cleaned
