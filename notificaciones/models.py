from django.db import models
from django.contrib.auth.models import User

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('solicitud', 'Solicitud de ingreso'),
        ('aceptacion', 'Solicitud aceptada'),
        ('rechazo', 'Solicitud rechazada'),
        ('calificacion', 'Ejercicio calificado'),
        ('anuncio', 'Nuevo anuncio'),
        ('recordatorio', 'Recordatorio'),
        ('sistema', 'Sistema'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='sistema')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    url_destino = models.CharField(max_length=500, blank=True, null=True)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.titulo}"