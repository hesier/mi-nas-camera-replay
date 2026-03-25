# NAS 摄像头回放系统设计方案

**日期：** 2026-03-24

**状态：** 已确认，可进入实施规划

## 1. 项目目标

构建一个面向单摄像头、单用户、本地网页访问场景的 NAS 视频回放系统。

系统需要支持以下核心能力：

- 基于 NAS 中的 mp4 文件建立可靠的时间索引
- 根据日期切换回放
- 在 24 小时时间轴上展示录像区间与断档区间
- 点击或拖动时间轴，快速跳转到目标时间点
- 支持 1x、2x、4x 倍速播放
- 允许跨切片播放时存在轻微切换感

## 2. 已确认范围

### 2.1 第一阶段范围

- 单摄像头
- 单用户
- 本地启动后台服务
- 网页端回放
- 后端使用 Python
- 元数据索引使用 SQLite
- 文件由摄像头定时上传至 NAS
- 后台按天定时解析视频文件
- 时间轴必须显式展示断档

### 2.2 第一阶段不做

- 多摄像头
- 用户登录与权限系统
- 云端部署
- 实时转码
- AI 事件识别
- 缩略图预览
- 手机端专项适配
- HLS 预生成

## 3. 技术路线对比与结论

### 3.1 方案 A：索引优先 + 原始 MP4 回放

后端离线扫描视频文件，解析时间并建立索引；前端按时间点定位到具体 mp4 文件并设置片内偏移播放。

优点：

- 实现复杂度最低
- 断档展示最自然
- 与原始文件一一对应，问题排查简单
- 非常适合本地工具型第一版

缺点：

- 跨切片时会有轻微切换感

### 3.2 方案 B：索引优先 + HLS 作为增强层

在方案 A 的索引基础上，为每日录像额外生成 HLS 播放清单。

优点：

- 后续可提供更连续的播放体验

缺点：

- 预处理更重
- 第一版开发和验证成本明显增加

### 3.3 方案 C：纯流媒体优先

直接把原始文件重组成统一播放流，前端主要围绕流式播放构建。

优点：

- 理论上连续播放体验最好

缺点：

- 时间轴、断档、精确 seek 仍需额外设计
- 第一版风险和复杂度最高

### 3.4 最终结论

第一版采用 **方案 A：索引优先 + 原始 MP4 回放**。

架构上预留未来升级到 HLS 的空间，但当前不实现 HLS 生成与播放。

## 4. 总体架构

系统采用前后端分离架构，后端承担离线索引与视频访问职责，前端承担时间轴回放交互职责。

```text
[NAS 挂载目录]
       │
       ▼
[Python 索引任务]
  - 扫描 mp4 文件
  - 解析文件名时间
  - ffprobe 校验时长
  - 识别断档 / 重叠 / 异常
  - 写入 SQLite
       │
       ▼
[Python API 服务]
  - 日期列表接口
  - 单日时间轴接口
  - 时间点定位接口
  - 视频流访问接口
  - 手动重建索引接口
       │
       ▼
[Web 前端]
  - 日期切换
  - 时间轴展示
  - 点击 / 拖动定位
  - 倍速播放
  - 断档提示
       │
       ▼
[HTML5 Video]
  - 加载原始 mp4
  - 设置 currentTime
  - 处理暂停 / 播放 / 倍速
```

### 4.1 模块边界

#### 文件扫描模块

职责：

- 遍历 NAS 挂载目录
- 识别新增或变更文件
- 采集文件路径、文件名、大小、修改时间

不负责：

- 业务时间推断
- 多文件关系判断

#### 媒体解析模块

职责：

- 从文件名提取开始时间和结束时间
- 调用 `ffprobe` 获取真实时长与媒体信息
- 输出单文件标准化元数据

不负责：

- 断档与重叠判定
- 日期级时间轴构建

#### 时间轴构建模块

职责：

- 按日期聚合同一天涉及的文件
- 识别连续、重叠、断档关系
- 生成前端直接可消费的时间轴片段与断档数据

这是整个系统最核心的业务模块。

#### API 服务模块

职责：

- 查询日期摘要
- 查询单日时间轴
- 定位某个时间点所属片段
- 提供原始视频的 Range 访问

不负责：

- 复杂播放器状态管理

#### Web 播放器模块

职责：

- 渲染日期选择与时间轴
- 处理 seek、倍速、暂停与续播
- 反映断档状态与异常状态

不负责：

- 视频解码
- 时间轴真值计算

## 5. 核心数据流

