from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class Ejercicio(models.Model):

    TIPO_CHOICES = [
        ('quiz', 'Quiz'),
        ('video_quiz', 'Video + Quiz'),  # ✅ Reemplaza a imagen_quiz
        ('juego', 'Juego'),
        ('texto', 'Texto'),
        ('verdadero_falso', 'Verdadero o Falso'),
        ('completar', 'Completar'),
    ]
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='quiz')
    clase = models.ForeignKey('clase.Clase', on_delete=models.CASCADE, related_name='ejercicios')
    titulo = models.CharField(max_length=200)
    
    descripcion = models.TextField(blank=True, null=True)
    contenido = models.TextField(blank=True, null=True)

    #  CAMPOS PARA VIDEO
    video_principal = models.FileField(
        upload_to='ejercicios/videos/',
        blank=True,
        null=True,
        verbose_name="Video principal"
    )
    
    video_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="URL del video (YouTube, Vimeo)"
    )

    #  Campo de imagen opcional (para thumbnail o imagen adicional)
    imagen_principal = models.ImageField(
        upload_to='ejercicios/',
        blank=True,
        null=True,
        verbose_name="Imagen (opcional)"
    )

    juego_tipo = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_limite = models.DateTimeField(
        verbose_name="Fecha de entrega",
        blank=True,
        null=True
    )

    def __str__(self):
        return self.titulo
    
    #  Propiedad para verificar si es video quiz
    @property
    def es_video_quiz(self):
        return self.tipo == 'video_quiz'
    
    #  Propiedad para obtener la URL del video (archivo o externa)
    @property
    def url_video(self):
        if self.video_principal:
            return self.video_principal.url
        return self.video_url

    class Meta:
        verbose_name = "Ejercicio"
        verbose_name_plural = "Ejercicios"

class Pregunta(models.Model):
    ejercicio = models.ForeignKey(
        Ejercicio,
        on_delete=models.CASCADE,
        related_name='preguntas'
    )

    enunciado = models.TextField()

    imagen = models.ImageField(
        upload_to='preguntas_img/',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.enunciado[:50]}..."
    
    #  AGREGAR ESTA PROPIEDAD
    @property
    def opcion_correcta(self):
        """Devuelve la opción correcta de esta pregunta"""
        return self.opciones.filter(es_correcta=True).first()


class Opcion(models.Model):
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name='opciones'
    )

    texto_opcion = models.CharField(
        max_length=255
    )

    es_correcta = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.texto_opcion


class IntentoEjercicio(models.Model):
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='intentos'
    )

    ejercicio = models.ForeignKey(
        Ejercicio,
        on_delete=models.CASCADE,
        related_name='intentos'
    )

    fecha_envio = models.DateTimeField(
        auto_now_add=True
    )

    calificacion = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1.0),
            MaxValueValidator(5.0)
        ]
    )

    retroalimentacion = models.TextField(
        blank=True,
        null=True
    )

    aprobado = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"Intento de {self.estudiante.username} en {self.ejercicio}"


class RespuestaEstudiante(models.Model):
    intento = models.ForeignKey(
        IntentoEjercicio,
        on_delete=models.CASCADE,
        related_name='respuestas'
    )

    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE
    )

    opcion_seleccionada = models.ForeignKey(
        Opcion,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return (
            f"{self.intento.estudiante.username} - "
            f"{self.pregunta.enunciado[:30]}"
        )