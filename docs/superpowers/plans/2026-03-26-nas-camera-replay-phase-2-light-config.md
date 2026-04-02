# NAS 摄像头回放系统第二阶段（轻配置版）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有单摄像头本地回放系统上，增加基于 `.env` 的多摄像头支持与单密码登录，并保持前后端交互尽量简单。

**Architecture:** 后端继续使用 FastAPI + SQLite，但把所有索引与查询维度从“仅按日期”扩展为“按 `camera_no + day`”。摄像头来源完全由 `VIDEO_ROOT_n` 配置驱动；认证层不引入用户表，而是使用 `APP_PASSWORD` + HttpOnly 会话级 Cookie 保护现有业务接口。前端保留单页回放结构，只在顶层增加登录门禁、通道切换和空状态处理。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, pytest, React 19, TypeScript, Vite, Vitest, Testing Library

---

## 预期目录与职责

### 后端文件

- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/db.py`
- Create: `backend/app/core/auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/video_file.py`
- Modify: `backend/app/models/timeline_segment.py`
- Modify: `backend/app/models/day_summary.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/camera.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/cameras.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/api/days.py`
- Modify: `backend/app/api/timeline.py`
- Modify: `backend/app/api/locate.py`
- Modify: `backend/app/api/index_jobs.py`
- Modify: `backend/app/api/videos.py`
- Modify: `backend/app/tasks/index_videos.py`
- Modify: `backend/app/tasks/rebuild_day.py`
- Modify: `backend/app/tasks/index_scheduler.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_config.py`
- Modify: `backend/tests/test_db_models.py`
- Modify: `backend/tests/test_index_tasks.py`
- Modify: `backend/tests/test_index_scheduler.py`
- Modify: `backend/tests/test_days_api.py`
- Modify: `backend/tests/test_timeline_api.py`
- Modify: `backend/tests/test_locate_api.py`
- Modify: `backend/tests/test_index_rebuild_api.py`
- Modify: `backend/tests/test_video_stream_api.py`
- Create: `backend/tests/test_cameras_api.py`
- Create: `backend/tests/test_auth_api.py`

### 前端文件

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/replay.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/cameras.ts`
- Modify: `frontend/src/hooks/useDays.ts`
- Modify: `frontend/src/hooks/useTimeline.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/hooks/useCameras.ts`
- Create: `frontend/src/components/CameraPicker.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/pages/ReplayPage.tsx`
- Modify: `frontend/tests/ReplayPage.test.tsx`
- Modify: `frontend/src/api/replay.test.ts`
- Create: `frontend/tests/App.test.tsx`
- Create: `frontend/tests/LoginPage.test.tsx`

### 文档与配置文件

