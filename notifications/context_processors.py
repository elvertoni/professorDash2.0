from django.core.cache import cache

from .models import Notificacao
from .services import ensure_timed_notifications_for_user


def notification_summary(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}

    cache_key = f'notif_ensured:{user.pk}'
    if not cache.get(cache_key):
        ensure_timed_notifications_for_user(user)
        cache.set(cache_key, True, 300)

    unread = Notificacao.objects.filter(usuario=user, lida=False)
    return {
        'notifications_unread_count': unread.count(),
        'notifications_preview': list(unread.order_by('-created_at')[:5]),
    }
