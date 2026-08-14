from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.contrib.auth.models import User
from .models import Clase, SolicitudClase, Anuncio, Leccion, Actividad, Pregunta, Opcion, RespuestaEstudiante
from django.core.exceptions import ValidationError

# ═══════════════════════════════════════════
#         PERFIL DOCENTE
# ═══════════════════════════════════════════

@login_required
def perfil_docente(request):
    clases = Clase.objects.filter(docente=request.user)
    total_estudiantes = sum(c.estudiantes.count() for c in clases)
    solicitudes_pendientes = SolicitudClase.objects.filter(clase__docente=request.user, estado='pendiente')
    
    # Estados guardados en sesión
    estados_estudiantes = request.session.get('estados_estudiantes', {})
    estados_inactivos = [int(k) for k, v in estados_estudiantes.items() if v == 'inactivo']
    
    context = {
        'clases': clases,
        'total_estudiantes': total_estudiantes,
        'solicitudes_pendientes': solicitudes_pendientes,
        'estados_inactivos': estados_inactivos,
    }
    
    return render(request, 'docente/perfil_docente.html', context)


# ═══════════════════════════════════════════
#         GESTIÓN DE CLASES
# ═══════════════════════════════════════════

@login_required
def crear_clase(request):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        categoria_tema = request.POST.get('categoria_tema')
        descripcion = request.POST.get('descripcion', '').strip()
        imagen = request.FILES.get('imagen')
        max_estudiantes = request.POST.get('max_estudiantes')
        fecha_inicio = request.POST.get('fecha_inicio') or None
        fecha_fin = request.POST.get('fecha_fin') or None
        nivel_previo_id = request.POST.get('nivel_previo')

        nivel_previo = None
        if nivel_previo_id:
            nivel_previo = Clase.objects.filter(id=nivel_previo_id).first()

        if nombre:
            try:
                clase = Clase(
                    nombre=nombre,
                    categoria_tema=categoria_tema,
                    descripcion=descripcion,
                    docente=request.user,
                    imagen=imagen,
                    max_estudiantes=max_estudiantes,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    nivel_previo=nivel_previo,
                )
                clase.full_clean()
                clase.save()
                messages.success(request, 'Clase creada exitosamente.')
            except ValidationError as e:
                messages.error(request, e.messages[0])

    return redirect('mis_clases')


