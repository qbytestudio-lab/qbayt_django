from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.contrib.auth.models import User
from .models import Clase, SolicitudClase, Anuncio, Leccion, Actividad, Pregunta, Opcion, RespuestaEstudiante
from django.core.exceptions import ValidationError

@login_required
def crear_clase(request):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        imagen = request.FILES.get('imagen')

        if nombre:
            try:
                clase = Clase(
                    nombre=nombre,
                    descripcion=descripcion,
                    docente=request.user,
                    imagen=imagen
                )

                clase.full_clean()   # Ejecuta clean()
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
        imagen = request.FILES.get('imagen')  # Por si cambian el banner
        
        if nombre:
            clase.nombre = nombre
            clase.descripcion = descripcion
            if imagen:
                clase.imagen = imagen
            clase.save()
            messages.success(request, "¡Clase actualizada correctamente!")
            # Redirige inmediatamente tras un POST exitoso
            return redirect('detalle_clase', clase_id=clase.id)  
        else:
            messages.error(request, "El nombre de la clase no puede estar vacío.")
            
    # Si entra por GET (o si falla el nombre), vuelve al detalle
    return redirect('detalle_clase', clase_id=clase.id)  


@login_required
def eliminar_clase(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        clase.delete()
        messages.success(request, "La clase fue eliminada para siempre.")
        # Nota: Asegúrate de tener una URL llamada 'mis_clases_docente' en el urls.py principal o de esta app
        return redirect('mis_clases_docente')  
        
    return redirect('detalle_clase', clase_id=clase.id)
    
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
    return render(request, 'docente/perfil_docente.html', {
        'clases': clases,
        'total_estudiantes': total_estudiantes,
        'solicitudes_pendientes': solicitudes_pendientes,
    })

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
    
    # Obtenemos todos los datos que la plantilla necesita
    solicitudes = SolicitudClase.objects.filter(clase=clase, estado='pendiente')
    anuncios = clase.anuncios.all().order_by('-fecha')
    lecciones = clase.lecciones.all()
    
    # Obtenemos los ejercicios creados con la nueva app
    ejercicios = clase.ejercicios.all()
    
    # ¡Cambiamos la ruta aquí agregando 'docente/' al principio!
    return render(request, 'docente/detalle_clase.html', {
        'clase': clase,
        'solicitudes': solicitudes,
        'anuncios': anuncios,
        'lecciones': lecciones,
        'ejercicios': ejercicios,
    })
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

@login_required
def crear_actividad(request, clase_id, leccion_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    leccion = get_object_or_404(Leccion, id=leccion_id, clase__docente=request.user)
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        tipo = request.POST.get('tipo', 'texto')
        contenido = request.POST.get('contenido', '').strip()
        imagen = request.FILES.get('imagen')
        orden = leccion.actividades.count() + 1
        if titulo:
            fecha_limite = request.POST.get('fecha_limite') or None
            Actividad.objects.create(
            leccion=leccion, titulo=titulo, tipo=tipo,
            contenido=contenido, imagen=imagen, orden=orden,
            fecha_limite=fecha_limite
)
            messages.success(request, 'Actividad creada.')
    return redirect('detalle_leccion', clase_id=clase_id, leccion_id=leccion_id)

@login_required
def detalle_leccion(request, clase_id, leccion_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    leccion = get_object_or_404(Leccion, id=leccion_id, clase__docente=request.user)
    actividades = leccion.actividades.all()
    return render(request, 'docente/detalle_leccion.html', {
        'leccion': leccion,
        'actividades': actividades,
        'clase': leccion.clase,
    })

@login_required
def detalle_actividad(request, clase_id, leccion_id, actividad_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    actividad = get_object_or_404(Actividad, id=actividad_id, leccion__clase__docente=request.user)
    return render(request, 'docente/detalle_actividad_docente.html', {
        'actividad': actividad,
        'leccion': actividad.leccion,
        'clase': actividad.leccion.clase,
    })

@login_required
def crear_pregunta(request, actividad_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
    actividad = get_object_or_404(Actividad, id=actividad_id, leccion__clase__docente=request.user)
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        imagen = request.FILES.get('imagen')
        opciones = request.POST.getlist('opciones')
        correcta = request.POST.get('correcta')
        if texto and opciones:
            pregunta = Pregunta.objects.create(
                actividad=actividad, texto=texto, imagen=imagen,
                orden=actividad.preguntas.count() + 1
            )
            for i, op_texto in enumerate(opciones):
                if op_texto.strip():
                    Opcion.objects.create(
                        pregunta=pregunta,
                        texto=op_texto.strip(),
                        es_correcta=(str(i) == correcta)
                    )
            messages.success(request, 'Pregunta agregada.')
    return redirect('detalle_actividad', 
                    clase_id=actividad.leccion.clase.id,
                    leccion_id=actividad.leccion.id,
                    actividad_id=actividad.id)
@login_required
def generar_reporte_pdf(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    # Creamos la respuesta HTTP con el tipo de contenido PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Reporte_{clase.nombre}.pdf"'
    
    # Creamos el objeto canvas de ReportLab
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle(f"Reporte {clase.nombre}")
    
    # contenido
    p.setFont("Helvetica-Bold", 20)
    p.drawString(100, 750, f"Reporte de Clase: {clase.nombre}")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"Docente: {clase.docente.get_full_name()}")
    p.drawString(100, 715, f"Fecha de creación: {clase.fecha_creacion.strftime('%d/%m/%Y')}")
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 680, "Lista de Estudiantes:")
    
    # Listamos a los estudiantes
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
    
    # Por cada estudiante, calcular su progreso y puntaje
    data_estudiantes = []
    for estudiante in estudiantes:
        respuestas = RespuestaEstudiante.objects.filter(
            estudiante=estudiante,
            actividad__leccion__clase=clase
        ).select_related('actividad', 'opcion')
        
        completadas = respuestas.values('actividad').distinct().count()
        total = actividades.count()
        progreso = round((completadas / total) * 100) if total > 0 else 0
        
        # Puntaje promedio en quizzes
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
    
    # Por cada actividad, cuántos la completaron
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