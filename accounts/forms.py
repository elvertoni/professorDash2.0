from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    UserChangeForm as BaseUserChangeForm,
    UserCreationForm as BaseUserCreationForm,
    _unicode_ci_compare,
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
        for name, field in self.fields.items():
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

            # Associar help_text com aria-describedby
            if field.help_text:
                field_id = self.auto_id % name if self.auto_id and '%s' in str(self.auto_id) else name
                widget.attrs['aria-describedby'] = f'hint_{field_id}'

    def full_clean(self):
        super().full_clean()
        for name, field in self.fields.items():
            if name in self.errors:
                field.widget.attrs['aria-invalid'] = 'true'
                field_id = self.auto_id % name if self.auto_id and '%s' in str(self.auto_id) else name
                err_id = f'error_{field_id}'
                existing_desc = field.widget.attrs.get('aria-describedby', '')
                if existing_desc:
                    if err_id not in existing_desc:
                        field.widget.attrs['aria-describedby'] = f'{err_id} {existing_desc}'
                else:
                    field.widget.attrs['aria-describedby'] = err_id


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


class InitialPasswordResetForm(StyledFormMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_design_system_classes()

    def get_users(self, email):
        email_field_name = User.get_email_field_name()
        active_users = User._default_manager.filter(
            **{
                f'{email_field_name}__iexact': email,
                'is_active': True,
            }
        )
        return (
            user
            for user in active_users
            if _unicode_ci_compare(email, getattr(user, email_field_name))
        )
