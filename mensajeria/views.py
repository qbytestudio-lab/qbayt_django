from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from clase.models import Clase
from .models import Conversacion, Mensaje
from notificaciones.services import crear_notificacion
from django.db.models import Count


@login_required
def listar_conversaciones(request):
    # Solo conversaciones donde participa el usuario Y que tengan al menos 2 participantes
    conversaciones = Conversacion.objects.filter(
        participantes=request.user
    ).annotate(
        num_participantes=Count('participantes')
    ).filter(
        num_participantes__gte=2  # filtra las huérfanas
    ).distinct()

    items = []
    for conv in conversaciones:
        # Buscar el "otro" participante (que no sea el usuario actual)
        otro = conv.participantes.exclude(id=request.user.id).first()

        # Si no hay otro, saltar esta conversación (defensivo)
        if otro is None:
            continue

        ultimo = conv.mensajes.order_by('-fecha_envio').first()

        items.append({
            'conversacion': conv,
            'otro_participante': otro,
            'ultimo_mensaje': ultimo,
        })

    return render(request, 'mensajeria/lista_conversaciones.html', {
        'items': items,
    })

@login_required
def contactos_clase(request, clase_id):
    """
    Vista para ver los contactos de una clase
    """
    clase = get_object_or_404(Clase, id=clase_id)
    
    # Verificar acceso
    if request.user.perfil.rol == 'docente':
        if clase.docente != request.user:
            messages.error(request, 'No tienes acceso a esta clase.')
            return redirect('mensajeria:lista')
        contactos = clase.estudiantes.all()
    else:
        if request.user not in clase.estudiantes.all():
            messages.error(request, 'No tienes acceso a esta clase.')
            return redirect('mensajeria:lista')
        # Para estudiantes: contactos son el docente y compañeros
        contactos = list(clase.estudiantes.exclude(id=request.user.id))
        contactos.insert(0, clase.docente)
    
    context = {
        'clase': clase,
        'contactos': contactos,
    }
    return render(request, 'mensajeria/contactos_clase.html', context)


@login_required
def iniciar_conversacion(request, usuario_id):
    """Iniciar o continuar conversación con un usuario"""
    otro_usuario = get_object_or_404(User, id=usuario_id)
    
    if otro_usuario == request.user:
        messages.error(request, 'No puedes iniciar una conversación contigo mismo.')
        return redirect('mensajeria:lista')
    
    conversacion = Conversacion.objects.filter(
        participantes=request.user
    ).filter(
        participantes=otro_usuario
    ).first()
    
    if not conversacion:
        conversacion = Conversacion.objects.create()
        conversacion.participantes.add(request.user, otro_usuario)
    
    return redirect('mensajeria:detalle', conversacion_id=conversacion.id)


@login_required
def detalle_conversacion(request, conversacion_id):
    """Ver mensajes de una conversación"""
    conversacion = get_object_or_404(Conversacion, id=conversacion_id)
    
    if request.user not in conversacion.participantes.all():
        messages.error(request, 'No tienes acceso a esta conversación.')
        return redirect('mensajeria:lista')
    
    # ✅ CORREGIDO: usar "leido" en lugar de "leida"
    conversacion.mensajes.filter(leido=False).exclude(
        remitente=request.user
    ).update(leido=True)
    
    mensajes = conversacion.mensajes.all()
    otro_participante = conversacion.obtener_otro_participante(request.user)
    
    if request.method == 'POST':
        contenido = request.POST.get('contenido', '').strip()
        
        if contenido:
            mensaje = Mensaje.objects.create(
                conversacion=conversacion,
                remitente=request.user,
                contenido=contenido
            )
            
            conversacion.ultimo_mensaje = mensaje.fecha_envio
            conversacion.save()
            
            crear_notificacion(
                usuario=otro_participante,
                tipo='sistema',
                titulo='Nuevo mensaje',
                mensaje=f'{request.user.get_full_name() or request.user.username} te envió un mensaje',
                url_destino=f'/mensajeria/conversacion/{conversacion.id}/'
            )
            
            return redirect('mensajeria:detalle', conversacion_id=conversacion.id)
    
    context = {
        'conversacion': conversacion,
        'mensajes': mensajes,
        'otro_participante': otro_participante,
    }
    return render(request, 'mensajeria/detalle_conversacion.html', context)