# NAS 摄像头回放系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个单摄像头、单用户、本地网页访问的 NAS 视频回放系统，支持离线索引、按日期回放、24 小时时间轴、断档展示、拖动定位与倍速播放。

**Architecture:** 后端使用 Python + FastAPI + SQLite 构建离线索引与查询服务，前端使用 React + TypeScript 构建时间轴驱动的网页播放器。系统以“文件名提供墙上时间、ffprobe 校验真实时长、SQLite 存储标准化时间轴”为核心，播放层直接使用原始 mp4 并支持轻微跨切片切换感。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, pytest, ffprobe, React, TypeScript, Vite, Vitest, Testing Library

---

## 预期目录与职责

### 后端文件

- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/db.py`
- Create: `backend/app/models/video_file.py`
- Create: `backend/app/models/timeline_segment.py`
- Create: `backend/app/models/day_summary.py`
- Create: `backend/app/models/index_job.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/day.py`
- Create: `backend/app/schemas/timeline.py`
- Create: `backend/app/schemas/locate.py`
- Create: `backend/app/services/file_scanner.py`
- Create: `backend/app/services/filename_parser.py`
- Create: `backend/app/services/media_probe.py`
- Create: `backend/app/services/timeline_builder.py`
- Create: `backend/app/services/locate_service.py`
- Create: `backend/app/services/video_stream.py`
- Create: `backend/app/api/days.py`
- Create: `backend/app/api/timeline.py`
- Create: `backend/app/api/locate.py`
- Create: `backend/app/api/videos.py`
- Create: `backend/app/api/index_jobs.py`
- Create: `backend/app/tasks/index_videos.py`
- Create: `backend/app/tasks/rebuild_day.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_filename_parser.py`
- Create: `backend/tests/test_media_probe.py`
- Create: `backend/tests/test_timeline_builder.py`
- Create: `backend/tests/test_locate_service.py`
- Create: `backend/tests/test_days_api.py`
- Create: `backend/tests/test_timeline_api.py`
- Create: `backend/tests/test_locate_api.py`
- Create: `backend/tests/test_index_rebuild_api.py`
- Create: `backend/tests/test_video_stream_api.py`

### 前端文件

- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/replay.ts`
- Create: `frontend/src/hooks/useDays.ts`
- Create: `frontend/src/hooks/useTimeline.ts`
- Create: `frontend/src/hooks/usePlaybackController.ts`
- Create: `frontend/src/components/DatePicker.tsx`
- Create: `frontend/src/components/PlayerPanel.tsx`
- Create: `frontend/src/components/TimelineBar.tsx`
- Create: `frontend/src/components/PlaybackControls.tsx`
- Create: `frontend/src/pages/ReplayPage.tsx`
- Create: `frontend/src/utils/time.ts`
- Create: `frontend/src/utils/timeline.ts`
- Create: `frontend/tests/TimelineBar.test.tsx`
- Create: `frontend/tests/ReplayPage.test.tsx`
- Create: `frontend/tests/usePlaybackController.test.tsx`

### 文档与根目录文件

- Modify: `.gitignore`
- Modify: `docs/superpowers/specs/2026-03-24-nas-camera-replay-design.md`
- Create: `README.md`

## 实施约束

- 后端所有时间统一使用 `Asia/Shanghai`
- SQLite 中统一保存 ISO 8601 文本时间
- `issue_flags` 统一使用 JSON 数组字符串
- HTTP 视频播放必须支持 Range 请求
- 时间轴按 24 小时固定宽度渲染，断档显式显示
- 第一版不实现 HLS，不实现多摄像头

### Task 1: 初始化仓库骨架与开发工具

**Files:**
- Create: `backend/pyproject.toml`
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: 写一条失败的环境检查说明**

```bash
test -f backend/pyproject.toml
```

Expected: exit code 非 0，说明后端项目骨架尚未建立。

- [ ] **Step 2: 建立后端依赖定义**

```toml
[project]
name = "nas-camera-replay-backend"
version = "0.1.0"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "sqlalchemy",
  "pydantic",
]
```

- [ ] **Step 3: 建立前端依赖定义**

```json
{
  "name": "nas-camera-replay-frontend",
  "private": true,
  "scripts": {
    "dev": "vite",
    "test": "vitest run"
  }
}
```

- [ ] **Step 4: 补充 README 的启动说明**

```md
## 开发命令

- 后端：`python -m uvicorn app.main:app --reload`
- 前端：`npm run dev`
```

