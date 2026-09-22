"""
Utilidades de lógica de negocio para el módulo estudiante.
Centraliza las reglas de bloqueo de clases.
"""
from datetime import timedelta
from django.utils import timezone


# ═══════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════

DIAS_GRACIA_VENCIDA = 5          # días para ocultar clases vencidas
DIAS_BLOQUEO_REPROBADA = 5       # días bloqueado tras reprobar
DIAS_CLASE_NUEVA = 7             # días que cuenta una clase como "nueva"
NOTA_APROBACION = 3.0            # nota mínima para aprobar


# ═══════════════════════════════════════════════════════════
# HELPERS BÁSICOS
# ═══════════════════════════════════════════════════════════

def clases_visibles_estudiante(user):
    """
    Clases activas del estudiante. Oculta las vencidas hace más de 5 días.
    Las clases vencidas recientemente (≤ 5 días) siguen visibles para mostrar
    el estado final.
    """
    from clase.models import Clase
    limite = timezone.now().date() - timedelta(days=DIAS_GRACIA_VENCIDA)
    return Clase.objects.filter(
        estudiantes=user
    ).exclude(
        fecha_fin__lt=limite
    ).distinct()


def calcular_progreso_clase(estudiante, clase):
    """Devuelve el % de ejercicios completados en una clase."""
    from ejercicios.models import Ejercicio, IntentoEjercicio
    
    total_ejercicios = Ejercicio.objects.filter(clase=clase).count()
    if total_ejercicios == 0:
        return 0
    
    completados = IntentoEjercicio.objects.filter(
        estudiante=estudiante,
        ejercicio__clase=clase
    ).values('ejercicio').distinct().count()
    
    return round((completados / total_ejercicios) * 100)


def calcular_promedio_clase(estudiante, clase):
    """
    Calcula el promedio de calificaciones del estudiante en una clase.
    Solo considera intentos calificados.
    Devuelve None si no hay intentos calificados.
    """
    from ejercicios.models import IntentoEjercicio
    
    intentos_calificados = IntentoEjercicio.objects.filter(
        estudiante=estudiante,
        ejercicio__clase=clase,
        calificacion__isnull=False
    ).values_list('calificacion', flat=True)
    
    if not intentos_calificados:
        return None
    
    return sum(intentos_calificados) / len(intentos_calificados)


def estudiante_reprobo_clase(estudiante, clase):
    """
    Determina si un estudiante reprobó una clase.
    Criterio: promedio < NOTA_APROBACION O no completó todos los ejercicios.
    """
    from ejercicios.models import Ejercicio, IntentoEjercicio
    
    total_ejercicios = Ejercicio.objects.filter(clase=clase).count()
    if total_ejercicios == 0:
        return False
    
    intentos_calificados = IntentoEjercicio.objects.filter(
        estudiante=estudiante,
        ejercicio__clase=clase,
        calificacion__isnull=False
    ).values('ejercicio').distinct().count()
    
    if intentos_calificados < total_ejercicios:
        return True
    
    promedio = calcular_promedio_clase(estudiante, clase)
    if promedio is None:
        return True
    
    return promedio < NOTA_APROBACION


# ═══════════════════════════════════════════════════════════
# 🚫 VALIDACIONES DE BLOQUEO
# ═══════════════════════════════════════════════════════════

def _clases_reprobadas_recientes(estudiante):
    """
    Devuelve las clases que el estudiante reprobó y cuya fecha_fin
    fue hace menos de DIAS_BLOQUEO_REPROBADA días.
    """
    from clase.models import Clase
    
    limite = timezone.now().date() - timedelta(days=DIAS_BLOQUEO_REPROBADA)
    
    clases_recientes = Clase.objects.filter(
        estudiantes=estudiante,
        fecha_fin__isnull=False,
        fecha_fin__gte=limite,
        fecha_fin__lt=timezone.now().date()
    )
    
    reprobadas = []
    for clase in clases_recientes:
        if estudiante_reprobo_clase(estudiante, clase):
            reprobadas.append(clase)
    
    return reprobadas


def puede_unirse_a_clase(estudiante, clase):
    """
    Verifica si el estudiante puede unirse a una clase.
    Devuelve (puede_unirse: bool, motivo: str).
    """
    from clase.models import Clase
    
    # ─── Regla 1: Bloqueo por reprobación ───
    clases_reprobadas = _clases_reprobadas_recientes(estudiante)
    
    for reprobada in clases_reprobadas:
        mismo_nombre = reprobada.nombre.strip().lower() == clase.nombre.strip().lower()
        misma_categoria = reprobada.categoria_tema == clase.categoria_tema
        
        if mismo_nombre and misma_categoria:
            dias_restantes = DIAS_BLOQUEO_REPROBADA - (
                timezone.now().date() - reprobada.fecha_fin
            ).days
            motivo = (
                f"Reprobaste la clase '{reprobada.nombre}' "
                f"(categoría: {reprobada.get_categoria_tema_display()}). "
                f"Debes esperar {dias_restantes} día(s) para unirte a otra clase "
                f"con el mismo nombre y categoría."
            )
            return False, motivo
    
    # ─── Regla 2: Bloqueo por duplicado con clase antigua ───
    clases_actuales = Clase.objects.filter(
        estudiantes=estudiante,
        categoria_tema=clase.categoria_tema,
        nombre__iexact=clase.nombre
    ).exclude(id=clase.id)
    
    for actual in clases_actuales:
        fecha_inicio = actual.fecha_inicio or actual.fecha_creacion.date()
        dias_iniciada = (timezone.now().date() - fecha_inicio).days
        
        if dias_iniciada > DIAS_CLASE_NUEVA:
            motivo = (
                f"Ya estás inscrito en otra clase con el mismo nombre y categoría "
                f"('{actual.nombre}') que lleva {dias_iniciada} días iniciada. "
                f"Solo puedes unirte a una clase nueva (menos de "
                f"{DIAS_CLASE_NUEVA} días desde su inicio)."
            )
            return False, motivo
    
    return True, ""


def esta_inscrito_en_otra_igual(estudiante, clase):
    """Devuelve la clase conflictiva (mismo nombre+categoría) o None."""
    from clase.models import Clase
    
    return Clase.objects.filter(
        estudiantes=estudiante,
        categoria_tema=clase.categoria_tema,
        nombre__iexact=clase.nombre
    ).exclude(id=clase.id).first()


def clases_bloqueadas_para_estudiante(estudiante):
    """
    Devuelve dict: {clase_id: motivo_bloqueo} para clases donde el estudiante
    NO puede unirse. Útil para filtrar "explorar_clases".
    """
    from clase.models import Clase
    
    clases_candidatas = Clase.objects.exclude(estudiantes=estudiante)
    
    bloqueos = {}
    for clase in clases_candidatas:
        puede, motivo = puede_unirse_a_clase(estudiante, clase)
        if not puede:
            bloqueos[clase.id] = motivo
    
    return bloqueos