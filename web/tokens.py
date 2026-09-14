from django.contrib.auth.tokens import PasswordResetTokenGenerator


class TokenVerificacionCuenta(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{timestamp}{user.is_active}"


generador_token_verificacion = TokenVerificacionCuenta()