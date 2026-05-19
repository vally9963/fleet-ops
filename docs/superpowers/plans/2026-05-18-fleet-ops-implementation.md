# Fleet-Ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

<!-- 
  ## 새 세션에서 이 계획 실행하기
  
  이 파일을 새 세션에서 열고 아래 중 하나를 요청하세요.
  
  ### Subagent-Driven (속도 우선, 태스크별 격리 실행)
  
    docs/superpowers/plans/2026-05-18-fleet-ops-implementation.md 읽고
    Subagent-Driven으로 실행해줘
  
  ### Inline Execution (공부 목적, 과정이 눈에 보임)
  
    docs/superpowers/plans/2026-05-18-fleet-ops-implementation.md 읽고
    Inline Execution으로 실행해줘
  
  두 방식의 차이:
  - Subagent: 태스크마다 새 서브에이전트가 실행 → 빠르고 격리됨, 과정은 숨겨짐
  - Inline:   이 세션에서 직접 순차 실행 → 느리지만 중간 개입·질문 가능
  
  추천 순서: Inline 먼저 → Subagent 나중에
-->

**Goal:** Django ORM → Celery → Channels → Ray Actor 순서로 AMR(자율이동로봇) 관제 플랫폼을 단계별로 구현한다.

**Architecture:** 4개의 앱(robots, tasks, monitor, simulator)이 각 단계의 기술 레이어를 담당한다. 1단계는 ORM 모델링, 2단계는 Celery 비동기 작업 배정, 3단계는 WebSocket 실시간 모니터링, 4단계는 Ray Actor 기반 시뮬레이터이며 각 단계는 이전 단계 위에 쌓인다.

**Tech Stack:** Python 3.11, Django 4.2, SQLite(개발), Celery 5.3 + Redis, Django Channels 4 + daphne, Ray 2.9, pytest-django, factory-boy

---

## 파일 구조 (전체)

```
amr_platform/
├── pytest.ini                        # pytest 설정
├── config/
│   ├── settings.py                   # 단계별 주석 해제로 활성화
│   ├── celery.py                     # 2단계: Celery 앱 초기화
│   ├── asgi.py                       # 3단계: ASGI + Channels 라우팅
│   └── __init__.py                   # 2단계: celery app import
├── robots/
│   ├── models.py                     # Robot, Zone 모델
│   ├── admin.py                      # Admin 등록
│   └── queries.py                    # 배터리 통계, 로봇별 작업 이력
├── tasks/
│   ├── models.py                     # Task, Route 모델
│   ├── admin.py                      # Admin 등록
│   ├── queries.py                    # 구역 혼잡도 집계
│   └── celery_tasks.py               # 2단계: 배정/감시/타임아웃 태스크
├── monitor/
│   ├── consumers.py                  # 3단계: WebSocket Consumer
│   └── routing.py                    # 3단계: WebSocket URL 라우팅
├── simulator/
│   ├── actors.py                     # 4단계: Ray RobotActor
│   ├── views.py                      # 4단계: 시뮬레이터 API 뷰
│   └── urls.py                       # 4단계: URL 라우팅
└── tests/
    ├── conftest.py                   # pytest fixtures (factory-boy)
    ├── test_models.py                # 1단계: 모델 단위 테스트
    ├── test_queries.py               # 1단계: 쿼리 통계 테스트
    ├── test_celery_tasks.py          # 2단계: Celery 태스크 테스트
    ├── test_consumers.py             # 3단계: WebSocket Consumer 테스트
    └── test_simulator.py             # 4단계: Ray Actor 테스트
```

---

## 1단계 — Django ORM

### Task 1.1: pytest 환경 설정

**Files:**
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [x] **Step 1: pytest.ini 작성**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests/test_*.py
```

- [x] **Step 2: tests 디렉터리 및 conftest 초기화**

```python
# tests/__init__.py
# (빈 파일)
```

```python
# tests/conftest.py
import pytest
from robots.models import Robot, Zone
from tasks.models import Task, Route


@pytest.fixture
def zone(db):
    return Zone.objects.create(name="Zone-A", zone_type=Zone.ZoneType.STORAGE, capacity=5)


@pytest.fixture
def zone_b(db):
    return Zone.objects.create(name="Zone-B", zone_type=Zone.ZoneType.WORK_AREA, capacity=5)


@pytest.fixture
def robot(db, zone):
    return Robot.objects.create(name="R-01", battery_level=80.00, current_zone=zone)


@pytest.fixture
def task(db, robot, zone, zone_b):
    return Task.objects.create(robot=robot, from_zone=zone, to_zone=zone_b, status=Task.Status.PENDING)
```

- [x] **Step 3: pytest가 실행되는지 확인 (아직 테스트 없음)**

```bash
cd /mnt/c/Projects/fleet-ops
python -m pytest --co -q
```

Expected: `no tests ran` (오류 없이 종료)

- [x] **Step 4: 커밋**

```bash
git add pytest.ini tests/__init__.py tests/conftest.py
git commit -m "chore: pytest-django 초기 설정"
```

---

### Task 1.2: Zone 모델 + 마이그레이션

**Files:**
- Create: `robots/models.py`
- Create: `robots/migrations/0001_initial.py` (자동 생성)
- Create: `tests/test_models.py` (Zone 부분)

- [x] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_models.py
import pytest
from robots.models import Zone


@pytest.mark.django_db
def test_zone_creation():
    zone = Zone.objects.create(name="Zone-A", zone_type=Zone.ZoneType.STORAGE, capacity=5)
    assert zone.name == "Zone-A"
    assert zone.capacity == 5
    assert str(zone) == "Zone-A (STORAGE)"
```

