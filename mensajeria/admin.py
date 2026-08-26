from django.contrib import admin
from .models import Conversacion, Mensaje

@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ['id', 'fecha_creacion', 'ultimo_mensaje']
    filter_horizontal = ['participantes']
    search_fields = ['participantes__username']

@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversacion', 'remitente', 'fecha_envio', 'leido']
    list_filter = ['leido', 'fecha_envio']
    search_fields = ['contenido', 'remitente__username']