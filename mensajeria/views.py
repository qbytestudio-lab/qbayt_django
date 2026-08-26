from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from clase.models import Clase
from .models import Conversacion, Mensaje
from notificaciones.services import crear_notificacion


@login_required
def listar_conversaciones(request):
    """
    Vista principal de mensajería
    """
    # Obtener clases según el rol
    if request.user.perfil.rol == 'docente':
        clases = Clase.objects.filter(docente=request.user)
    else:
        clases = request.user.clases_estudiante.all()
    
    # Obtener conversaciones
    conversaciones = Conversacion.objects.filter(
        participantes=request.user
    ).order_by('-ultimo_mensaje', '-fecha_creacion')
    
    conversaciones_info = []
    for conversacion in conversaciones:
        otro_participante = conversacion.obtener_otro_participante(request.user)
        no_leidos = conversacion.contar_no_leidos(request.user)
        ultimo_mensaje = conversacion.mensajes.last()
        
        conversaciones_info.append({
            'conversacion': conversacion,
            'otro_participante': otro_participante,
            'no_leidos': no_leidos,
            'ultimo_mensaje': ultimo_mensaje,
        })
    
    context = {
        'clases': clases,
        'conversaciones': conversaciones_info,
    }
    return render(request, 'mensajeria/lista_conversaciones.html', context)


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