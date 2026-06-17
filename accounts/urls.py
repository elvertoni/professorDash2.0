from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from .forms import StyledPasswordChangeForm
from .views import LoginView, ProfileUpdateView, ProfileView

app_name = 'accounts'

urlpatterns = [
    path('entrar/', LoginView.as_view(), name='login'),
    path(
        'sair/',
        auth_views.LogoutView.as_view(next_page=reverse_lazy('accounts:logged_out')),
        name='logout',
    ),
    path(
        'saiu/',
        TemplateView.as_view(template_name='accounts/logged_out.html'),
        name='logged_out',
    ),
    path('perfil/', ProfileView.as_view(), name='profile'),
    path('perfil/editar/', ProfileUpdateView.as_view(), name='profile_edit'),
    path(
        'senha/',
        auth_views.PasswordChangeView.as_view(
            form_class=StyledPasswordChangeForm,
            template_name='accounts/password_change_form.html',
            success_url=reverse_lazy('accounts:password_change_done'),
        ),
        name='password_change',
    ),
    path(
        'senha/concluida/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='accounts/password_change_done.html',
        ),
        name='password_change_done',
    ),
    path(
        'recuperar-senha/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('accounts:password_reset_done'),
            extra_context={'form_title': 'Recuperar senha'},
        ),
        name='password_reset',
    ),
    path(
        'recuperar-senha/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'recuperar-senha/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'recuperar-senha/concluido/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]