- [ ] **Step 5: 验证目录骨架存在**

Run: `find backend frontend -maxdepth 2 -type f | sort`
Expected: 输出 `backend/pyproject.toml` 与 `frontend/package.json` 等基础文件

- [ ] **Step 6: Commit**

```bash
git add .gitignore README.md backend frontend
git commit -m "chore: bootstrap replay project structure"
```

### Task 2: 建立后端配置、数据库与 ORM 模型

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/db.py`
- Create: `backend/app/models/video_file.py`
- Create: `backend/app/models/timeline_segment.py`
- Create: `backend/app/models/day_summary.py`
- Create: `backend/app/models/index_job.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: 先写数据库初始化测试**

```python
def test_create_all_tables(sqlite_session):
    tables = sqlite_session.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    assert {"video_files", "timeline_segments", "day_summaries", "index_jobs"} <= {
        row[0] for row in tables
    }
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/conftest.py -q`
Expected: FAIL，提示模型或初始化逻辑不存在

- [ ] **Step 3: 实现配置与数据库连接**

```python
class Settings(BaseSettings):
    timezone: str = "Asia/Shanghai"
    sqlite_url: str = "sqlite:///./replay.db"
    video_root: str
```

- [ ] **Step 4: 实现 4 张表的 ORM 模型**

```python
class VideoFile(Base):
    __tablename__ = "video_files"
    id = Column(Integer, primary_key=True)
    file_path = Column(Text, unique=True, nullable=False)
    status = Column(String, nullable=False)
```

- [ ] **Step 5: 再次运行测试**

Run: `cd backend && pytest tests/conftest.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core backend/app/models backend/tests/conftest.py
git commit -m "feat: add backend settings and database models"
```

### Task 3: 实现文件名解析服务

**Files:**
- Create: `backend/app/services/filename_parser.py`
- Create: `backend/tests/test_filename_parser.py`

- [ ] **Step 1: 编写文件名解析失败测试**

```python
def test_parse_camera_filename():
    parsed = parse_camera_filename("00_20260318015937_20260318021002.mp4")
    assert parsed.name_start_at.isoformat() == "2026-03-18T01:59:37+08:00"
    assert parsed.name_end_at.isoformat() == "2026-03-18T02:10:02+08:00"
```

- [ ] **Step 2: 增加非法文件名测试**

```python
def test_parse_invalid_camera_filename():
    with pytest.raises(ValueError):
        parse_camera_filename("broken-name.mp4")
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && pytest tests/test_filename_parser.py -q`
Expected: FAIL，提示解析函数不存在

- [ ] **Step 4: 实现最小解析逻辑**

```python
FILENAME_RE = re.compile(r"^\d+_(\d{14})_(\d{14})\.mp4$")

def parse_camera_filename(file_name: str) -> ParsedFilename:
    match = FILENAME_RE.match(file_name)
    if not match:
        raise ValueError("invalid camera filename")
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_filename_parser.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/filename_parser.py backend/tests/test_filename_parser.py
git commit -m "feat: parse camera file names into wall-clock time"
```

### Task 4: 实现 ffprobe 媒体探测服务

**Files:**
- Create: `backend/app/services/media_probe.py`
- Create: `backend/tests/test_media_probe.py`

- [ ] **Step 1: 编写探测结果解析测试**

```python
def test_parse_ffprobe_json():
    payload = {"format": {"duration": "625.0", "start_time": "0.0"}}
    result = parse_probe_payload(payload)
    assert result.duration_sec == 625.0
    assert result.start_time_sec == 0.0
```

- [ ] **Step 2: 编写 probe 失败测试**

```python
def test_parse_ffprobe_missing_duration():
    with pytest.raises(ValueError):
        parse_probe_payload({"format": {}})
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && pytest tests/test_media_probe.py -q`
Expected: FAIL

- [ ] **Step 4: 实现 ffprobe 调用与 JSON 解析**

```python
cmd = [
    "ffprobe",
    "-v", "error",
    "-print_format", "json",
    "-show_format",
    "-show_streams",
    file_path,
]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_media_probe.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/media_probe.py backend/tests/test_media_probe.py
git commit -m "feat: add ffprobe media inspection service"
```

### Task 5: 实现时间轴构建与异常判定

**Files:**
- Create: `backend/app/services/timeline_builder.py`
- Create: `backend/tests/test_timeline_builder.py`