@login_required
def editar_clase(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        imagen = request.FILES.get('imagen')
        
        if nombre:
            clase.nombre = nombre
            clase.descripcion = descripcion
            if imagen:
                clase.imagen = imagen
            clase.save()
            messages.success(request, "¡Clase actualizada correctamente!")
            return redirect('detalle_clase', clase_id=clase.id)
        else:
            messages.error(request, "El nombre de la clase no puede estar vacío.")
    
    return redirect('detalle_clase', clase_id=clase.id)


@login_required
def eliminar_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        clase.delete()
        messages.success(request, "La clase fue eliminada para siempre.")
        return redirect('perfil_docente')
    
    return redirect('detalle_clase', clase_id=clase.id)


@login_required
def detalle_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    solicitudes = clase.solicitudes.filter(estado='pendiente')
    anuncios = clase.anuncios.all().order_by('-fecha')
    lecciones = clase.lecciones.all()
    ejercicios = clase.ejercicios.all()
    
    return render(request, 'docente/detalle_clase.html', {
        'clase': clase,
        'solicitudes': solicitudes,
        'solicitudes_pendientes': solicitudes,
        'anuncios': anuncios,
        'lecciones': lecciones,
        'ejercicios': ejercicios,
    })


# ═══════════════════════════════════════════
#         GESTIÓN DE ESTUDIANTES
# ═══════════════════════════════════════════

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
                SolicitudClase.objects.filter(
                    clase=clase, estudiante=estudiante
                ).update(estado='aceptada')
                messages.success(request, f'"{username}" agregado a la clase.')
        except User.DoesNotExist:
            messages.error(request, f'No existe un estudiante con usuario "{username}".')
    
    return redirect('detalle_clase', clase_id=clase_id)


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
def expulsar_estudiante_clase(request, clase_id, estudiante_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    estudiante = get_object_or_404(User, id=estudiante_id)
    
    if estudiante in clase.estudiantes.all():
        clase.estudiantes.remove(estudiante)
        
        try:
            solicitud = SolicitudClase.objects.get(estudiante=estudiante, clase=clase)
            solicitud.estado = 'rechazada'
            
            if solicitud.intentos >= 2:
                solicitud.bloqueado = True
                messages.warning(request, f"El estudiante ha agotado sus 2 oportunidades y ha sido bloqueado definitivamente.")
            else:
                messages.success(request, f"El estudiante fue retirado. Le queda 1 oportunidad restante.")
            
            solicitud.save()
        except SolicitudClase.DoesNotExist:
            pass
    
    return redirect('detalle_clase', clase_id=clase.id)


# ═══════════════════════════════════════════
#         GESTIÓN DE SOLICITUDES
# ═══════════════════════════════════════════

@login_required
def aceptar_solicitud(request, solicitud_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id, clase__docente=request.user)
    solicitud.clase.estudiantes.add(solicitud.estudiante)
    solicitud.estado = 'aceptada'
    solicitud.save()
    messages.success(request, f'"{solicitud.estudiante.username}" aceptado en "{solicitud.clase.nombre}".')
    return redirect('detalle_clase', clase_id=solicitud.clase.id)


@login_required
def rechazar_solicitud(request, solicitud_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id, clase__docente=request.user)
    solicitud.estado = 'rechazada'
    solicitud.save()
    messages.info(request, f'Solicitud de "{solicitud.estudiante.username}" rechazada.')
    return redirect('detalle_clase', clase_id=solicitud.clase.id)


# ═══════════════════════════════════════════
#         ANUNCIOS
# ═══════════════════════════════════════════

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
def eliminar_anuncio(request, clase_id, anuncio_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    anuncio = get_object_or_404(Anuncio, id=anuncio_id, clase__docente=request.user)
    anuncio.delete()
    messages.success(request, 'Anuncio eliminado.')
    return redirect('detalle_clase', clase_id=clase_id)
# ═══════════════════════════════════════════
#         REPORTES Y ESTADÍSTICAS
# ═══════════════════════════════════════════

@login_required
def generar_reporte_pdf(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Reporte_{clase.nombre}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle(f"Reporte {clase.nombre}")
    
    p.setFont("Helvetica-Bold", 20)
    p.drawString(100, 750, f"Reporte de Clase: {clase.nombre}")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"Docente: {clase.docente.get_full_name()}")
    p.drawString(100, 715, f"Fecha de creación: {clase.fecha_creacion.strftime('%d/%m/%Y')}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 680, "Lista de Estudiantes:")
    
    y = 660
    estudiantes = clase.estudiantes.all()
    if estudiantes:
        for est in estudiantes:
            p.setFont("Helvetica", 12)
            p.drawString(120, y, f"- {est.get_full_name()} (@{est.username})")
            y -= 20
    else:
        p.drawString(120, y, "No hay estudiantes inscritos.")
    
    p.showPage()
    p.save()
    return response


@login_required
def estadisticas_clase(request, clase_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    estudiantes = clase.estudiantes.all()
    actividades = Actividad.objects.filter(leccion__clase=clase)
    
    data_estudiantes = []
    for estudiante in estudiantes:
        respuestas = RespuestaEstudiante.objects.filter(
            estudiante=estudiante,
            actividad__leccion__clase=clase
        ).select_related('actividad', 'opcion')
        
        completadas = respuestas.values('actividad').distinct().count()
        total = actividades.count()
        progreso = round((completadas / total) * 100) if total > 0 else 0
        
        correctas = sum(1 for r in respuestas if r.opcion.es_correcta)
        total_resp = respuestas.count()
        puntaje = round((correctas / total_resp) * 100) if total_resp > 0 else 0
        
        data_estudiantes.append({
            'estudiante': estudiante,
            'completadas': completadas,
            'total': total,
            'progreso': progreso,
            'puntaje': puntaje,
        })
    
    data_actividades = []
    for act in actividades:
        completaron = RespuestaEstudiante.objects.filter(
            actividad=act
        ).values('estudiante').distinct().count()
        porcentaje = round((completaron / estudiantes.count()) * 100) if estudiantes.count() > 0 else 0
        data_actividades.append({
            'actividad': act,
            'completaron': completaron,
            'total_estudiantes': estudiantes.count(),
            'porcentaje': porcentaje,
        })
    
    return render(request, 'docente/estadisticas.html', {
        'clase': clase,
        'data_estudiantes': data_estudiantes,
        'data_actividades': data_actividades,
        'total_estudiantes': estudiantes.count(),
        'total_actividades': actividades.count(),
    })