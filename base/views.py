from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


@require_GET
def health(request):
    """Liveness probe: 200 sem tocar o banco e sem exigir autenticação."""
    return JsonResponse({'status': 'ok'})


class HomeView(TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'is_aluno') and request.user.is_aluno:
                return redirect('classroom:aluno_dashboard')
            return redirect('classroom:professor_dashboard')
        return super().get(request, *args, **kwargs)
