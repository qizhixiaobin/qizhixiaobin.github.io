<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

type Bead = { code: string; name: string; hex: string; count: number }
const sourceUrl = ref('')
const selectedFile = ref<File | null>(null)
const patternUrl = ref('')
const columns = ref(48)
const colorLimit = ref(16)
const showGrid = ref(true)
const error = ref('')
const beads = ref<Bead[]>([])
const patternCells = ref<string[]>([])
const patternWidth = ref(0)
const patternHeight = ref(0)
const rows = computed(() => patternHeight.value)
const renderedColumns = computed(() => patternWidth.value)
const totalBeads = computed(() => beads.value.reduce((total, bead) => total + bead.count, 0))
const imageRatio = ref(1)
let renderRequest = 0
const exportFormat = ref<'png' | 'pdf' | 'svg'>('png')
const colorFormat = ref<'hex0x' | 'rgb' | 'hexhash'>('hexhash')

watch([columns, colorLimit, showGrid], () => {
  if (selectedFile.value) loadImage(selectedFile.value)
})

function loadImage(file: File) {
  const request = ++renderRequest
  error.value = ''
  if (!file.type.startsWith('image/')) { error.value = '请选择图片文件。'; return }
  if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value)
  if (patternUrl.value) URL.revokeObjectURL(patternUrl.value)
  sourceUrl.value = URL.createObjectURL(file)
  const image = new Image()
  image.onload = () => {
    if (request !== renderRequest) return
    imageRatio.value = image.height / image.width
    const w = Math.max(1, Math.min(256, Math.round(columns.value)))
    const h = Math.max(1, Math.round(w * image.height / image.width))
    const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, w, h)
    ctx.drawImage(image, 0, 0, w, h)
    const pixels = ctx.getImageData(0, 0, w, h).data
    const cellColors: string[] = []
    const histogram = new Map<string, number>()
    for (let i = 0; i < pixels.length; i += 4) {
      if (pixels[i + 3] < 255) {
        const alpha = pixels[i + 3] / 255
        pixels[i] = Math.round(pixels[i] * alpha + 255 * (1 - alpha))
        pixels[i + 1] = Math.round(pixels[i + 1] * alpha + 255 * (1 - alpha))
        pixels[i + 2] = Math.round(pixels[i + 2] * alpha + 255 * (1 - alpha))
        pixels[i + 3] = 255
      }
      const rgb = [pixels[i], pixels[i + 1], pixels[i + 2]].map((value) => Math.min(255, Math.round(value / 8) * 8))
      const key = rgb.join(',')
      histogram.set(key, (histogram.get(key) ?? 0) + 1)
    }
    const palette = [...histogram.entries()].sort((a, b) => b[1] - a[1]).slice(0, colorLimit.value).map(([key]) => {
      const [r, g, b] = key.split(',').map(Number)
      const code = `RGB(${r}, ${g}, ${b})`
      return { code, name: code, hex: `#${[r, g, b].map((value) => value.toString(16).padStart(2, '0')).join('')}` }
    })
    for (let i = 0; i < pixels.length; i += 4) {
      let best = palette[0], distance = Infinity
      for (const color of palette.slice(0, colorLimit.value)) {
        const r = parseInt(color.hex.slice(1, 3), 16), g = parseInt(color.hex.slice(3, 5), 16), b = parseInt(color.hex.slice(5), 16)
        const d = 2 * (pixels[i] - r) ** 2 + 4 * (pixels[i + 1] - g) ** 2 + 3 * (pixels[i + 2] - b) ** 2
        if (d < distance) { distance = d; best = color }
      }
      const mapped = best
      cellColors.push(mapped.hex)
      pixels[i] = parseInt(mapped.hex.slice(1, 3), 16); pixels[i + 1] = parseInt(mapped.hex.slice(3, 5), 16); pixels[i + 2] = parseInt(mapped.hex.slice(5), 16)
    }
    ctx.putImageData(new ImageData(pixels, w, h), 0, 0)
    const out = document.createElement('canvas'); const scale = Math.max(6, Math.min(18, Math.floor(900 / w))); out.width = w * scale; out.height = h * scale
    const o = out.getContext('2d')!; o.imageSmoothingEnabled = false; o.drawImage(canvas, 0, 0, out.width, out.height)
    if (showGrid.value) { o.strokeStyle = 'rgba(38,59,71,.2)'; o.lineWidth = 1; for(let x=0;x<=w;x++) {o.beginPath();o.moveTo(x*scale,0);o.lineTo(x*scale,out.height);o.stroke()} for(let y=0;y<=h;y++){o.beginPath();o.moveTo(0,y*scale);o.lineTo(out.width,y*scale);o.stroke()} }
    patternUrl.value = out.toDataURL('image/png')
    patternCells.value = cellColors
    patternWidth.value = w
    patternHeight.value = h
    const paletteByHex = new Map(palette.map(color => [color.hex, color]))
    const counts = new Map<string, number>()
    for (const hex of cellColors) counts.set(hex, (counts.get(hex) ?? 0) + 1)
    beads.value = [...counts].flatMap(([hex, count]) => {
      const color = paletteByHex.get(hex)
      return color ? [{ ...color, count }] : []
    }).sort((a, b) => b.count - a.count)
  }
  image.onerror = () => { if (request === renderRequest) error.value = '图片读取失败，请换一张图片。' }
  image.src = sourceUrl.value
}

