# apps/logs/admin.py

from django.contrib import admin
from .models import ActividadLog

@admin.register(ActividadLog)
class ActividadLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'activity_type', 'description', 'user', 'empresa', 'entity_name']
    list_filter = ['activity_type', 'empresa', 'timestamp', 'user']
    search_fields = ['description', 'user__username', 'empresa__nombre', 'entity_name']
    readonly_fields = ['timestamp', 'user', 'empresa', 'activity_type', 'description', 'entity_id', 'entity_name'] # Los logs no deben editarse
    # Los logs pueden volverse muy grandes, así que podrías querer deshabilitar la paginación o limitarla
    list_per_page = 20