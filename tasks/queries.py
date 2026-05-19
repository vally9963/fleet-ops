from django.db.models import Count, Q
from robots.models import Zone


def zone_congestion():
    """구역별 현재 진행 중인 작업 수를 반환한다."""
    return (
        Zone.objects.annotate(
            active_tasks=Count(
                "tasks_from",
                filter=Q(tasks_from__status="IN_PROGRESS"),
            )
        )
        .values("name", "active_tasks")
        .order_by("-active_tasks")
    )
