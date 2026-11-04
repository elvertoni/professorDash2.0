from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import Resolver404, resolve, reverse
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
        return (
            Notificacao.objects.filter(usuario=self.request.user)
            .only(
                'pk',
                'titulo',
                'mensagem',
                'link',
                'lida',
                'tipo',
                'created_at',
            )
            .order_by('-created_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.mark_unavailable_lessons(context['notificacoes'])
        return context

    @staticmethod
    def mark_unavailable_lessons(notificacoes):
        '''Avisos de aula guardam o link como texto. Se a publicação foi
        ocultada, removida ou reagendada, o botão levaria a um 404 (A30).'''
        from classroom.models import AulaPublicada

        targets = {}
        for notificacao in notificacoes:
            notificacao.link_indisponivel = False
            if notificacao.tipo != 'aula' or not notificacao.link:
                continue
            try:
                match = resolve(urlsplit(notificacao.link).path)
            except Resolver404:
                continue
            if match.view_name == 'classroom:aluno_aula_detail':
                targets[notificacao.pk] = match.kwargs.get('pk')

        if not targets:
            return
        disponiveis = {
            publicada.pk
            for publicada in AulaPublicada.objects.filter(
                pk__in=set(targets.values())
            ).select_related('aula')
            if publicada.is_available
        }
        for notificacao in notificacoes:
            if notificacao.pk in targets:
                notificacao.link_indisponivel = targets[notificacao.pk] not in disponiveis


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
