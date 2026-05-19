import pytest
from robots.models import Robot, Zone
from tasks.models import Task
from robots.queries import robot_task_summary, battery_stats
from tasks.queries import zone_congestion


@pytest.fixture
def setup_robots_and_tasks(db):
    zone_a = Zone.objects.create(name="Z-A", zone_type=Zone.ZoneType.STORAGE, capacity=5)
    zone_b = Zone.objects.create(name="Z-B", zone_type=Zone.ZoneType.WORK_AREA, capacity=5)
    r1 = Robot.objects.create(name="R-01", battery_level=90.0, current_zone=zone_a)
    r2 = Robot.objects.create(name="R-02", battery_level=30.0, current_zone=zone_a)
    Task.objects.create(robot=r1, from_zone=zone_a, to_zone=zone_b, status=Task.Status.DONE)
    Task.objects.create(robot=r1, from_zone=zone_a, to_zone=zone_b, status=Task.Status.DONE)
    Task.objects.create(robot=r1, from_zone=zone_a, to_zone=zone_b, status=Task.Status.TIMEOUT)
    Task.objects.create(robot=r2, from_zone=zone_a, to_zone=zone_b, status=Task.Status.DONE)
    return r1, r2, zone_a, zone_b


@pytest.mark.django_db
def test_robot_task_summary(setup_robots_and_tasks):
    r1, *_ = setup_robots_and_tasks
    summary = robot_task_summary(r1)
    status_map = {item["status"]: item["count"] for item in summary}
    assert status_map["DONE"] == 2
    assert status_map["TIMEOUT"] == 1


@pytest.mark.django_db
def test_battery_stats(setup_robots_and_tasks):
    stats = battery_stats()
    assert float(stats["min_battery"]) == 30.0
    assert float(stats["max_battery"]) == 90.0
    assert float(stats["avg_battery"]) == pytest.approx(60.0)


@pytest.mark.django_db
def test_zone_congestion(db):
    zone_a = Zone.objects.create(name="Zone-A", zone_type=Zone.ZoneType.STORAGE, capacity=5)
    zone_b = Zone.objects.create(name="Zone-B", zone_type=Zone.ZoneType.WORK_AREA, capacity=5)
    robot = Zone.objects.create(name="Zone-C", zone_type=Zone.ZoneType.CHARGING, capacity=5)
    r = Robot.objects.create(name="R-03", battery_level=70.0)
    Task.objects.create(robot=r, from_zone=zone_a, to_zone=zone_b, status=Task.Status.IN_PROGRESS)
    Task.objects.create(robot=r, from_zone=zone_a, to_zone=zone_b, status=Task.Status.IN_PROGRESS)
    Task.objects.create(robot=r, from_zone=zone_b, to_zone=zone_a, status=Task.Status.IN_PROGRESS)
    Task.objects.create(robot=r, from_zone=zone_b, to_zone=zone_a, status=Task.Status.DONE)

    congestion = {row["name"]: row["active_tasks"] for row in zone_congestion()}
    assert congestion["Zone-A"] == 2
    assert congestion["Zone-B"] == 1
