from django.core.cache import cache
from django.db.models import Count, Window

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

    unread = list(
        Notificacao.objects.filter(usuario=user, lida=False)
        .only('pk', 'titulo', 'mensagem', 'link')
        .annotate(unread_count=Window(expression=Count('pk')))
        .order_by('-created_at')[:5]
    )
    return {
        'notifications_unread_count': unread[0].unread_count if unread else 0,
        'notifications_preview': unread,
    }
