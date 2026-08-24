from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notificacion

@login_required
def listar_notificaciones(request):
    """Vista para listar todas las notificaciones del usuario"""
    # Primero obtenemos el queryset base
    notificaciones_queryset = Notificacion.objects.filter(usuario=request.user)
    
    # Contamos las no leídas ANTES de hacer slice
    no_leidas = notificaciones_queryset.filter(leida=False).count()
    
    # Después hacemos el slice para mostrar solo 50
    notificaciones = notificaciones_queryset[:50]
    
    context = {
        'notificaciones': notificaciones,
        'no_leidas': no_leidas,
    }
    return render(request, 'notificaciones/lista.html', context)


@login_required
def marcar_leida(request, notificacion_id):
    """Marcar una notificación como leída"""
    notificacion = get_object_or_404(
        Notificacion, 
        id=notificacion_id, 
        usuario=request.user
    )
    notificacion.leida = True
    notificacion.save()
    
    if notificacion.url_destino:
        return redirect(notificacion.url_destino)
    return redirect('notificaciones:lista')


@login_required
def marcar_todas_leidas(request):
    """Marcar todas las notificaciones como leídas"""
    Notificacion.objects.filter(
        usuario=request.user, 
        leida=False
    ).update(leida=True)
    return redirect('notificaciones:lista')


@login_required
def obtener_no_leidas(request):
    """API para obtener notificaciones no leídas (para AJAX)"""
    # Primero filtramos
    notificaciones_queryset = Notificacion.objects.filter(
        usuario=request.user, 
        leida=False
    )
    
    # Contamos antes del slice
    count = notificaciones_queryset.count()
    
    # Después hacemos el slice
    notificaciones = notificaciones_queryset[:10]
    
    data = {
        'count': count,
        'notificaciones': [
            {
                'id': n.id,
                'titulo': n.titulo,
                'mensaje': n.mensaje,
                'tipo': n.tipo,
                'url': n.url_destino or '#',
                'fecha': n.fecha_creacion.strftime('%d %b %H:%M'),
            }
            for n in notificaciones
        ]
    }
    return JsonResponse(data)