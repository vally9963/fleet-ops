from django.contrib import admin
from .models import Task, Route


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "robot", "status", "from_zone", "to_zone", "priority", "created_at", "completed_at")
    list_filter = ("status",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "created_at")
