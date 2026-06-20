# docente/utils.py
from .models import Actividad, RespuestaEstudiante

def calcular_progreso_clase(estudiante, clase):
    total_actividades = Actividad.objects.filter(leccion__clase=clase).count()
    if total_actividades == 0:
        return 0
    completadas = RespuestaEstudiante.objects.filter(
        estudiante=estudiante,
        actividad__leccion__clase=clase
    ).values('actividad').distinct().count()
    return round((completadas / total_actividades) * 100)