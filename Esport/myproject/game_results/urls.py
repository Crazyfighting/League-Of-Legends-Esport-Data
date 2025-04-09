# game_results/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.game_results, name='game_results'),
]
