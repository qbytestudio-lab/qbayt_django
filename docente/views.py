from datetime import datetime
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from clase.models import Clase, SolicitudClase, Anuncio
from ejercicios.models import Ejercicio, IntentoEjercicio
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
                # 1. VERIFICAR SI YA ESTÁ EN OTRA CLASE DE LA MISMA CATEGORÍA USANDO 'categoria_tema'
                clases_misma_categoria = Clase.objects.filter(
                    categoria_tema=clase.categoria_tema,
                    estudiantes=estudiante
                ).exclude(id=clase.id)
                
                if clases_misma_categoria.exists():
                    otra_clase = clases_misma_categoria.first()
                    messages.error(request, f'El estudiante "{username}" ya se encuentra inscrito en otra clase de la misma categoría/tema ("{otra_clase.nombre}").')
                else:
                    # 2. Si pasa la validación, lo agregamos normalmente
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
        
        # Mapear los intentos en un diccionario por ID de ejercicio para acceso directo en la matriz
        intentos_dict = {intento.ejercicio_id: intento for intento in intentos}
        
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
            'intentos_dict': intentos_dict,  # <-- Agregado para mostrar las calificaciones en la matriz
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
    
    # CREAR NOTIFICACIÓN
    notificar_aceptacion(solicitud.estudiante, solicitud.clase)
    
    messages.success(request, 'Solicitud aceptada.')
    return redirect('detalle_clase', clase_id=solicitud.clase.id)

# En la función rechazar_solicitud
def rechazar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudClase, id=solicitud_id)
    solicitud.estado = 'rechazada'
    solicitud.save()
    
    # CREAR NOTIFICACIÓN
    notificar_rechazo(solicitud.estudiante, solicitud.clase)
    
    messages.success(request, 'Solicitud rechazada.')
    return redirect('detalle_clase', clase_id=solicitud.clase.id)

@login_required
def editar_ejercicio(request, clase_id, ejercicio_id):
    from datetime import datetime
    from ejercicios.models import Ejercicio
    
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite = request.POST.get('fecha_limite')
        video_url = request.POST.get('video_url', '').strip()
        video_principal = request.FILES.get('video_principal')
        imagen_principal = request.FILES.get('imagen_principal')
        
        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect('detalle_clase', clase_id=clase.id)
        
        ejercicio.titulo = titulo
        ejercicio.descripcion = descripcion
        
        if fecha_limite:
            try:
                ejercicio.fecha_limite = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect('detalle_clase', clase_id=clase.id)
        else:
            ejercicio.fecha_limite = None
        
        if video_url:
            ejercicio.video_url = video_url
        
        if video_principal:
            ejercicio.video_principal = video_principal
        
        if imagen_principal:
            ejercicio.imagen_principal = imagen_principal
        
        ejercicio.save()
        
        messages.success(request, f'Ejercicio "{titulo}" actualizado correctamente.')
        return redirect('detalle_clase', clase_id=clase.id)
    
    context = {
        'clase': clase,
        'ejercicio': ejercicio,
    }
    
    return render(request, 'docente/editar_ejercicio.html', context)

@login_required
def eliminar_ejercicio(request, clase_id, ejercicio_id):
    from ejercicios.models import Ejercicio
    
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    if request.method == 'POST':
        ejercicio.delete()
        messages.success(request, 'Ejercicio eliminado correctamente.')
    
    return redirect('detalle_clase', clase_id=clase.id)

@login_required
def mis_clases(request):
    if request.user.perfil.rol == 'docente':
        clases = Clase.objects.filter(docente=request.user)
        solicitudes_pendientes = SolicitudClase.objects.filter(
            clase__docente=request.user, estado='pendiente'
        )
        total_estudiantes = sum(c.estudiantes.count() for c in clases)
        return render(request, 'docente/mis_clases_docente.html', {
            'clases': clases,
            'solicitudes_pendientes': solicitudes_pendientes,
            'total_estudiantes': total_estudiantes,
        })
    else:
        clases = request.user.clases_estudiante.all()
        return render(request, 'docente/mis_clases.html', {'clases': clases}) 