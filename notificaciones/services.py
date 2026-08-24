from .models import Notificacion

def crear_notificacion(usuario, tipo, titulo, mensaje, url_destino=None):
    """
    Función auxiliar para crear notificaciones
    """
    notificacion = Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        url_destino=url_destino
    )
    return notificacion

def notificar_solicitud_clase(docente, estudiante, clase):
    """Notificar al docente sobre una nueva solicitud"""
    crear_notificacion(
        usuario=docente,
        tipo='solicitud',
        titulo='Nueva solicitud de ingreso',
        mensaje=f'{estudiante.get_full_name() or estudiante.username} solicita unirse a {clase.nombre}',
        url_destino=f'/docente/clase/{clase.id}/'
    )

def notificar_aceptacion(estudiante, clase):
    """Notificar al estudiante que fue aceptado"""
    crear_notificacion(
        usuario=estudiante,
        tipo='aceptacion',
        titulo='Solicitud aceptada',
        mensaje=f'Fuiste aceptado en la clase {clase.nombre}',
        url_destino=f'/estudiante/clase/{clase.id}/'
    )

def notificar_rechazo(estudiante, clase):
    """Notificar al estudiante que fue rechazado"""
    crear_notificacion(
        usuario=estudiante,
        tipo='rechazo',
        titulo='Solicitud rechazada',
        mensaje=f'Tu solicitud para la clase {clase.nombre} fue rechazada',
        url_destino=f'/estudiante/explorar-clases/'
    )

def notificar_calificacion(estudiante, ejercicio, calificacion):
    """Notificar al estudiante que su ejercicio fue calificado"""
    crear_notificacion(
        usuario=estudiante,
        tipo='calificacion',
        titulo='Ejercicio calificado',
        mensaje=f'Tu ejercicio "{ejercicio.titulo}" fue calificado con {calificacion}/5.0',
        url_destino=f'/estudiante/clase/{ejercicio.clase.id}/'
    )

def notificar_anuncio(estudiantes, clase, anuncio):
    """Notificar a todos los estudiantes sobre un nuevo anuncio"""
    for estudiante in estudiantes:
        crear_notificacion(
            usuario=estudiante,
            tipo='anuncio',
            titulo=f'Nuevo anuncio en {clase.nombre}',
            mensaje=anuncio.texto[:100],
            url_destino=f'/estudiante/clase/{clase.id}/'
        )
def notificar_nuevo_ejercicio(estudiantes, clase, ejercicio):
    """Notificar a todos los estudiantes sobre un nuevo ejercicio"""
    for estudiante in estudiantes:
        crear_notificacion(
            usuario=estudiante,
            tipo='anuncio',
            titulo=f'Nuevo ejercicio en {clase.nombre}',
            mensaje=f'El docente publicó un nuevo ejercicio: "{ejercicio.titulo}"',
            url_destino=f'/estudiante/clase/{clase.id}/'
        )