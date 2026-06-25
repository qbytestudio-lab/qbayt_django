from django.db import models
from django.contrib.auth.models import User
# Importa tu modelo Clase desde donde lo tengas definido

class Ejercicio(models.Model):
    clase = models.ForeignKey('docente.Clase', on_delete=models.CASCADE, related_name='ejercicios')
    titulo = models.CharField(max_length=200, verbose_name="Título del Ejercicio")
    enunciado = models.TextField(verbose_name="Instrucciones o Enunciado")
    imagen_contexto = models.ImageField(upload_to='ejercicios/contextos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    visible = models.BooleanField(default=True, verbose_name="Disponible para estudiantes")

    def __str__(self):
        return self.titulo

class Pregunta(models.Model):
    TIPO_RESPUESTA = [
        ('OPCION_MULTIPLE', 'Selección Múltiple con Única Respuesta'),
        ('TEXTO', 'Texto Abierto / Escribir Respuesta'),
    ]
    
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE, related_name='preguntas')
    texto_pregunta = models.TextField(verbose_name="Pregunta")
    tipo = models.CharField(max_length=20, choices=TIPO_RESPUESTA, default='OPCION_MULTIPLE')

    def __str__(self):
        return f"{self.ejercicio.titulo} - {self.texto_pregunta[:30]}"