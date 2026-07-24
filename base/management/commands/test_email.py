from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends a test email to verify SMTP configuration.'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Recipient email address')

    def handle(self, *args, **options):
        recipient = options['email']
        sender = settings.DEFAULT_FROM_EMAIL
        
        self.stdout.write(self.style.WARNING(f"Tentando enviar e-mail via: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}"))
        self.stdout.write(self.style.WARNING(f"Remetente: {sender}"))
        self.stdout.write(self.style.WARNING(f"Destinatário: {recipient}"))
        self.stdout.write(self.style.WARNING(f"Usa TLS: {settings.EMAIL_USE_TLS}"))
        self.stdout.write(self.style.WARNING(f"EMAIL_BACKEND ativo: {getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')}"))
        
        try:
            send_mail(
                subject='ProfessorDash - Teste de SMTP',
                message='Se você recebeu este e-mail, a configuração SMTP do seu projeto ProfessorDash está funcionando com sucesso!',
                from_email=sender,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS("E-mail enviado com sucesso! Verifique sua caixa de entrada e spam."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Erro ao enviar e-mail: {str(e)}"))
            self.stderr.write(self.style.ERROR("Verifique se as credenciais no arquivo .env (ou no Easypanel) estão configuradas corretamente."))
