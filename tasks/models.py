from django.db import models
from robots.models import Robot, Zone


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "대기"
        ASSIGNED = "ASSIGNED", "배정됨"
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        DONE = "DONE", "완료"
        TIMEOUT = "TIMEOUT", "타임아웃"

    robot = models.ForeignKey(
        Robot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    from_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="tasks_from")
    to_zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="tasks_to")
    priority = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "task"
        ordering = ["-priority", "created_at"]

    def __str__(self):
        return f"Task#{self.pk} [{self.status}] {self.from_zone} → {self.to_zone}"


class Route(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="route")
    # waypoints: [{"zone_id": 1, "seq": 0}, ...]
    waypoints = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "route"

    def __str__(self):
        return f"Route for Task#{self.task_id}"
