from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from datetime import datetime
from django.utils import timezone
from .models import (Ejercicio, Pregunta, Opcion, IntentoEjercicio, RespuestaEstudiante,)
from clase.models import Clase
from docente.models import RecursoMusical
from notificaciones.services import notificar_nuevo_ejercicio, notificar_calificacion


# ============================================================
# VISTA GENERAL / ENRUTADOR PARA CREAR EJERCICIO
# ============================================================
@login_required
def crear_ejercicio(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    tipo = request.GET.get('tipo', 'quiz')
    
    if tipo == 'quiz':
        return redirect('ejercicios:crear_quiz', clase_id=clase.id)
    elif tipo == 'juego':
        return redirect('ejercicios:crear_juego', clase_id=clase.id)
    elif tipo == 'texto':
        return redirect('ejercicios:crear_texto', clase_id=clase.id)
    elif tipo == 'verdadero_falso':
        return redirect('ejercicios:crear_verdadero_falso', clase_id=clase.id)
    elif tipo == 'completar':
        return redirect('ejercicios:crear_completar', clase_id=clase.id)
        
    return render(request, 'ejercicios/crear_quiz.html', {'clase': clase})

@login_required
def toggle_estado_ejercicio(request, ejercicio_id):
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id)
    
    # Validar que el usuario sea el docente dueño de la clase o superusuario
    if request.user != ejercicio.clase.docente and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para modificar este ejercicio.")
        return redirect('inicio')
    
    # Alternar el estado booleano
    ejercicio.activo = not ejercicio.activo
    ejercicio.save()
    
    estado_texto = "activado" if ejercicio.activo else "desactivado"
    messages.success(request, f"El ejercicio ha sido {estado_texto} correctamente.")
    
    return redirect('clase:detalle_clase', clase_id=ejercicio.clase.id) # Ajusta la ruta según tu proyecto
# ============================================================
# CREAR EJERCICIO (QUIZ O VIDEO-QUIZ UNIFICADO)
# ============================================================
@login_required
def crear_quiz(request, clase_id):
    """
    Vista unificada para crear un Quiz o un Video + Quiz con preguntas 
    de selección múltiple o verdadero/falso y opciones dinámicas.
    """
    clase = get_object_or_404(Clase, id=clase_id, docente=request.user)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite = request.POST.get('fecha_limite')
        video_principal = request.FILES.get('video_principal')
        video_url = request.POST.get('video_url', '').strip()
        
        # Validaciones básicas
        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        if not fecha_limite:
            messages.error(request, 'La fecha límite es obligatoria.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        try:
            fecha_limite_dt = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        ahora = timezone.now()
        if fecha_limite_dt < ahora.replace(tzinfo=None):
            messages.error(request, 'No puedes usar una fecha límite pasada.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        if video_principal and video_principal.size > 100 * 1024 * 1024:
            messages.error(request, 'El video no debe superar los 100MB.')
            return redirect('ejercicios:crear_quiz', clase_id=clase.id)
        
        # Determinar el tipo de ejercicio automáticamente
        tipo_ejercicio = 'video_quiz' if (video_principal or video_url) else 'quiz'
        
        # Crear el ejercicio principal
        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo=tipo_ejercicio,
            fecha_limite=fecha_limite_dt,
            video_principal=video_principal if video_principal else None,
            video_url=video_url if video_url else None,
        )
        
        # Guardar recursos de apoyo seleccionados
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)
        
        # Procesar preguntas dinámicas
        pregunta_ids = []
        for key in request.POST.keys():
            if key.startswith('pregunta_'):
                parts = key.split('_')
                if len(parts) == 2 and parts[1].isdigit():
                    num = int(parts[1])
                    if num not in pregunta_ids:
                        pregunta_ids.append(num)
        
        pregunta_ids.sort()
        
        for i in pregunta_ids:
            texto_pregunta = request.POST.get(f'pregunta_{i}', '').strip()
            imagen_pregunta = request.FILES.get(f'imagen_pregunta_{i}')
            
            if not texto_pregunta:
                continue
            
            pregunta = Pregunta.objects.create(
                ejercicio=ejercicio,
                enunciado=texto_pregunta,
                imagen=imagen_pregunta if imagen_pregunta else None
            )
            
            opcion_correcta_index = request.POST.get(f'correcta_{i}')
            
            # Capturar dinámicamente cuántas opciones llegaron para esta pregunta
            j = 1
            while f'opcion_{i}_{j}' in request.POST:
                texto_opcion = request.POST.get(f'opcion_{i}_{j}', '').strip()
                
                if texto_opcion:
                    es_correcta = (str(j) == str(opcion_correcta_index))
                    Opcion.objects.create(
                        pregunta=pregunta,
                        texto_opcion=texto_opcion,
                        es_correcta=es_correcta
                    )
                j += 1
        
        # Notificar a los estudiantes de la clase
        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)
        
        messages.success(request, f'Ejercicio "{titulo}" creado correctamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)
    
    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_quiz.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })


# ============================================================
# CREAR JUEGO
# ============================================================
@login_required
def crear_juego(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        juego_tipo = request.POST.get('juego_tipo', '').strip()

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(request.path)

        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            juego_tipo=juego_tipo,
            tipo='juego'
        )
        
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Juego creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_juego.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })


# ============================================================
# CREAR TEXTO
# ============================================================
@login_required
def crear_texto(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        contenido = request.POST.get('contenido', '').strip()
        imagen = request.FILES.get('imagen')

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(request.path)

        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            contenido=contenido,
            imagen_principal=imagen,
            tipo='texto'
        )
        
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Texto creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_texto.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })





# ============================================================
# CREAR COMPLETAR
# ============================================================
@login_required
def crear_completar(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not titulo:
            messages.error(request, 'El título es obligatorio.')
            return redirect(request.path)

        ejercicio = Ejercicio.objects.create(
            clase=clase,
            titulo=titulo,
            descripcion=descripcion,
            tipo='completar'
        )
        
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)

        notificar_nuevo_ejercicio(clase.estudiantes.all(), clase, ejercicio)

        messages.success(request, 'Ejercicio de completar creado exitosamente.')
        return redirect('clase:detalle_clase', clase_id=clase.id)

    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    return render(request, 'ejercicios/crear_completar.html', {
        'clase': clase,
        'recursos_disponibles': recursos_disponibles,
    })


# ============================================================
# EDITAR EJERCICIO
# ============================================================
@login_required
def editar_ejercicio(request, clase_id, ejercicio_id):
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
            return redirect(f'/clase/detalle/{clase.id}/')
        
        ejercicio.titulo = titulo
        ejercicio.descripcion = descripcion
        
        if fecha_limite:
            try:
                ejercicio.fecha_limite = datetime.strptime(fecha_limite, '%Y-%m-%dT%H:%M')
            except ValueError:
                messages.error(request, 'Formato de fecha inválido.')
                return redirect(f'/clase/detalle/{clase.id}/')
        else:
            ejercicio.fecha_limite = None
        
        if video_url:
            ejercicio.video_url = video_url
        
        if video_principal:
            ejercicio.video_principal = video_principal
        
        if imagen_principal:
            ejercicio.imagen_principal = imagen_principal
        
        # ✅ GUARDAR RECURSOS
        recursos_ids = request.POST.getlist('recursos')
        if recursos_ids:
            recursos = RecursoMusical.objects.filter(id__in=recursos_ids, docente=request.user)
            ejercicio.recursos.set(recursos)
        else:
            ejercicio.recursos.clear()
        
        ejercicio.save()
        
        messages.success(request, f'Ejercicio "{titulo}" actualizado correctamente.')
        return redirect(f'/clase/detalle/{clase.id}/')
    
    recursos_disponibles = RecursoMusical.objects.filter(docente=request.user)
    recursos_seleccionados = ejercicio.recursos.all().values_list('id', flat=True)
    
    context = {
        'clase': clase,
        'ejercicio': ejercicio,
        'recursos_disponibles': recursos_disponibles,
        'recursos_seleccionados': recursos_seleccionados,
    }
    
    return render(request, 'docente/editar_ejercicio.html', context)