### 5.1 离线建索引链路

```text
定时任务触发
→ 扫描目标目录
→ 找到新增 / 变化文件
→ 逐个解析文件名与 ffprobe
→ 更新 video_files
→ 重建受影响日期的时间轴
→ 更新 day_summaries
→ 记录 index_jobs
```

### 5.2 在线回放链路

```text
用户选择日期
→ 前端请求当天时间轴
→ 渲染 24 小时时间轴与断档
→ 用户点击或拖动到某个时间点
→ 前端请求 /api/locate 或本地使用时间轴定位
→ video 加载目标 mp4
→ 设置片内偏移并播放
```

## 6. 文件时间识别与校验规则

### 6.1 输入文件命名模式

当前示例文件名模式如下：

```text
00_20260318015937_20260318021002.mp4
```

可解析为：

- 文件名起始时间：`2026-03-18 01:59:37`
- 文件名结束时间：`2026-03-18 02:10:02`

### 6.2 三层时间策略

系统采用“文件名为主，ffprobe 校验，系统生成实际时间”的策略。

#### 规则 1：优先使用文件名解析墙上时间

文件名中的开始和结束时间用来表达摄像头声明的录像时间范围，是时间轴的第一信息源。

#### 规则 2：使用 ffprobe 校验真实媒体时长

读取以下信息：

- `format.duration`
- `start_time`
- 编码信息
- 分辨率

计算：

```text
name_duration_sec = name_end_at - name_start_at
duration_diff_sec = abs(name_duration_sec - probe_duration_sec)
```

#### 规则 3：生成系统认定时间

第一版采用：

- `actual_start_at = name_start_at`
- `actual_end_at = name_start_at + probe_duration_sec`

即：

- 起点优先信文件名
- 终点优先信真实时长

这样可以更早暴露“文件名显示连续，但内容实际不足”的异常情况。

## 7. 异常与断档判定规则

### 7.1 时长不一致

判定条件：

```text
abs((name_end_at - name_start_at) - probe_duration_sec) > threshold
```

建议阈值：

- 小于等于 2 秒：正常
- 大于 2 秒且小于等于 10 秒：警告
- 大于 10 秒：高风险异常

标签：

- `duration_mismatch`

### 7.2 文件无效

场景：

- ffprobe 执行失败
- 时长小于等于 0
- 文件损坏
- 关键元数据缺失

标签：

- `invalid_media`

此类文件保留记录，但不进入可播放时间轴。

### 7.3 前后重叠

当相邻文件存在时间重叠时，标记为：

- `overlap_with_prev`

第一版处理策略：

- 允许存在轻微重叠
- 时间轴构建时按排序顺序裁剪显示边界，避免同一时刻落入多段录像

### 7.4 中间断档

判定条件：

```text
next.actual_start_at - current.actual_end_at > threshold
```

建议阈值：

- 小于等于 2 秒：视为连续
- 大于 2 秒且小于等于 30 秒：小断档
- 大于 30 秒：明显断档

标签：

- `gap_before`
- `gap_after`

断档必须在前端时间轴中显式展示。

## 8. 跨天文件处理规则

文件可能跨越自然日，例如：

```text
00_20260317201545_20260318015937.mp4
```

因此时间轴构建不能仅按文件所在目录或文件名起始日期简单归属。

系统必须按“文件实际时间范围与自然日是否相交”来归属片段。

结论：

- 同一个原始文件可以映射到多个自然日
- `video_files` 保留一条原始文件记录
- `timeline_segments` 可为不同日期拆出多条日内片段

## 9. SQLite 数据模型

第一版建议使用 3 张核心表和 1 张任务表。

### 9.1 `video_files`

用途：记录原始文件及其解析结果。

