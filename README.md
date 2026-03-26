# NAS Camera Replay

本项目用于本地查看 NAS 中的小米摄像头回放文件，当前阶段聚焦单摄像头、单用户、本地网页访问。

## 目录说明

- [backend/README.md](/Users/siyu/develop/ai/mi/backend/README.md)：后端启动、`.env` 配置、初始化扫描、定时索引
- [frontend/README.md](/Users/siyu/develop/ai/mi/frontend/README.md)：前端开发启动、接口代理、测试与构建

## 快速启动

### 1. 启动后端

在 `backend/` 目录准备 `.env`：

```env
VIDEO_ROOT=./videos
INDEX_SCHEDULER_ENABLED=false
INDEX_SCHEDULER_TIME=03:00
SQLITE_URL=sqlite:///./replay.db
TIMEZONE=Asia/Shanghai
```

启动命令：

```bash
cd backend
./.venv/bin/python -m uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`

### 2. 初始化一次视频索引

首次建议执行一次同步扫描：

```bash
cd backend
./.venv/bin/python -m app.tasks.index_videos
```

也可以通过接口异步触发：

```bash
curl -X POST http://127.0.0.1:8000/api/index/rebuild
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://127.0.0.1:5173`

前端开发环境已内置 `/api` 代理，会自动转发到 `http://127.0.0.1:8000`。

## 当前能力

- 单摄像头、单用户、本地网页查看
- 后端离线索引、SQLite 元数据、按天时间轴查询
- 原始 MP4 视频流与 HTTP Range
- 日期切换、24 小时时间轴、断档显式展示
- 点击时间轴定位、倍速切换、近连续片段自动续播

## 故障排查

- 如果时间轴为空，先检查索引任务是否已经执行，以及 `backend/replay.db` 中是否已有 `day_summaries` 数据
- 如果视频无法拖动或浏览器不能 seek，先检查 `/api/videos/{fileId}/stream` 是否返回了正确的 `Accept-Ranges` 与 `Content-Range`
- 如果页面能打开但没有日期，先确认后端 `GET /api/days` 是否返回 200 且不是空数组
- 如果点击时间轴没有切到预期位置，优先检查 `/api/locate` 返回值与时间轴数据是否一致
