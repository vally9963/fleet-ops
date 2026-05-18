# fleet-ops 로드맵

> **목표**: Django ORM → Celery → Channels → Ray Actor 순으로 하나의 프로젝트에 단계별로 쌓기

---

## 프로젝트 구조

```
amr_platform/
├── config/
│   ├── settings.py
│   ├── celery.py
│   └── asgi.py
├── robots/          # 1단계: 모델
├── tasks/           # 2단계: Celery
├── monitor/         # 3단계: Channels
├── simulator/       # 4단계: Ray
└── requirements/
    ├── base.txt
    └── dev.txt
```

---

## 1단계 — Django ORM

**주제**: 로봇 · 맵 · 작업 데이터 모델링

| 항목 | 내용 |
|------|------|
| 모델 설계 | `Robot`, `Zone`, `Task`, `Route` |
| 통계 쿼리 | 로봇별 작업 이력, 배터리 소모 통계 |
| 혼잡도 집계 | 특정 구역 혼잡도 (`annotate`) |

### 핵심 포인트
- `Robot` ↔ `Zone` FK 관계 (현재 위치)
- `Task` 상태 머신: `PENDING` → `ASSIGNED` → `IN_PROGRESS` → `DONE` / `TIMEOUT`
- `Route`에 waypoints JSON 저장
- `annotate`로 구역별 동시 진행 작업 수 집계

---

## 2단계 — Celery + Redis

**주제**: 비동기 작업 배정 + 주기 처리

| 항목 | 내용 |
|------|------|
| 작업 배정 | 작업 요청 시 최적 로봇 배정을 Celery task로 처리 |
| 주기 처리 | `celery beat`으로 배터리 낮은 로봇 자동 복귀 명령 |
| 예외 처리 | 작업 타임아웃 감지 및 재배정 |

### 핵심 포인트
- Redis를 브로커 + 결과 백엔드로 사용
- `@shared_task`로 최적 로봇 선택 로직 비동기화
- `celery beat` 주기 스케줄로 배터리 감시
- `task.apply_async(countdown=timeout)` + 타임아웃 시 재배정 체인

---

## 3단계 — Django Channels

**주제**: 실시간 로봇 위치 · 상태 모니터링

| 항목 | 내용 |
|------|------|
| 위치 전송 | 로봇이 WebSocket으로 위치/상태 전송 |
| 실시간 반영 | 관제 대시보드에 실시간 반영 |
| 즉시 알림 | 작업 완료 시 즉시 알림 |

### 핵심 포인트
- ASGI 서버 전환 (Daphne / Uvicorn)
- `WebsocketConsumer`로 로봇 ↔ 서버 연결
- Channel Layer(Redis)로 그룹 브로드캐스트
- Celery task 완료 시 Channel Layer로 대시보드 push

---

## 4단계 — Ray Actor

**주제**: 다중 로봇 시뮬레이터

| 항목 | 내용 |
|------|------|
| Actor 설계 | 각 로봇을 Ray Actor로 구현 (상태: 위치, 배터리, 현재 작업) |
| 명령 연결 | Django API로 명령 전송 → Ray로 실행 |
| 시뮬레이션 | 실제 로봇 없이 다중 로봇 동시 시뮬레이션 |

### 핵심 포인트
- `@ray.remote` 클래스로 로봇 상태 캡슐화
- Django view에서 `ray.get_actor(name)` 으로 명령 전달
- 여러 Actor 동시 실행 → `ray.get([...])` 병렬 수집
- 시뮬레이션 결과를 DB에 저장해 1~3단계 데이터와 연동

---

## 단계별 의존성

```
1단계  Django, PostgreSQL
2단계  + Celery, Redis
3단계  + channels, channels-redis, daphne
4단계  + ray
```

---

## 참고 링크

- [Django ORM - annotate/aggregate](https://docs.djangoproject.com/en/stable/topics/db/aggregation/)
- [Celery + Django](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [Django Channels](https://channels.readthedocs.io/en/stable/)
- [Ray Actors](https://docs.ray.io/en/latest/ray-core/actors.html)
