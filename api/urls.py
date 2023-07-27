from django.urls import path
from .views import api_rt

urlpatterns = [
    path('rt/<code>', api_rt, name='api_rt'),
]
