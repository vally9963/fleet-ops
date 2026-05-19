import pytest
from robots.models import Robot, Zone
from tasks.models import Task, Route


@pytest.fixture
def zone(db):
    return Zone.objects.create(
        name="Zone-A",
        zone_type=Zone.ZoneType.STORAGE,
        capacity=5,
    )


@pytest.fixture
def zone_b(db):
    return Zone.objects.create(
        name="Zone-B",
        zone_type=Zone.ZoneType.WORK_AREA,
        capacity=5,
    )


@pytest.fixture
def robot(db, zone):
    return Robot.objects.create(
        name="R-01",
        battery_level=80.00,
        current_zone=zone,
    )


@pytest.fixture
def task(db, robot, zone, zone_b):
    return Task.objects.create(
        robot=robot,
        from_zone=zone,
        to_zone=zone_b,
        status=Task.Status.PENDING,
    )
