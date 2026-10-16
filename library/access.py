from django.conf import settings

from accounts.mixins import RoleRequiredMixin


def is_library_owner(user):
    email = settings.LIBRARY_OWNER_EMAIL.strip().casefold()
    return bool(
        email
        and user.is_authenticated
        and user.is_active
        and user.role in ('professor', 'admin')
        and user.email.casefold() == email
    )


class LibraryOwnerMixin(RoleRequiredMixin):
    def test_func(self):
        return is_library_owner(self.request.user)
