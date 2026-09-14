from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import generador_token_verificacion


def enviar_correo_verificacion(request, user):
    """
    Envía el correo con el link de verificación al usuario recién registrado.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = generador_token_verificacion.make_token(user)

    path = reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token})
    url_verificacion = request.build_absolute_uri(path)

    contexto = {
        'user': user,
        'url_verificacion': url_verificacion,
        'sitio': 'QBYT',
    }

    asunto = '✅ Verifica tu cuenta en QBYT'

    texto_plano = (
        f'Hola {user.first_name or user.username},\n\n'
        f'Gracias por registrarte en QBYT.\n'
        f'Para activar tu cuenta, haz clic en este enlace:\n\n'
        f'{url_verificacion}\n\n'
        f'Si no te registraste, ignora este correo.\n\n'
        f'— El equipo de QBYT'
    )

    html = render_to_string('web/emails/verificacion.html', contexto)

    email = EmailMultiAlternatives(
        subject=asunto,
        body=texto_plano,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html, 'text/html')
    email.send(fail_silently=False)