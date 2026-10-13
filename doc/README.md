# Forest Bloom 设计文档索引

本目录记录 Forest Bloom 个人网站的产品与前端设计约定。所有页面先以本地静态数据实现，再逐步演进为独立 Vue 路由与内容文件。

| 文档 | 页面 / 范围 | 当前阶段 |
| --- | --- | --- |
| [forest-bloom-design.md](./design/forest-bloom-design.md) | 视觉语言与全站信息架构 | 已完成 |
| [01-journey.md](./design/01-journey.md) | 经历（默认首页） | 原型已完成 |
| [02-interests.md](./design/02-interests.md) | 兴趣 | 原型已完成 |
| [03-notes.md](./design/03-notes.md) | 笔记 | 原型已完成 |
| [04-map.md](./design/04-map.md) | 地图 | 原型已完成 |
| [05-shell-and-footer.md](./design/05-shell-and-footer.md) | Header、切换动画、Footer 与部署 | 原型已完成 |

## 开发顺序

1. 先将 `App.vue` 中的页面片段拆到 `views/` 和 `components/`。
2. 建立 Vue Router 路由，使每个栏目有可分享的 URL。
3. 将页面内联示例数据移动到 `src/data/`；笔记进一步迁为 Markdown。
4. 最后处理 GitHub Pages 的构建、资源路径和部署工作流。
