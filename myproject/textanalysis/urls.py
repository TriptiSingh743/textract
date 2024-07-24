from django.contrib import admin
from django.urls import path
from textanalysis import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('upload/', views.upload_image, name='upload_image'),
    path('entities/', views.entities, name='detected_entities'),
]
