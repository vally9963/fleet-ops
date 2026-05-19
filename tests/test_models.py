import pytest
from robots.models import Robot, Zone
from tasks.models import Task, Route


@pytest.mark.django_db
def test_zone_creation():
    zone = Zone.objects.create(name="Zone-A", zone_type=Zone.ZoneType.STORAGE, capacity=5)
    assert zone.name == "Zone-A"
    assert zone.capacity == 5
    assert str(zone) == "Zone-A (STORAGE)"


@pytest.mark.django_db
def test_robot_creation(zone):
    robot = Robot.objects.create(name="R-01", battery_level=80.0, current_zone=zone)
    assert robot.name == "R-01"
    assert robot.battery_level == 80.0
    assert robot.status == Robot.Status.IDLE
    assert robot.current_zone == zone
    assert str(robot) == "R-01 [IDLE] 80.0%"


@pytest.mark.django_db
def test_robot_default_status():
    robot = Robot.objects.create(name="R-02", battery_level=50.0)
    assert robot.status == Robot.Status.IDLE
    assert robot.current_zone is None


@pytest.mark.django_db
def test_task_default_status(robot, zone, zone_b):
    task = Task.objects.create(robot=robot, from_zone=zone, to_zone=zone_b)
    assert task.status == Task.Status.PENDING
    assert task.completed_at is None


@pytest.mark.django_db
def test_task_transition_to_assigned(robot, zone, zone_b):
    from django.utils import timezone
    task = Task.objects.create(robot=robot, from_zone=zone, to_zone=zone_b)
    task.status = Task.Status.ASSIGNED
    task.save()
    task.refresh_from_db()
    assert task.status == Task.Status.ASSIGNED


@pytest.mark.django_db
def test_route_waypoints(task):
    waypoints = [{"zone_id": 1, "seq": 0}, {"zone_id": 2, "seq": 1}]
    route = Route.objects.create(task=task, waypoints=waypoints)
    route.refresh_from_db()
    assert route.waypoints == waypoints
    assert len(route.waypoints) == 2
