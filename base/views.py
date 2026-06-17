from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


@require_GET
def health(request):
    """Liveness probe: 200 sem tocar o banco e sem exigir autenticação."""
    return JsonResponse({'status': 'ok'})


class HomeView(TemplateView):
    """Landing provisória (Sprint 0): valida a integração do design system."""

    template_name = 'home.html'
