from django.db import models
from django.contrib.auth.models import User , AbstractUser

# Create your models here.
class Perfil(models.Model):
    ROL_CHOICES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('administrador', 'Administrador'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default='estudiante'
    )

    foto_perfil = models.ImageField(
        upload_to='perfiles/',
        blank=True,
        null=True
    )
    
    # ✅ AGREGAR ESTE CAMPO
    banner = models.ImageField(
        upload_to='banners/',
        blank=True,
        null=True
    )
    
    def __str__(self):
        return f"{self.user.username} - {self.rol}"
    

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
