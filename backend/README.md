# Backend

## 作用

后端负责：

- 扫描 NAS 中的 MP4 文件
- 解析文件名和媒体时长
- 将索引结果写入 SQLite
- 提供日期、时间轴、定位、视频流等接口
- 按配置时间执行每日自动索引

后端不会删除、改写或移动 `VIDEO_ROOT` 下的原始视频文件。

## 环境准备

推荐在 `backend/` 目录使用虚拟环境：

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -e .
```

## 配置

后端会自动读取 `backend/.env`。

可以先复制示例文件：

```bash
cd backend
cp .env.example .env
```

常用配置：

```env
VIDEO_ROOT=./videos
INDEX_ON_STARTUP=false
INDEX_SCHEDULER_ENABLED=false
INDEX_SCHEDULER_TIME=03:00
SQLITE_URL=sqlite:///./replay.db
TIMEZONE=Asia/Shanghai
```

说明：

- `VIDEO_ROOT`：NAS 视频目录挂载点
- `INDEX_ON_STARTUP`：服务启动时是否自动提交一次后台补扫任务
- `INDEX_SCHEDULER_ENABLED`：是否开启内建每日调度器
- `INDEX_SCHEDULER_TIME`：每日执行时间，支持 `03:00` 和 `3:00`
- `SQLITE_URL`：SQLite 数据库地址
- `TIMEZONE`：业务时区，默认 `Asia/Shanghai`

## 启动

```bash
cd backend
./.venv/bin/python -m uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`

## 初始化扫描

首次建议先做一次同步扫描：

```bash
cd backend
./.venv/bin/python -m app.tasks.index_videos
```

只扫描某一天：

```bash
cd backend
./.venv/bin/python -m app.tasks.index_videos --day 2026-03-20
```

执行完成后，终端会输出类似：

```text
scanned=123 success=120 warning=3 failed=0
```

## 通过接口触发索引

全量异步触发：

```bash
curl -X POST http://127.0.0.1:8000/api/index/rebuild
```

只重建某一天：

```bash
curl -X POST "http://127.0.0.1:8000/api/index/rebuild?day=2026-03-20"
```

## 定时调度

当前内建调度器为“每日一次”模式。

例如：

```env
INDEX_SCHEDULER_ENABLED=true
INDEX_SCHEDULER_TIME=03:00
```

表示每天凌晨 3 点执行一次索引任务。

## 启动时补扫

如果你希望后端每次启动后自动提交一次后台索引任务，可以这样配置：

```env
INDEX_ON_STARTUP=true
```

说明：

- 启动补扫是异步提交，不会阻塞 Web 服务启动
- `uvicorn --reload` 开发模式下每次重启都会触发一次，开发时通常建议保持关闭

## 测试

```bash
cd backend
./.venv/bin/python -m pytest tests -q
```

## 常见问题

- 时间轴为空：先确认是否执行过初始化扫描
- 没有日期数据：检查 `GET /api/days` 是否返回非空数组
- 视频文件很多时首次扫描较慢：属于预期，后续重复扫描会跳过未变化文件的重新探测
- 修改了 `.env` 后不生效：需要重启 `uvicorn`
