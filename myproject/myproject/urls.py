# myproject/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('textanalysis.urls')),  # Ensure this points to your app's urls.py
]
