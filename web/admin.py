from django.contrib import admin
from .models import Curso, Modulo

class ModuloInline(admin.TabularInline):
    model = Modulo
    extra = 1  # Te da un espacio en blanco inicial para añadir un módulo rápido

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'nivel', 'duracion_horas')
    list_filter = ('categoria', 'nivel')
    search_fields = ('nombre', 'descripcion')
    inlines = [ModuloInline]  # <-- Esto permite meter el contenido adentro del curso