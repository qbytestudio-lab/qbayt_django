from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.utils import timezone

from ejercicios.models import Ejercicio, Pregunta, Opcion, IntentoEjercicio, RespuestaEstudiante
from clase.models import Clase, InscripcionNivel
from docente.models import SolicitudClase
from web.models import Perfil, InscripcionCurso
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

def calcular_progreso_clase(estudiante, clase):
    """Devuelve el % de ejercicios completados en una clase."""
    total_ejercicios = Ejercicio.objects.filter(clase=clase).count()
    if total_ejercicios == 0:
        return 0
    
    completados = IntentoEjercicio.objects.filter(
        estudiante=estudiante,
        ejercicio__clase=clase
    ).values('ejercicio').distinct().count()
    
    return round((completados / total_ejercicios) * 100)


@login_required
def perfil_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    clases = request.user.clases_estudiante.all()
    solicitudes = SolicitudClase.objects.filter(estudiante=request.user)

    # Progreso por cada clase
    progreso_clases = []
    for clase in clases:
        progreso_clases.append({
            'clase': clase,
            'porcentaje': calcular_progreso_clase(request.user, clase)
        })

    # Progreso general
    if progreso_clases:
        progreso_general = round(sum(p['porcentaje'] for p in progreso_clases) / len(progreso_clases))
    else:
        progreso_general = 0

    # Ejercicios hechos
    ejercicios_hechos = IntentoEjercicio.objects.filter(
        estudiante=request.user
    ).values('ejercicio').distinct().count()

    # Pendientes
    ahora = timezone.now()
    
    ejercicios_completados = IntentoEjercicio.objects.filter(
        estudiante=request.user
    ).values_list('ejercicio_id', flat=True).distinct()
    
    pendientes = Ejercicio.objects.filter(
        clase__in=clases,
        fecha_limite__isnull=False,
        fecha_limite__gte=ahora
    ).exclude(id__in=ejercicios_completados).select_related('clase')
    
    pendientes_count = pendientes.count()

    # Historial
    historial = []
    
    for clase in clases:
        if clase.fecha_fin and clase.fecha_fin < ahora.date():
            estado = 'completada'
        else:
            estado = 'activa'
        
        historial.append({
            'nombre': clase.nombre,
            'tipo': 'clase',
            'estado': estado,
            'docente_nombre': clase.docente.get_full_name() or clase.docente.username,
            'fecha': clase.fecha_creacion,
        })
    
    # Clases rechazadas/eliminadas
    solicitudes_rechazadas = SolicitudClase.objects.filter(
        estudiante=request.user,
        estado='rechazada'
    ).select_related('clase', 'clase__docente')
    
    for solicitud in solicitudes_rechazadas:
        historial.append({
            'nombre': solicitud.clase.nombre,
            'tipo': 'clase',
            'estado': 'eliminada',
            'docente_nombre': solicitud.clase.docente.get_full_name() or solicitud.clase.docente.username,
            'fecha': solicitud.fecha,
        })
    
    # Cursos inscritos
    cursos = InscripcionCurso.objects.filter(estudiante=request.user).select_related('curso')
    for inscripcion in cursos:
        historial.append({
            'nombre': inscripcion.curso.nombre,
            'tipo': 'curso',
            'estado': 'activa',
            'docente_nombre': 'N/A',
            'fecha': getattr(inscripcion, 'fecha_inscripcion', timezone.now()),
        })

    return render(request, 'estudiante/perfil_estudiante.html', {
        'clases': clases,
        'solicitudes': solicitudes,
        'progreso_clases': progreso_clases,
        'progreso_general': progreso_general,
        'ejercicios_hechos': ejercicios_hechos,
        'pendientes': pendientes,
        'pendientes_count': pendientes_count,
        'historial': historial,
        'clases_activas': clases.count(),
        'clases_completadas': sum(1 for h in historial if h['estado'] == 'completada'),
    })