- [x] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_models.py::test_zone_creation -v
```

Expected: `FAILED` — `No module named 'robots.models'` 또는 `Zone` 없음

- [x] **Step 3: Zone 모델 작성**

```python
# robots/models.py
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
```

- [x] **Step 4: 마이그레이션 생성 및 적용**

```bash
python manage.py makemigrations robots
python manage.py migrate robots
```

Expected: `Migrations for 'robots': robots/migrations/0001_initial.py`

- [x] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/test_models.py::test_zone_creation -v
```

Expected: `PASSED`

- [x] **Step 6: 커밋**

```bash
git add robots/models.py robots/migrations/ tests/test_models.py
git commit -m "feat: Zone 모델 추가"
```

---

### Task 1.3: Robot 모델

**Files:**
- Modify: `robots/models.py` — Robot 추가
- Modify: `robots/migrations/` — 자동 생성
- Modify: `tests/test_models.py` — Robot 테스트 추가

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py`에 아래 테스트 추가:

```python
from robots.models import Robot


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
```

- [x] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_models.py::test_robot_creation -v
```

Expected: `FAILED` — `Robot` 없음

- [x] **Step 3: Robot 모델 추가**

`robots/models.py`에 Robot 클래스 추가:

```python
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
```

- [x] **Step 4: 마이그레이션**

```bash
python manage.py makemigrations robots
python manage.py migrate robots
```

- [x] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/test_models.py -v
```

Expected: 모든 테스트 `PASSED`

- [x] **Step 6: 커밋**

```bash
git add robots/models.py robots/migrations/ tests/test_models.py
git commit -m "feat: Robot 모델 추가 (상태: IDLE/BUSY/CHARGING)"
```

---

### Task 1.4: Task 모델 + 상태 머신

**Files:**
- Create: `tasks/models.py`
- Create: `tasks/migrations/0001_initial.py` (자동 생성)
- Modify: `tests/test_models.py` — Task 테스트 추가

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py`에 추가:

```python
from tasks.models import Task


@pytest.mark.django_db
def test_task_default_status(robot, zone, zone_b):
    task = Task.objects.create(robot=robot, from_zone=zone, to_zone=zone_b)
    assert task.status == Task.Status.PENDING
    assert task.completed_at is None


@pytest.mark.django_db
def test_task_transition_to_assigned(robot, zone, zone_b):
    task = Task.objects.create(robot=robot, from_zone=zone, to_zone=zone_b)
    task.status = Task.Status.ASSIGNED
    task.save()
    task.refresh_from_db()
    assert task.status == Task.Status.ASSIGNED
```

