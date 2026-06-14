from django.urls import path
from . import views

app_name = 'clase'

urlpatterns = [
    path('', views.index, name='index'),
]