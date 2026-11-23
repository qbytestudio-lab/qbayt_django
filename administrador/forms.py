from django import forms
from ejercicios.models import PreguntaPersonalizada

class PreguntaPersonalizadaForm(forms.ModelForm):
    class Meta:
        model = PreguntaPersonalizada
        fields = ['tipo_practica', 'enunciado', 'audio', 'opcion_1', 'opcion_2', 'opcion_3', 'opcion_4', 'respuesta_correcta']
        widgets = {
            'tipo_practica': forms.Select(attrs={'class': 'form-select'}),
            'enunciado': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'audio': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'opcion_1': forms.TextInput(attrs={'class': 'form-control'}),
            'opcion_2': forms.TextInput(attrs={'class': 'form-control'}),
            'opcion_3': forms.TextInput(attrs={'class': 'form-control'}),
            'opcion_4': forms.TextInput(attrs={'class': 'form-control'}),
            'respuesta_correcta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Do Mayor'}),
        }