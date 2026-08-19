from django.db import models
from django.contrib.auth.models import User , AbstractUser
from clase.models import Actividad, Opcion

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
    CATEGORIA_CHOICES = [
        ('teoria', '🎵 Teoría Musical'),
        ('auditivo', '👂 Entrenamiento Auditivo'),
        ('instrumento', '🎸 Instrumento'),
    ]
    
    NIVEL_CHOICES = [
        ('basico', '🟢 Básico'),
        ('intermedio', '🟠 Intermedio'),
        ('avanzado', '🔴 Avanzado'),
    ]
    
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='teoria')
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='basico')
    duracion_horas = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to='cursos/', blank=True, null=True)
    imagen_url = models.URLField(blank=True, null=True)
    icono = models.CharField(max_length=50, default='bi-book')
    
    # ✅ AGREGAR ESTE CAMPO
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,  # Si el usuario se elimina, el curso no se borra
        null=True, 
        blank=True,
        related_name='cursos_creados'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
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
    nombre = models.CharField(max_length=200)
    contenido = models.TextField()
    orden = models.IntegerField(default=1)  # ← Agrega este campo
    
    class Meta:
        ordering = ['orden']  # ← Ordenar por este campo
    
    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
  nivel_musical = models.IntegerField(default=1, blank=True, null=True)

  # Solución para el error de conflicto de nombres:
  groups = models.ManyToManyField(
      'auth.Group',
      verbose_name='groups',
      blank=True,
      help_text=(
          'The groups this user belongs to. A user will get all permissions'
          ' granted to each of their groups.'
      ),
      related_name='usuario_set',  # <--- Cambia esto
      related_query_name='usuario',
  )
  user_permissions = models.ManyToManyField(
      'auth.Permission',
      verbose_name='user permissions',
      blank=True,
      help_text='Specific permissions for this user.',
      related_name='usuario_permissions_set',  # <--- Cambia esto
      related_query_name='usuario',
  )
