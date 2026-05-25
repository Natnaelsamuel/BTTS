# pyright: reportUnusedParameter=false
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    min_length = 8

    def validate(self, password, _user=None):
        errors = []

        if len(password) < self.min_length:
            errors.append(
                _(f"Password must be at least {self.min_length} characters long.")
            )
        if not any(char.islower() for char in password):
            errors.append(_("Password must include at least one lowercase letter."))
        if not any(char.isupper() for char in password):
            errors.append(_("Password must include at least one uppercase letter."))
        if not any(char.isdigit() for char in password):
            errors.append(_("Password must include at least one number."))
        if not any(not char.isalnum() for char in password):
            errors.append(_("Password must include at least one special character."))

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            f"Password must be at least {self.min_length} characters long and include uppercase and lowercase letters, a number, and a special character."
        )

    def password_changed(self, _password, _user=None):
        return None