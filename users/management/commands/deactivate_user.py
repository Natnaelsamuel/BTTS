from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Deactivate or reactivate a user account'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str,
                            help='Username or email of the user')
        parser.add_argument(
            '--reactivate',
            action='store_true',
            help='Reactivate a deactivated user instead of deactivating',
        )

    def handle(self, *args, **options):
        username_or_email = options['username']
        reactivate = options['reactivate']

        # Try to find user by username or email
        try:
            user = User.objects.get(username=username_or_email)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email__iexact=username_or_email)
            except User.DoesNotExist as exc:
                raise CommandError(
                    f'User "{username_or_email}" not found') from exc

        if reactivate:
            if user.is_active:
                self.stdout.write(getattr(self.style, "WARNING")(
                    f'User {user.username} is already active.'))
            else:
                user.is_active = True
                user.save()
                self.stdout.write(getattr(self.style, "SUCCESS")(
                    f'User {user.username} has been reactivated.'))
        else:
            if not user.is_active:
                self.stdout.write(getattr(self.style, "WARNING")(
                    f'User {user.username} is already deactivated.'))
            else:
                user.is_active = False
                user.save()
                self.stdout.write(getattr(self.style, "SUCCESS")(
                    f'User {user.username} has been deactivated.'))