function onFile(event: Event) { const file = (event.target as HTMLInputElement).files?.[0]; if (file) { selectedFile.value = file; loadImage(file) } }
function formatColor(hex: string) { const rgb=hex.slice(1).match(/.{2}/g)!.map(v=>parseInt(v,16)); return colorFormat.value==='rgb'?`RGB(${rgb.join(', ')})`:colorFormat.value==='hexhash'?hex.toUpperCase():`0x${hex.slice(1).toUpperCase()}` }
function download() {
  if (!patternUrl.value) return
  const header = 72, rowHeight = 28, legendColumns = 3, scale = Math.max(6, Math.min(18, Math.floor(900 / patternWidth.value)))
  const patternPixelWidth = patternWidth.value * scale
  const patternPixelHeight = patternHeight.value * scale
  const legendRows = Math.ceil(beads.value.length / legendColumns)
  const exportHeight = header + patternPixelHeight + legendRows * rowHeight + 30
  if (exportFormat.value === 'svg') {
    const cellRects=patternCells.value.map((color,i)=>`<rect x="${(i%patternWidth.value)*scale}" y="${Math.floor(i/patternWidth.value)*scale+header}" width="${scale}" height="${scale}" fill="${color}"/>`).join('')
    const grid=showGrid.value?`<path d="${Array.from({length:patternWidth.value+1},(_,i)=>`M${i*scale} ${header}v${patternPixelHeight}`).join(' ')} ${Array.from({length:patternHeight.value+1},(_,i)=>`M0 ${header+i*scale}h${patternPixelWidth}`).join(' ')}" fill="none" stroke="#263b4740" stroke-width="1"/>`:''
    const legendY = header + patternPixelHeight + 26
    const legend = beads.value.map((bead,index)=>{
      const x = (index % legendColumns) * (patternPixelWidth / legendColumns) + 16
      const y = legendY + Math.floor(index / legendColumns) * rowHeight
      return `<rect x="${x}" y="${y-12}" width="16" height="16" fill="${bead.hex}" stroke="#263b4740"/><text x="${x+24}" y="${y+1}" fill="#263b47">${formatColor(bead.hex)} · ${bead.count} 颗</text>`
    }).join('')
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${patternPixelWidth}" height="${exportHeight}" viewBox="0 0 ${patternPixelWidth} ${exportHeight}"><rect width="100%" height="100%" fill="#fffaf8"/><text x="24" y="38" fill="#263b47" font-family="sans-serif" font-size="26" font-weight="bold">RGB 拼豆图</text><text x="24" y="61" fill="#6a90a6" font-family="sans-serif" font-size="14">${patternWidth.value} × ${patternHeight.value} 颗 · ${totalBeads.value} 颗 · ${beads.value.length} 色 · RGB 色值</text><g shape-rendering="crispEdges">${cellRects}${grid}</g><g font-family="sans-serif" font-size="13">${legend}</g></svg>`
    saveFile(new Blob([svg],{type:'image/svg+xml'}),'abin-rgb-bead-pattern.svg'); return
  }
  const pattern = new Image(); pattern.onload = () => {
    const canvas = document.createElement('canvas'); canvas.width = pattern.width; canvas.height = exportHeight
    const ctx = canvas.getContext('2d')!; ctx.fillStyle = '#fffaf8'; ctx.fillRect(0,0,canvas.width,canvas.height)
    ctx.fillStyle='#263b47'; ctx.font='bold 26px sans-serif'; ctx.fillText('RGB 拼豆图',24,38)
    ctx.fillStyle='#6a90a6'; ctx.font='14px sans-serif'; ctx.fillText(`${patternWidth.value} × ${patternHeight.value} 颗 · ${totalBeads.value} 颗 · ${beads.value.length} 色 · RGB 色值`,24,61)
    ctx.drawImage(pattern,0,header)
    const y0=header+pattern.height+26, cellW=canvas.width/legendColumns
    ctx.font='13px sans-serif'; beads.value.forEach((bead,index)=>{const x=(index%legendColumns)*cellW+16,y=y0+Math.floor(index/legendColumns)*rowHeight;ctx.fillStyle=bead.hex;ctx.fillRect(x,y-12,16,16);ctx.strokeStyle='#263b4740';ctx.strokeRect(x,y-12,16,16);ctx.fillStyle='#263b47';ctx.fillText(`${formatColor(bead.hex)} · ${bead.count} 颗`,x+24,y+1)})
    if(exportFormat.value==='pdf'){const w=window.open('','_blank');if(!w)return;w.document.write(`<title>Abin RGB Pattern</title><img style="width:100%" src="${canvas.toDataURL('image/png')}" onload="window.print()">`);w.document.close();return}
    canvas.toBlob(blob=>{if(blob)saveFile(blob,'abin-rgb-bead-pattern.png')},'image/png')
  }; pattern.src=patternUrl.value
}
function saveFile(blob:Blob,name:string){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
</script>

<template>
  <div class="bead-app">
    <header><RouterLink to="/?section=diy" class="brand">✦ Abin <span>DIY STUDIO</span></RouterLink><span class="local-note">图片仅在本机处理</span></header>
    <main>
      <section class="intro"><p>IMAGE TO BEADS</p><h1>把喜欢的图片，<em>织成拼豆。</em></h1><span>从图片提取 RGB 色彩，并在图例中完整显示 RGB 数值。</span></section>
      <section class="workspace">
        <aside class="controls">
          <label class="upload"><input type="file" accept="image/*" @change="onFile"/><b>＋</b><strong>选择一张图片</strong><small>PNG、JPG、WebP 等格式</small></label>
          <label class="setting"><span>图案宽度</span><div class="range-row"><input v-model.number="columns" type="range" min="16" max="256"/><input v-model.number="columns" class="number-input" type="number" min="16" max="256" aria-label="图案宽度数值" @change="columns = Math.max(16, Math.min(256, columns || 16))"/><span>颗</span></div></label>
          <label class="setting"><span>颜色数量</span><div class="range-row"><input v-model.number="colorLimit" type="range" min="4" max="36"/><input v-model.number="colorLimit" class="number-input" type="number" min="4" max="36" aria-label="颜色数量数值" @change="colorLimit = Math.max(4, Math.min(36, colorLimit || 4))"/><span>色</span></div></label>
          <label class="check"><input v-model="showGrid" type="checkbox"/>显示拼豆网格</label>
          <fieldset class="export-format"><legend>导出格式</legend><div class="format-options"><label><input v-model="exportFormat" type="radio" value="png"/><span class="format-card"><b>PNG</b><small>方便分享<br/>兼容性好</small></span></label><label><input v-model="exportFormat" type="radio" value="pdf"/><span class="format-card"><b>PDF</b><small>适合打印<br/>纸质参考</small></span></label><label><input v-model="exportFormat" type="radio" value="svg"/><span class="format-card"><b>SVG</b><small>矢量图形<br/>平板放大清晰</small></span></label></div></fieldset>
          <fieldset class="export-format"><legend>色值格式</legend><div class="format-options"><label><input v-model="colorFormat" type="radio" value="hexhash"/><span class="format-card"><b>#HEX</b><small>#RRGGBB<br/>默认 · 网页常用</small></span></label><label><input v-model="colorFormat" type="radio" value="rgb"/><span class="format-card"><b>RGB</b><small>RGB(r, g, b)<br/>通道值</small></span></label><label><input v-model="colorFormat" type="radio" value="hex0x"/><span class="format-card"><b>0x</b><small>0xRRGGBB<br/>十六进制</small></span></label></div></fieldset>
          <button class="download" :disabled="!patternUrl" @click="download">导出拼豆图 ↓</button>
          <p v-if="error" class="error">{{ error }}</p>
        </aside>
        <section class="preview"><div v-if="patternUrl" class="images"><figure><figcaption>生成图 · {{ renderedColumns }} × {{ rows }}</figcaption><img :src="patternUrl" alt="生成的拼豆格图"/></figure><figure><figcaption>原始图片</figcaption><img :src="sourceUrl" alt="上传的原始图片"/></figure></div><div v-else class="empty"><span>▦</span><b>你的拼豆图会出现在这里</b><small>上传图片开始制作</small></div></section>
      </section>
      <section v-if="beads.length" class="palette"><h2>拼豆用量清单 <small>共 {{ totalBeads }} 颗 · {{ renderedColumns }} × {{ rows }} 格</small></h2><span v-for="bead in beads" :key="bead.code"><i :style="{background:bead.hex}"></i>{{ formatColor(bead.hex) }} · {{ bead.count }} 颗</span></section>
    </main>
    <footer><span>Abin · DIY Studio</span><RouterLink to="/?section=diy">返回功能目录</RouterLink></footer>
  </div>
</template>

<style scoped>
.bead-app{min-height:100vh;background:#fffaf8;color:#263b47}.bead-app header,.bead-app footer{height:72px;padding:0 max(24px,calc((100% - 1160px)/2));display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #263b471c}.brand{font:600 19px Georgia,serif}.brand span,.local-note{margin-left:10px;color:#6a90a6;font:10px monospace;letter-spacing:.1em}.local-note{margin:0}.bead-app main{width:min(1160px,calc(100% - 40px));margin:auto;padding:60px 0}.intro p{color:#6a90a6;font:11px monospace;letter-spacing:.15em}.intro h1{font:600 clamp(32px,5vw,56px) Georgia,serif;margin:12px 0}.intro h1 em{color:#6a90a6;font-style:normal}.intro>span{color:#728077}.workspace{display:grid;grid-template-columns:280px 1fr;gap:24px;margin-top:36px}.controls,.preview{padding:22px;border:1px solid #263b4720;border-radius:18px;background:white}.upload{height:150px;border:1px dashed #6a90a6;border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;cursor:pointer}.upload input{display:none}.upload b{font-size:26px;color:#6a90a6}.upload small,.empty small{color:#77877c;font-size:12px}.setting{display:block;margin-top:24px;font-size:13px}.range-row{display:flex;align-items:center;gap:8px;margin-top:10px}.range-row input[type=range]{min-width:0;flex:1;margin:0;accent-color:#6a90a6}.range-row span{color:#728077;font-size:12px}.number-input{width:68px;padding:6px 7px;border:1px solid #263b4728;border-radius:8px;background:#fffaf8;color:#263b47;text-align:center;font:13px monospace}.number-input:focus{outline:2px solid #6a90a655;border-color:#6a90a6}.check{display:flex;gap:8px;margin:22px 0;font-size:13px}.check input{accent-color:#6a90a6}.export-format{margin:20px 0;padding:0;border:0}.export-format legend{margin-bottom:10px;font-size:13px}.format-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.format-options label{cursor:pointer}.format-options input{position:absolute;opacity:0}.format-card{height:62px;padding:5px 4px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;border:1px solid #263b4728;border-radius:10px;background:#fff;color:#263b47}.format-card b{font:600 12px monospace}.format-card small{color:#627078;font-size:9px;line-height:1.2;text-align:center}.format-options input:checked+.format-card{border-color:#6a90a6;background:#edf2f3;box-shadow:inset 0 0 0 1px #6a90a6}.format-options input:focus-visible+.format-card{outline:2px solid #263b47;outline-offset:2px}.download{width:100%;padding:12px;border:0;border-radius:999px;background:#263b47;color:white}.download:disabled{opacity:.4;cursor:not-allowed}.preview{min-height:440px;display:grid;place-items:center;background:#edf2f3}.empty{display:flex;flex-direction:column;align-items:center;gap:12px;color:#6a90a6}.empty span{font-size:60px}.images{display:flex;gap:20px;align-items:flex-start;justify-content:center;width:100%;flex-wrap:wrap}.images figure{margin:0;max-width:48%;text-align:center}.images figcaption{margin-bottom:12px;font-size:12px}.images img{display:block;max-width:100%;max-height:420px;object-fit:contain;image-rendering:pixelated}.palette{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.palette h2{width:100%;font:600 20px Georgia,serif}.palette span{padding:8px 11px;border-radius:999px;background:#edf2f3;font:11px monospace}.palette i{display:inline-block;width:12px;height:12px;margin-right:7px;border-radius:50%;vertical-align:middle}.error{color:#b65e5e}footer{border-top:3px solid #f2b6b6;background:#263b47;color:#fff}footer a{color:#b7cbd2;font-size:13px}@media(max-width:760px){.workspace{grid-template-columns:1fr}.preview{min-height:300px}.bead-app main{padding:38px 0}.images figure{max-width:100%}.bead-app footer{padding:0 20px}}
</style>
