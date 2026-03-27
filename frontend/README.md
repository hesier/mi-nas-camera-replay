# Frontend

## 作用

前端提供本地网页回放界面，当前能力包括：

- 单密码登录与会话恢复
- 多通道切换
- 按日期切换回放
- 播放器内嵌时间轴
- 点击时间轴定位
- 断档提示
- `0.5x / 1x / 2x / 4x` 倍速切换

## 环境准备

```bash
cd frontend
npm install
```

## 启动开发环境

```bash
cd frontend
npm run dev
```

默认地址：`http://127.0.0.1:5173`

## 接口代理

开发环境已内置 Vite 代理：

- 浏览器访问 `/api/...`
- 自动转发到 `http://127.0.0.1:8000`

因此本地开发时，不需要额外设置 `VITE_API_BASE_URL`。

如果后端不是运行在 `127.0.0.1:8000`，则需要调整 [vite.config.ts](/Users/siyu/develop/ai/mi/frontend/vite.config.ts) 中的代理目标，或显式配置 `VITE_API_BASE_URL`。

注意：

- 所有请求默认都会带 `credentials: 'include'`
- 本地联调时，前后端必须统一 host 形态：都用 `127.0.0.1`、都用 `localhost`，或者通过同源代理访问
- 不要一边开 `http://localhost:5173`，一边把接口打到 `http://127.0.0.1:8000`，否则浏览器可能不会携带登录 Cookie

## 测试

```bash
cd frontend
npm test
npx tsc --noEmit
```

## 构建

```bash
cd frontend
npx vite build
```

## 常见问题

- 页面能打开但数据请求 404：先确认后端是否已启动在 `127.0.0.1:8000`
- 页面一直显示登录页：先确认密码正确、后端 `/api/auth/status` 可访问，并且没有混用 `localhost` / `127.0.0.1`
- 页面没有日期：先确认后端已完成一次初始化扫描
- 某个通道显示“该通道暂无录像”：说明该通道当前没有可用日期，前端不会继续请求时间轴
- 单通道时看不到通道选择器：属于预期
- 视频无法播放：先检查 `/api/videos/{fileId}/stream` 是否可直接访问
- 修改前端代码后代理不生效：重启 `npm run dev`
