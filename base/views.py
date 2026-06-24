import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.utils._os import safe_join
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


@require_GET
def health(request):
    """Liveness probe: 200 sem tocar o banco e sem exigir autenticação."""
    return JsonResponse({'status': 'ok'})


@require_GET
def public_media(request, path):
    """Serve arquivos públicos de MEDIA_ROOT, como capas de aulas."""
    parts = Path(path).parts
    is_catalog_cover = (
        len(parts) >= 3
        and parts[0] == 'catalog'
        and parts[1] == 'capas'
    )
    is_avatar = len(parts) >= 2 and parts[0] == 'avatars'
    if not (is_catalog_cover or is_avatar):
        raise Http404

    try:
        full_path = safe_join(settings.MEDIA_ROOT, path)
    except ValueError as exc:
        raise Http404 from exc

    media_path = Path(full_path)
    if not media_path.is_file():
        raise Http404

    content_type, _ = mimetypes.guess_type(media_path.name)
    return FileResponse(media_path.open('rb'), content_type=content_type)


class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'is_aluno') and request.user.is_aluno:
                return redirect('classroom:aluno_dashboard')
            return redirect('classroom:professor_dashboard')
        return super().get(request, *args, **kwargs)
