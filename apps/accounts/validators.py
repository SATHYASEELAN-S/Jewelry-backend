import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class UppercaseValidator:
    """Validate that the password contains at least one uppercase letter."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_upper",
            )

    def get_help_text(self):
        return _("Your password must contain at least one uppercase letter.")


class LowercaseValidator:
    """Validate that the password contains at least one lowercase letter."""

    def validate(self, password, user=None):
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lower",
            )

    def get_help_text(self):
        return _("Your password must contain at least one lowercase letter.")


class DigitValidator:
    """Validate that the password contains at least one digit."""

    def validate(self, password, user=None):
        if not re.search(r"\d", password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code="password_no_digit",
            )

    def get_help_text(self):
        return _("Your password must contain at least one digit.")


class SpecialCharacterValidator:
    """Validate that the password contains at least one special character."""

    SPECIAL_CHARS = r"""!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?"""

    def validate(self, password, user=None):
        if not re.search(f"[{re.escape(self.SPECIAL_CHARS)}]", password):
            raise ValidationError(
                _("Password must contain at least one special character (e.g. !@#$%%^&*)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least one special character (e.g. !@#$%%^&*)."
        )


class NoWhitespaceValidator:
    """Validate that the password does not contain whitespace."""

    def validate(self, password, user=None):
        if re.search(r"\s", password):
            raise ValidationError(
                _("Password must not contain spaces or whitespace characters."),
                code="password_has_whitespace",
            )

    def get_help_text(self):
        return _("Your password must not contain any spaces.")


class EmailSimilarityValidator:
    """Validate that the password is not too similar to the user's email."""

    def validate(self, password, user=None):
        if not user or not getattr(user, "email", None):
            return

        email_local_part = user.email.split("@")[0].lower()
        if email_local_part and email_local_part in password.lower():
            raise ValidationError(
                _("Password cannot contain your email address."),
                code="password_too_similar_email",
            )

    def get_help_text(self):
        return _("Your password can't be too similar to your email address.")