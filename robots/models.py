from django.db import models


class Zone(models.Model):
    class ZoneType(models.TextChoices):
        STORAGE = "STORAGE", "보관 구역"
        CHARGING = "CHARGING", "충전 구역"
        WORK_AREA = "WORK_AREA", "작업 구역"
        STAGING = "STAGING", "대기 구역"

    name = models.CharField(max_length=100, unique=True)
    zone_type = models.CharField(max_length=20, choices=ZoneType.choices)
    capacity = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "zone"

    def __str__(self):
        return f"{self.name} ({self.zone_type})"


class Robot(models.Model):
    class Status(models.TextChoices):
        IDLE = "IDLE", "대기"
        BUSY = "BUSY", "작업 중"
        CHARGING = "CHARGING", "충전 중"
        ERROR = "ERROR", "오류"

    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDLE)
    battery_level = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    current_zone = models.ForeignKey(
        Zone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="robots",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "robot"

    def __str__(self):
        return f"{self.name} [{self.status}] {self.battery_level}%"
