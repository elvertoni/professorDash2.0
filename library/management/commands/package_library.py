import json
import os

from django.core.management.base import BaseCommand, CommandError

from library.packages import SOURCES, build_package


class Command(BaseCommand):
    help = (
        'Exporta apenas notas selecionadas; não inclui arquivos originais nem anexos.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--vault', required=True)
        parser.add_argument('--source', required=True, choices=SOURCES)
        parser.add_argument('--selection', choices=['pilot', 'all'], default='pilot')
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        try:
            package = build_package(
                options['vault'], options['source'], options['selection']
            )
            # Exclusive creation prevents overwriting an already reviewed package.
            fd = os.open(options['output'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(package, stream, ensure_ascii=False, indent=2)
        except (OSError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(f'{len(package["notes"])} notas selecionadas:')
        for note in package['notes']:
            self.stdout.write(f'  {note["status"]}: {note["path"]}')
        self.stdout.write(
            self.style.SUCCESS('Pacote local criado. Nenhum envio realizado.')
        )
