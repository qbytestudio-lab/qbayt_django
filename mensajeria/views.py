from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone

from clase.models import Clase
from .models import Conversacion, Mensaje
from notificaciones.services import crear_notificacion


# ═══════════════════════════════════════════════════════════
# HELPER DE EXPIRACIÓN
# ═══════════════════════════════════════════════════════════

DIAS_GRACIA = 5


def _filtrar_clases_visibles_estudiante(queryset):
    """Excluye clases vencidas hace más de DIAS_GRACIA días."""
    limite = timezone.now().date() - timedelta(days=DIAS_GRACIA)
    return queryset.exclude(fecha_fin__lt=limite)


@login_required
def listar_conversaciones(request):
    usuario = request.user

    # ─────────────────────────────────────────────
    # 1. Asegurar chat de clase por cada clase donde participa
    # ─────────────────────────────────────────────
    if usuario.perfil.rol == 'docente':
        clases = Clase.objects.filter(docente=usuario)
    else:
        clases = _filtrar_clases_visibles_estudiante(usuario.clases_estudiante.all())

    for clase in clases:
        conv, _ = Conversacion.objects.get_or_create(
            clase=clase,
            defaults={'tipo': 'clase'}
        )
        if conv.tipo != 'clase':
            conv.tipo = 'clase'
            conv.save(update_fields=['tipo'])

        participantes_ids = [clase.docente.id] + list(
            clase.estudiantes.values_list('id', flat=True)
        )
        conv.participantes.set(participantes_ids)

    # ─────────────────────────────────────────────
    # 2. Traer TODAS las conversaciones del usuario
    # ─────────────────────────────────────────────
    conversaciones = Conversacion.objects.filter(
        participantes=usuario
    ).annotate(
        num_participantes=Count('participantes')
    ).filter(
        num_participantes__gte=2
    ).distinct().order_by('-ultimo_mensaje', '-fecha_creacion')

    items = []
    for conv in conversaciones:
        otro = conv.obtener_otro_participante(usuario)
        ultimo = conv.mensajes.order_by('-fecha_envio').first()
        no_leidos = conv.contar_no_leidos(usuario)

        if conv.tipo == 'privada' and otro is None:
            continue

        # Ocultar chats de clase expirada (> 5 días vencida)
        if (
            usuario.perfil.rol == 'estudiante'
            and conv.tipo == 'clase'
            and conv.clase
            and conv.clase.esta_expirada
        ):
            continue

        items.append({
            'conversacion': conv,
            'otro_participante': otro,
            'ultimo_mensaje': ultimo,
            'no_leidos': no_leidos,
            'es_clase': conv.tipo == 'clase',
            'clase': conv.clase if conv.tipo == 'clase' else None,
        })

    # Sidebar: clases del usuario
    if usuario.perfil.rol == 'docente':
        clases_sidebar = Clase.objects.filter(docente=usuario)
    else:
        clases_sidebar = _filtrar_clases_visibles_estudiante(usuario.clases_estudiante.all())

    return render(request, 'mensajeria/lista_conversaciones.html', {
        'items': items,
        'clases': clases_sidebar,
    })


@login_required
def contactos_clase(request, clase_id):
    """
    Vista para ver los contactos de una clase + chat grupal.
    Si la clase está bloqueada y el usuario es estudiante, se bloquea TODO.
    Si la clase expiró (> 5 días), no existe para el estudiante.
    """
    clase = get_object_or_404(Clase, id=clase_id)

    # Verificar acceso + bloqueo
    if request.user.perfil.rol == 'docente':
        if clase.docente != request.user:
            messages.error(request, 'No tienes acceso a esta clase.')
            return redirect('mensajeria:lista')
        contactos = clase.estudiantes.all()
    else:
        if request.user not in clase.estudiantes.all():
            messages.error(request, 'No tienes acceso a esta clase.')
            return redirect('mensajeria:lista')

        # Si expiró, no existe para el estudiante
        if clase.esta_expirada:
            messages.error(request, 'Esta clase ya no está disponible.')
            return redirect('mensajeria:lista')

        # Si está bloqueada (≤ 5 días), no entra
        if clase.esta_bloqueada:
            messages.error(request, clase.motivo_bloqueo)
            return redirect('mensajeria:lista')

        contactos = list(clase.estudiantes.exclude(id=request.user.id))
        contactos.insert(0, clase.docente)

    # Obtener o crear chat grupal
    conversacion_clase, _ = Conversacion.objects.get_or_create(
        clase=clase,
        defaults={'tipo': 'clase'}
    )
    if conversacion_clase.tipo != 'clase':
        conversacion_clase.tipo = 'clase'
        conversacion_clase.save(update_fields=['tipo'])

    participantes_ids = [clase.docente.id] + list(
        clase.estudiantes.values_list('id', flat=True)
    )
    conversacion_clase.participantes.set(participantes_ids)

    context = {
        'clase': clase,
        'contactos': contactos,
        'conversacion_clase': conversacion_clase,
    }
    return render(request, 'mensajeria/contactos_clase.html', context)


