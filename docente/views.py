from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Clase, SolicitudClase, Anuncio, Leccion

@login_required
def perfil_docente(request):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clases = Clase.objects.filter(docente=request.user)
    total_estudiantes = sum(c.estudiantes.count() for c in clases)
    solicitudes_pendientes = SolicitudClase.objects.filter(
        clase__docente=request.user,
        estado='pendiente'
    )
    return render(request, 'perfil_docente.html', {
        'clases': clases,
        'total_estudiantes': total_estudiantes,
        'solicitudes_pendientes': solicitudes_pendientes,
    })

@login_required
def crear_clase(request):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        if not nombre:
            messages.error(request, 'El nombre es obligatorio.')
            return redirect('perfil_docente')
        Clase.objects.create(nombre=nombre, descripcion=descripcion, docente=request.user)
        messages.success(request, f'¡Clase "{nombre}" creada!')
        return redirect('perfil_docente')
    return redirect('perfil_docente')

@login_required
def agregar_estudiante(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        try:
            estudiante = User.objects.get(username=username, perfil__rol='estudiante')
            if estudiante in clase.estudiantes.all():
                messages.warning(request, f'"{username}" ya está en esta clase.')
            else:
                clase.estudiantes.add(estudiante)
                # Si tenía solicitud pendiente la marcamos aceptada
                SolicitudClase.objects.filter(
                    clase=clase, estudiante=estudiante
                ).update(estado='aceptada')
                messages.success(request, f'"{username}" agregado a la clase.')
        except User.DoesNotExist:
            messages.error(request, f'No existe un estudiante con usuario "{username}".')
    return redirect('detalle_clase', clase_id=clase_id)

@login_required
def aceptar_solicitud(request, solicitud_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id, clase__docente=request.user)
    solicitud.clase.estudiantes.add(solicitud.estudiante)
    solicitud.estado = 'aceptada'
    solicitud.save()
    messages.success(request, f'"{solicitud.estudiante.username}" aceptado en "{solicitud.clase.nombre}".')
    return redirect('perfil_docente')

@login_required
def rechazar_solicitud(request, solicitud_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id, clase__docente=request.user)
    solicitud.estado = 'rechazada'
    solicitud.save()
    messages.info(request, f'Solicitud de "{solicitud.estudiante.username}" rechazada.')
    return redirect('perfil_docente')

@login_required
def detalle_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    solicitudes = SolicitudClase.objects.filter(clase=clase, estado='pendiente')
    return render(request, 'detalle_clase.html', {'clase': clase, 'solicitudes': solicitudes})

@login_required
def eliminar_estudiante_clase(request, clase_id, estudiante_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    estudiante = get_object_or_404(User, id=estudiante_id)
    clase.estudiantes.remove(estudiante)
    messages.success(request, 'Estudiante removido.')
    return redirect('detalle_clase', clase_id=clase_id)

@login_required
def eliminar_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    clase.delete()
    messages.success(request, 'Clase eliminada.')
    return redirect('perfil_docente')

@login_required
def detalle_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    solicitudes = SolicitudClase.objects.filter(clase=clase, estado='pendiente')
    anuncios = clase.anuncios.all().order_by('-fecha')
    lecciones = clase.lecciones.all()
    return render(request, 'detalle_clase.html', {
        'clase': clase,
        'solicitudes': solicitudes,
        'anuncios': anuncios,
        'lecciones': lecciones,
    })

@login_required
def crear_anuncio(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto:
            Anuncio.objects.create(clase=clase, texto=texto)
            messages.success(request, 'Anuncio publicado.')
    return redirect('detalle_clase', clase_id=clase_id)

@login_required
def crear_leccion(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        disponible = request.POST.get('disponible') == 'on'
        orden = clase.lecciones.count() + 1
        if titulo:
            Leccion.objects.create(
                clase=clase,
                titulo=titulo,
                descripcion=descripcion,
                disponible=disponible,
                orden=orden
            )
            messages.success(request, 'Lección agregada.')
    return redirect('detalle_clase', clase_id=clase_id)

@login_required
def eliminar_leccion(request, clase_id, leccion_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    leccion = get_object_or_404(Leccion, id=leccion_id, clase__docente=request.user)
    leccion.delete()
    messages.success(request, 'Lección eliminada.')
    return redirect('detalle_clase', clase_id=clase_id)

@login_required
def eliminar_anuncio(request, clase_id, anuncio_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    anuncio = get_object_or_404(Anuncio, id=anuncio_id, clase__docente=request.user)
    anuncio.delete()
    messages.success(request, 'Anuncio eliminado.')
    return redirect('detalle_clase', clase_id=clase_id)