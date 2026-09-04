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
    
