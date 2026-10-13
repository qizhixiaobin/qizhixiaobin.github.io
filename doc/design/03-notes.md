# 03 · 笔记页面（Notes）

## 页面定位

路径为 `/notes`。这是一个可长期积累的公开笔记花园，记录学习、产品、生活与旅行中的短思考。列表页负责发现内容，详情页负责阅读。

## 页面结构

```text
/notes                  笔记列表：标题、标签、日期、阅读时长、摘要
/notes/:slug            单篇笔记：正文、目录、上一篇 / 下一篇
```

## 技术设计

| 范围 | 技术 | 用途 |
| --- | --- | --- |
| 路由 | Vue Router 的静态路由 + 动态参数 | 区分列表页和详情页 |
| 列表 | `NotesView.vue` + `NoteCard.vue` | 筛选、分页或“加载更多” |
| 内容 | 第一阶段 `src/data/notes.ts`；第二阶段 Markdown | 先学 Vue，再引入内容构建链路 |
| 状态 | `ref` + `computed` | 标签筛选、关键词搜索 |
| Markdown（第二阶段） | `markdown-it` 或 Vite 内容插件 | 将 Markdown 安全渲染为 HTML |

```ts
export interface NoteMeta {
  slug: string
  title: string
  date: string
  tags: string[]
  summary: string
  readingMinutes: number
}
```

## 交互规则

- 标签以可访问的 `<button>` 实现；选中项有 `aria-pressed="true"`。
- 搜索首版仅匹配标题、摘要和标签，输入做轻量防抖。
- 单篇详情页的标题和正文由路由 `slug` 找到；找不到时显示 404 页面。
- Markdown 不允许直接放不可信 HTML；个人笔记也要保持渲染器的默认安全策略。

## GitHub Pages 注意事项

GitHub Pages 是静态托管。部署 SPA 时，需要准备 `404.html` 回退或使用 Hash History；更推荐在构建阶段静态生成笔记页。第一版仅用 Router 管理示例内容，部署前再确定静态生成方案。

## 完成标准

- 列表页可以按标签筛选，刷新后内容准确可读。
- 详情 URL 能被复制和打开。
- 空筛选结果有明确的空状态与清除筛选按钮。
