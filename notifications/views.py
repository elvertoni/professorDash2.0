from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView

from .models import Notificacao


class NotificacaoListView(LoginRequiredMixin, ListView):
    template_name = 'notifications/notificacao_list.html'
    context_object_name = 'notificacoes'
    paginate_by = 20

    def get_queryset(self):
        return Notificacao.objects.filter(usuario=self.request.user).order_by(
            '-created_at'
        )


class NotificacaoMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notificacao = get_object_or_404(
            Notificacao.objects.filter(usuario=request.user),
            pk=pk,
        )
        notificacao.mark_read()
        messages.success(request, 'Notificação marcada como lida.')
        return redirect(self.get_redirect_url(request))

    def get_redirect_url(self, request):
        target = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if target and url_has_allowed_host_and_scheme(
            target,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return target
        return reverse('notifications:list')


class NotificacaoMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notificacao.objects.filter(usuario=request.user, lida=False).update(
            lida=True,
            updated_at=timezone.now(),
        )
        messages.success(request, 'Notificações marcadas como lidas.')
        return redirect(self.get_redirect_url(request))

    def get_redirect_url(self, request):
        target = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if target and url_has_allowed_host_and_scheme(
            target,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return target
        return reverse('notifications:list')
