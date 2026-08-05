import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from clase.models import Clase
from .models import Ejercicio, Pregunta, Opcion, IntentoEjercicio, RespuestaEstudiante

def crear_ejercicio(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    # Si la petición viene por JSON (desde el script interactivo)
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            titulo = data.get('titulo')
            descripcion = data.get('descripcion', '')
            
            # 🔧 Corrección aquí: extraemos del JSON 'data' en lugar de request.POST
            fecha_limite = data.get('fecha_limite') or None
            
            preguntas_data = data.get('preguntas', [])

            if not titulo:
                return JsonResponse({'status': 'error', 'message': 'El título es obligatorio.'}, status=400)

            # 1. Creamos el Ejercicio incluyendo la fecha límite
            ejercicio = Ejercicio.objects.create(
                clase=clase,
                titulo=titulo,
                descripcion=descripcion,
                fecha_limite=fecha_limite  # ➕ Se asigna aquí
            )

            # 2. Recorremos y guardamos preguntas y opciones
            for p_data in preguntas_data:
                enunciado = p_data.get('texto')
                if enunciado:
                    pregunta = Pregunta.objects.create(
                        ejercicio=ejercicio,
                        enunciado=enunciado
                    )

                    opciones_data = p_data.get('opciones', [])
                    for o_data in opciones_data:
                        contenido_opcion = o_data.get('texto')
                        if contenido_opcion:
                            Opcion.objects.create(
                                pregunta=pregunta,
                                texto_opcion=contenido_opcion,
                                es_correcta=o_data.get('es_correcta', False)
                            )

            return JsonResponse({'status': 'success', 'message': '¡Ejercicio creado con éxito!'})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return render(request, 'ejercicios/crear_ejercicio.html', {'clase': clase})
    
def eliminar_ejercicio(request, clase_id, ejercicio_id):
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase_id=clase_id)
    
    if request.method == 'POST':
        ejercicio.delete()
        messages.success(request, "¡Ejercicio eliminado correctamente!")
        return redirect('detalle_clase', clase_id=clase_id)
        
    return redirect('detalle_clase', clase_id=clase_id)


def editar_ejercicio(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    # Manejo de actualización por JSON
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            titulo = data.get('titulo')
            descripcion = data.get('descripcion', '')
            preguntas_data = data.get('preguntas', [])

            if not titulo:
                return JsonResponse({'status': 'error', 'message': 'El título es obligatorio.'}, status=400)

            # Actualizamos datos principales
            ejercicio.titulo = titulo
            ejercicio.descripcion = descripcion
            ejercicio.save()

            # Reemplazamos las preguntas anteriores limpiando y creando las nuevas
            ejercicio.preguntas.all().delete()

            for p_data in preguntas_data:
                enunciado = p_data.get('texto')
                if enunciado:
                    pregunta = Pregunta.objects.create(
                        ejercicio=ejercicio,
                        enunciado=enunciado
                    )

                    opciones_data = p_data.get('opciones', [])
                    for o_data in opciones_data:
                        contenido_opcion = o_data.get('texto')
                        if contenido_opcion:
                            Opcion.objects.create(
                                pregunta=pregunta,
                                texto_opcion=contenido_opcion,
                                es_correcta=o_data.get('es_correcta', False)
                            )

            return JsonResponse({'status': 'success', 'message': '¡Ejercicio actualizado con éxito!'})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return render(request, 'ejercicios/editar_ejercicio.html', {
        'clase': clase,
        'ejercicio': ejercicio
    })

    
    
def detalle_ejercicio_docente(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)
    
    # Obtenemos todos los intentos de los estudiantes para este ejercicio
    intentos = IntentoEjercicio.objects.filter(ejercicio=ejercicio).order_by('-fecha_envio')

    return render(request, 'ejercicios/detalle_ejercicio_docente.html', {
        'clase': clase,
        'ejercicio': ejercicio,
        'intentos': intentos
    })



# VISTA DEL DOCENTE: Calificar el intento de un estudiante
def calificar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
    
    # Obtenemos las respuestas asociadas a este intento
    respuestas = intento.respuestas.all()
    
    if request.method == 'POST':
        nota_str = request.POST.get('calificacion')
        retro = request.POST.get('retroalimentacion', '')
        
        if not nota_str:
            messages.error(request, "Por favor ingresa una calificación.")
            return redirect(request.path)

        nota = float(nota_str)
        intento.calificacion = nota
        intento.retroalimentacion = retro
        
        # 📌 Define aquí tu nota mínima para aprobar (ej: 3.0)
        NOTA_MINIMA = 3.0 
        
        ejercicio = intento.ejercicio
        clase_id = ejercicio.clase.id
        ejercicio_id = ejercicio.id

        if nota >= NOTA_MINIMA:
            # 🟢 Aprobado
            intento.save()
            messages.success(request, "¡Calificación guardada correctamente! El estudiante aprobó.")
        else:
            # 🔴 Reprobado -> Reenvío automático para nuevo intento
            messages.warning(request, f"Calificación menor a {NOTA_MINIMA}. El ejercicio ha sido reenviado para que el estudiante lo repita.")
            
            # Borramos las respuestas y el intento para que el estudiante pueda volver a responder
            intento.respuestas.all().delete()
            intento.delete()
        
        return redirect('detalle_ejercicio_docente', clase_id=clase_id, ejercicio_id=ejercicio_id)

    # Pasamos 'respuestas' al contexto del render
    return render(request, 'ejercicios/calificar_ejercicio.html', {
        'intento': intento,
        'respuestas': respuestas
    })


def reenviar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
    clase_id = intento.ejercicio.clase.id
    ejercicio_id = intento.ejercicio.id
    
    # Borramos las respuestas y el intento para que el estudiante pueda volver a hacerlo
    intento.respuestas.all().delete()
    intento.delete()
    
    messages.warning(request, "El ejercicio ha sido reenviado para que el estudiante lo vuelva a realizar.")
    return redirect('detalle_ejercicio_docente', clase_id=clase_id, ejercicio_id=ejercicio_id)


def responder_actividad(request, pregunta_id): # Aquí 'pregunta_id' es el ID del Ejercicio
    ejercicio = get_object_or_404(Ejercicio, id=pregunta_id)
    clase = ejercicio.clase

    if request.method == 'POST':
        # 1. Creamos o recuperamos el intento de forma segura para soportar reenvíos
        intento, created = IntentoEjercicio.objects.get_or_create(
            estudiante=request.user,
            ejercicio=ejercicio
        )

        # Limpiamos respuestas anteriores si se está reenviando
        intento.respuestas.all().delete()

        # 2. Guardamos las respuestas nuevas del formulario
        for pregunta in ejercicio.preguntas.all():
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                opcion_seleccionada = get_object_or_404(Opcion, id=opcion_id)
                RespuestaEstudiante.objects.create(
                    intento=intento,
                    pregunta=pregunta,
                    opcion_seleccionada=opcion_seleccionada
                )

        messages.success(request, "¡Ejercicio enviado con éxito! Quedó pendiente de calificación.")
        return redirect('estudiante:detalle_clase_estudiante', clase_id=clase.id)

    # 3. Renderizamos utilizando la plantilla moderna dentro de ejercicios
    return render(request, 'ejercicios/resolver_ejercicio.html', {
        'ejercicio': ejercicio,
        'clase': clase,
    })