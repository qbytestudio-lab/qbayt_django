from django.db import models
# Importa tu modelo Clase de la app donde lo tengas definido (ej. 'docente' o 'clases')
# Si tu modelo de clase está en 'docente', sería:
# from docente.models import Clase

class Ejercicio(models.Model):
    # Apuntamos a la app 'clase' y al modelo 'Clase'
    clase = models.ForeignKey('clase.Clase', on_delete=models.CASCADE, related_name='ejercicios')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

class Pregunta(models.Model):
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.CASCADE, related_name='preguntas')
    enunciado = models.TextField()
    imagen = models.ImageField(upload_to='preguntas_img/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.enunciado[:50]}..."

class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    texto_opcion = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return self.texto_opcion