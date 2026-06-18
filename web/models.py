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

    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    portada = models.ImageField(upload_to='cursos/portadas/', null=True, blank=True)
    url_portada_respaldo = models.URLField(blank=True, help_text="Por si usas links de Unsplash")
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='basico')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='teoria')
    duracion_horas = models.IntegerField(default=0)

    def __str__(self):
        return self.titulo

class Modulo(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos')
    titulo = models.CharField(max_length=150)
    contenido = models.TextField(help_text="Qué se enseñará en este módulo")

    def __str__(self):
        return f"{self.curso.titulo} - {self.titulo}"