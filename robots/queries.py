from django.db.models import Count, Min, Max, Avg
from robots.models import Robot
from tasks.models import Task


def robot_task_summary(robot):
    """로봇 한 대의 상태별 작업 수를 반환한다."""
    return (
        Task.objects.filter(robot=robot)
        .values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )


def battery_stats():
    """전체 로봇의 배터리 최솟값·최댓값·평균을 반환한다."""
    return Robot.objects.aggregate(
        min_battery=Min("battery_level"),
        max_battery=Max("battery_level"),
        avg_battery=Avg("battery_level"),
    )
