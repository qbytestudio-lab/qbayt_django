from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Perfil(models.Model):
    ROL_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('administrador', 'Administrador'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='estudiante')

    def __str__(self):
        return f"{self.user.username} - {self.rol}"

class Curso(models.Model):
    NIVEL_CHOICES = [
        ('basico', 'Básico'),
        ('intermedio', 'Intermedio'),
        ('avanzado', 'Avanzado'),
    ]
    CATEGORIA_CHOICES = [
        ('teoria', 'Teoría Musical'),
        ('auditivo', 'Entrenamiento Auditivo'),
        ('instrumento', 'Instrumento'),
    ]
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='basico')
    duracion_horas = models.PositiveIntegerField(default=1)
    imagen_url = models.URLField(blank=True)  # para usar las imágenes que ya tienes
    icono = models.CharField(max_length=50, default='bi-music-note')

    def __str__(self):
        return self.nombre


class InscripcionCurso(models.Model):
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cursos_inscritos')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='inscritos')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    progreso = models.PositiveIntegerField(default=0)  # % manual o calculado luego

    class Meta:
        unique_together = ('estudiante', 'curso')

    def __str__(self):
        return f"{self.estudiante.username} - {self.curso.nombre}"

class Modulo(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos')
    titulo = models.CharField(max_length=150)
    contenido = models.TextField(help_text="Qué se enseñará en este módulo")

    def __str__(self):
        return f"{self.curso.titulo} - {self.titulo}"