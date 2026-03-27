# NAS Camera Replay

本项目用于本地查看 NAS 中的小米摄像头回放文件，当前阶段聚焦多摄像头、单密码登录、本地网页访问。

## 目录说明

- [backend/README.md](/Users/siyu/develop/ai/mi/backend/README.md)：后端启动、`.env` 配置、初始化扫描、定时索引
- [frontend/README.md](/Users/siyu/develop/ai/mi/frontend/README.md)：前端开发启动、接口代理、测试与构建

## 快速启动

### 1. 启动后端

在 `backend/` 目录准备 `.env`：

```env
VIDEO_ROOT_1=./videos/cam1
VIDEO_ROOT_2=./videos/cam2
APP_PASSWORD=change-me
INDEX_ON_STARTUP=false
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

注意：

- 只能使用 `VIDEO_ROOT_1`、`VIDEO_ROOT_2` 这类 `VIDEO_ROOT_n` 配置，不能只配旧的 `VIDEO_ROOT`
- 修改任意 `VIDEO_ROOT_n` 或 `APP_PASSWORD` 后，都需要重启后端服务
- 如果你是从旧版单通道数据库升级过来，需要手动删除旧的 `backend/replay.db` 后重新建索引

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

联调时必须统一 host 形态：

- 前后端都用 `127.0.0.1`
- 或前后端都用 `localhost`
- 或通过同源代理访问

不要混用 `127.0.0.1` 和 `localhost`，否则浏览器可能不会携带登录 Cookie。

## 当前能力

- 多摄像头回放，通道来源完全由 `VIDEO_ROOT_n` 决定
- 单密码登录，使用 HttpOnly Cookie 保持会话
- 后端离线索引、SQLite 元数据、按天时间轴查询
- 原始 MP4 视频流与 HTTP Range
- 日期切换、24 小时时间轴、断档显式展示
- 点击时间轴定位、倍速切换、近连续片段自动续播

UI 预期：

- 单通道时不显示通道切换器
- 多通道时显示“通道 1 / 通道 2 ...”切换器
- 某个通道没有日期数据时，页面显示“该通道暂无录像”，并且不会继续请求时间轴

## 故障排查

- 如果时间轴为空，先检查索引任务是否已经执行，以及 `backend/replay.db` 中是否已有 `day_summaries` 数据
- 如果视频无法拖动或浏览器不能 seek，先检查 `/api/videos/{fileId}/stream` 是否返回了正确的 `Accept-Ranges` 与 `Content-Range`
- 如果页面能打开但没有日期，先确认后端 `GET /api/days` 是否返回 200 且不是空数组
- 如果点击时间轴没有切到预期位置，优先检查 `/api/locate` 返回值与时间轴数据是否一致
- 如果页面一直停在登录页，先确认前后端没有混用 `localhost` / `127.0.0.1`
