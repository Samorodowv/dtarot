from django.urls import path
from . import telegram_views, views

app_name = "tarot_readings"

urlpatterns = [
    path("", views.GetReadingView.as_view(), name="home"),
    path("reading/result/<int:reading_id>/", views.ReadingResultView.as_view(), name="reading_result"),
    path("api/reading/<int:reading_id>/status/", views.reading_status_api, name="reading_status_api"),
    path("telegram/webhook/", telegram_views.telegram_webhook, name="telegram_webhook"),
    path("api/health/", views.health_check, name="health_check"),
    path("api/metrics/", views.metrics_api, name="metrics_api"),
]