- [ ] **Step 1: 编写连续片段测试**

```python
def test_build_timeline_marks_small_gap_as_continuous():
    segments, gaps = build_day_timeline([...])
    assert len(segments) == 2
    assert gaps == []
```

- [ ] **Step 2: 编写断档与跨天测试**

```python
def test_build_timeline_splits_cross_day_file():
    result = split_file_ranges_by_day(file_record)
    assert {item.day for item in result} == {"2026-03-17", "2026-03-18"}
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && pytest tests/test_timeline_builder.py -q`
Expected: FAIL

- [ ] **Step 4: 实现时间轴规则**

```python
if gap_sec <= 2:
    gap_sec = 0
elif gap_sec > 30:
    issue_flags.append("gap_before")
```

- [ ] **Step 5: 增加时长异常与重叠判定**

```python
duration_diff = abs(name_duration - probe_duration)
status = "warning" if duration_diff > 2 else "ready"
```

- [ ] **Step 6: 让时间轴构建返回每日汇总结果**

```python
return TimelineBuildResult(
    segments=segments,
    gaps=gaps,
    summary=DaySummarySnapshot(
        first_segment_at=first_at,
        last_segment_at=last_at,
        total_recorded_sec=recorded_sec,
        total_gap_sec=gap_sec,
        has_warning=has_warning,
    ),
)
```

- [ ] **Step 7: 运行测试确认通过**

Run: `cd backend && pytest tests/test_timeline_builder.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/timeline_builder.py backend/tests/test_timeline_builder.py
git commit -m "feat: build daily timeline with gap and overlap handling"
```

### Task 6: 实现索引任务与增量更新

