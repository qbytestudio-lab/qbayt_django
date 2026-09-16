from django.db import models
from django.contrib.auth.models import User


class Conversacion(models.Model):
    TIPO_CHOICES = [
        ('privada', 'Privada'),
        ('clase', 'Chat de clase'),
    ]

    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default='privada'
    )

    clase = models.OneToOneField(
        'clase.Clase',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='conversacion'
    )

    participantes = models.ManyToManyField(User, related_name='conversaciones')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultimo_mensaje = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-ultimo_mensaje', '-fecha_creacion']

    def __str__(self):
        if self.tipo == 'clase' and self.clase:
            return f"Chat de clase: {self.clase.nombre}"
        nombres = [p.username for p in self.participantes.all()]
        return f"Conversación: {', '.join(nombres)}"

    def obtener_otro_participante(self, usuario):
        # En chats de clase no aplica "el otro participante"
        if self.tipo == 'clase':
            return None
        return self.participantes.exclude(id=usuario.id).first()

    def contar_no_leidos(self, usuario):
        return self.mensajes.filter(leido=False).exclude(remitente=usuario).count()


class Mensaje(models.Model):
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados')
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['fecha_envio']

    def __str__(self):
        return f"{self.remitente.username}: {self.contenido[:50]}"