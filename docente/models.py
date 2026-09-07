# docente/models.py
from django.db import models
from django.contrib.auth.models import User
from clase.models import ( Clase, SolicitudClase, Anuncio )


class RecursoMusical(models.Model):
    TIPO_CHOICES = [
        ('audio', 'Audio'),
        ('partitura', 'Partitura'),
        ('video', 'Video'),
        ('documento', 'Documento'),
        ('imagen', 'Imagen'),
    ]
    
    CATEGORIA_CHOICES = [
        ('intervalos', 'Intervalos'),
        ('acordes', 'Acordes'),
        ('escalas', 'Escalas'),
        ('ritmo', 'Ritmo'),
        ('melodia', 'Melodía'),
        ('armonia', 'Armonía'),
        ('teoria', 'Teoría Musical'),
        ('otro', 'Otro'),
    ]
    
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='documento')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otro')
    
    archivo = models.FileField(upload_to='recursos/', blank=True, null=True)
    url_externa = models.URLField(blank=True, null=True)
    
    docente = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='recursos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Recurso Musical'
        verbose_name_plural = 'Recursos Musicales'
    
    def __str__(self):
        return self.titulo
    
    @property
    def tiene_archivo(self):
        return self.archivo is not None
    
    @property
    def tiene_url(self):
        return self.url_externa is not None