@login_required
def iniciar_conversacion(request, usuario_id):
    """
    Iniciar o continuar conversación privada con un usuario.
    - Bloqueado si estudiante y comparte con el otro una clase bloqueada (≤ 5 días).
    - Si la clase ya expiró (> 5 días), ya no bloquea.
    """
    otro_usuario = get_object_or_404(User, id=usuario_id)

    if otro_usuario == request.user:
        messages.error(request, 'No puedes iniciar una conversación contigo mismo.')
        return redirect('mensajeria:lista')

    # Bloqueo: si soy estudiante y comparto una clase aún bloqueada
    if request.user.perfil.rol == 'estudiante':
        clases_en_comun = (
            Clase.objects.filter(
                Q(estudiantes=request.user) & Q(estudiantes=otro_usuario)
            )
            | Clase.objects.filter(
                Q(estudiantes=request.user) & Q(docente=otro_usuario)
            )
        ).distinct()

        bloqueadas = [
            c for c in clases_en_comun
            if c.esta_bloqueada and not c.esta_expirada
        ]

        if bloqueadas:
            messages.error(
                request,
                f'No puedes enviar mensajes mientras la clase '
                f'"{bloqueadas[0].nombre}" esté cerrada. '
                f'{bloqueadas[0].motivo_bloqueo}'
            )
            return redirect('mensajeria:lista')

    # Buscar o crear conversación privada
    conversacion = Conversacion.objects.filter(
        tipo='privada',
        participantes=request.user
    ).filter(
        participantes=otro_usuario
    ).first()

    if not conversacion:
        conversacion = Conversacion.objects.create(tipo='privada')
        conversacion.participantes.add(request.user, otro_usuario)

    return redirect('mensajeria:detalle', conversacion_id=conversacion.id)


@login_required
def detalle_conversacion(request, conversacion_id):
    conversacion = get_object_or_404(Conversacion, id=conversacion_id)

    # Verificar acceso
    if request.user not in conversacion.participantes.all():
        messages.error(request, 'No tienes acceso a esta conversación.')
        return redirect('mensajeria:lista')

    # Chat grupal de clase
    if (
        conversacion.tipo == 'clase'
        and conversacion.clase
        and request.user.perfil.rol == 'estudiante'
    ):
        if conversacion.clase.esta_expirada:
            messages.error(request, 'Esta clase ya no está disponible.')
            return redirect('mensajeria:lista')

        if conversacion.clase.esta_bloqueada:
            messages.error(request, conversacion.clase.motivo_bloqueo)
            return redirect('mensajeria:lista')

    # Chat privado con persona de una clase bloqueada aún vigente
    if conversacion.tipo == 'privada' and request.user.perfil.rol == 'estudiante':
        otro = conversacion.obtener_otro_participante(request.user)
        if otro:
            clases_en_comun = (
                Clase.objects.filter(
                    Q(estudiantes=request.user) & Q(estudiantes=otro)
                )
                | Clase.objects.filter(
                    Q(estudiantes=request.user) & Q(docente=otro)
                )
            ).distinct()

            bloqueadas = [
                c for c in clases_en_comun
                if c.esta_bloqueada and not c.esta_expirada
            ]

            if bloqueadas:
                messages.error(
                    request,
                    f'No puedes enviar mensajes mientras la clase '
                    f'"{bloqueadas[0].nombre}" esté cerrada. '
                    f'{bloqueadas[0].motivo_bloqueo}'
                )
                return redirect('mensajeria:lista')

    # Marcar como leídos
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
            conversacion.save(update_fields=['ultimo_mensaje'])

            if conversacion.tipo == 'privada' and otro_participante:
                crear_notificacion(
                    usuario=otro_participante,
                    tipo='sistema',
                    titulo='Nuevo mensaje',
                    mensaje=f'{request.user.get_full_name() or request.user.username} te envió un mensaje',
                    url_destino=f'/mensajeria/conversacion/{conversacion.id}/'
                )
            elif conversacion.tipo == 'clase':
                for participante in conversacion.participantes.exclude(id=request.user.id):
                    crear_notificacion(
                        usuario=participante,
                        tipo='sistema',
                        titulo=f'Nuevo mensaje en {conversacion.clase.nombre}',
                        mensaje=f'{request.user.get_full_name() or request.user.username}: {contenido[:60]}',
                        url_destino=f'/mensajeria/conversacion/{conversacion.id}/'
                    )

            return redirect('mensajeria:detalle', conversacion_id=conversacion.id)

    context = {
        'conversacion': conversacion,
        'mensajes': mensajes,
        'otro_participante': otro_participante,
        'es_clase': conversacion.tipo == 'clase',
    }
    return render(request, 'mensajeria/detalle_conversacion.html', context)