# ============================================================
# CALIFICAR EJERCICIO
# ============================================================
@login_required
def calificar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)

    respuestas = intento.respuestas.select_related(
        'pregunta',
        'opcion_seleccionada'
    ).all()

    if request.method == 'POST':
        nota_str = request.POST.get('calificacion', '').strip()
        retroalimentacion = request.POST.get('retroalimentacion', '').strip()

        if not nota_str:
            messages.error(request, 'Por favor ingresa una calificación.')
            return redirect(request.path)

        try:
            nota = Decimal(nota_str)
        except InvalidOperation:
            messages.error(request, 'La calificación ingresada no es válida.')
            return redirect(request.path)

        if nota < Decimal('1.0') or nota > Decimal('5.0'):
            messages.error(request, 'La calificación debe estar entre 1.0 y 5.0.')
            return redirect(request.path)

        NOTA_MINIMA = Decimal('3.0')

        intento.calificacion = nota
        intento.retroalimentacion = retroalimentacion
        intento.aprobado = nota >= NOTA_MINIMA
        intento.save()

        ejercicio = intento.ejercicio
        clase = ejercicio.clase
        estudiante = intento.estudiante

        notificar_calificacion(estudiante, ejercicio, nota)

        total_intentos = IntentoEjercicio.objects.filter(
            estudiante=estudiante,
            ejercicio=ejercicio
        ).count()

        if intento.aprobado:
            messages.success(request, '¡Calificación guardada correctamente! El estudiante aprobó.')
        else:
            if total_intentos < 2:
                messages.warning(
                    request,
                    f'Calificación menor a {NOTA_MINIMA}. El estudiante puede realizar un segundo y último intento.'
                )
            else:
                messages.error(
                    request,
                    f'Calificación menor a {NOTA_MINIMA}. El estudiante ha agotado sus 2 intentos y ha sido bloqueado de la clase.'
                )
                if estudiante in clase.estudiantes.all():
                    clase.estudiantes.remove(estudiante)

        return redirect('ejercicios:detalle_ejercicio_docente', clase_id=clase.id, ejercicio_id=ejercicio.id)

    return render(
        request,
        'ejercicios/calificar_ejercicio.html',
        {
            'intento': intento,
            'respuestas': respuestas,
            'ejercicio': intento.ejercicio,       
            'clase': intento.ejercicio.clase,
        }
    )


# ============================================================
# DETALLE EJERCICIO DOCENTE
# ============================================================
@login_required
def detalle_ejercicio_docente(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    intentos = IntentoEjercicio.objects.filter(
        ejercicio=ejercicio
    ).select_related('estudiante').order_by('-fecha_envio')
    
    recursos = ejercicio.recursos.all()

    return render(
        request,
        'ejercicios/detalle_ejercicio_docente.html',
        {
            'clase': clase,
            'ejercicio': ejercicio,
            'intentos': intentos,
            'recursos': recursos,
        }
    )


# ============================================================
# ELIMINAR EJERCICIO
# ============================================================
@login_required
def eliminar_ejercicio(request, clase_id, ejercicio_id):
    if request.user.perfil.rol != 'docente':
        return redirect('inicio')
        
    ejercicio = get_object_or_404(
        Ejercicio, 
        id=ejercicio_id, 
        clase_id=clase_id, 
        clase__docente=request.user
    )
    
    ejercicio.delete()
    
    messages.success(request, 'Ejercicio eliminado con éxito.')
    return redirect(f'/clase/detalle/{clase_id}/')


# ============================================================
# REENVIAR EJERCICIO
# ============================================================
@login_required
def reenviar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
    
    clase_id = intento.ejercicio.clase.id
    ejercicio_id = intento.ejercicio.id
    
    intento.respuestas.all().delete()
    intento.delete()
    
    messages.warning(request, "El intento ha sido rechazado. El estudiante ya puede volver a realizar el ejercicio.")
    
    return redirect('ejercicios:detalle_ejercicio_docente', clase_id=clase_id, ejercicio_id=ejercicio_id)