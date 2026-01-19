from django.urls import path
from . import views

app_name = 'readings'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('reading/', views.GetReadingView.as_view(), name='get_reading'),
] 