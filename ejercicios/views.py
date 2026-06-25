from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Importa tu modelo Clase
from .models import Ejercicio
from .forms import EjercicioForm, PreguntaFormSet
from docente.models import Clase

@login_required
def crear_ejercicio(request, clase_id):
    # Buscamos la clase para asegurar que existe
    clase = get_object_or_404(Clase, id=clase_id)
    
    if request.method == 'POST':
        ejercicio_form = EjercicioForm(request.POST, request.FILES)
        opciones_formset = PreguntaFormSet(request.POST, prefix='preguntas')
        
        if ejercicio_form.is_valid() and opciones_formset.is_valid():
            # 1. Guardamos el ejercicio de forma temporal sin hacer commit a la BD
            ejercicio = ejercicio_form.save(commit=False)
            # 2. Le asignamos la clase actual
            ejercicio.clase = clase
            # 3. Guardamos definitivamente el Ejercicio padre
            ejercicio.save()
            
            # 4. Pasamos la instancia guardada al formset de preguntas y salvamos
            opciones_formset.instance = ejercicio
            opciones_formset.save()
            
            messages.success(request, '¡El ejercicio ha sido publicado con éxito en esta clase!')
            return redirect('detalle_clase', clase_id=clase.id)
        else:
            messages.error(request, 'Por favor verifica los datos del formulario.')
    else:
        ejercicio_form = EjercicioForm()
        opciones_formset = PreguntaFormSet(prefix='preguntas')
        
    return render(request, 'ejercicios/crear_ejercicio.html', {
        'clase': clase,
        'ejercicio_form': ejercicio_form,
        'opciones_formset': opciones_formset,
    })