from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from .forms import (
    AlunoProfileForm,
    EmailAuthenticationForm,
    ProfessorProfileForm,
    UserProfileForm,
)
from .models import AlunoProfile, ProfessorProfile, User


class LoginView(DjangoLoginView):
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True
    template_name = 'accounts/login.html'


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_template_names(self):
        role_templates = {
            User.Role.ADMIN: 'accounts/profile_admin.html',
            User.Role.PROFESSOR: 'accounts/profile_professor.html',
            User.Role.ALUNO: 'accounts/profile_aluno.html',
        }
        return [role_templates.get(self.request.user.role, self.template_name)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_role_profile()
        return context

    def get_role_profile(self):
        user = self.request.user
        if user.role == User.Role.PROFESSOR:
            profile, _ = ProfessorProfile.objects.get_or_create(user=user)
            return profile
        if user.role == User.Role.ALUNO:
            profile, _ = AlunoProfile.objects.get_or_create(user=user)
            return profile
        return None


class ProfileUpdateView(LoginRequiredMixin, View):
    template_name = 'accounts/profile_edit.html'

    def get(self, request):
        return self.render_forms(request)

    def post(self, request):
        user_form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=request.user,
        )
        role_form = self.get_role_form(request.POST)

        if user_form.is_valid() and (role_form is None or role_form.is_valid()):
            user_form.save()
            if role_form is not None:
                role_form.save()
            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('accounts:profile')

        return self.render_forms(request, user_form=user_form, role_form=role_form)

    def render_forms(self, request, user_form=None, role_form=None):
        context = {
            'user_form': user_form or UserProfileForm(instance=request.user),
            'role_form': role_form if role_form is not None else self.get_role_form(),
        }
        return render(request, self.template_name, context)

    def get_role_form(self, data=None):
        user = self.request.user
        if user.role == User.Role.PROFESSOR:
            profile, _ = ProfessorProfile.objects.get_or_create(user=user)
            return ProfessorProfileForm(data=data, instance=profile)
        if user.role == User.Role.ALUNO:
            profile, _ = AlunoProfile.objects.get_or_create(user=user)
            return AlunoProfileForm(data=data, instance=profile)
        return None
