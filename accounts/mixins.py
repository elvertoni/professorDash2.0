from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import User


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()
    raise_exception = True

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False

        if user.is_superuser or user.role == User.Role.ADMIN:
            return True

        return user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied('Você não tem permissão para acessar esta área.')
        return redirect_to_login(
            self.request.get_full_path(),
            self.get_login_url(),
            self.get_redirect_field_name(),
        )


class ProfessorRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.PROFESSOR,)


class AlunoRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.ALUNO,)


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.ADMIN,)