- Modify: `backend/.env.example`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`

## 实施约束

- 只识别 `.env` 中的 `VIDEO_ROOT_数字`
- `camera_no` 是所有索引、查询和前端切换的唯一通道标识
- 目录重复或父子嵌套时必须启动失败
- 第二阶段不自动迁移旧版 `replay.db`
- 发现旧版数据库结构不兼容时必须显式报错，并提示删除 `replay.db`
- 未登录访问业务接口统一返回 `401`
- `/api/cameras` 只返回当前配置出的通道，并按 `camera_no` 升序排列
- 单通道时不显示通道切换器
- 空通道必须显示空状态，不得继续请求时间轴

### Task 1: 扩展配置层，支持多通道与单密码

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/tests/test_config.py`
- Modify: `backend/tests/test_index_scheduler.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: 先写配置解析失败测试**

```python
def test_settings_load_multiple_video_roots_and_password(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "VIDEO_ROOT_1=/tmp/cam1",
                "VIDEO_ROOT_3=/tmp/cam3",
                "APP_PASSWORD=secret-pass",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.app_password == "secret-pass"
    assert [item.camera_no for item in settings.camera_roots] == [1, 3]
```

- [ ] **Step 2: 再写目录冲突校验测试**

```python
def test_settings_reject_overlapping_video_roots(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                f"VIDEO_ROOT_1={tmp_path / 'videos'}",
                f"VIDEO_ROOT_2={tmp_path / 'videos' / 'cam2'}",
                "APP_PASSWORD=secret-pass",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError):
        Settings()
```

- [ ] **Step 3: 补一个空通道配置失败测试**

```python
def test_settings_require_at_least_one_video_root(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("APP_PASSWORD=secret-pass", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="VIDEO_ROOT"):
        Settings()
```

- [ ] **Step 4: 补一个缺少密码的失败测试**

```python
def test_settings_require_app_password(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("VIDEO_ROOT_1=/tmp/cam1", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="APP_PASSWORD"):
        Settings()
```

- [ ] **Step 5: 更新直接构造 `Settings()` 的旧测试**

```python
monkeypatch.setenv("VIDEO_ROOT_1", "/tmp/cam1")
assert Settings(app_password="secret-pass").index_scheduler_time == time(hour=3, minute=0)
```

- [ ] **Step 6: 运行测试确认失败**

Run: `cd backend && pytest tests/test_config.py tests/test_index_scheduler.py -q`
Expected: FAIL，提示 `Settings` 尚未暴露 `camera_roots` / `app_password` 或未做目录校验

- [ ] **Step 7: 实现最小配置结构**

```python
@dataclass(frozen=True)
class CameraRoot:
    camera_no: int
    video_root: str


class Settings(BaseSettings):
    app_password: str = ""

    @property
    def camera_roots(self) -> list[CameraRoot]:
        ...
```

实现要求：

- 从 `Settings` 已加载的环境源中解析所有 `VIDEO_ROOT_数字`
- 至少要求存在一个 `VIDEO_ROOT_数字`
- 生成按 `camera_no` 升序的 `camera_roots`
- 校验 `APP_PASSWORD` 非空
- 校验目录不能重复、不能父子重叠

- [ ] **Step 8: 更新示例配置**

```env
VIDEO_ROOT_1=./videos/cam1
APP_PASSWORD=123456
```

- [ ] **Step 9: 重新运行测试**

Run: `cd backend && pytest tests/test_config.py tests/test_index_scheduler.py -q`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/core/config.py backend/tests/test_config.py backend/tests/test_index_scheduler.py backend/.env.example
git commit -m "feat: add light-config camera settings"
```

### Task 2: 升级数据库模型，并在旧库不兼容时显式报错

**Files:**
- Modify: `backend/app/core/db.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/tasks/index_videos.py`
- Modify: `backend/app/models/video_file.py`
- Modify: `backend/app/models/timeline_segment.py`
- Modify: `backend/app/models/day_summary.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_db_models.py`

- [ ] **Step 1: 先写模型列变更测试**

```python
def test_spec_columns_exist(sqlite_session):
    ...
    assert "camera_no" in table_columns["video_files"]
    assert "camera_no" in table_columns["timeline_segments"]
    assert "camera_no" in table_columns["day_summaries"]
    assert "id" in table_columns["day_summaries"]
```

- [ ] **Step 2: 再写旧库兼容性失败测试**

```python
def test_incompatible_day_summary_schema_requires_manual_reset(tmp_path):
    db_path = tmp_path / "replay.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE day_summaries (day TEXT PRIMARY KEY)"))

    with pytest.raises(RuntimeError, match="删除 replay.db"):
        assert_sqlite_schema_compatible(engine)
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && pytest tests/test_db_models.py -q`
Expected: FAIL，提示缺少 `camera_no` 列或缺少兼容性检查

- [ ] **Step 4: 调整 ORM 与兼容性检查**

```python
class VideoFile(Base):
    camera_no = Column(Integer, nullable=False, index=True)


class DaySummary(Base):
    id = Column(Integer, primary_key=True)
    camera_no = Column(Integer, nullable=False, index=True)
```

实现要求：

- `video_files`、`timeline_segments`、`day_summaries` 全部新增 `camera_no`
- `day_summaries` 改为自增 `id` 主键 + `camera_no + day` 联合唯一
- 在 `backend/app/core/db.py` 新增 `assert_sqlite_schema_compatible(...)`
- 在 `backend/app/main.py` 的 app lifespan 中，`create_all` 前先执行兼容性检查
- 在 `backend/app/tasks/index_videos.py` 的 CLI / job 创建入口中，使用数据库前先执行兼容性检查

- [ ] **Step 5: 更新测试夹具**

```python
existing_record = VideoFile(
    camera_no=1,
    ...
)
```

- [ ] **Step 6: 重新运行测试**

Run: `cd backend && pytest tests/test_db_models.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/db.py backend/app/main.py backend/app/tasks/index_videos.py backend/app/models backend/tests/conftest.py backend/tests/test_db_models.py
git commit -m "feat: add camera-aware database schema"
```

### Task 3: 改造索引、启动补扫与按通道重建链路

**Files:**
- Modify: `backend/app/tasks/index_videos.py`
- Modify: `backend/app/tasks/rebuild_day.py`
- Modify: `backend/app/tasks/index_scheduler.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_index_tasks.py`
- Modify: `backend/tests/test_index_scheduler.py`

- [ ] **Step 1: 先写多通道索引失败测试**

```python
def test_run_index_job_persists_camera_scoped_records(sqlite_session, monkeypatch, tmp_path):
    cam1 = tmp_path / "cam1"
    cam2 = tmp_path / "cam2"
    ...
    job = run_index_job(
        sqlite_session,
        camera_roots=[
            CameraRoot(camera_no=1, video_root=str(cam1)),
            CameraRoot(camera_no=2, video_root=str(cam2)),
        ],
    )

    assert {row.camera_no for row in sqlite_session.query(VideoFile).all()} == {1, 2}
```

- [ ] **Step 2: 再写按通道重建测试**

```python
def test_rebuild_day_timeline_is_scoped_by_camera(sqlite_session):
    rebuild_day_timeline(sqlite_session, camera_no=1, day="2026-03-17")
    assert {row.camera_no for row in sqlite_session.query(TimelineSegment).all()} == {1}
    assert sqlite_session.query(DaySummary).one().camera_no == 1
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && pytest tests/test_index_tasks.py tests/test_index_scheduler.py -q`
Expected: FAIL，提示索引入口仍然只接受单个 `root` 或重建仍只按 `day`

- [ ] **Step 4: 实现多通道索引入口**

```python
def run_index_job(
    session: Session,
    *,
    camera_roots: Sequence[CameraRoot],
    target_day: str | None = None,
) -> IndexJob:
    for camera_root in camera_roots:
        ...
```

实现要求：

- `run_index_job` 与后台线程入口改为接收 `camera_roots`
- 写入 `VideoFile` 时保存 `camera_no`
- `rebuild_day_timeline(session, camera_no, day)` 只处理单通道
- `upsert_day_summary(session, camera_no, day, ...)` 必须按 `camera_no + day` 写入或更新日期摘要
- 启动补扫和调度补扫统一从 `settings.camera_roots` 取目录

- [ ] **Step 5: 补充单通道调度回归**

```python
assert captured["camera_roots"][0].camera_no == 1
```

- [ ] **Step 6: 重新运行测试**

Run: `cd backend && pytest tests/test_index_tasks.py tests/test_index_scheduler.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/tasks/index_videos.py backend/app/tasks/rebuild_day.py backend/app/tasks/index_scheduler.py backend/app/main.py backend/tests/test_index_tasks.py backend/tests/test_index_scheduler.py
git commit -m "feat: scope indexing by camera"
```

### Task 4: 增加 `/api/cameras`，并让查询接口全部按通道工作

**Files:**
- Create: `backend/app/schemas/camera.py`
- Create: `backend/app/api/cameras.py`
- Modify: `backend/app/api/days.py`
- Modify: `backend/app/api/timeline.py`
- Modify: `backend/app/api/locate.py`
- Modify: `backend/app/services/locate_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_cameras_api.py`
- Modify: `backend/tests/test_days_api.py`
- Modify: `backend/tests/test_timeline_api.py`
- Modify: `backend/tests/test_locate_api.py`

- [ ] **Step 1: 先写通道列表接口失败测试**

```python
def test_list_cameras_returns_sorted_configured_channels(client, settings_override):
    response = client.get("/api/cameras")
    assert response.status_code == 200
    assert response.json() == [
        {"cameraNo": 1, "label": "通道 1"},
        {"cameraNo": 3, "label": "通道 3"},
    ]
```

- [ ] **Step 2: 再写 camera 查询过滤测试**

```python
def test_list_days_filters_by_camera(client, sqlite_session):
    response = client.get("/api/days", params={"camera": 2})
    assert response.status_code == 200
    assert [item["day"] for item in response.json()] == ["2026-03-18"]
```

```python
def test_timeline_returns_404_for_unknown_camera(client):
    response = client.get("/api/timeline", params={"camera": 99, "day": "2026-03-18"})
    assert response.status_code == 404
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && pytest tests/test_cameras_api.py tests/test_days_api.py tests/test_timeline_api.py tests/test_locate_api.py -q`
Expected: FAIL，提示缺少 `/api/cameras` 或现有查询未带 `camera`

- [ ] **Step 4: 实现接口与过滤逻辑**

```python
@router.get("/api/cameras", response_model=list[CameraItem])
def list_cameras(settings: Settings = Depends(get_settings)) -> list[CameraItem]:
    return [
        CameraItem(cameraNo=item.camera_no, label=f"通道 {item.camera_no}")
        for item in settings.camera_roots
    ]
```

实现要求：

- `/api/days?camera=...`
- `/api/timeline?camera=...&day=...`
- `/api/locate?camera=...&at=...`
- 未配置通道统一返回 `404`
- 已配置但无日期数据时 `/api/days` 返回 `[]`

- [ ] **Step 5: 重新运行测试**

Run: `cd backend && pytest tests/test_cameras_api.py tests/test_days_api.py tests/test_timeline_api.py tests/test_locate_api.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/camera.py backend/app/api/cameras.py backend/app/api/days.py backend/app/api/timeline.py backend/app/api/locate.py backend/app/services/locate_service.py backend/app/main.py backend/tests/conftest.py backend/tests/test_cameras_api.py backend/tests/test_days_api.py backend/tests/test_timeline_api.py backend/tests/test_locate_api.py
git commit -m "feat: add camera-aware replay APIs"
```

### Task 5: 增加单密码认证与后端接口守卫

**Files:**
- Create: `backend/app/core/auth.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/api/days.py`
- Modify: `backend/app/api/timeline.py`
- Modify: `backend/app/api/locate.py`
- Modify: `backend/app/api/index_jobs.py`
- Modify: `backend/app/api/videos.py`
- Modify: `backend/app/api/cameras.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth_api.py`
- Modify: `backend/tests/test_cameras_api.py`
- Modify: `backend/tests/test_days_api.py`
- Modify: `backend/tests/test_timeline_api.py`
- Modify: `backend/tests/test_locate_api.py`
- Modify: `backend/tests/test_video_stream_api.py`
- Modify: `backend/tests/test_index_rebuild_api.py`

- [ ] **Step 1: 先写认证接口失败测试**

```python
def test_login_sets_session_cookie(client):
    response = client.post("/api/auth/login", json={"password": "secret-pass"})
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert "Set-Cookie" in response.headers
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=Lax" in response.headers["set-cookie"]
```

```python
def test_unauthenticated_days_request_returns_401(client):
    response = client.get("/api/days", params={"camera": 1})
    assert response.status_code == 401
```

```python
def test_login_rejects_wrong_password(client):
    response = client.post("/api/auth/login", json={"password": "wrong-pass"})
    assert response.status_code == 401
```

```python
def test_auth_status_reflects_cookie_state(authenticated_client):
    response = authenticated_client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
```

```python
def test_logout_clears_cookie(authenticated_client):
    response = authenticated_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "Set-Cookie" in response.headers
```

```python
def test_auth_status_is_false_without_cookie(client):
    response = client.get("/api/auth/status")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}
```

```python
def test_tampered_cookie_is_rejected(client):
    client.cookies.set("replay_session", "tampered")
    assert client.get("/api/days", params={"camera": 1}).status_code == 401
    assert client.get("/api/auth/status").json() == {"authenticated": False}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_auth_api.py tests/test_cameras_api.py tests/test_days_api.py tests/test_timeline_api.py tests/test_locate_api.py tests/test_video_stream_api.py tests/test_index_rebuild_api.py -q`
Expected: FAIL，提示缺少 `/api/auth/*` 或接口尚未保护

- [ ] **Step 3: 实现最小认证辅助**

```python
COOKIE_NAME = "replay_session"


def build_session_value(password: str) -> str:
    return hmac.new(password.encode(), b"authenticated", hashlib.sha256).hexdigest()


def require_authenticated(request: Request, settings: Settings = Depends(get_settings)) -> None:
    ...
```

实现要求：

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/status`
- 未登录访问 `GET /api/auth/status` 时返回 `200 {"authenticated": false}`
- 使用会话级 HttpOnly Cookie
- 必须校验签名 Cookie 完整性，篡改后的 Cookie 视为未登录
- 所有业务接口统一挂载 `require_authenticated`

- [ ] **Step 4: 给测试客户端补登录夹具**

```python
@pytest.fixture
def authenticated_client(client):
    client.post("/api/auth/login", json={"password": "secret-pass"})
    return client
```

- [ ] **Step 5: 重新运行测试**

Run: `cd backend && pytest tests/test_auth_api.py tests/test_cameras_api.py tests/test_days_api.py tests/test_timeline_api.py tests/test_locate_api.py tests/test_video_stream_api.py tests/test_index_rebuild_api.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/auth.py backend/app/schemas/auth.py backend/app/api/auth.py backend/app/api/cameras.py backend/app/api/days.py backend/app/api/timeline.py backend/app/api/locate.py backend/app/api/index_jobs.py backend/app/api/videos.py backend/app/main.py backend/tests/conftest.py backend/tests/test_auth_api.py backend/tests/test_cameras_api.py backend/tests/test_days_api.py backend/tests/test_timeline_api.py backend/tests/test_locate_api.py backend/tests/test_video_stream_api.py backend/tests/test_index_rebuild_api.py
git commit -m "feat: protect replay APIs with password auth"
```

### Task 6: 改造前端 API、类型与 hooks，支持登录态和通道维度

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/replay.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/cameras.ts`
- Modify: `frontend/src/hooks/useDays.ts`
- Modify: `frontend/src/hooks/useTimeline.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/hooks/useCameras.ts`
- Modify: `frontend/src/api/replay.test.ts`

- [ ] **Step 1: 先写前端 API 失败测试**

```ts
it('passes camera query when requesting days', async () => {
  await listDays(2);
  expect(globalThis.fetch).toHaveBeenCalledWith('/api/days?camera=2', {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });
});
```

```ts
it('requests auth status with credentials included', async () => {
  await getAuthStatus();
  expect(globalThis.fetch).toHaveBeenCalledWith('/api/auth/status', expect.objectContaining({
    credentials: 'include',
  }));
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm run test -- src/api/replay.test.ts`
Expected: FAIL，提示缺少 `camera` 参数或 `credentials: 'include'`

- [ ] **Step 3: 实现最小 API 改造**

```ts
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(resolveApiUrl(path), {
    credentials: 'include',
    ...init,
    headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
  });
  ...
}
```

实现要求：

- `listDays(cameraNo)`
- `getTimeline(cameraNo, day)`
- `locateAt(cameraNo, at)`
- `listCameras()`
- `login(password)` / `logout()` / `getAuthStatus()`
- `useDays(cameraNo)` 与 `useTimeline(cameraNo, day)`

- [ ] **Step 4: 补充新类型定义**

```ts
export interface CameraItem {
  cameraNo: number;
  label: string;
}

export interface AuthStatus {
  authenticated: boolean;
}
```

- [ ] **Step 5: 重新运行测试**

Run: `cd frontend && npm run test -- src/api/replay.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/api/replay.ts frontend/src/api/auth.ts frontend/src/api/cameras.ts frontend/src/hooks/useDays.ts frontend/src/hooks/useTimeline.ts frontend/src/hooks/useAuth.ts frontend/src/hooks/useCameras.ts frontend/src/api/replay.test.ts
git commit -m "feat: add camera and auth client APIs"
```

### Task 7: 增加登录页、通道切换、空状态与退出登录

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/components/CameraPicker.tsx`
- Modify: `frontend/src/pages/ReplayPage.tsx`
- Modify: `frontend/tests/ReplayPage.test.tsx`
- Create: `frontend/tests/App.test.tsx`
- Create: `frontend/tests/LoginPage.test.tsx`

- [ ] **Step 1: 先写登录门禁失败测试**

```tsx
it('renders login page when auth status is false', async () => {
  render(<App />);
  expect(await screen.findByLabelText('访问密码')).toBeInTheDocument();
});
```

```tsx
it('shows camera picker when multiple cameras exist', () => {
  render(<ReplayPage />);
  expect(screen.getByLabelText('回放通道')).toBeInTheDocument();
});
```

```tsx
it('hides camera picker when only one camera exists', () => {
  render(<ReplayPage />);
  expect(screen.queryByLabelText('回放通道')).not.toBeInTheDocument();
});
```

```tsx
it('shows empty state instead of timeline when selected camera has no days', () => {
  render(<ReplayPage />);
  expect(screen.getByText('该通道暂无录像')).toBeInTheDocument();
});
```

```tsx
it('shows login error when password is invalid', async () => {
  render(<LoginPage onLogin={failingLogin} />);
  ...
  expect(await screen.findByText('密码错误，请重试。')).toBeInTheDocument();
});
```

```tsx
it('restores replay page after auth status confirms existing session', async () => {
  render(<App />);
  expect(await screen.findByText('监控回放工作台')).toBeInTheDocument();
});
```

```tsx
it('switches camera by reloading days and selecting latest day before loading timeline', async () => {
  render(<ReplayPage />);
  ...
  expect(useDaysMock).toHaveBeenLastCalledWith(2);
  expect(useTimelineMock).toHaveBeenLastCalledWith(2, '2026-03-21');
});
```

```tsx
it('does not request timeline when selected camera has no days', () => {
  render(<ReplayPage />);
  expect(useTimelineMock).toHaveBeenLastCalledWith(2, null);
});
```

```tsx
it('returns to login page after logout succeeds', async () => {
  render(<App />);
  ...
  expect(await screen.findByLabelText('访问密码')).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm run test -- tests/App.test.tsx tests/ReplayPage.test.tsx tests/LoginPage.test.tsx`
Expected: FAIL，提示缺少登录页、通道切换或空状态

- [ ] **Step 3: 实现最小页面流转**

```tsx
export default function App() {
  const auth = useAuth();
  if (!auth.ready) return null;
  return auth.authenticated ? <ReplayPage onLogout={auth.logout} /> : <LoginPage onLogin={auth.login} />;
}
```

实现要求：

- `LoginPage` 只有一个密码输入框和提交按钮
- 登录失败时显示统一错误提示
- `App` 启动时先检查 `/api/auth/status`，已登录则直接恢复回放页
- `ReplayPage` 初始默认选中最小 `cameraNo`
- 单通道时隐藏 `CameraPicker`
- 切换通道时先重新请求日期列表
- 如果新通道存在日期，自动选中最新日期，再请求对应时间轴
- 如果新通道没有日期，停止时间轴请求并显示空状态
- 切换通道时重置播放器状态
- 空通道显示“该通道暂无录像”
- 页面提供明确的“退出登录”按钮，成功后返回登录页

- [ ] **Step 4: 重新运行测试**

Run: `cd frontend && npm run test -- tests/App.test.tsx tests/ReplayPage.test.tsx tests/LoginPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/LoginPage.tsx frontend/src/components/CameraPicker.tsx frontend/src/pages/ReplayPage.tsx frontend/tests/ReplayPage.test.tsx frontend/tests/App.test.tsx frontend/tests/LoginPage.test.tsx
git commit -m "feat: add login gate and camera switcher"
```

### Task 8: 更新文档、示例配置并做全量验证

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`
- Modify: `backend/.env.example`

- [ ] **Step 1: 先补文档缺口**

```md
VIDEO_ROOT_1=/nas/cam1
VIDEO_ROOT_2=/nas/cam2
APP_PASSWORD=123456
```

文档必须明确：

- 多通道配置方式
- 单密码登录方式
- 旧版 `replay.db` 需要手动删除后重建
- 修改 `VIDEO_ROOT_n` 或 `APP_PASSWORD` 后需要重启服务
- 空通道和单通道 UI 的预期行为

- [ ] **Step 2: 运行后端测试**

Run: `cd backend && pytest -q`
Expected: PASS

- [ ] **Step 3: 运行前端测试**

Run: `cd frontend && npm run test`
Expected: PASS

- [ ] **Step 4: 检查仓库变更**

Run: `git status --short`
Expected: 只包含第二阶段相关文件

- [ ] **Step 5: Commit**

```bash
git add README.md backend/README.md frontend/README.md backend/.env.example
git commit -m "docs: document phase 2 light-config workflow"
```
