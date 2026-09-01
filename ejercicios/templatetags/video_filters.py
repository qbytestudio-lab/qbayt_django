# En ejercicios/templatetags/video_filters.py
from django import template
import re

register = template.Library()

@register.filter
def youtube_embed(url):
    """Convierte URL de YouTube a URL de embed"""
    if 'youtube.com/watch' in url:
        video_id = url.split('v=')[-1].split('&')[0]
        return f'https://www.youtube.com/embed/{video_id}'
    elif 'youtu.be/' in url:
        video_id = url.split('youtu.be/')[-1]
        return f'https://www.youtube.com/embed/{video_id}'
    return url

@register.filter
def vimeo_embed(url):
    """Convierte URL de Vimeo a URL de embed"""
    if 'vimeo.com/' in url:
        video_id = url.split('vimeo.com/')[-1]
        return f'https://player.vimeo.com/video/{video_id}'
    return url