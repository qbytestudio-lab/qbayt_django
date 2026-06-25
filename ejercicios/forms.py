from django import forms
from django.forms import inlineformset_factory
from .models import Ejercicio, Pregunta

class EjercicioForm(forms.ModelForm):
    class Meta:
        model = Ejercicio
        fields = ['titulo', 'enunciado', 'imagen_contexto', 'visible']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Dictado de Intervalos de Quinta'}),
            'enunciado': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Escribe las instrucciones para los estudiantes...'}),
            'imagen_contexto': forms.FileInput(attrs={'class': 'form-control'}),
            'visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Este FormSet generará los formularios de preguntas asociados a un Ejercicio.
# 'extra=1' significa que por defecto pintará una pregunta vacía en la carga inicial.
PreguntaFormSet = inlineformset_factory(
    Ejercicio, 
    Pregunta,
    fields=['texto_pregunta', 'tipo'],
    extra=1,
    can_delete=True,
    widgets={
        'texto_pregunta': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Escribe la pregunta o instrucción del ítem...'}),
        'tipo': forms.Select(attrs={'class': 'form-select'}),
    }
)