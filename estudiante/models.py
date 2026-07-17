from django.db import models
from django.conf import settings

class RespuestaEstudiante(models.Model):
    # Solucionamos el choque usando un related_name único para esta app
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='respuestas_estudiante_directas' 
    )
    
    # Cambia 'docente.Pregunta' por la app y modelo reales de tus preguntas.
    # Por ejemplo, si está en la app 'clase', usa 'clase.Pregunta'
    pregunta = models.ForeignKey(
        'clase.Pregunta', # <-- ¡Ajusta esta app y modelo!
        on_delete=models.CASCADE, 
        related_name='respuestas_estudiantes_preguntas'
    ) 
    
    respuesta_seleccionada = models.CharField(max_length=255) 
    es_correcta = models.BooleanField(default=False)
    fecha_respuesta = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('estudiante', 'pregunta')