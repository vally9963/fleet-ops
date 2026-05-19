-- fleet-ops DDL (PostgreSQL)
-- 1단계: Robot, Zone, Task, Route

CREATE TABLE zone (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    zone_type   VARCHAR(20)  NOT NULL CHECK (zone_type IN ('STORAGE','CHARGING','WORK_AREA','STAGING')),
    capacity    INTEGER      NOT NULL DEFAULT 10 CHECK (capacity >= 0),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE robot (
    id           BIGSERIAL    PRIMARY KEY,
    name         VARCHAR(100) NOT NULL UNIQUE,
    status       VARCHAR(20)  NOT NULL DEFAULT 'IDLE' CHECK (status IN ('IDLE','BUSY','CHARGING','ERROR')),
    battery_level NUMERIC(5,2) NOT NULL DEFAULT 100.00 CHECK (battery_level BETWEEN 0 AND 100),
    current_zone_id BIGINT    REFERENCES zone(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE task (
    id            BIGSERIAL   PRIMARY KEY,
    robot_id      BIGINT      REFERENCES robot(id) ON DELETE SET NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                              CHECK (status IN ('PENDING','ASSIGNED','IN_PROGRESS','DONE','TIMEOUT')),
    from_zone_id  BIGINT      NOT NULL REFERENCES zone(id) ON DELETE RESTRICT,
    to_zone_id    BIGINT      NOT NULL REFERENCES zone(id) ON DELETE RESTRICT,
    priority      SMALLINT    NOT NULL DEFAULT 5 CHECK (priority >= 0),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE TABLE route (
    id         BIGSERIAL   PRIMARY KEY,
    task_id    BIGINT      NOT NULL UNIQUE REFERENCES task(id) ON DELETE CASCADE,
    waypoints  JSONB       NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_robot_status        ON robot(status);
CREATE INDEX idx_robot_zone          ON robot(current_zone_id);
CREATE INDEX idx_task_robot          ON task(robot_id);
CREATE INDEX idx_task_status         ON task(status);
CREATE INDEX idx_task_priority_time  ON task(priority DESC, created_at ASC);
CREATE INDEX idx_route_waypoints     ON route USING GIN(waypoints);