```sql
CREATE TABLE video_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL UNIQUE,
  file_name TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  file_mtime INTEGER NOT NULL,
  name_start_at TEXT,
  name_end_at TEXT,
  probe_duration_sec REAL,
  probe_video_codec TEXT,
  probe_audio_codec TEXT,
  probe_width INTEGER,
  probe_height INTEGER,
  probe_start_time_sec REAL,
  actual_start_at TEXT,
  actual_end_at TEXT,
  time_source TEXT NOT NULL,
  status TEXT NOT NULL,
  issue_flags TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

关键说明：

- `issue_flags` 使用 JSON 数组字符串保存异常标签
- `time_source` 用于标记时间结论来源，例如 `filename+probe`
- `status` 建议使用 `ready`、`warning`、`invalid`

### 9.2 `timeline_segments`

用途：为前端提供按天回放的标准化片段。

```sql
CREATE TABLE timeline_segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_id INTEGER NOT NULL,
  day TEXT NOT NULL,
  segment_start_at TEXT NOT NULL,
  segment_end_at TEXT NOT NULL,
  duration_sec REAL NOT NULL,
  playback_url TEXT NOT NULL,
  file_offset_sec REAL NOT NULL DEFAULT 0,
  prev_gap_sec REAL,
  next_gap_sec REAL,
  status TEXT NOT NULL,
  FOREIGN KEY(file_id) REFERENCES video_files(id)
);
```

关键说明：

- `day` 为自然日，例如 `2026-03-20`
- 第一版 `file_offset_sec` 大多为 `0`
- `prev_gap_sec`、`next_gap_sec` 用于辅助快速构建断档展示

### 9.3 `day_summaries`

用途：支持日期列表与每日概览。

```sql
CREATE TABLE day_summaries (
  day TEXT PRIMARY KEY,
  first_segment_at TEXT,
  last_segment_at TEXT,
  total_segment_count INTEGER NOT NULL,
  total_recorded_sec REAL NOT NULL,
  total_gap_sec REAL NOT NULL,
  has_warning INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
```

### 9.4 `index_jobs`

用途：跟踪每日索引任务状态，便于补跑与排查。

```sql
CREATE TABLE index_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_day TEXT NOT NULL,
  status TEXT NOT NULL,
  scanned_count INTEGER NOT NULL DEFAULT 0,
  success_count INTEGER NOT NULL DEFAULT 0,
  warning_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL,
  finished_at TEXT
);
```

## 10. 后端 API 设计

### 10.1 `GET /api/days`

用途：

- 返回有录像的日期列表
- 提供每日统计概览

返回示例：

```json
[
  {
    "day": "2026-03-20",
    "segmentCount": 132,
    "recordedSeconds": 81234,
    "gapSeconds": 512,
    "hasWarning": true,
    "firstSegmentAt": "2026-03-20T00:12:15",
    "lastSegmentAt": "2026-03-20T23:58:41"
  }
]
```

### 10.2 `GET /api/timeline?day=2026-03-20`

用途：

- 获取某天完整时间轴
- 返回片段列表与断档列表

返回示例：

```json
{
  "day": "2026-03-20",
  "timezone": "Asia/Shanghai",
  "summary": {
    "segmentCount": 132,
    "recordedSeconds": 81234,
    "gapSeconds": 512,
    "warningCount": 3
  },
  "segments": [
    {
      "id": 101,
      "fileId": 888,
      "startAt": "2026-03-20T02:56:09",
      "endAt": "2026-03-20T03:06:34",
      "durationSec": 625,
      "playbackUrl": "/api/videos/888/stream",
      "fileOffsetSec": 0,
      "status": "ready",
      "issueFlags": []
    }
  ],
  "gaps": [
    {
      "startAt": "2026-03-20T04:09:05",
      "endAt": "2026-03-20T04:11:42",
      "durationSec": 157
    }
  ]
}
```

### 10.3 `GET /api/locate?at=2026-03-20T03:27:15`

用途：

- 将一个真实时间点定位到可播放片段

命中录像时：

```json
{
  "found": true,
  "segment": {
    "id": 105,
    "fileId": 892,
    "startAt": "2026-03-20T03:16:59",
    "endAt": "2026-03-20T03:27:24",
    "playbackUrl": "/api/videos/892/stream"
  },
  "seekOffsetSec": 616
}
```

命中断档时：

```json
{
  "found": false,
  "gap": {
    "startAt": "2026-03-20T03:27:24",
    "endAt": "2026-03-20T03:30:00"
  },
  "nextSegment": {
    "id": 106,
    "startAt": "2026-03-20T03:30:00",
    "endAt": "2026-03-20T03:40:25",
    "playbackUrl": "/api/videos/893/stream"
  }
}
```

第一版前端命中断档时，不自动跳到下一段，而是明确提示“该时间点无录像”。

### 10.4 `GET /api/videos/{fileId}/stream`

用途：

- 为浏览器 `video` 标签提供原始 mp4 访问

要求：

- 支持 HTTP Range
- 正确返回 `Content-Type: video/mp4`

### 10.5 `POST /api/index/rebuild`

用途：

- 手动触发全量或按日重建索引

建议支持：

- `POST /api/index/rebuild`
- `POST /api/index/rebuild?day=2026-03-20`

返回示例：

```json
{
  "accepted": true,
  "jobId": 12,
  "scope": "day",
  "day": "2026-03-20"
}
```

## 11. 定时任务与增量更新策略

### 11.1 推荐执行流程

```text
每天固定时间触发
→ 扫描视频目录
→ 找出新增或变化文件
→ 逐个执行 ffprobe
→ 更新 video_files
→ 重建受影响日期的 timeline_segments
→ 更新 day_summaries
→ 记录 index_jobs
```

### 11.2 增量更新规则

通过以下字段判断文件是否需要重新解析：

- `file_path`
- `file_size`
- `file_mtime`

若三者均未变化，则默认跳过重新探测。

若文件发生变化，则：

1. 重新解析该文件
2. 计算其影响到的日期范围
3. 仅重建受影响日期

### 11.3 失败处理

单文件失败：

- 标记该文件为 `invalid` 或 `warning`
- 不中断整批任务

系统级失败：

- NAS 不可访问
- SQLite 写入失败
- ffprobe 不可用

此类情况将整体任务标记为 `failed`。

## 12. 前端交互设计

### 12.1 页面布局

建议采用单页布局，包含四个区域：

1. 顶部工具栏
2. 中间播放器
3. 下方时间轴
4. 底部控制栏

### 12.2 时间轴设计

时间轴固定展示整天 24 小时，而不是只展示有录像的区间。

设计原则：

- 左端固定 `00:00:00`
- 右端固定 `23:59:59`
- 任一点都对应真实墙上时间

视觉表达建议：

- 蓝色或绿色块：可播放录像
- 黄色强调：存在警告的录像片段
- 灰色空区：断档
- 竖线指针：当前播放位置

### 12.3 点击与拖动规则

- 点击时间轴：立即定位并尝试播放
- 拖动指针：拖动过程中仅更新预览时间，松手后再发起定位

命中录像时：

- 加载对应文件
- 设置 `currentTime = seekOffsetSec`

命中断档时：

- 不自动跳最近片段
- 明确提示“该时间点无录像”

### 12.4 播放状态机

建议前端维护以下状态：

- `idle`
- `loading`
- `playing`
- `paused`
- `gap`
- `error`

### 12.5 跨片段切换策略

播放到片段结尾时：

1. 查找时间上下一段可播放片段
2. 若下一段与当前段间隔小于等于 2 秒，则自动切换并续播
3. 若间隔大于 2 秒，则停止播放并进入 `gap` 状态

### 12.6 倍速策略

第一版支持：

- `1x`
- `2x`
- `4x`

规则：

- 切换片段后保持当前倍速
- 切换日期后保持当前倍速
- 命中断档后保留倍速选择

### 12.7 日期切换策略

切换日期时：

1. 请求当天时间轴
2. 渲染当天录像区间与断档区间
3. 默认不自动播放
4. 指针默认放在当天第一段录像开始时间

若当天无录像：

- 仍展示完整 24 小时时间轴
- 页面提示“当天无录像”

## 13. 技术选型

### 13.1 后端

- Python 3.11+
- FastAPI
- SQLite
- SQLAlchemy 或 SQLModel
- ffprobe / ffmpeg
- APScheduler 或系统 cron

推荐理由：

- FastAPI 适合本地工具型服务
- SQLite 与单用户场景高度匹配
- ffprobe 可为时间索引提供可靠校验

### 13.2 前端

- React
- TypeScript
- Vite
- HTML5 Video
- CSS Modules 或简洁 CSS 方案

推荐理由：

- 开发速度快
- 组件化适合时间轴和播放器拆分
- 原生 `video` 足够覆盖第一版场景

## 14. 建议目录结构

```text
project/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── days.py
│   │   │   ├── timeline.py
│   │   │   ├── locate.py
│   │   │   ├── videos.py
│   │   │   └── index_jobs.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   └── logging.py
│   │   ├── models/
│   │   │   ├── video_file.py
│   │   │   ├── timeline_segment.py
│   │   │   ├── day_summary.py
│   │   │   └── index_job.py
│   │   ├── schemas/
│   │   │   ├── day.py
│   │   │   ├── timeline.py
│   │   │   └── locate.py
│   │   ├── services/
│   │   │   ├── file_scanner.py
│   │   │   ├── media_probe.py
│   │   │   ├── timeline_builder.py
│   │   │   ├── locate_service.py
│   │   │   └── video_stream.py
│   │   ├── tasks/
│   │   │   ├── index_videos.py
│   │   │   └── rebuild_day.py
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   │   ├── PlayerPanel.tsx
│   │   │   ├── TimelineBar.tsx
│   │   │   ├── DatePicker.tsx
│   │   │   └── PlaybackControls.tsx
│   │   ├── hooks/
│   │   ├── pages/
│   │   │   └── ReplayPage.tsx
│   │   ├── types/
│   │   └── main.tsx
│   ├── tests/
│   └── package.json
├── docs/
│   └── superpowers/
│       ├── specs/
│       └── plans/
└── sample-data/
```

## 15. 测试策略

第一版建议至少覆盖以下 4 类测试。

### 15.1 文件名解析测试

验证：

- 正常文件名解析成功
- 跨天文件解析成功
- 非法文件名被识别为异常

### 15.2 时间校验测试

验证：

- 文件名时长与 probe 时长接近时判为正常
- 差异过大时判为警告
- probe 失败时判为无效文件

### 15.3 时间轴构建测试

验证：

- 连续片段排序正确
- 重叠片段可识别
- 断档可识别
- 跨天文件可拆分到多个日期

### 15.4 前端交互测试

验证：

- 点击时间轴能定位到正确片段
- 命中断档时显示无录像状态
- 倍速切换后跨片段仍保持
- 近连续片段能自动续播

## 16. 分阶段实施建议

### 第 1 阶段：后端索引链路

目标：

- 扫描目录
- 解析文件名
- 调用 ffprobe
- 写入 SQLite
- 构建每日时间轴

交付物：

- 数据库结构
- 索引命令
- 可验证的日期级时间轴数据

### 第 2 阶段：后端查询接口

目标：

- 实现 `/api/days`
- 实现 `/api/timeline`
- 实现 `/api/locate`
- 实现 `/api/videos/{fileId}/stream`

交付物：

- 完整查询接口
- 支持前端联调的后端服务

### 第 3 阶段：前端播放器

目标：

- 日期切换
- 时间轴展示
- 点击 / 拖动定位
- 播放 / 暂停
- 倍速切换
- 断档提示

交付物：

- 可用的网页回放页

### 第 4 阶段：体验补齐

目标：

- 自动续播近连续片段
- 手动重建索引
- 异常状态提示
- 本地状态记忆
- 索引任务状态展示

交付物：

- 可长期使用的第一版回放系统

## 17. 风险与设计取舍

### 17.1 文件名与真实内容可能不一致

这是整个系统最重要的风险点，因此必须坚持：

- 文件名提供墙上时间
- ffprobe 提供真实时长
- 系统生成最终认定时间

### 17.2 原始 mp4 播放存在轻微切换感

这是当前版本明确接受的取舍，以换取更低实现复杂度和更快落地速度。

### 17.3 跨天文件会增加时间轴构建复杂度

该复杂度必须在后端解决，不能留给前端临时处理。

## 18. 后续演进方向

在当前设计稳定后，可逐步扩展：

- 多摄像头支持
- 事件标记
- 缩略图预览
- HLS 增强播放
- 异常文件修复工具

## 19. 最终结论

第一版应以“**离线索引 + SQLite 时间轴 + 原始 MP4 回放**”为核心。

后端负责把原始视频文件转化为可靠的时间数据，前端负责让用户按真实日期时间进行可视化回放。

只要时间轴底座做准，后续无论是增强播放体验，还是扩展更多摄像头和能力，都可以在当前架构上平滑演进。

## 20. 当前实现状态（2026-03-25）

截至 2026-03-25，本设计中的第一版核心能力已经完成：

- 后端索引链路已实现：文件扫描、文件名解析、`ffprobe` 校验、按天时间轴构建、`day_summaries` 汇总
- 后端查询接口已实现：`/api/days`、`/api/timeline`、`/api/locate`、`/api/videos/{fileId}/stream`、`/api/index/rebuild`
- 前端回放页已实现：日期切换、24 小时时间轴、断档展示、点击定位、基础播放器、倍速切换
- 播放状态控制已实现：gap 提示、近连续片段自动续播、定位结果防旧响应覆盖

本地联调验证结论：

- 后端测试通过：`63 passed`
- 前端测试通过：`12 passed`
- `uvicorn` 本地启动正常，`GET /api/days` 返回 `200`
- `vite` 本地启动正常，首页可返回 HTML

当前仍属于第一版实现，后续可继续补充：

- 时间轴拖动预览与拖动结束后定位
- 更细的自动续播与暂停策略
- 多摄像头支持与任务状态展示
