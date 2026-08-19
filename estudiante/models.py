from django.db import models
from django.conf import settings
from clase.models import Clase
from ejercicios.models import Ejercicio, Pregunta  # ← Importa de ejercicios, NO definas aquí


class RespuestaEstudiante(models.Model):
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='respuestas_estudiante_directas'
    )
    
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name='respuestas_estudiantes_preguntas'
    )
    
    respuesta_seleccionada = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)
    fecha_respuesta = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('estudiante', 'pregunta')

    def __str__(self):
        return f"{self.estudiante.username} - {self.pregunta.enunciado[:30]}"


class Intento(models.Model):
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='intentos_estudiante'
    )
    ejercicio = models.ForeignKey(
        Ejercicio,
        on_delete=models.CASCADE,
        related_name='intentos_ejercicio'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Intento de {self.estudiante.username} - {self.ejercicio.titulo}"


class Perfil(models.Model):
    # ... campos existentes ...
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)