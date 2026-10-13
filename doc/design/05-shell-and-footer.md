# 05 · 全局框架、页间切换与 Footer

## 范围

这份文档描述所有页面共享的 Header、导航、页面切换动画、Footer 以及 GitHub Pages 部署边界。

## Header

### 内容与排版

- 顶部是全宽贴边、桌面端约 360–440px 高的完整个人封面，主色采用雾蓝 `#6A90A6` 和柔粉 `#F2B6B6` 撞色；第一版用 CSS 渐变，后续可在配置中替换为个人背景图。横幅本身不使用圆角或左右外边距。
- 头像位于封面左下方；第一版显示姓名首字，后续替换为本地头像图片。
- 资料直接叠放于封面右侧，使用深色渐变遮罩保证可读性：名称、账号、个人简介、IP 属地和当前所在地均右对齐。
- 资料底部显示经历阶段、公开笔记、城市足迹统计，以及 GitHub 和邮件入口，避免封面出现无意义留白。
- 经历、兴趣、笔记、地图导航独立位于封面下方；点击头像回到经历首页。

头像、背景和资料需集中到 `src/data/profile.ts` 管理，避免散落在模板中：

```ts
export const profile = {
  name: '你的名字',
  avatar: '',
  coverImage: '',
  bio: '用代码记录生活，也在每一段平凡日子里持续生长。',
  ip: 'IP 属地：吉林',
  location: '现居 · 中国',
}
```

### 技术

| 内容 | 技术 | 说明 |
| --- | --- | --- |
| 封面 | CSS linear-gradient / `background-image` | 无图片时使用撞色渐变；有个人图片时采用 `background-size: cover`、`background-position: center 42%`、禁止重复，确保不拉伸且适应横幅比例 |
| 头像 | `<img>` + 文字 fallback | 图片加载失败时仍显示可识别的姓名首字；只保留外部边框，不使用内部白色圆线 |
| 导航 | `RouterLink` | 自动管理 active class 和可访问 URL |
| 移动端 | `ref<boolean>` | 控制目录开关和 `aria-expanded` |
| 数据 | `src/config/navigation.ts` | 用数组生成导航，避免模板重复 |
| 样式 | CSS media query | 小屏减少封面高度，资料仍然右对齐，导航可横向滚动 |

## 页面切换

原型中用 Vue `<Transition mode="out-in">` 切换内联栏目。正式实现改为：

```vue
<RouterView v-slot="{ Component, route }">
  <Transition :name="transitionName" mode="out-in">
    <component :is="Component" :key="route.path" />
  </Transition>
</RouterView>
```

- 向右侧栏目导航：旧页向左淡出，新页从右侧进入。
- 返回左侧栏目：反向播放。
- `prefers-reduced-motion: reduce` 下取消位移动画。
- 页面切换后将焦点移到 `<main tabindex="-1">`，帮助键盘和读屏用户确认上下文改变。

## Footer

### 内容

- 固定文案：“想聊聊？随时来信。”
- 邮箱、GitHub、可选社交链接。
- 年份和技术栈署名。

### 技术

- `AppFooter.vue` 使用 props 接收链接数组，或从 `src/config/site.ts` 读取。
- 对外链接加 `target="_blank" rel="noreferrer"`，邮件使用 `mailto:`。
- Footer 在内容之后，不使用 `position: fixed`，避免遮挡小屏幕页面。

## GitHub Pages 部署设计

| 项目 | 方案 |
| --- | --- |
| 构建工具 | Vite |
| 发布产物 | `dist/` |
| 自动化 | GitHub Actions，在 push 到默认分支时执行 `npm ci`、`npm run build`、上传并部署 `dist` |
| 仓库子路径 | 若仓库不是 `用户名.github.io`，在 `vite.config.ts` 配置 `base: '/仓库名/'` |
| 静态资源 | 放在 `public/` 或使用 Vite 的 `new URL(..., import.meta.url)` 管理 |

## 完成标准

- 每个主栏目都有独立 URL、当前态和正确的浏览器前进/后退行为。
- 页面在低动态设置下仍清晰可用。
- 无论页面内容高度如何，Footer 都不覆盖内容。