**Files:**
- Create: `backend/app/services/file_scanner.py`
- Create: `backend/app/tasks/index_videos.py`
- Create: `backend/app/tasks/rebuild_day.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: 编写扫描器测试**

```python
def test_scanner_returns_mp4_files(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    files = scan_video_files(tmp_path)
    assert [item.name for item in files] == ["a.mp4"]
```

- [ ] **Step 2: 编写增量跳过测试**

```python
def test_skip_reprobe_when_size_and_mtime_unchanged(existing_record):
    assert should_reprobe(existing_record, incoming_file) is False
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && pytest tests/test_filename_parser.py tests/test_media_probe.py -q`
Expected: PASS，但扫描器相关逻辑尚未存在

- [ ] **Step 4: 实现目录扫描与增量判断**

```python
def should_reprobe(existing, incoming):
    return (
        existing.file_size != incoming.file_size
        or existing.file_mtime != incoming.file_mtime
    )
```

- [ ] **Step 5: 实现按受影响日期重建的索引命令**

```python
def rebuild_impacted_days(session, file_record):
    for day in collect_impacted_days(file_record):
        rebuild_day_timeline(session, day)
```

- [ ] **Step 6: 为索引任务写入 `index_jobs` 记录**

```python
job = IndexJob(
    job_day=target_day or "all",
    status="running",
    started_at=now_iso(),
)
```

- [ ] **Step 7: 在索引结束时更新统计字段与完成时间**

```python
job.scanned_count = scanned_count
job.success_count = success_count
job.warning_count = warning_count
job.failed_count = failed_count
job.finished_at = now_iso()
job.status = "success" if failed_count == 0 else "warning"
```

- [ ] **Step 8: 将时间轴汇总持久化到 `day_summaries`**

```python
summary = build_result.summary
upsert_day_summary(session, day, summary)
```

- [ ] **Step 9: 手工跑一次索引命令**

Run: `cd backend && python -m app.tasks.index_videos`
Expected: 输出扫描数量、成功数量、警告数量

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/file_scanner.py backend/app/tasks backend/tests
git commit -m "feat: add incremental indexing workflow"
```

### Task 7: 实现日期、时间轴、定位查询 API

**Files:**
- Create: `backend/app/schemas/day.py`
- Create: `backend/app/schemas/timeline.py`
- Create: `backend/app/schemas/locate.py`
- Create: `backend/app/services/locate_service.py`
- Create: `backend/app/api/days.py`
- Create: `backend/app/api/timeline.py`
- Create: `backend/app/api/locate.py`
- Create: `backend/app/api/index_jobs.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_days_api.py`
- Create: `backend/tests/test_timeline_api.py`
- Create: `backend/tests/test_locate_api.py`
- Create: `backend/tests/test_index_rebuild_api.py`
- Create: `backend/tests/test_locate_service.py`

- [ ] **Step 1: 编写 `/api/days` 测试**

```python
def test_list_days_returns_summaries(client, seeded_day_summary):
    response = client.get("/api/days")
    assert response.status_code == 200
    assert response.json()[0]["day"] == "2026-03-20"
```

- [ ] **Step 2: 编写 `/api/timeline` 与 `/api/locate` 测试**

```python
def test_locate_returns_gap_payload(client, seeded_gap_day):
    response = client.get("/api/locate", params={"at": "2026-03-20T03:27:30"})
    assert response.json()["found"] is False
```

- [ ] **Step 3: 编写手动重建索引接口测试**

```python
def test_rebuild_index_returns_job_payload(client, monkeypatch):
    response = client.post("/api/index/rebuild", params={"day": "2026-03-20"})
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["scope"] == "day"
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd backend && pytest tests/test_days_api.py tests/test_timeline_api.py tests/test_locate_api.py tests/test_index_rebuild_api.py -q`
Expected: FAIL

- [ ] **Step 5: 实现 schema、service 与查询路由**

```python
@router.get("/api/locate", response_model=LocateResponse)
def locate(at: datetime):
    return locate_at(session, at)
```

- [ ] **Step 6: 实现 `POST /api/index/rebuild` 路由**

```python
@router.post("/api/index/rebuild", response_model=RebuildResponse)
def rebuild(day: str | None = None):
    job = enqueue_rebuild(session, day=day)
    return {"accepted": True, "jobId": job.id, "scope": "day" if day else "all", "day": day}
```

- [ ] **Step 7: 实现应用入口并注册全部路由**

```python
app = FastAPI(title="NAS Camera Replay")
app.include_router(days_router)
app.include_router(timeline_router)
app.include_router(locate_router)
app.include_router(index_jobs_router)
```

- [ ] **Step 8: 运行测试确认通过**

Run: `cd backend && pytest tests/test_days_api.py tests/test_timeline_api.py tests/test_locate_api.py tests/test_index_rebuild_api.py tests/test_locate_service.py -q`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/main.py backend/app/api backend/app/schemas backend/app/services/locate_service.py backend/tests
git commit -m "feat: add replay query api endpoints"
```

### Task 8: 实现视频流接口与 Range 支持

**Files:**
- Create: `backend/app/services/video_stream.py`
- Create: `backend/app/api/videos.py`
- Create: `backend/tests/test_video_stream_api.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 编写 Range 请求测试**

```python
def test_video_stream_supports_range(client, seeded_video_file):
    response = client.get(
        f"/api/videos/{seeded_video_file.id}/stream",
        headers={"Range": "bytes=0-99"},
    )
    assert response.status_code == 206
    assert response.headers["content-range"].startswith("bytes 0-99/")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_video_stream_api.py -q`
Expected: FAIL

- [ ] **Step 3: 实现字节范围解析**

```python
def parse_range_header(header: str, file_size: int) -> tuple[int, int]:
    start_text, end_text = header.replace("bytes=", "").split("-")
    return int(start_text), int(end_text)
```

- [ ] **Step 4: 实现视频流接口**

```python
return StreamingResponse(
    iter_file_chunks(file_path, start, end),
    status_code=206,
    headers=headers,
    media_type="video/mp4",
)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_video_stream_api.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/video_stream.py backend/app/api/videos.py backend/tests/test_video_stream_api.py backend/app/main.py
git commit -m "feat: stream mp4 files with range support"
```

### Task 9: 初始化前端应用与 API 客户端

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles/global.css`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/replay.ts`
- Create: `frontend/src/hooks/useDays.ts`
- Create: `frontend/src/hooks/useTimeline.ts`

- [ ] **Step 1: 编写 API 客户端单元测试**

```tsx
it("maps day summary payload", async () => {
  const days = await listDays()
  expect(days[0].day).toBe("2026-03-20")
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm test -- --runInBand`
Expected: FAIL

- [ ] **Step 3: 实现 API 类型与请求封装**

```ts
export async function listDays(): Promise<DaySummary[]> {
  return request("/api/days")
}
```

- [ ] **Step 4: 建立应用入口与全局样式**

```tsx
createRoot(document.getElementById("root")!).render(<App />)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npm test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src frontend/package.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html
git commit -m "feat: bootstrap frontend app and api client"
```

### Task 10: 实现时间轴与基础播放器页面

**Files:**
- Create: `frontend/src/utils/time.ts`
- Create: `frontend/src/utils/timeline.ts`
- Create: `frontend/src/components/DatePicker.tsx`
- Create: `frontend/src/components/PlayerPanel.tsx`
- Create: `frontend/src/components/TimelineBar.tsx`
- Create: `frontend/src/components/PlaybackControls.tsx`
- Create: `frontend/src/pages/ReplayPage.tsx`
- Create: `frontend/tests/TimelineBar.test.tsx`

- [ ] **Step 1: 编写时间轴渲染测试**

```tsx
it("renders gap and segment blocks", () => {
  render(<TimelineBar segments={segments} gaps={gaps} />)
  expect(screen.getByText("03:00")).toBeInTheDocument()
})
```

- [ ] **Step 2: 编写点击时间轴测试**

```tsx
it("converts click position to wall clock second", () => {
  expect(positionToSecond(0.5, 86400)).toBe(43200)
})
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd frontend && npm test -- TimelineBar.test.tsx`
Expected: FAIL

- [ ] **Step 4: 实现 24 小时时间轴与日期选择器**

```tsx
<div className={styles.timeline}>
  {segments.map((segment) => (
    <button key={segment.id} style={{ left: `${segment.left}%` }} />
  ))}
</div>
```

- [ ] **Step 5: 实现播放器面板和控制栏**

```tsx
<video ref={videoRef} controls playsInline preload="metadata" />
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd frontend && npm test -- TimelineBar.test.tsx`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components frontend/src/pages frontend/src/utils frontend/tests/TimelineBar.test.tsx
git commit -m "feat: add replay timeline and player layout"
```

### Task 11: 实现播放控制、断档处理与自动续播

**Files:**
- Create: `frontend/src/hooks/usePlaybackController.ts`
- Create: `frontend/tests/usePlaybackController.test.tsx`
- Create: `frontend/tests/ReplayPage.test.tsx`
- Modify: `frontend/src/pages/ReplayPage.tsx`
- Modify: `frontend/src/components/PlayerPanel.tsx`
- Modify: `frontend/src/components/PlaybackControls.tsx`

- [ ] **Step 1: 编写命中断档测试**

```tsx
it("shows gap state when locate returns no recording", async () => {
  expect(await screen.findByText("该时间点无录像")).toBeInTheDocument()
})
```

- [ ] **Step 2: 编写自动续播测试**

```tsx
it("autoplays next segment when gap is within 2 seconds", async () => {
  expect(playNextSegment).toHaveBeenCalled()
})
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd frontend && npm test -- ReplayPage.test.tsx usePlaybackController.test.tsx`
Expected: FAIL

- [ ] **Step 4: 实现播放状态机**

```ts
type PlaybackState = "idle" | "loading" | "playing" | "paused" | "gap" | "error"
```

- [ ] **Step 5: 实现拖动 seek、倍速保持和自动续播**

```ts
if (nextGapSec <= 2) {
  loadSegment(nextSegment, persistedRate)
}
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd frontend && npm test -- ReplayPage.test.tsx usePlaybackController.test.tsx`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/usePlaybackController.ts frontend/src/pages/ReplayPage.tsx frontend/src/components frontend/tests
git commit -m "feat: handle replay state, seek, speed and gap playback"
```

### Task 12: 联调、回归验证与文档收尾

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-03-24-nas-camera-replay-design.md`

- [ ] **Step 1: 跑后端测试**

Run: `cd backend && pytest -q`
Expected: 全部 PASS

- [ ] **Step 2: 跑前端测试**

Run: `cd frontend && npm test`
Expected: 全部 PASS

- [ ] **Step 3: 本地联调启动**

Run: `cd backend && uvicorn app.main:app --reload`
Expected: 服务监听本地端口并返回 200

- [ ] **Step 4: 启动前端**

Run: `cd frontend && npm run dev`
Expected: 本地页面可打开并完成日期切换、时间轴跳转、倍速播放

- [ ] **Step 5: 更新 README 的运行截图说明与故障排查**

```md
- 如果时间轴为空，先检查索引任务是否已执行
- 如果视频无法拖动，检查 Range 响应头是否正确
```

- [ ] **Step 6: 最终 Commit**

```bash
git add README.md docs/superpowers/specs/2026-03-24-nas-camera-replay-design.md
git commit -m "docs: finalize replay implementation guidance"
```
