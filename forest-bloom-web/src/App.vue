<script setup lang="ts">
import { computed, ref } from 'vue'
import { profile } from './data/profile'

type Page = 'journey' | 'interests' | 'notes' | 'map'

const activePage = ref<Page>('journey')
const direction = ref<'forward' | 'back'>('forward')
const pages: Array<{ id: Page; label: string; index: string }> = [
  { id: 'journey', label: '经历', index: '01' },
  { id: 'interests', label: '兴趣', index: '02' },
  { id: 'notes', label: '笔记', index: '03' },
  { id: 'map', label: '地图', index: '04' },
]
const activeLabel = computed(() => pages.find((page) => page.id === activePage.value)?.label)

function changePage(page: Page) {
  const next = pages.findIndex((item) => item.id === page)
  const current = pages.findIndex((item) => item.id === activePage.value)
  direction.value = next > current ? 'forward' : 'back'
  activePage.value = page
}
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="profile-hero" :style="profile.coverImage ? { backgroundImage: `url(${profile.coverImage})` } : undefined">
        <span v-if="!profile.coverImage" class="cover-orb orb-blue" aria-hidden="true"></span>
        <span v-if="!profile.coverImage" class="cover-orb orb-pink" aria-hidden="true"></span>
        <div class="hero-shade" aria-hidden="true"></div>
        <div class="profile-details">
          <p class="profile-kicker">PERSONAL SPACE · 2026</p>
          <div class="name-line"><h1>{{ profile.name }}</h1><span class="verified" aria-label="个人认证">✦</span></div>
          <p class="handle">{{ profile.handle }}</p>
          <p class="profile-bio">{{ profile.bio }}</p>
          <div class="profile-meta"><span>{{ profile.ip }}</span><i></i><span>{{ profile.location }}</span></div>
          <div class="profile-stats" aria-label="个人统计">
            <div v-for="stat in profile.stats" :key="stat.label"><strong>{{ stat.value }}</strong><span>{{ stat.label }}</span></div>
          </div>
          <div class="profile-actions">
            <a :href="profile.githubUrl" target="_blank" rel="noreferrer">GitHub <span>↗</span></a>
            <a :href="`mailto:${profile.email}`">写封邮件 <span>↗</span></a>
          </div>
        </div>
        <a class="avatar" :class="{ 'has-image': profile.avatarImage }" :style="profile.avatarImage ? { backgroundImage: `url(${profile.avatarImage})` } : undefined" href="#" aria-label="返回经历首页" @click.prevent="changePage('journey')"><span v-if="!profile.avatarImage">你</span></a>
      </div>
      <nav class="profile-nav" aria-label="主导航">
        <button
          v-for="page in pages"
          :key="page.id"
          :class="{ active: activePage === page.id }"
          :aria-current="activePage === page.id ? 'page' : undefined"
          @click="changePage(page.id)"
        >
          <small>{{ page.index }}</small>{{ page.label }}
        </button>
      </nav>
    </header>

    <main>
      <p class="section-mark">{{ pages.find((page) => page.id === activePage)?.index }} / {{ activeLabel?.toUpperCase() }}</p>
      <Transition :name="direction === 'forward' ? 'slide-forward' : 'slide-back'" mode="out-in">
        <section :key="activePage" class="page-content">
          <template v-if="activePage === 'journey'">
            <div class="hero-copy">
              <p class="eyebrow">PERSONAL JOURNEY · 2026</p>
              <h1>把走过的路，<br />种成一座<em>花园。</em></h1>
              <p class="lead">这里收集我正在成为的模样，也为每一段值得回望的时光留下坐标。</p>
            </div>
            <div class="timeline" aria-label="人生经历时间轴">
              <article><span>2016</span><div><p>第一次写下代码</p><h2>好奇心，开始有了方向</h2></div></article>
              <article class="featured"><span>2020</span><div><p>大学 · 计算机科学</p><h2>把喜欢的事，变成可以创造的事</h2><b>正在阅读</b></div></article>
              <article><span>2024</span><div><p>工作与持续学习</p><h2>在真实的问题里继续生长</h2></div></article>
            </div>
          </template>

          <template v-else-if="activePage === 'interests'">
            <div class="hero-copy compact"><p class="eyebrow">THINGS I KEEP RETURNING TO</p><h1>让日子有光的，<br />是那些小小的<em>热爱。</em></h1></div>
            <div class="card-grid">
              <article v-for="item in [['跑步','用双脚重新认识城市','每周 3 次'], ['阅读','在别人的故事里旅行','今年 12 本'], ['摄影','记录光落下来的瞬间','持续练习中']]" :key="item[0]" class="soft-card">
                <i>✦</i><p>{{ item[2] }}</p><h2>{{ item[0] }}</h2><span>{{ item[1] }}</span>
              </article>
            </div>
          </template>

          <template v-else-if="activePage === 'notes'">
            <div class="hero-copy compact"><p class="eyebrow">NOTES FROM THE GARDEN</p><h1>一些思考，<br />一些还在发芽的<em>问题。</em></h1></div>
            <div class="note-list">
              <article v-for="note in [['设计不是装饰，是选择','产品 / 05 MIN'], ['如何与长期目标和平相处','生活 / 03 MIN'], ['写给开始学习前端的自己','学习 / 08 MIN']]" :key="note[0]"><span>{{ note[1] }}</span><h2>{{ note[0] }}</h2><b>↗</b></article>
            </div>
          </template>

          <template v-else>
            <div class="hero-copy compact"><p class="eyebrow">PLACES, STORIES, WISHES</p><h1>把去过和想去的地方，<br />标成自己的<em>坐标。</em></h1></div>
            <div class="map-panel"><span class="pin pin-one">长春</span><span class="pin pin-two">上海</span><span class="pin pin-three">京都</span><div class="map-caption"><p>03 places collected</p><h2>脚步会记得，<em>心也会。</em></h2></div></div>
          </template>
        </section>
      </Transition>
    </main>

    <footer>
      <div><p class="eyebrow">KEEP IN TOUCH</p><h2>想聊聊？<br /><em>随时来信。</em></h2></div>
      <a class="mail" href="mailto:abin_fu@foxamil.com">abin_fu@foxamil.com <span>↗</span></a>
      <p class="copyright">© 2026 BLOOM · BUILT WITH CURIOSITY</p>
    </footer>
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; overflow: hidden; position: relative; }
.site-header, main, footer { width: min(1160px, calc(100% - 48px)); margin: auto; position: relative; }
.site-header { width: 100%; overflow: hidden; border-bottom: 1px solid rgba(32,51,43,.16); background: #f8f5ef; }
.profile-hero { min-height: clamp(360px, 32vw, 440px); padding: 44px 5vw; position: relative; display: flex; justify-content: flex-end; align-items: center; overflow: hidden; background-color: #6a90a6; background-image: linear-gradient(108deg, #6a90a6 0%, #88a7b5 42%, #f2b6b6 100%); background-position: center 42%; background-repeat: no-repeat; background-size: cover; }.hero-shade { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(15,27,35,.22) 0%, rgba(15,27,35,.03) 42%, rgba(15,27,35,.62) 100%); }.cover-orb { position: absolute; border-radius: 50%; filter: blur(2px); }.orb-blue { width: 300px; height: 300px; top: -100px; left: 16%; background: rgba(42,78,96,.38); }.orb-pink { width: 400px; height: 400px; right: 7%; top: -200px; border: 1px solid rgba(255,255,255,.34); background: rgba(255,222,214,.24); }
.profile-details { z-index: 1; width: min(520px, 54vw); color: white; text-align: right; }.profile-kicker, .handle { margin: 0; color: rgba(255,255,255,.72); font: 11px 'DM Mono', monospace; letter-spacing: .08em; }.name-line { display: flex; gap: 9px; align-items: center; justify-content: flex-end; margin-top: 7px; }.name-line h1 { margin: 0; color: white; font: 600 clamp(32px, 3vw, 44px) 'Noto Serif SC', serif; text-shadow: 0 3px 18px rgba(0,0,0,.2); }.verified { width: 21px; height: 21px; display: grid; place-items: center; color: #fff; border-radius: 50%; background: #6a90a6; box-shadow: 0 2px 10px rgba(0,0,0,.24); font-size: 11px; }.handle { margin-top: 6px; }.profile-bio { margin: 19px 0 0 auto; max-width: 490px; color: rgba(255,255,255,.95); line-height: 1.75; font-size: 14px; }.profile-meta { display: flex; justify-content: flex-end; align-items: center; gap: 9px; margin-top: 13px; color: rgba(255,255,255,.78); font-size: 12px; }.profile-meta i { width: 3px; height: 3px; border-radius: 50%; background: #f2b6b6; }.profile-stats { display: flex; justify-content: flex-end; gap: 0; margin-top: 27px; }.profile-stats div { min-width: 92px; padding: 0 13px; border-left: 1px solid rgba(255,255,255,.3); }.profile-stats div:first-child { border-left: 0; }.profile-stats strong, .profile-stats span { display: block; }.profile-stats strong { font: 500 21px 'DM Mono', monospace; }.profile-stats span { margin-top: 4px; color: rgba(255,255,255,.7); font-size: 11px; }.profile-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }.profile-actions a { padding: 8px 12px; border: 1px solid rgba(255,255,255,.6); border-radius: 999px; color: white; font-size: 12px; transition: background .18s ease, color .18s ease; }.profile-actions a:hover { background: white; color: #263b47; }.profile-actions span { margin-left: 5px; }.avatar { position: absolute; z-index: 1; left: 5vw; bottom: 43px; width: clamp(118px, 10vw, 150px); aspect-ratio: 1; display: grid; place-items: center; border: 5px solid rgba(255,255,255,.94); border-radius: 50%; background: radial-gradient(circle at 33% 30%, #f4d7cb 0 8%, transparent 8.5%), linear-gradient(140deg, #2e4b5d, #6a90a6 50%, #f2b6b6); color: white; box-shadow: 0 10px 28px rgba(0,0,0,.3); font: 600 42px 'Noto Serif SC', serif; }.avatar.has-image { background-position: center; background-repeat: no-repeat; background-size: cover; }
.profile-nav { min-height: 65px; padding: 0 5vw; display: flex; align-items: center; gap: 5px; border-top: 1px solid var(--line); background: #fffaf8; } .profile-nav button { border: 0; background: transparent; color: #627078; padding: 10px 15px; border-radius: 999px; } .profile-nav button:hover, .profile-nav button.active { background: #6a90a6; color: white; } .profile-nav small { margin-right: 6px; opacity: .7; font: 10px 'DM Mono', monospace; }
h1 em, h2 em { font-family: 'Noto Serif SC', serif; font-style: normal; color: var(--moss); }
main { min-height: 650px; padding: 50px 0 72px; }.section-mark, .eyebrow, .copyright { color: #77877c; font: 11px 'DM Mono', monospace; letter-spacing: .09em; }.section-mark { margin: 0 0 42px; }
.page-content { min-height: 500px; }.hero-copy { max-width: 675px; }.hero-copy.compact { max-width: 800px; }.eyebrow { margin: 0 0 18px; }.hero-copy h1 { margin: 0; font: 600 clamp(42px, 6vw, 75px)/1.18 'Noto Serif SC', serif; letter-spacing: -.05em; }.lead { max-width: 425px; margin: 28px 0 0; color: #58675e; line-height: 1.9; font-size: 16px; }
.timeline { border-top: 1px solid var(--line); margin-top: 70px; display: grid; grid-template-columns: repeat(3, 1fr); }.timeline article { min-height: 230px; padding: 22px 26px 25px 0; border-right: 1px solid var(--line); }.timeline article + article { padding-left: 26px; }.timeline article:last-child { border-right: 0; }.timeline span, .note-list span, .soft-card p { color: var(--moss); font: 11px 'DM Mono', monospace; }.timeline p { margin: 30px 0 10px; color: #728077; font-size: 13px; }.timeline h2, .soft-card h2 { font: 600 23px/1.4 'Noto Serif SC', serif; margin: 0; }.featured { background: var(--mist); margin-top: -15px; border-radius: 20px; padding-top: 37px !important; }.featured b { display: inline-block; margin-top: 23px; background: var(--petal); padding: 5px 9px; border-radius: 20px; font: 10px 'DM Mono', monospace; }
.card-grid { margin-top: 55px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }.soft-card { min-height: 230px; padding: 28px; border-radius: 20px; background: var(--mist); transition: transform .18s ease; }.soft-card:hover { transform: translateY(-4px); }.soft-card i { color: var(--petal); font-style: normal; }.soft-card p { margin: 35px 0 7px; }.soft-card span { display: block; color: #6a786f; margin-top: 12px; }
.note-list { margin-top: 50px; border-top: 1px solid var(--line); }.note-list article { display: grid; grid-template-columns: 180px 1fr auto; align-items: center; min-height: 105px; border-bottom: 1px solid var(--line); }.note-list h2 { margin: 0; font: 600 24px 'Noto Serif SC', serif; }.note-list b { font-size: 23px; color: var(--moss); }
.map-panel { height: 350px; margin-top: 47px; border-radius: 24px; position: relative; overflow: hidden; background: linear-gradient(125deg, #dce5d3 0%, #c5d5bc 40%, #e4d9ad 100%); }.map-panel::before, .map-panel::after { content: ''; position: absolute; inset: 15% 8%; border: 2px solid rgba(79,114,93,.18); border-radius: 45% 55% 43% 57%; transform: rotate(-12deg); }.map-panel::after { inset: 32% 22%; transform: rotate(25deg); }.pin { position: absolute; z-index: 1; padding: 8px 12px; border-radius: 999px; background: var(--ink); color: white; font-size: 13px; box-shadow: 0 8px 16px rgba(32,51,43,.16); }.pin-one { left: 22%; top: 31%; }.pin-two { left: 51%; top: 55%; }.pin-three { right: 20%; top: 22%; }.map-caption { position: absolute; z-index: 2; left: 28px; bottom: 24px; }.map-caption p { font: 11px 'DM Mono', monospace; }.map-caption h2 { margin: 7px 0 0; font: 600 25px 'Noto Serif SC', serif; }
footer { border-top: 1px solid var(--line); padding: 58px 0 35px; display: grid; grid-template-columns: 1fr auto; align-items: end; } footer h2 { margin: 0; font: 600 37px/1.3 'Noto Serif SC', serif; }.mail { color: var(--moss); font: 16px 'DM Mono', monospace; border-bottom: 1px solid var(--moss); padding-bottom: 8px; }.mail span { margin-left: 8px; }.copyright { grid-column: 1 / -1; margin: 60px 0 0; }
.slide-forward-enter-active, .slide-forward-leave-active, .slide-back-enter-active, .slide-back-leave-active { transition: all .42s cubic-bezier(.22, .61, .36, 1); }.slide-forward-enter-from, .slide-back-leave-to { opacity: 0; transform: translateX(52px); }.slide-forward-leave-to, .slide-back-enter-from { opacity: 0; transform: translateX(-52px); }
@media (max-width: 760px) { main, footer { width: min(100% - 28px, 1160px); }.profile-hero { min-height: 415px; padding: 34px 22px 27px; align-items: flex-end; }.hero-shade { background: linear-gradient(180deg, rgba(15,27,35,.14), rgba(15,27,35,.72)); }.profile-details { width: 100%; }.profile-kicker { font-size: 10px; }.name-line h1 { font-size: 31px; }.profile-bio { font-size: 13px; }.profile-stats div { min-width: 0; flex: 1; padding: 0 8px; }.profile-actions { margin-top: 18px; }.avatar { left: 22px; bottom: auto; top: 27px; width: 94px; font-size: 29px; }.profile-nav { padding: 0 10px; overflow-x: auto; }.profile-nav button { white-space: nowrap; padding: 10px 11px; }.timeline, .card-grid { grid-template-columns: 1fr; }.timeline article { min-height: 155px; border-right: 0; border-bottom: 1px solid var(--line); padding: 22px 0 !important; }.featured { margin: 0 -14px; padding: 26px 14px !important; }.note-list article { grid-template-columns: 1fr auto; gap: 10px; padding: 22px 0; }.note-list span { grid-column: 1 / -1; }.note-list h2 { font-size: 20px; } footer { grid-template-columns: 1fr; gap: 35px; }.hero-copy h1 { font-size: clamp(38px, 11vw, 58px); } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; } }
</style>
