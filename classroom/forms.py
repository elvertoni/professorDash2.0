from django import forms

from accounts.forms import StyledFormMixin
from accounts.models import AlunoProfile, User
from catalog.models import Aula, Disciplina

from .models import AulaPublicada, Matricula, Turma


class TurmaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Turma
        fields = ('nome', 'disciplina', 'serie', 'ano_letivo', 'ativa')
        labels = {
            'nome': 'Nome da turma',
            'disciplina': 'Disciplina',
            'serie': 'Série',
            'ano_letivo': 'Ano letivo',
            'ativa': 'Turma ativa',
        }
        widgets = {
            'ano_letivo': forms.NumberInput(attrs={'min': 2024, 'max': 2100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['disciplina'].queryset = Disciplina.objects.order_by('label')
        self.apply_design_system_classes()


class TurmaAdminForm(TurmaForm):
    class Meta(TurmaForm.Meta):
        fields = ('nome', 'disciplina', 'serie', 'ano_letivo', 'professor', 'ativa')
        labels = {
            **TurmaForm.Meta.labels,
            'professor': 'Professor responsável',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['professor'].queryset = User.objects.filter(
            role=User.Role.PROFESSOR,
            is_active=True,
        ).order_by('nome_completo')


class StudentEnrollmentForm(StyledFormMixin, forms.Form):
    nome_completo = forms.CharField(label='Nome completo', max_length=255)
    email = forms.EmailField(label='E-mail')
    school_registration = forms.CharField(
        label='Matrícula escolar',
        max_length=80,
        required=False,
    )
    grade = forms.CharField(label='Série', max_length=80, required=False)
    responsible_name = forms.CharField(
        label='Responsável',
        max_length=255,
        required=False,
    )
    birth_date = forms.DateField(
        label='Data de nascimento',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    status = forms.ChoiceField(
        label='Status da matrícula',
        choices=Matricula.Status.choices,
        initial=Matricula.Status.ATIVA,
    )

    def __init__(self, *args, turma=None, instance=None, **kwargs):
        self.turma = turma
        self.instance = instance
        initial = kwargs.pop('initial', {})

        if instance is not None:
            student = instance.aluno
            profile, _ = AlunoProfile.objects.get_or_create(user=student)
            initial = {
                **initial,
                'nome_completo': student.nome_completo,
                'email': student.email,
                'school_registration': profile.school_registration or '',
                'grade': profile.grade,
                'responsible_name': profile.responsible_name,
                'birth_date': profile.birth_date,
                'status': instance.status,
            }

        super().__init__(*args, initial=initial, **kwargs)
        self.apply_design_system_classes()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        existing = User.objects.filter(email__iexact=email).first()

        if existing and self.instance is not None and existing.pk != self.instance.aluno_id:
            raise forms.ValidationError('Já existe outro usuário com este e-mail.')
        if existing and existing.role != User.Role.ALUNO:
            raise forms.ValidationError(
                'Este e-mail já pertence a uma conta que não é de aluno.'
            )

        return email

    def clean_school_registration(self):
        registration = self.cleaned_data.get('school_registration', '').strip()
        if not registration:
            return None

        queryset = AlunoProfile.objects.filter(school_registration=registration)
        if self.instance is not None:
            queryset = queryset.exclude(user=self.instance.aluno)
        else:
            email = self.cleaned_data.get('email')
            if email:
                existing = User.objects.filter(email__iexact=email).first()
                if existing:
                    queryset = queryset.exclude(user=existing)

        if queryset.exists():
            raise forms.ValidationError('Esta matrícula escolar já está em uso.')

        return registration

    def save(self):
        email = self.cleaned_data['email']
        user = self.get_or_create_student(email)
        user.nome_completo = self.cleaned_data['nome_completo'].strip()
        user.email = email
        user.role = User.Role.ALUNO
        user.save()

        profile, _ = AlunoProfile.objects.get_or_create(user=user)
        profile.school_registration = self.cleaned_data['school_registration']
        profile.grade = self.cleaned_data.get('grade', '').strip()
        profile.responsible_name = self.cleaned_data.get('responsible_name', '').strip()
        profile.birth_date = self.cleaned_data.get('birth_date')
        profile.save()

        matricula, created = Matricula.objects.update_or_create(
            turma=self.turma,
            aluno=user,
            defaults={'status': self.cleaned_data['status']},
        )
        return matricula, created

    def get_or_create_student(self, email):
        if self.instance is not None:
            return self.instance.aluno

        user = User.objects.filter(email__iexact=email).first()
        if user:
            return user

        return User.objects.create_user(
            email=email,
            password=None,
            nome_completo=self.cleaned_data['nome_completo'].strip(),
            role=User.Role.ALUNO,
        )


class AulaPublicadaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AulaPublicada
        fields = ('aula', 'disponivel_em', 'publicada')
        labels = {
            'aula': 'Aula do catálogo',
            'disponivel_em': 'Disponível em',
            'publicada': 'Publicar imediatamente',
        }
        widgets = {
            'disponivel_em': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, turma=None, **kwargs):
        self.turma = turma
        super().__init__(*args, **kwargs)
        self.fields['disponivel_em'].input_formats = ['%Y-%m-%dT%H:%M']
        ja_publicadas = AulaPublicada.objects.filter(turma=turma).values_list(
            'aula_id', flat=True
        )
        self.fields['aula'].queryset = (
            Aula.objects.filter(status=Aula.Status.APROVADA)
            .exclude(pk__in=ja_publicadas)
            .select_related('disciplina', 'trilha')
            .order_by('disciplina__label', 'trilha__label', 'ordem')
        )
        self.apply_design_system_classes()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.turma = self.turma
        if not instance.ordem_na_turma:
            ultimo = (
                AulaPublicada.objects.filter(turma=self.turma)
                .order_by('-ordem_na_turma')
                .first()
            )
            instance.ordem_na_turma = (ultimo.ordem_na_turma + 1) if ultimo else 1
        if commit:
            instance.save()
        return instance


class AulaPublicadaEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AulaPublicada
        fields = ('ordem_na_turma', 'disponivel_em', 'publicada')
        labels = {
            'ordem_na_turma': 'Ordem na turma',
            'disponivel_em': 'Disponível em',
            'publicada': 'Publicada',
        }
        widgets = {
            'disponivel_em': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['disponivel_em'].input_formats = ['%Y-%m-%dT%H:%M']
        self.apply_design_system_classes()


class StudentCsvImportForm(StyledFormMixin, forms.Form):
    file = forms.FileField(
        label='Arquivo CSV',
        help_text=(
            'Use colunas: nome_completo, email, matricula_escolar, serie, '
            'responsavel, data_nascimento.'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_design_system_classes()
