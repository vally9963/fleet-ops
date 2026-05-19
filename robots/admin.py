from django.contrib import admin
from .models import Robot, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "zone_type", "capacity", "created_at")
    list_filter = ("zone_type",)


@admin.register(Robot)
class RobotAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "battery_level", "current_zone", "updated_at")
    list_filter = ("status",)
