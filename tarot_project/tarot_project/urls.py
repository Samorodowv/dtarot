from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tarot_readings.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler400 = 'tarot_readings.error_views.custom_400'
handler403 = 'tarot_readings.error_views.custom_403'
handler404 = 'tarot_readings.error_views.custom_404'
handler500 = 'tarot_readings.error_views.custom_500'
