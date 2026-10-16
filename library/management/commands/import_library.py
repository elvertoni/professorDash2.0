from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from library.access import is_library_owner
from library.packages import import_package, read_package


class Command(BaseCommand):
    help = 'Prévia da biblioteca; grava somente com --apply. Não apaga notas ausentes.'

    def add_arguments(self, parser):
        parser.add_argument('--package', required=True)
        parser.add_argument('--owner-email', required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        try:
            owner = get_user_model().objects.get(email__iexact=options['owner_email'])
            if not is_library_owner(owner):
                raise ValueError(
                    'Conta não corresponde ao proprietário ativo configurado.'
                )
            package = read_package(options['package'])
            counts = import_package(package, owner, apply=options['apply'])
        except (
            OSError,
            ValueError,
            ValidationError,
            get_user_model().DoesNotExist,
        ) as error:
            raise CommandError(str(error)) from error
        mode = 'Aplicado' if options['apply'] else 'Prévia — nada gravado'
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode}: {counts["created"]} novas, {counts["updated"]} atualizadas, '
                f'{counts["unchanged"]} inalteradas. Nenhuma exclusão.'
            )
        )