def configurar_nivel(request):
    if 'registro_temporal' not in request.session:
        return redirect('registro')

    datos = request.session['registro_temporal']

    if request.method == 'POST':
        nivel_seleccionado = request.POST.get('nivel')

        user = User.objects.create_user(
            username=datos['username'],
            email=datos['email'],
            password=datos['password'],
            first_name=datos['first_name'],
            last_name=datos['last_name'],
        )
        user.save()

        Perfil.objects.create(user=user, rol=datos['rol'])
        InscripcionNivel.objects.create(estudiante=user, nivel=nivel_seleccionado)

        del request.session['registro_temporal']

        login(request, user)
        messages.success(request, '¡Cuenta creada con éxito!')
        return redirect('inicio')

    return render(request, 'estudiante/configurar_nivel.html')


@login_required
def unirse_clase(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()

        try:
            clase_nueva = Clase.objects.get(codigo=codigo)

            solicitud, created = SolicitudClase.objects.get_or_create(
                estudiante=request.user,
                clase=clase_nueva,
                defaults={'estado': 'pendiente', 'intentos': 1}
            )

            if solicitud.bloqueado:
                messages.error(request, 'Has agotado tus 2 oportunidades en esta clase y estás bloqueado permanentemente.')
                return redirect('estudiante:explorar_clases')

            if request.user in clase_nueva.estudiantes.all():
                messages.warning(request, 'Ya estás en esta clase.')
                return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_nueva.id)

            if not created and solicitud.estado == 'rechazada':
                if solicitud.intentos < 2:
                    solicitud.intentos += 1
                    solicitud.estado = 'pendiente'
                    solicitud.save()
                    messages.success(request, f'Nueva solicitud enviada. Intento de curso: {solicitud.intentos}/2')
                else:
                    solicitud.bloqueado = True
                    solicitud.save()
                    messages.error(request, 'Has agotado tus 2 oportunidades de cursar esta clase.')
                    return redirect('estudiante:explorar_clases')
            else:
                messages.success(request, f'¡Solicitud enviada para la clase "{clase_nueva.nombre}"!')

            return redirect('estudiante:explorar_clases')

        except Clase.DoesNotExist:
            messages.error(request, 'Código inválido.')
            return redirect('estudiante:explorar_clases')

    return redirect('estudiante:explorar_clases')


