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
    # NUEVO
    tags = models.CharField(max_length=255, blank=True, help_text="Etiquetas separadas por coma")
    vistas = models.PositiveIntegerField(default=0)
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
        """True si hay un archivo subido Y no está vacío."""
        try:
            return bool(self.archivo and self.archivo.name)
        except (ValueError, AttributeError):
            return False
    @property
    def tiene_url(self):
        """True si hay una URL externa."""
        return bool(self.url_externa)
    @property
    def archivo_url(self):
        """Devuelve la URL del archivo o cadena vacía."""
        try:
            if self.archivo and self.archivo.name:
                return self.archivo.url
        except (ValueError, AttributeError):
            pass
        return ''
    # NUEVA PROPIEDAD: lista de tags
    @property
    def tags_lista(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]