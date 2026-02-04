from django.contrib import admin, messages
from django.http import HttpResponseRedirect

from .models import InteractionLog, InteractionRetentionConfig, PromptConfig


@admin.register(PromptConfig)
class PromptConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "updated_at")
    list_editable = ("is_active",)
    search_fields = ("name", "content")
    ordering = ("-updated_at",)
    actions = ("apply_prompt",)
    change_form_template = "admin/tarot_readings/promptconfig/change_form.html"

    def apply_prompt(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Выберите один промпт для применения.",
                level=messages.ERROR,
            )
            return
        prompt = queryset.first()
        prompt.is_active = True
        prompt.save()
        self.message_user(request, "Промпт применен.")

    apply_prompt.short_description = "Применить"

    def response_change(self, request, obj):
        if "_apply" in request.POST:
            self.message_user(request, "Промпт применен.")
            return HttpResponseRedirect(".")
        return super().response_change(request, obj)


@admin.register(InteractionRetentionConfig)
class InteractionRetentionConfigAdmin(admin.ModelAdmin):
    list_display = ("retention_days", "is_enabled", "updated_at")

    def has_add_permission(self, request):
        if InteractionRetentionConfig.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(InteractionLog)
class InteractionLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "source", "direction", "event_type", "interaction_id", "user_identifier", "reading")
    list_filter = ("source", "direction", "event_type", "created_at")
    search_fields = ("interaction_id", "user_identifier", "content")
    readonly_fields = (
        "created_at",
        "source",
        "direction",
        "event_type",
        "interaction_id",
        "user_identifier",
        "content",
        "metadata",
        "reading",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
