from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator

class Clase(models.Model):
    TEMA_CATEGORIAS = [
        ('armonia', 'Armonía'),
        ('ritmo', 'Ritmo'),
        ('melodia', 'Melodía'),
    ]

    nombre = models.CharField(max_length=100)
    categoria_tema = models.CharField(max_length=20, choices=TEMA_CATEGORIAS, default='armonia') 
    descripcion = models.TextField(blank=True)
    docente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clases_docente')
    estudiantes = models.ManyToManyField(User, related_name='clases_estudiante', blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    codigo = models.CharField(max_length=8, unique=True, blank=True)
    imagen = models.ImageField(upload_to='clases/', blank=True, null=True)
    nivel_previo = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='nivel_siguiente'
    )
    max_estudiantes = models.PositiveIntegerField(default=35,validators=[MinValueValidator(1),
        MaxValueValidator(35)
    ])
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    def clean(self):
        # Máx 3 clases por docente
        clases_docente = Clase.objects.filter(docente=self.docente).exclude(pk=self.pk).count()
        if clases_docente >= 3:
            raise ValidationError("Haz alcanzado el maximo de clases permitidas.")

    def agregar_estudiante(self, estudiante):
        if self.estudiantes.count() >= self.max_estudiantes:
            raise ValidationError(f"La clase ya tiene el máximo de {self.max_estudiantes} estudiantes.")
        self.estudiantes.add(estudiante)

    def save(self, *args, **kwargs):
        if not self.codigo:
            import random, string
            self.codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre
    
class InscripcionClase(models.Model):
        estudiante = models.ForeignKey(User, on_delete=models.CASCADE)
        clase = models.ForeignKey(Clase, on_delete=models.CASCADE)
        veces_inscrito = models.PositiveIntegerField(default=1)
        bloqueado = models.BooleanField(default=False) # Si ya agotó sus 2 oportunidades de la clase
        fecha_inscripcion = models.DateTimeField(auto_now=True)

        class Meta:
            unique_together = ('estudiante', 'clase')
        def __str__(self):
            return f"{self.estudiante.username} - {self.clase.nombre} (Intento {self.veces_inscrito})"


class SolicitudClase(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='solicitudes')
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_clase')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')
    intentos = models.PositiveIntegerField(default=1)  # 👈 Cuenta las veces que ha cursado/solicitado
    bloqueado = models.BooleanField(default=False)    # 👈 Se activa si llega a 2 y reprueba/es expulsado
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('clase', 'estudiante')

    def __str__(self):
        return f"{self.estudiante.username} → {self.clase.nombre} ({self.estado} - Intento {self.intentos}/2)"


class Anuncio(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='anuncios')
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anuncio en {self.clase.nombre}"

    class Meta:
        unique_together = ('estudiante', 'pregunta')

class HistorialInscripcion(models.Model):
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE)
    categoria_tema = models.CharField(max_length=100) # O puedes relacionarlo directamente con la clase
    intentos = models.PositiveIntegerField(default=1)
    bloqueado = models.BooleanField(default=False)