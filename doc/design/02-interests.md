# 02 · 兴趣页面（Interests）

## 页面定位

路径为 `/interests`。它展示工作之外持续滋养你的事物，让个人形象从“技术简历”变成有生活感的人。

## 页面内容

1. **页面引言**：一句关于热爱的短句。
2. **兴趣卡片**：跑步、阅读、摄影、音乐等；每张卡片展示频率、进度或近期状态。
3. **近期清单**：本月正在读、正在听、正在练习的内容。
4. **延伸入口**：将某项兴趣关联到笔记、照片或地图地点。

## 技术设计

| 范围 | 技术 | 用途 |
| --- | --- | --- |
| 页面 | `InterestsView.vue` | 兴趣列表与筛选状态 |
| 组件 | `InterestCard.vue` | 通过 props 接收图标、标题、说明和状态 |
| 数据 | `src/data/interests.ts` | 以数组管理兴趣，方便增删排序 |
| 交互 | `ref`、`computed` | 可选的标签筛选与“展开更多” |
| 样式 | CSS Grid + Container Query（可选） | 卡片随容器宽度自适应 |

```ts
export interface Interest {
  title: string
  category: 'outdoor' | 'creative' | 'learning'
  description: string
  status: string
  link?: string
}
```

## 交互与视觉规则

- 卡片 hover 上移 4px；触屏设备不依赖 hover 才能看到信息。
- 图标优先使用简洁符号或本地 SVG；避免为小图标引入完整图标库。
- 兴趣筛选切换只过滤卡片，不改变 URL 的第一版可接受；后续可将筛选项放进 query string。

## 完成标准

- 卡片文字长度增加时仍保持稳定高度或自然换行。
- 所有兴趣图标都有文字标题，不将符号作为唯一信息载体。
- 该页不使用全局状态管理；跨页共享的兴趣标签出现后再考虑 Pinia。