@login_required
def solicitar_clase(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
        
    if request.method == 'POST':
        clase_id = request.POST.get('clase_id')
        clase_solicitada = get_object_or_404(Clase, id=clase_id)

        clases_misma_categoria = request.user.clases_estudiante.filter(categoria_tema=clase_solicitada.categoria_tema)

        if request.user in clase_solicitada.estudiantes.all():
            messages.warning(request, 'Ya estás en esta clase.')
        elif clases_misma_categoria.exists():
            messages.error(request, f'Ya tienes una clase en la categoría "{clase_solicitada.get_categoria_tema_display()}".')
        elif SolicitudClase.objects.filter(clase=clase_solicitada, estudiante=request.user, estado='pendiente').exists():
            messages.warning(request, 'Ya tienes una solicitud pendiente para esta clase.')
        else:
            SolicitudClase.objects.create(clase=clase_solicitada, estudiante=request.user)
            messages.success(request, f'Solicitud enviada a "{clase_solicitada.nombre}". Espera que el docente la acepte.')
    
    # Redirigir de vuelta a la página anterior o al inicio
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('inicio')

@login_required
def salir_clase(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clase = get_object_or_404(Clase, id=clase_id)
    clase.estudiantes.remove(request.user)
    messages.success(request, f'Saliste de "{clase.nombre}".')
    return redirect('estudiante:perfil_estudiante')


@login_required
def explorar_clases(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    clases = Clase.objects.exclude(estudiantes=request.user)
    solicitudes_enviadas = SolicitudClase.objects.filter(
        estudiante=request.user
    ).values_list('clase_id', flat=True)
    return render(request, 'estudiante/explorar_clases.html', {
        'clases': clases,
        'solicitudes_enviadas': solicitudes_enviadas,
    })


@login_required
def detalle_clase_estudiante(request, clase_id):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
        
    clase = get_object_or_404(Clase, id=clase_id)
    
    # 1. Validación de categoría: Verificar si ya está inscrito en OTRA clase de la misma categoría
    if hasattr(clase, 'categoria') and clase.categoria:
        otra_clase_misma_categoria = Clase.objects.filter(
            categoria=clase.categoria,
            estudiantes=request.user
        ).exclude(id=clase.id).exists()
        
        if otra_clase_misma_categoria and request.user not in clase.estudiantes.all():
            messages.error(request, "Ya estás participando en otra clase de esta misma categoría y no puedes ingresar a esta.")
            return redirect('estudiante:dashboard')

    # 2. Validación estándar de inscripción a la clase actual
    if request.user not in clase.estudiantes.all():
        messages.error(request, "No tienes acceso a esta clase.")
        return redirect('estudiante:dashboard')
    
    ejercicios = clase.ejercicios.all()

    for ejercicio in ejercicios:
        ejercicio.mi_intento = ejercicio.intentos.filter(estudiante=request.user).first()
        ejercicio.total_intentos = ejercicio.intentos.filter(estudiante=request.user).count()

    solicitud = SolicitudClase.objects.filter(estudiante=request.user, clase=clase).first()

    return render(request, 'estudiante/detalle_clase_estudiante.html', {
        'clase': clase,
        'ejercicios': ejercicios,
        'solicitud': solicitud,
    })


@login_required
def mis_calificaciones_estudiante(request):
    if request.user.perfil.rol != 'estudiante':
        return redirect('inicio')
    
    clases = Clase.objects.filter(estudiantes=request.user)
    
    reporte_clases = []
    for clase in clases:
        ejercicios = clase.ejercicios.all().order_by('id')
        
        ejercicios_con_intentos = []
        for ejercicio in ejercicios:
            intento = ejercicio.intentos.filter(estudiante=request.user).first()
            ejercicios_con_intentos.append({
                'ejercicio': ejercicio,
                'intento': intento
            })
            
        reporte_clases.append({
            'clase': clase,
            'ejercicios': ejercicios_con_intentos
        })

    return render(request, 'estudiante/mis_calificaciones.html', {
        'reporte_clases': reporte_clases,
    })


@login_required
def resolver_ejercicio(request, clase_id, ejercicio_id):
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)
    
    if request.method == 'POST':
        preguntas = ejercicio.preguntas.all()
        
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio,
            calificacion=None,
            aprobado=False
        )
        
        for pregunta in preguntas:
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                opcion_seleccionada = Opcion.objects.filter(id=opcion_id, pregunta=pregunta).first()
                if opcion_seleccionada:
                    RespuestaEstudiante.objects.create(
                        intento=intento,
                        pregunta=pregunta,
                        opcion_seleccionada=opcion_seleccionada
                    )
            
        messages.success(request, 'Ejercicio enviado. Espera la calificación del docente.')
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase_id)

    return render(request, 'estudiante/resolver_ejercicio.html', {
        'ejercicio': ejercicio,
        'clase_id': clase_id
    })

@login_required
@require_POST
def subir_foto_perfil(request):
    try:
        foto = request.FILES.get('foto_perfil')

        if not foto:
            return JsonResponse({
                'success': False,
                'error': 'No se recibió imagen'
            })

        perfil, created = Perfil.objects.get_or_create(
            user=request.user
        )

        perfil.foto_perfil.save(
            foto.name,
            foto,
            save=True
        )

        return JsonResponse({
            'success': True,
            'url': perfil.foto_perfil.url
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def subir_banner(request):
    """
    Vista para subir el banner de perfil del estudiante
    """
    if request.method == 'POST' and request.FILES.get('banner'):
        try:
            banner = request.FILES['banner']
            
            # Validar que sea imagen
            if not banner.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'El archivo debe ser una imagen.'})
            
            # Validar tamaño (máx 10MB)
            if banner.size > 10 * 1024 * 1024:
                return JsonResponse({'success': False, 'error': 'La imagen no debe superar los 10MB.'})
            
            # Guardar banner
            request.user.perfil.banner = banner
            request.user.perfil.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'No se recibió imagen.'})