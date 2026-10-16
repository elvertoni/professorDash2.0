from .access import is_library_owner


def library_access(request):
    return {'can_access_library': is_library_owner(request.user)}
