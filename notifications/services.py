from django.urls import reverse

from classroom.models import AulaPublicada, Matricula

from .models import Notificacao


def notify_user(usuario, tipo, titulo, mensagem, link='', dedupe_key=''):
    defaults = {
        'titulo': titulo,
        'mensagem': mensagem,
        'link': link,
    }
    if dedupe_key:
        notificacao, created = Notificacao.objects.get_or_create(
            usuario=usuario,
            tipo=tipo,
            dedupe_key=dedupe_key,
            defaults=defaults,
        )
        if not created:
            changed = []
            for field, value in defaults.items():
                if getattr(notificacao, field) != value:
                    setattr(notificacao, field, value)
                    changed.append(field)
            if changed:
                notificacao.save(update_fields=[*changed, 'updated_at'])
        return notificacao

    return Notificacao.objects.create(
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        link=link,
    )


def notify_active_students(turma, tipo, titulo, mensagem, link, dedupe_key):
    matriculas = Matricula.objects.filter(
        turma=turma,
        status=Matricula.Status.ATIVA,
        aluno__is_active=True,
    ).select_related('aluno')
    for matricula in matriculas:
        notify_user(
            matricula.aluno,
            tipo,
            titulo,
            mensagem,
            link=link,
            dedupe_key=dedupe_key,
        )


def notify_aula_publicada(aula_publicada):
    if not aula_publicada.is_available:
        return

    notify_active_students(
        aula_publicada.turma,
        Notificacao.Tipo.AULA,
        'Nova aula disponível',
        (
            f'{aula_publicada.aula.titulo} foi liberada em '
            f'{aula_publicada.turma.nome}.'
        ),
        reverse('classroom:aluno_aula_detail', kwargs={'pk': aula_publicada.pk}),
        f'aula:{aula_publicada.pk}',
    )


def ensure_timed_notifications_for_user(user):
    if not user.is_authenticated or not user.is_aluno:
        return

    ensure_available_lesson_notifications_for_user(user)


def ensure_available_lesson_notifications_for_user(user):
    publicadas = (
        AulaPublicada.objects.available()
        .filter(
            turma__matriculas__aluno=user,
            turma__matriculas__status=Matricula.Status.ATIVA,
        )
        .select_related('aula', 'turma')
        .distinct()
        .order_by('-disponivel_em')[:20]
    )
    for publicada in publicadas:
        notify_user(
            user,
            Notificacao.Tipo.AULA,
            'Nova aula disponível',
            f'{publicada.aula.titulo} foi liberada em {publicada.turma.nome}.',
            link=reverse('classroom:aluno_aula_detail', kwargs={'pk': publicada.pk}),
            dedupe_key=f'aula:{publicada.pk}',
        )
