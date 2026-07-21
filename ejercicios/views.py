import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from clase.models import Clase
from .models import Ejercicio, Pregunta, Opcion, RespuestaEstudiante, IntentoEjercicio

def crear_ejercicio(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    # Si la petición viene por JSON (desde el script interactivo)
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            titulo = data.get('titulo')
            descripcion = data.get('descripcion', '')
            preguntas_data = data.get('preguntas', [])

            if not titulo:
                return JsonResponse({'status': 'error', 'message': 'El título es obligatorio.'}, status=400)

            # 1. Creamos el Ejercicio
            ejercicio = Ejercicio.objects.create(
                clase=clase,
                titulo=titulo,
                descripcion=descripcion
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

def resolver_ejercicio(request, clase_id, ejercicio_id):
    clase = get_object_or_404(Clase, id=clase_id)
    ejercicio = get_object_or_404(Ejercicio, id=ejercicio_id, clase=clase)

    if request.method == 'POST':
        # Creamos el intento usando el usuario autenticado actual
        intento = IntentoEjercicio.objects.create(
            estudiante=request.user,
            ejercicio=ejercicio
        )
        
        # Guardar las respuestas enviadas por el formulario...
        for pregunta in ejercicio.preguntas.all():
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                opcion = Opcion.objects.get(id=opcion_id)
                RespuestaEstudiante.objects.create(
                    intento=intento,
                    pregunta=pregunta,
                    opcion_seleccionada=opcion
                )
        return redirect('detalle_clase', clase_id=clase.id) # O a donde desees redirigir

    return render(request, 'ejercicios/resolver_ejercicio.html', {
        'clase': clase,
        'ejercicio': ejercicio
    })

# VISTA DEL DOCENTE: Calificar el intento de un estudiante
def calificar_ejercicio(request, intento_id):
    intento = get_object_or_404(IntentoEjercicio, id=intento_id)
    
    if request.method == 'POST':
        nota = request.POST.get('calificacion')
        retro = request.POST.get('retroalimentacion', '')
        
        intento.calificacion = nota
        intento.retroalimentacion = retro
        intento.save()
        
        messages.success(request, "¡Calificación guardada correctamente!")
        return redirect('detalle_ejercicio_docente', clase_id=intento.ejercicio.clase.id, ejercicio_id=intento.ejercicio.id)

    return render(request, 'ejercicios/calificar_ejercicio.html', {'intento': intento})