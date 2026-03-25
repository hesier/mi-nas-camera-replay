# NAS Camera Replay

## 本地运行

### 后端

在 `backend/` 目录执行：

```bash
./.venv/bin/python -m uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`

### 前端

在 `frontend/` 目录执行：

```bash
npm install
npm run dev
```

默认地址：`http://127.0.0.1:5173`

## 测试命令

### 后端测试

```bash
cd backend
./.venv/bin/python -m pytest tests -q
```

### 前端测试

```bash
cd frontend
npm test
npx tsc --noEmit
```

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