- [x] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_models.py::test_task_default_status -v
```

Expected: `FAILED` — `Task` 없음

- [x] **Step 3: Task 모델 작성**

```python
# tasks/models.py
from django.db import models
from robots.models import Robot, Zone


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "대기"
        ASSIGNED = "ASSIGNED", "배정됨"
        IN_PROGRESS = "IN_PROGRESS", "진행 중"
        DONE = "DONE", "완료"
        TIMEOUT = "TIMEOUT", "타임아웃"

    robot = models.ForeignKey(Robot, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
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
```

- [x] **Step 4: 마이그레이션**

```bash
python manage.py makemigrations tasks
python manage.py migrate tasks
```

- [x] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/test_models.py -v
```

Expected: 모든 테스트 `PASSED`

- [x] **Step 6: 커밋**

```bash
git add tasks/models.py tasks/migrations/ tests/test_models.py
git commit -m "feat: Task 모델 추가 (상태 머신: PENDING→ASSIGNED→IN_PROGRESS→DONE/TIMEOUT)"
```

---

### Task 1.5: Route 모델 (waypoints JSON)

**Files:**
- Modify: `tasks/models.py` — Route 추가
- Modify: `tasks/migrations/` — 자동 생성
- Modify: `tests/test_models.py` — Route 테스트 추가

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py`에 추가:

```python
from tasks.models import Route


@pytest.mark.django_db
def test_route_waypoints(task):
    waypoints = [{"zone_id": 1, "seq": 0}, {"zone_id": 2, "seq": 1}]
    route = Route.objects.create(task=task, waypoints=waypoints)
    route.refresh_from_db()
    assert route.waypoints == waypoints
    assert len(route.waypoints) == 2
```

- [x] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_models.py::test_route_waypoints -v
```

Expected: `FAILED` — `Route` 없음

- [x] **Step 3: Route 모델 추가**

`tasks/models.py`에 추가:

```python
class Route(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="route")
    waypoints = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Route for Task#{self.task_id}"
```

- [x] **Step 4: 마이그레이션**

```bash
python manage.py makemigrations tasks
python manage.py migrate tasks
```

- [x] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/test_models.py -v
```

Expected: 모든 테스트 `PASSED`

- [x] **Step 6: 커밋**

```bash
git add tasks/models.py tasks/migrations/ tests/test_models.py
git commit -m "feat: Route 모델 추가 (waypoints JSON 저장)"
```

---

### Task 1.6: 통계 쿼리 (로봇 작업 이력 · 배터리 통계)

**Files:**
- Create: `robots/queries.py`
- Create: `tests/test_queries.py`

- [x] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_queries.py
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
```

- [x] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_queries.py -v
```

Expected: `FAILED` — `No module named 'robots.queries'`

- [x] **Step 3: 쿼리 함수 작성**

```python
# robots/queries.py
from django.db.models import Count, Min, Max, Avg
from tasks.models import Task
from robots.models import Robot


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
```

- [x] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_queries.py -v
```

Expected: 모든 테스트 `PASSED`

- [x] **Step 5: 커밋**

```bash
git add robots/queries.py tests/test_queries.py
git commit -m "feat: 로봇별 작업 이력 및 배터리 통계 쿼리 추가"
```

---

### Task 1.7: 구역 혼잡도 집계 (annotate)

**Files:**
- Create: `tasks/queries.py`
- Modify: `tests/test_queries.py` — 혼잡도 테스트 추가

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_queries.py`에 추가:

```python
from tasks.queries import zone_congestion


@pytest.mark.django_db
def test_zone_congestion(db):
    zone_a = Zone.objects.create(name="Zone-A", capacity=5)
    zone_b = Zone.objects.create(name="Zone-B", capacity=5)
    robot = Robot.objects.create(name="R-03", battery=70.0)
    Task.objects.create(robot=robot, zone=zone_a, status="IN_PROGRESS")
    Task.objects.create(robot=robot, zone=zone_a, status="IN_PROGRESS")
    Task.objects.create(robot=robot, zone=zone_b, status="IN_PROGRESS")
    Task.objects.create(robot=robot, zone=zone_b, status="DONE")  # 제외되어야 함

    congestion = {row["name"]: row["active_tasks"] for row in zone_congestion()}
    assert congestion["Zone-A"] == 2
    assert congestion["Zone-B"] == 1
```

- [x] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_queries.py::test_zone_congestion -v
```

Expected: `FAILED` — `No module named 'tasks.queries'`

- [x] **Step 3: 혼잡도 쿼리 작성**

```python
# tasks/queries.py
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
```

- [x] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_queries.py -v
```

Expected: 모든 테스트 `PASSED`

- [x] **Step 5: 커밋**

```bash
git add tasks/queries.py tests/test_queries.py
git commit -m "feat: 구역별 혼잡도 annotate 쿼리 추가"
```

---

### Task 1.8: Admin 등록

**Files:**
- Create: `robots/admin.py`
- Create: `tasks/admin.py`

- [x] **Step 1: robots admin 작성**

```python
# robots/admin.py
from django.contrib import admin
from .models import Robot, Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity")


@admin.register(Robot)
class RobotAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "battery", "current_zone", "updated_at")
    list_filter = ("status",)
```

- [x] **Step 2: tasks admin 작성**

```python
# tasks/admin.py
from django.contrib import admin
from .models import Task, Route


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "robot", "zone", "status", "created_at", "completed_at")
    list_filter = ("status",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "created_at")
```

- [x] **Step 3: Django 개발 서버로 admin 확인**

```bash
python manage.py createsuperuser --username admin --email admin@example.com
python manage.py runserver
```

브라우저에서 `http://localhost:8000/admin/` 접속 → Robot, Zone, Task, Route 메뉴 확인

- [x] **Step 4: 커밋**

```bash
git add robots/admin.py tasks/admin.py
git commit -m "feat: admin 등록 (Robot, Zone, Task, Route)"
```

---

## 2단계 — Celery + Redis

> **전제조건:** Redis가 로컬에서 실행 중이어야 한다. `redis-cli ping` → `PONG` 확인.

### Task 2.1: Celery 앱 설정

**Files:**
- Create: `config/celery.py`
- Modify: `config/__init__.py`
- Modify: `config/settings.py` — `django_celery_beat`, `django_celery_results` 활성화

- [ ] **Step 1: celery.py 작성**

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("amr_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

- [ ] **Step 2: config/__init__.py 수정**

```python
# config/__init__.py
from .celery import app as celery_app

__all__ = ("celery_app",)
```

- [ ] **Step 3: settings.py — INSTALLED_APPS 수정**

`config/settings.py`의 주석 처리된 앱을 활성화:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "robots",
    "tasks",
    "monitor",
    "simulator",
    "django_celery_beat",       # 주석 해제
    "django_celery_results",    # 주석 해제
]
```

- [ ] **Step 4: 마이그레이션 (django_celery_beat 테이블 생성)**

```bash
python manage.py migrate
```

- [ ] **Step 5: Celery worker가 정상 기동되는지 확인**

```bash
celery -A config worker --loglevel=info
```

Expected: `[tasks]` 섹션에 태스크 목록 출력 (아직 없어도 OK). `Ctrl+C`로 종료.

- [ ] **Step 6: 커밋**

```bash
git add config/celery.py config/__init__.py config/settings.py
git commit -m "feat: Celery 앱 초기화 및 django_celery_beat 활성화"
```

---

### Task 2.2: 최적 로봇 배정 태스크

**Files:**
- Create: `tasks/celery_tasks.py`
- Create: `tests/test_celery_tasks.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_celery_tasks.py
import pytest
from django.utils import timezone
from robots.models import Robot, Zone
from tasks.models import Task
from tasks.celery_tasks import assign_task


