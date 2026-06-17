from django.conf import settings
from django.core.files.storage import FileSystemStorage


class ProtectedFileSystemStorage(FileSystemStorage):
    """Storage for media that must never be exposed publicly.

    Files live in ``PROTECTED_MEDIA_ROOT`` (outside ``MEDIA_ROOT``) and have no
    public URL. Serve them only through a view that checks permissions
    (aluno da turma ou professor) — see the materials/activities apps.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('location', settings.PROTECTED_MEDIA_ROOT)
        kwargs.setdefault('base_url', None)
        super().__init__(*args, **kwargs)

    def url(self, name):
        raise NotImplementedError(
            'Media protegida não tem URL pública; sirva via view com checagem de permissão.'
        )


protected_storage = ProtectedFileSystemStorage()
