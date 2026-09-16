from django.db import models
from django.contrib.auth.models import User , AbstractUser
from django.utils import timezone
from django.conf import settings

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
    
    # AGREGAR ESTE CAMPO
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
class Certificado(models.Model):
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificados_recibidos'
    )
    clase = models.ForeignKey(
        'clase.Clase',
        on_delete=models.CASCADE,
        related_name='certificados'
    )
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificados_emitidos'
    )

    fecha_emision = models.DateTimeField(auto_now_add=True)
    promedio_final = models.DecimalField(max_digits=3, decimal_places=1)
    progreso_final = models.PositiveIntegerField(default=100)
    horas_completadas = models.PositiveIntegerField(default=0)
    codigo_verificacion = models.CharField(max_length=50, unique=True)

    # PDF generado (opcional, si lo guardas)
    pdf = models.FileField(upload_to='certificados/', blank=True, null=True)

    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('estudiante', 'clase')
        ordering = ['-fecha_emision']
        verbose_name = 'Certificado'
        verbose_name_plural = 'Certificados'

    def __str__(self):
        return f"Certificado de {self.estudiante.username} en {self.clase.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo_verificacion:
            año = timezone.now().year
            self.codigo_verificacion = (
                f"CERT-{año}-{self.clase.id:04d}-{self.estudiante.id:04d}"
            )
        super().save(*args, **kwargs)