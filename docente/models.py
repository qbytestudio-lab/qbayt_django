from django.db import models
from django.contrib.auth.models import User

class Clase(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    docente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clases_docente')
    estudiantes = models.ManyToManyField(User, related_name='clases_estudiante', blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    codigo = models.CharField(max_length=8, unique=True, blank=True)
    imagen = models.ImageField(
        upload_to='clases/',
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        if not self.codigo:
            import random, string
            self.codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class SolicitudClase(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='solicitudes')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_clase')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('clase', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.username} → {self.clase.nombre} ({self.estado})"
    

class Anuncio(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='anuncios')
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anuncio en {self.clase.nombre}"


class Leccion(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='lecciones')
    titulo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=200, blank=True)
    orden = models.PositiveIntegerField(default=1)
    disponible = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return f"{self.orden}. {self.titulo}"
    
class Actividad(models.Model):
    TIPO_CHOICES = [
        ('texto', 'Texto / Lectura'),
        ('quiz', 'Quiz de selección múltiple'),
    ]
    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE, related_name='actividades')
    titulo = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='texto')
    contenido = models.TextField(blank=True)  # para tipo texto
    imagen = models.ImageField(upload_to='actividades/', blank=True, null=True)
    orden = models.PositiveIntegerField(default=1)
    fecha_limite = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.titulo


class Pregunta(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.CharField(max_length=300)
    imagen = models.ImageField(upload_to='preguntas/', blank=True, null=True)
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['orden']

    def __str__(self):
        return self.texto


class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=200)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return self.texto


class RespuestaEstudiante(models.Model):
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE)
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('estudiante', 'pregunta')