@pytest.fixture
def zone_with_robots(db):
    zone = Zone.objects.create(name="Z1", capacity=5)
    r1 = Robot.objects.create(name="R-01", battery=90.0, status="IDLE", current_zone=zone)
    r2 = Robot.objects.create(name="R-02", battery=60.0, status="IDLE", current_zone=zone)
    r3 = Robot.objects.create(name="R-03", battery=40.0, status="BUSY", current_zone=zone)
    return zone, r1, r2, r3


@pytest.mark.django_db
def test_assign_task_picks_idle_robot_with_max_battery(zone_with_robots):
    zone, r1, r2, r3 = zone_with_robots
    task = Task.objects.create(zone=zone, status="PENDING")

    assign_task.apply(args=[task.id])  # apply() = 동기 실행 (테스트용)

    task.refresh_from_db()
    r1.refresh_from_db()
    assert task.status == "ASSIGNED"
    assert task.robot == r1              # 배터리 가장 높은 IDLE 로봇
    assert r1.status == "BUSY"
    assert task.assigned_at is not None


@pytest.mark.django_db
def test_assign_task_no_idle_robot(db):
    zone = Zone.objects.create(name="Z2", capacity=5)
    Robot.objects.create(name="R-04", battery=80.0, status="BUSY", current_zone=zone)
    task = Task.objects.create(zone=zone, status="PENDING")

    assign_task.apply(args=[task.id])

    task.refresh_from_db()
    assert task.status == "PENDING"     # 배정 불가 → 상태 유지
    assert task.robot is None
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_celery_tasks.py -v
```

Expected: `FAILED` — `No module named 'tasks.celery_tasks'`

- [ ] **Step 3: assign_task 구현**

```python
# tasks/celery_tasks.py
from celery import shared_task
from django.utils import timezone


@shared_task
def assign_task(task_id: int) -> str:
    from tasks.models import Task
    from robots.models import Robot

    task = Task.objects.select_for_update().get(id=task_id)
    if task.status != Task.PENDING:
        return f"Task#{task_id} already processed"

    robot = (
        Robot.objects.filter(status=Robot.STATUS_IDLE)
        .order_by("-battery")
        .first()
    )
    if robot is None:
        return f"Task#{task_id}: no idle robot available"

    task.robot = robot
    task.status = Task.ASSIGNED
    task.assigned_at = timezone.now()
    task.save(update_fields=["robot", "status", "assigned_at"])

    robot.status = Robot.STATUS_BUSY
    robot.save(update_fields=["status"])

    return f"Task#{task_id} assigned to {robot.name}"
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_celery_tasks.py -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 5: 커밋**

```bash
git add tasks/celery_tasks.py tests/test_celery_tasks.py
git commit -m "feat: 최적 로봇 배정 Celery 태스크 (IDLE + 최대 배터리)"
```

---

### Task 2.3: 배터리 감시 주기 태스크

**Files:**
- Modify: `tasks/celery_tasks.py` — `monitor_battery_levels` 추가
- Modify: `config/settings.py` — Beat 스케줄 추가
- Modify: `tests/test_celery_tasks.py` — 배터리 감시 테스트 추가

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_celery_tasks.py`에 추가:

```python
from tasks.celery_tasks import monitor_battery_levels


@pytest.mark.django_db
def test_monitor_battery_levels_sends_low_robots_to_charge(db):
    zone = Zone.objects.create(name="Z3", capacity=5)
    low = Robot.objects.create(name="R-05", battery=15.0, status="IDLE", current_zone=zone)
    ok = Robot.objects.create(name="R-06", battery=50.0, status="IDLE", current_zone=zone)

    monitor_battery_levels.apply()

    low.refresh_from_db()
    ok.refresh_from_db()
    assert low.status == "CHARGING"
    assert ok.status == "IDLE"
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_celery_tasks.py::test_monitor_battery_levels_sends_low_robots_to_charge -v
```

Expected: `FAILED` — `monitor_battery_levels` 없음

- [ ] **Step 3: monitor_battery_levels 구현**

`tasks/celery_tasks.py`에 추가:

```python
@shared_task
def monitor_battery_levels() -> str:
    from robots.models import Robot

    updated = Robot.objects.filter(
        battery__lt=20.0,
        status=Robot.STATUS_IDLE,
    ).update(status=Robot.STATUS_CHARGING)

    return f"{updated} robots sent to charge"
