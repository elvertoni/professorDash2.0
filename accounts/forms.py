from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserChangeForm as BaseUserChangeForm,
    UserCreationForm as BaseUserCreationForm,
)

from .models import AlunoProfile, ProfessorProfile, User


class StyledFormMixin:
    input_class = 'input'
    select_class = 'select'
    textarea_class = 'textarea'
    unstyled_widgets = (
        forms.CheckboxInput,
        forms.CheckboxSelectMultiple,
        forms.RadioSelect,
        forms.HiddenInput,
    )

    def apply_design_system_classes(self):
        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, self.unstyled_widgets):
                continue
            if isinstance(widget, forms.Select):
                css_class = self.select_class
            elif isinstance(widget, forms.Textarea):
                css_class = self.textarea_class
            else:
                css_class = self.input_class

            existing = widget.attrs.get('class', '')
            widget.attrs['class'] = f'{existing} {css_class}'.strip()


class EmailAuthenticationForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    error_messages = {
        'invalid_login': 'E-mail ou senha inválidos.',
        'inactive': 'Esta conta está inativa.',
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.apply_design_system_classes()


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'nome_completo', 'role')


class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


class UserProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('nome_completo', 'email', 'avatar')
        labels = {
            'nome_completo': 'Nome completo',
            'email': 'E-mail',
            'avatar': 'Avatar',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'avatar': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_design_system_classes()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        queryset = User.objects.filter(email__iexact=email)

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError('Já existe uma conta com este e-mail.')

        return email


class ProfessorProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ProfessorProfile
        fields = ('seed_registration', 'disciplines')
        labels = {
            'seed_registration': 'Vínculo SEED',
            'disciplines': 'Disciplinas que leciona',
        }
        widgets = {
            'disciplines': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_design_system_classes()


class AlunoProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AlunoProfile
        fields = ('school_registration', 'grade', 'responsible_name', 'birth_date')
        labels = {
            'school_registration': 'Matrícula escolar',
            'grade': 'Série',
            'responsible_name': 'Responsável',
            'birth_date': 'Data de nascimento',
        }
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_design_system_classes()


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.apply_design_system_classes()
