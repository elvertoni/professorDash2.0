from django.db import migrations


TURMA_NOME = 'Inteligência Artificial'
DISCIPLINA_SLUG = 'inteligencia-artificial'
INVITE_CODE = 'IA2026'


def unique_invite_code(Turma):
    code = INVITE_CODE
    suffix = 1
    while Turma.objects.filter(codigo_convite=code).exists():
        code = f'{INVITE_CODE}{suffix}'
        suffix += 1
    return code


def seed_ai_turma(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Disciplina = apps.get_model('catalog', 'Disciplina')
    Turma = apps.get_model('classroom', 'Turma')

    professor = (
        User.objects.filter(email='elvertoni@gmail.com').first()
        or User.objects.filter(role='professor').order_by('id').first()
        or User.objects.filter(role='admin').order_by('id').first()
        or User.objects.filter(is_superuser=True).order_by('id').first()
    )
    if professor is None:
        return

    disciplina, _ = Disciplina.objects.update_or_create(
        slug=DISCIPLINA_SLUG,
        defaults={
            'label': 'Inteligência Artificial',
            'serie': 'Extra',
            'status': 'aprovada',
        },
    )

    turma, created = Turma.objects.get_or_create(
        nome=TURMA_NOME,
        ano_letivo=2026,
        professor=professor,
        defaults={
            'disciplina': disciplina,
            'serie': 'Extra',
            'codigo_convite': unique_invite_code(Turma),
            'ativa': True,
        },
    )
    if not created:
        turma.disciplina = disciplina
        turma.serie = 'Extra'
        turma.ativa = True
        if not turma.codigo_convite:
            turma.codigo_convite = unique_invite_code(Turma)
        turma.save(update_fields=['disciplina', 'serie', 'ativa', 'codigo_convite', 'updated_at'])


def unseed_ai_turma(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Turma = apps.get_model('classroom', 'Turma')

    professor = (
        User.objects.filter(email='elvertoni@gmail.com').first()
        or User.objects.filter(role='professor').order_by('id').first()
        or User.objects.filter(role='admin').order_by('id').first()
        or User.objects.filter(is_superuser=True).order_by('id').first()
    )
    if professor is None:
        return

    Turma.objects.filter(
        nome=TURMA_NOME,
        ano_letivo=2026,
        professor=professor,
        matriculas__isnull=True,
        aulas_publicadas__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_aula_imagem'),
        ('classroom', '0002_aulapublicada_progressoaula_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_ai_turma, unseed_ai_turma),
    ]
