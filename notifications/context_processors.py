from .models import Notificacao
from .services import ensure_timed_notifications_for_user


def notification_summary(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    ensure_timed_notifications_for_user(user)
    unread = Notificacao.objects.filter(usuario=user, lida=False)
    return {
        'notifications_unread_count': unread.count(),
        'notifications_preview': list(unread.order_by('-created_at')[:5]),
    }