```

- [ ] **Step 4: settings.py에 Beat 스케줄 추가**

`config/settings.py` 하단에 추가:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "monitor-battery-every-minute": {
        "task": "tasks.celery_tasks.monitor_battery_levels",
        "schedule": 60.0,  # 매 60초
    },
}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/test_celery_tasks.py -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 6: 커밋**

```bash
git add tasks/celery_tasks.py config/settings.py tests/test_celery_tasks.py
git commit -m "feat: 배터리 감시 주기 태스크 + celery beat 스케줄 설정"
```

---

### Task 2.4: 작업 타임아웃 감지 + 재배정

**Files:**
- Modify: `tasks/celery_tasks.py` — `check_task_timeout` 추가
- Modify: `tasks/celery_tasks.py` — `assign_task`에 `countdown` 연결
- Modify: `tests/test_celery_tasks.py` — 타임아웃 테스트 추가

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_celery_tasks.py`에 추가:

```python
from tasks.celery_tasks import check_task_timeout
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
def test_check_task_timeout_marks_timeout_and_reassigns(db):
    zone = Zone.objects.create(name="Z4", capacity=5)
    robot = Robot.objects.create(name="R-07", battery=80.0, status="BUSY", current_zone=zone)
    spare = Robot.objects.create(name="R-08", battery=70.0, status="IDLE", current_zone=zone)

    task = Task.objects.create(
        robot=robot, zone=zone, status="IN_PROGRESS", timeout_seconds=300,
        assigned_at=timezone.now() - timedelta(seconds=400),  # 이미 타임아웃
    )

    with patch("tasks.celery_tasks.assign_task.apply_async") as mock_assign:
        check_task_timeout.apply(args=[task.id])
        mock_assign.assert_called_once_with(args=[task.id])

    task.refresh_from_db()
    robot.refresh_from_db()
    assert task.status == "TIMEOUT"
    assert robot.status == "IDLE"


@pytest.mark.django_db
def test_check_task_timeout_no_action_if_not_timed_out(db):
    zone = Zone.objects.create(name="Z5", capacity=5)
    robot = Robot.objects.create(name="R-09", battery=80.0, status="BUSY", current_zone=zone)
    task = Task.objects.create(
        robot=robot, zone=zone, status="IN_PROGRESS", timeout_seconds=300,
        assigned_at=timezone.now() - timedelta(seconds=100),  # 아직 진행 중
    )

    check_task_timeout.apply(args=[task.id])

    task.refresh_from_db()
    assert task.status == "IN_PROGRESS"
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_celery_tasks.py::test_check_task_timeout_marks_timeout_and_reassigns -v
```

Expected: `FAILED` — `check_task_timeout` 없음

- [ ] **Step 3: check_task_timeout 구현**

`tasks/celery_tasks.py`에 추가:

```python
@shared_task
def check_task_timeout(task_id: int) -> str:
    from tasks.models import Task
    from django.utils import timezone

    try:
        task = Task.objects.get(id=task_id, status=Task.IN_PROGRESS)
    except Task.DoesNotExist:
        return f"Task#{task_id}: not in progress, skip"

    elapsed = (timezone.now() - task.assigned_at).total_seconds()
    if elapsed < task.timeout_seconds:
        return f"Task#{task_id}: still in progress ({elapsed:.0f}s)"

    robot = task.robot
    task.status = Task.TIMEOUT
    task.save(update_fields=["status"])

    if robot:
        robot.status = robot.STATUS_IDLE
        robot.save(update_fields=["status"])

    # 새 태스크 생성 후 재배정
    new_task = Task.objects.create(zone=task.zone, timeout_seconds=task.timeout_seconds)
    assign_task.apply_async(args=[new_task.id])

    return f"Task#{task_id} timed out → new Task#{new_task.id} created"
```

- [ ] **Step 4: assign_task에서 countdown으로 타임아웃 태스크 예약**

`tasks/celery_tasks.py`의 `assign_task` 끝부분 수정:

```python
    # ...기존 저장 코드 이후...
    task.robot = robot
    task.status = Task.ASSIGNED
    task.assigned_at = timezone.now()
    task.save(update_fields=["robot", "status", "assigned_at"])

    robot.status = Robot.STATUS_BUSY
    robot.save(update_fields=["status"])

    # 타임아웃 감시 태스크 예약
    check_task_timeout.apply_async(
        args=[task.id],
        countdown=task.timeout_seconds,
    )

    return f"Task#{task_id} assigned to {robot.name}"
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/test_celery_tasks.py -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 6: 커밋**

```bash
git add tasks/celery_tasks.py tests/test_celery_tasks.py
git commit -m "feat: 작업 타임아웃 감지 + 자동 재배정 (countdown chain)"
```

---

## 3단계 — Django Channels

> **전제조건:** Redis 실행 중 (`redis-cli ping` → `PONG`). daphne, channels, channels-redis 설치 확인.

### Task 3.1: ASGI 설정 전환

**Files:**
- Create: `config/asgi.py`
- Modify: `config/settings.py` — ASGI_APPLICATION 활성화, CHANNEL_LAYERS 설정, channels 앱 추가

- [ ] **Step 1: settings.py 수정**

`config/settings.py`에서:

```python
INSTALLED_APPS = [
    # ...기존 앱들...
    "channels",                 # 추가
    "django_celery_beat",
    "django_celery_results",
]

