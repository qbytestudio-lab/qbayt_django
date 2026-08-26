from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.contrib.auth.models import User
from .models import Clase, SolicitudClase, Anuncio, Leccion, Actividad, Pregunta, Opcion, RespuestaEstudiante
from django.core.exceptions import ValidationError
from clase.models import Clase
from ejercicios.models import Ejercicio, IntentoEjercicio
from django.contrib.auth import get_user_model
from notificaciones.services import notificar_aceptacion, notificar_rechazo

    


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
    
    User = get_user_model()
    
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    estudiantes = clase.estudiantes.all()
    ejercicios = Ejercicio.objects.filter(clase=clase)
    
    # Datos por estudiante
    data_estudiantes = []
    for estudiante in estudiantes:
        # Obtener intentos del estudiante en esta clase
        intentos = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio__clase=clase
        ).select_related('ejercicio')
        
        # Ejercicios completados (aprobados)
        completadas = intentos.filter(aprobado=True).values('ejercicio').distinct().count()
        
        # Total de ejercicios
        total = ejercicios.count()
        
        # Progreso
        progreso = round((completadas / total) * 100) if total > 0 else 0
        
        # Calcular puntaje promedio de las calificaciones
        calificaciones = intentos.exclude(calificacion__isnull=True).values_list('calificacion', flat=True)
        if calificaciones:
            promedio_calificaciones = sum(float(c) for c in calificaciones) / len(calificaciones)
            # Convertir a porcentaje (asumiendo calificación máxima de 5.0)
            puntaje = round((promedio_calificaciones / 5.0) * 100)
        else:
            puntaje = 0
        
        data_estudiantes.append({
            'estudiante': estudiante,
            'completadas': completadas,
            'total': total,
            'progreso': progreso,
            'puntaje': puntaje,
        })
    
    # Ordenar estudiantes por progreso (de mayor a menor)
    data_estudiantes.sort(key=lambda x: x['progreso'], reverse=True)
    
    # Datos por ejercicio
    data_ejercicios = []
    for ejercicio in ejercicios:
        # Estudiantes que completaron (aprobaron) el ejercicio
        completaron = IntentoEjercicio.objects.filter(
            ejercicio=ejercicio,
            aprobado=True
        ).values('estudiante').distinct().count()
        
        # Calcular porcentaje de completitud
        porcentaje = round((completaron / estudiantes.count()) * 100) if estudiantes.count() > 0 else 0
        
        # Calcular promedio de calificaciones del ejercicio
        calificaciones_ejercicio = IntentoEjercicio.objects.filter(
            ejercicio=ejercicio
        ).exclude(calificacion__isnull=True).values_list('calificacion', flat=True)
        
        if calificaciones_ejercicio:
            promedio = sum(float(c) for c in calificaciones_ejercicio) / len(calificaciones_ejercicio)
        else:
            promedio = 0
        
        data_ejercicios.append({
            'ejercicio': ejercicio,
            'completaron': completaron,
            'total_estudiantes': estudiantes.count(),
            'porcentaje': porcentaje,
            'promedio': promedio,
        })
    
    # Ordenar ejercicios por porcentaje de completitud
    data_ejercicios.sort(key=lambda x: x['porcentaje'], reverse=True)
    
    context = {
        'clase': clase,
        'data_estudiantes': data_estudiantes,
        'data_ejercicios': data_ejercicios,
        'total_estudiantes': estudiantes.count(),
        'total_ejercicios': ejercicios.count(),
    }
    
    return render(request, 'docente/estadisticas.html', context)

@login_required
def notas_estudiante(request, clase_id, estudiante_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    
    User = get_user_model()
    
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    estudiante = get_object_or_404(User, id=estudiante_id)
    
    # Verificar que el estudiante esté inscrito en la clase
    if not clase.estudiantes.filter(id=estudiante_id).exists():
        messages.error(request, 'El estudiante no está inscrito en esta clase.')
        return redirect('estadisticas_clase', clase_id=clase_id)
    
    # Obtener ejercicios de la clase
    ejercicios = Ejercicio.objects.filter(clase=clase).order_by('fecha_creacion')
    
    # Construir lista de notas
    notas = []
    total_calificaciones = 0
    cantidad_calificaciones = 0
    
    for ejercicio in ejercicios:
        # Obtener todos los intentos del estudiante en este ejercicio
        intentos_ejercicio = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio=ejercicio
        ).order_by('-fecha_envio')
        
        # El mejor intento (aprobado con mayor calificación)
        mejor_intento = intentos_ejercicio.filter(aprobado=True).order_by('-calificacion').first()
        
        # Si no hay aprobado, usar el último intento
        if not mejor_intento:
            mejor_intento = intentos_ejercicio.first()
        
        calificacion = mejor_intento.calificacion if mejor_intento else None
        aprobado = mejor_intento.aprobado if mejor_intento else False
        fecha_envio = mejor_intento.fecha_envio if mejor_intento else None
        total_intentos = intentos_ejercicio.count()
        
        if calificacion:
            total_calificaciones += float(calificacion)
            cantidad_calificaciones += 1
        
        notas.append({
            'ejercicio': ejercicio,
            'calificacion': calificacion,
            'aprobado': aprobado,
            'fecha_envio': fecha_envio,
            'total_intentos': total_intentos,
        })
    
    # Calcular promedio
    promedio = round((total_calificaciones / cantidad_calificaciones) * 20) if cantidad_calificaciones > 0 else 0
    # (multiplicamos por 20 porque la calificación es de 1-5 y queremos porcentaje)
    
    context = {
        'clase': clase,
        'estudiante': estudiante,
        'notas': notas,
        'total_ejercicios': ejercicios.count(),
        'completados': len([n for n in notas if n['aprobado']]),
        'promedio': promedio,
    }
    
    return render(request, 'docente/notas_estudiante.html', context)

# En la función aceptar_solicitud
def aceptar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    solicitud.estado = 'aceptada'
    solicitud.save()
    
    # Agregar estudiante a la clase
    solicitud.clase.estudiantes.add(solicitud.estudiante)
    
    # ✅ CREAR NOTIFICACIÓN
    notificar_aceptacion(solicitud.estudiante, solicitud.clase)
    
    messages.success(request, 'Solicitud aceptada.')
    return redirect('detalle_clase', clase_id=solicitud.clase.id)

# En la función rechazar_solicitud
def rechazar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    solicitud.estado = 'rechazada'
    solicitud.save()
    
    # ✅ CREAR NOTIFICACIÓN
    notificar_rechazo(solicitud.estudiante, solicitud.clase)
    
    messages.success(request, 'Solicitud rechazada.')
    return redirect('detalle_clase', clase_id=solicitud.clase.id)

    