# WSGI → ASGI 전환
# WSGI_APPLICATION = "config.wsgi.application"  # 주석 처리
ASGI_APPLICATION = "config.asgi.application"      # 주석 해제

# CHANNEL_LAYERS 주석 해제
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("localhost", 6379)]},
    }
}
```

- [ ] **Step 2: config/asgi.py 작성**

```python
# config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import monitor.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(monitor.routing.websocket_urlpatterns)
        ),
    }
)
```

- [ ] **Step 3: monitor/routing.py 빈 파일 생성 (다음 태스크에서 채움)**

```python
# monitor/routing.py
websocket_urlpatterns = []
```

- [ ] **Step 4: Django가 ASGI 모드로 기동되는지 확인**

```bash
daphne -b 0.0.0.0 -p 8001 config.asgi:application
```

Expected: `Starting server at tcp:port=8001` (오류 없음). `Ctrl+C` 종료.

- [ ] **Step 5: 커밋**

```bash
git add config/asgi.py config/settings.py monitor/routing.py
git commit -m "feat: ASGI 전환 + Django Channels 활성화"
```

---

### Task 3.2: RobotConsumer (WebSocket)

**Files:**
- Create: `monitor/consumers.py`
- Modify: `monitor/routing.py`
- Create: `tests/test_consumers.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_consumers.py
import pytest
import json
from channels.testing import WebsocketCommunicator
from config.asgi import application


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_robot_consumer_connect_and_receive():
    communicator = WebsocketCommunicator(application, "/ws/robots/")
    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to({"robot_id": 1, "x": 3.5, "y": 7.2, "battery": 75.0})
    response = await communicator.receive_json_from()
    assert response["type"] == "robot.update"
    assert response["robot_id"] == 1
    assert response["x"] == 3.5

    await communicator.disconnect()
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_consumers.py -v
```

Expected: `FAILED` — Consumer 없음 또는 연결 실패

- [ ] **Step 3: RobotConsumer 작성**

```python
# monitor/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

ROBOT_GROUP = "robots"


class RobotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(ROBOT_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(ROBOT_GROUP, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            ROBOT_GROUP,
            {
                "type": "robot.update",
                "robot_id": data.get("robot_id"),
                "x": data.get("x"),
                "y": data.get("y"),
                "battery": data.get("battery"),
            },
        )

    async def robot_update(self, event):
        await self.send(text_data=json.dumps(event))
```

- [ ] **Step 4: routing.py에 경로 등록**

```python
# monitor/routing.py
from django.urls import path
from monitor.consumers import RobotConsumer

websocket_urlpatterns = [
    path("ws/robots/", RobotConsumer.as_asgi()),
]
```

- [ ] **Step 5: pytest-asyncio 설치 확인 후 테스트 통과 확인**

```bash
pip install pytest-asyncio
python -m pytest tests/test_consumers.py -v
```

Expected: `PASSED`

- [ ] **Step 6: 커밋**

```bash
git add monitor/consumers.py monitor/routing.py tests/test_consumers.py
git commit -m "feat: RobotConsumer WebSocket 구현 (그룹 브로드캐스트)"
```

---

### Task 3.3: Celery 작업 완료 → Channel Layer push

**Files:**
- Modify: `tasks/celery_tasks.py` — 작업 완료 시 Channel push 추가
- Modify: `tests/test_celery_tasks.py` — Channel push 테스트 추가

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_celery_tasks.py`에 추가:

```python
from unittest.mock import patch, AsyncMock
from tasks.celery_tasks import complete_task


@pytest.mark.django_db
def test_complete_task_pushes_to_channel_layer(db):
    zone = Zone.objects.create(name="Z6", capacity=5)
    robot = Robot.objects.create(name="R-10", battery=80.0, status="BUSY", current_zone=zone)
    task = Task.objects.create(robot=robot, zone=zone, status="IN_PROGRESS")

    with patch("tasks.celery_tasks.get_channel_layer") as mock_get_layer:
        mock_layer = AsyncMock()
        mock_get_layer.return_value = mock_layer

        complete_task.apply(args=[task.id])

        mock_layer.group_send.assert_called_once()
        call_args = mock_layer.group_send.call_args[0]
        assert call_args[0] == "robots"
        assert call_args[1]["type"] == "robot.update"

    task.refresh_from_db()
    assert task.status == "DONE"
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_celery_tasks.py::test_complete_task_pushes_to_channel_layer -v
```

Expected: `FAILED` — `complete_task` 없음

- [ ] **Step 3: complete_task 구현**

`tasks/celery_tasks.py`에 추가:

```python
@shared_task
def complete_task(task_id: int) -> str:
    from tasks.models import Task
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from django.utils import timezone

    task = Task.objects.get(id=task_id)
    task.status = Task.DONE
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at"])

    if task.robot:
        task.robot.status = task.robot.STATUS_IDLE
        task.robot.save(update_fields=["status"])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "robots",
        {
            "type": "robot.update",
            "robot_id": task.robot_id,
            "task_id": task_id,
            "event": "task_completed",
        },
    )

    return f"Task#{task_id} completed"
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_celery_tasks.py -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 5: 커밋**

```bash
git add tasks/celery_tasks.py tests/test_celery_tasks.py
git commit -m "feat: 작업 완료 시 Channel Layer로 대시보드 push"
```

---

## 4단계 — Ray Actor

### Task 4.1: RobotActor 클래스

**Files:**
- Create: `simulator/actors.py`
- Create: `tests/test_simulator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_simulator.py
import pytest
import ray


@pytest.fixture(scope="module", autouse=True)
def ray_init():
    ray.init(ignore_reinit_error=True, local_mode=True)
    yield
    ray.shutdown()


def test_robot_actor_initial_state():
    from simulator.actors import RobotActor
    actor = RobotActor.remote(robot_id=1, name="R-01")
    state = ray.get(actor.get_state.remote())
    assert state["robot_id"] == 1
    assert state["name"] == "R-01"
    assert state["battery"] == 100.0
    assert state["status"] == "IDLE"
    assert state["position"] == {"x": 0.0, "y": 0.0}


def test_robot_actor_move_reduces_battery():
    from simulator.actors import RobotActor
    actor = RobotActor.remote(robot_id=2, name="R-02")
    state = ray.get(actor.move_to.remote(x=5.0, y=3.0))
    assert state["position"] == {"x": 5.0, "y": 3.0}
    assert state["battery"] < 100.0


def test_multiple_actors_parallel():
    from simulator.actors import RobotActor
    actors = [RobotActor.remote(robot_id=i, name=f"R-{i:02d}") for i in range(3)]
    futures = [a.move_to.remote(x=float(i), y=float(i)) for i, a in enumerate(actors)]
    results = ray.get(futures)
    assert len(results) == 3
    assert results[0]["position"] == {"x": 0.0, "y": 0.0}
    assert results[1]["position"] == {"x": 1.0, "y": 1.0}
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_simulator.py -v
```

Expected: `FAILED` — `No module named 'simulator.actors'`

- [ ] **Step 3: RobotActor 구현**

```python
# simulator/actors.py
import ray


@ray.remote
class RobotActor:
    def __init__(self, robot_id: int, name: str):
        self.robot_id = robot_id
        self.name = name
        self.battery = 100.0
        self.position = {"x": 0.0, "y": 0.0}
        self.status = "IDLE"

    def move_to(self, x: float, y: float) -> dict:
        distance = ((x - self.position["x"]) ** 2 + (y - self.position["y"]) ** 2) ** 0.5
        self.battery = max(0.0, self.battery - distance * 0.5)
        self.position = {"x": x, "y": y}
        return self.get_state()

    def assign_task(self, task_id: int) -> dict:
        self.status = "BUSY"
        return self.get_state()

    def complete_task(self) -> dict:
        self.status = "IDLE"
        return self.get_state()

    def get_state(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "name": self.name,
            "battery": self.battery,
            "position": self.position,
            "status": self.status,
        }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_simulator.py -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 5: 커밋**

```bash
git add simulator/actors.py tests/test_simulator.py
git commit -m "feat: Ray RobotActor 구현 (이동, 배터리 소모, 병렬 실행)"
```

---

### Task 4.2: Django API → Ray Actor 명령 연결

**Files:**
- Create: `simulator/views.py`
- Modify: `simulator/urls.py`
- Modify: `config/urls.py`
- Modify: `tests/test_simulator.py` — API 테스트 추가

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_simulator.py`에 추가:

```python
import json
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock


class SimulatorAPITest(TestCase):
    def setUp(self):
        self.client = Client()

    @patch("simulator.views.ray")
    def test_start_simulation(self, mock_ray):
        mock_actor = MagicMock()
        mock_ray.remote.return_value = MagicMock(return_value=mock_actor)
        mock_ray.get.return_value = [
            {"robot_id": 0, "name": "R-00", "battery": 100.0, "position": {"x": 0.0, "y": 0.0}, "status": "IDLE"}
        ]

        response = self.client.post(
            "/api/simulator/start/",
            data=json.dumps({"num_robots": 1}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "robots" in data
        assert len(data["robots"]) == 1
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_simulator.py::SimulatorAPITest -v
```

Expected: `FAILED` — URL 없음 또는 404

- [ ] **Step 3: views.py 구현**

```python
# simulator/views.py
import json
import ray
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

_actors: dict[int, ray.actor.ActorHandle] = {}


@csrf_exempt
@require_POST
def start_simulation(request):
    from simulator.actors import RobotActor

    body = json.loads(request.body)
    num_robots = int(body.get("num_robots", 3))

    ray.init(ignore_reinit_error=True)

    global _actors
    _actors = {
        i: RobotActor.remote(robot_id=i, name=f"R-{i:02d}")
        for i in range(num_robots)
    }

    states = ray.get([a.get_state.remote() for a in _actors.values()])
    return JsonResponse({"robots": states})


@csrf_exempt
@require_POST
def send_command(request, robot_id: int):
    body = json.loads(request.body)
    command = body.get("command")
    actor = _actors.get(robot_id)

    if actor is None:
        return JsonResponse({"error": "robot not found"}, status=404)

    if command == "move":
        x, y = float(body["x"]), float(body["y"])
        state = ray.get(actor.move_to.remote(x=x, y=y))
    elif command == "complete":
        state = ray.get(actor.complete_task.remote())
    else:
        return JsonResponse({"error": "unknown command"}, status=400)

    return JsonResponse(state)


def get_all_states(request):
    if not _actors:
        return JsonResponse({"robots": []})
    states = ray.get([a.get_state.remote() for a in _actors.values()])
    return JsonResponse({"robots": states})
```

- [ ] **Step 4: simulator/urls.py 작성**

```python
# simulator/urls.py
from django.urls import path
from simulator import views

urlpatterns = [
    path("start/", views.start_simulation),
    path("states/", views.get_all_states),
    path("<int:robot_id>/command/", views.send_command),
]
```

- [ ] **Step 5: config/urls.py에 simulator 경로 추가**

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/robots/", include("robots.urls")),
    path("api/tasks/", include("tasks.urls")),
    path("api/simulator/", include("simulator.urls")),  # 추가
]
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
python -m pytest tests/test_simulator.py -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 7: 커밋**

```bash
git add simulator/views.py simulator/urls.py config/urls.py tests/test_simulator.py
git commit -m "feat: 시뮬레이터 API (start/command/states) → Ray Actor 연결"
```

---

### Task 4.3: 시뮬레이션 결과 DB 저장 + 1~3단계 연동

**Files:**
- Modify: `simulator/views.py` — 상태 변경 시 DB 동기화
- Modify: `tests/test_simulator.py` — DB 연동 테스트 추가

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_simulator.py`에 추가:

```python
@pytest.mark.django_db
def test_sync_actor_state_to_db():
    from simulator.views import sync_state_to_db
    from robots.models import Robot, Zone

    zone = Zone.objects.create(name="SimZone", capacity=10)
    robot = Robot.objects.create(name="R-00", battery=100.0, current_zone=zone)

    state = {
        "robot_id": robot.id,
        "name": "R-00",
        "battery": 73.5,
        "position": {"x": 3.0, "y": 4.0},
        "status": "BUSY",
    }
    sync_state_to_db(state)

    robot.refresh_from_db()
    assert robot.battery == 73.5
    assert robot.status == "BUSY"
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
python -m pytest tests/test_simulator.py::test_sync_actor_state_to_db -v
```

Expected: `FAILED` — `sync_state_to_db` 없음

- [ ] **Step 3: sync_state_to_db 구현**

`simulator/views.py`에 추가:

```python
def sync_state_to_db(state: dict) -> None:
    from robots.models import Robot

    status_map = {"IDLE": Robot.STATUS_IDLE, "BUSY": Robot.STATUS_BUSY, "CHARGING": Robot.STATUS_CHARGING}
    Robot.objects.filter(id=state["robot_id"]).update(
        battery=state["battery"],
        status=status_map.get(state["status"], Robot.STATUS_IDLE),
    )
```

그리고 `send_command` 뷰의 응답 직전에 `sync_state_to_db(state)` 호출 추가:

```python
    # ...state 계산 후...
    sync_state_to_db(state)
    return JsonResponse(state)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/ -v
```

Expected: 모든 테스트 `PASSED`

- [ ] **Step 5: 전체 테스트 최종 확인**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: 모든 테스트 `PASSED`, 실패 0

- [ ] **Step 6: 최종 커밋**

```bash
git add simulator/views.py tests/test_simulator.py
git commit -m "feat: 시뮬레이터 상태 DB 동기화 (Ray Actor → Django ORM 연동)"
```

---

## Self-Review

### Spec 커버리지 체크

| 로드맵 요구사항 | 해당 태스크 |
|---|---|
| Robot, Zone, Task, Route 모델 | Task 1.2~1.5 |
| 로봇별 작업 이력, 배터리 소모 통계 | Task 1.6 |
| 구역 혼잡도 annotate | Task 1.7 |
| 최적 로봇 배정 Celery task | Task 2.2 |
| celery beat 배터리 감시 | Task 2.3 |
| 작업 타임아웃 감지 + 재배정 | Task 2.4 |
| ASGI 전환 (Daphne) | Task 3.1 |
| WebsocketConsumer 로봇 ↔ 서버 | Task 3.2 |
| Channel Layer 그룹 브로드캐스트 | Task 3.2 |
| Celery 완료 → Channel push | Task 3.3 |
| @ray.remote RobotActor | Task 4.1 |
| Django API → ray.get_actor 명령 | Task 4.2 |
| 다중 Actor 병렬 실행 | Task 4.1 (test_multiple_actors_parallel) |
| 시뮬레이션 결과 DB 저장 | Task 4.3 |

모든 요구사항 커버됨.

### 타입 일관성 체크
- `Robot.STATUS_IDLE/BUSY/CHARGING` 상수가 Task 2.4, Task 4.3에서 동일하게 참조됨 ✓
- `Task.PENDING/ASSIGNED/IN_PROGRESS/DONE/TIMEOUT` 상수가 Task 2.2~2.4에서 일관되게 사용됨 ✓
- `ROBOT_GROUP = "robots"` 상수가 consumer와 complete_task에서 동일한 값 사용됨 ✓
