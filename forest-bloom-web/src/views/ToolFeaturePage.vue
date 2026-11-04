<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { profile } from '../data/profile'

type PaletteColor = { id: string; code: string; name: string; hex: string; enabled: boolean }
type Bead = PaletteColor & { count: number }
type ColorOverride = { sourceHex: string; targetHex: string }
type CellCoordinate = { row: number; column: number; label: string }
type SavedWorkspace = {
  version: 1; width: number; height: number; cells: string[]; beads: Bead[]; sourceImage: string
  cleared?: boolean
  showAuthorMark?: boolean
  colorSource: 'personal' | 'image'; columns: number; colorLimit: number; showGrid: boolean; showBeadStyle: boolean
  exportFormat: 'png' | 'pdf' | 'svg'; colorFormat: 'hex0x' | 'rgb' | 'hexhash'; colorOverrides: ColorOverride[]
  hiddenColors: string[]; fullScreenFit: 'contain' | 'cover'; zoom: number; panX: number; panY: number
  selectedCell: { row: number; column: number } | null
  beadLabelMode: 'export' | 'name' | 'code'
}
const sourceUrl = ref('')
const previewElement = ref<HTMLElement | null>(null)
const infoDialogOpen = ref(false)
const toastMessage = ref('')
const selectedFile = ref<File | null>(null)
const patternUrl = ref('')
const columns = ref(48)
const colorSource = ref<'personal' | 'image'>('image')
const colorLimit = ref(16)
const showGrid = ref(true)
const showBeadStyle = ref(false)
const showAuthorMark = ref(true)
const hiddenColors = ref<string[]>([])
const beadMode = ref(false)
const fullScreenFit = ref<'contain' | 'cover'>('contain')
const fullscreenSvgUrl = ref('')
const fullscreenViewport = ref<HTMLElement | null>(null)
const minimapElement = ref<HTMLElement | null>(null)
const fullscreenImageSize = ref({ width: 0, height: 0 })
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
const colorsPanelOpen = ref(false)
const fullscreenColorSearch = ref('')
const beadLabelMode = ref<'export' | 'name' | 'code'>('export')
const hoveredCell = ref<CellCoordinate | null>(null)
const selectedCell = ref<CellCoordinate | null>(null)
const activeCell = computed(() => hoveredCell.value ?? selectedCell.value)
const activeCellBead = computed(() => {
  if (!activeCell.value) return undefined
  const hex = patternCells.value[(activeCell.value.row - 1) * patternWidth.value + activeCell.value.column - 1]
  return beads.value.find(bead => bead.hex === hex)
})
const fullscreenBeads = computed(() => beads.value.filter(bead =>
  `${bead.code} ${bead.name} ${bead.hex}`.toLowerCase().includes(fullscreenColorSearch.value.trim().toLowerCase())
))
const savedSourceImage = ref('')
const authorAvatarDataUrl = ref('')
const error = ref('')
const beads = ref<Bead[]>([])
const patternCells = ref<string[]>([])
const patternWidth = ref(0)
const patternHeight = ref(0)
const palette = ref<PaletteColor[]>(readSavedPalette())
const enabledPalette = computed(() => palette.value.filter(color => color.enabled))
const paletteSearch = ref('')
const showEnabledOnly = ref(false)
const filteredPalette = computed(() => palette.value.filter(color =>
  (!showEnabledOnly.value || color.enabled) &&
  `${color.code} ${color.name} ${color.hex}`.toLowerCase().includes(paletteSearch.value.trim().toLowerCase())
))
const newColorHex = ref('#c77878')
const newColorCode = ref('')
const newColorName = ref('')
const editingColorId = ref('')
const colorOverrides = ref<ColorOverride[]>([])
const samplingColor = ref('')
const samplingMode = ref(false)
const rows = computed(() => patternHeight.value)
const renderedColumns = computed(() => patternWidth.value)
const totalBeads = computed(() => beads.value.reduce((total, bead) => total + bead.count, 0))
const fullscreenImageStyle = computed(() => ({
  width: `${fullscreenImageSize.value.width}px`, height: `${fullscreenImageSize.value.height}px`,
  '--pan-x': `${panX.value}px`, '--pan-y': `${panY.value}px`, '--zoom': zoom.value
}))
const coordinateMarkerStyle = computed(() => {
  const cell = activeCell.value, bounds = fullscreenViewport.value?.getBoundingClientRect()
  if (!cell || !bounds || !fullscreenImageSize.value.width || !fullscreenImageSize.value.height) return { display: 'none' }
  const cellWidth = fullscreenImageSize.value.width * zoom.value / patternWidth.value
  const cellHeight = fullscreenImageSize.value.height * zoom.value / patternHeight.value
  const boardLeft = bounds.width / 2 + panX.value - fullscreenImageSize.value.width * zoom.value / 2
  const boardTop = bounds.height / 2 + panY.value - fullscreenImageSize.value.height * zoom.value / 2
  return { left: `${boardLeft + (cell.column - 1) * cellWidth}px`, top: `${boardTop + (cell.row - 1) * cellHeight}px`, width: `${cellWidth}px`, height: `${cellHeight}px` }
})
const minimapStyle = computed(() => {
  const bounds = fullscreenViewport.value?.getBoundingClientRect()
  const minimapBounds = minimapElement.value?.getBoundingClientRect()
  const boxWidth = minimapBounds?.width ?? 150, boxHeight = minimapBounds?.height ?? 90
  if (!bounds || !patternWidth.value || !patternHeight.value || !fullscreenImageSize.value.width) return { image: {}, view: {} }
  const scale = Math.min(boxWidth / patternWidth.value, boxHeight / patternHeight.value)
  const width = patternWidth.value * scale, height = patternHeight.value * scale
  const left = (boxWidth - width) / 2, top = (boxHeight - height) / 2
  const scaledWidth = fullscreenImageSize.value.width * zoom.value
  const scaledHeight = fullscreenImageSize.value.height * zoom.value
  const visibleWidth = Math.min(width, bounds.width / scaledWidth * width)
  const visibleHeight = Math.min(height, bounds.height / scaledHeight * height)
  const visibleLeft = Math.max(left, Math.min(left + width - visibleWidth, left + (0.5 - (bounds.width / 2 + panX.value) / scaledWidth) * width))
  const visibleTop = Math.max(top, Math.min(top + height - visibleHeight, top + (0.5 - (bounds.height / 2 + panY.value) / scaledHeight) * height))
  return {
    image: { left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` },
    view: { left: `${visibleLeft}px`, top: `${visibleTop}px`, width: `${visibleWidth}px`, height: `${visibleHeight}px` }
  }
})
const columnTicks = computed(() => makeColumnTicks())
const rowTicks = computed(() => makeRowTicks())
let renderRequest = 0
let toastTimer = 0
const exportFormat = ref<'png' | 'pdf' | 'svg'>('png')
const colorFormat = ref<'hex0x' | 'rgb' | 'hexhash'>('hexhash')

watch(() => palette.value.map(color => `${color.id}:${color.code}:${color.name}:${color.hex}:${color.enabled}`).join('|'), () => savePalette())
watch([columns, colorSource, colorLimit, showGrid, showBeadStyle, () => enabledPalette.value.map(color => `${color.id}:${color.code}:${color.name}:${color.hex}`).join('|'), () => JSON.stringify(colorOverrides.value)], () => {
  if (selectedFile.value) loadImage(selectedFile.value)
  saveWorkspace()
})
watch([exportFormat, colorFormat, hiddenColors, fullScreenFit, zoom, beadLabelMode, showAuthorMark], () => saveWorkspace())
watch([patternUrl, hiddenColors, showGrid, showBeadStyle], () => {
  if (beadMode.value && patternCells.value.length) updateFullscreenSvg()
})

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
  window.addEventListener('keydown', onBeadModeKeydown)
  window.addEventListener('resize', updateFullscreenLayout)
  loadAuthorAvatar()
  restoreWorkspace()
})
onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  window.removeEventListener('keydown', onBeadModeKeydown)
  window.removeEventListener('resize', updateFullscreenLayout)
  window.clearTimeout(toastTimer)
  if (fullscreenSvgUrl.value) URL.revokeObjectURL(fullscreenSvgUrl.value)
})

function loadImage(file: File) {
  const request = ++renderRequest
  error.value = ''
  if (!file.type.startsWith('image/')) { error.value = '请选择图片文件。'; return }
  if (sourceUrl.value.startsWith('blob:')) URL.revokeObjectURL(sourceUrl.value)
  if (patternUrl.value) URL.revokeObjectURL(patternUrl.value)
  const fileUrl = URL.createObjectURL(file)
  sourceUrl.value = fileUrl
  const image = new Image()
  image.onload = () => {
    if (request !== renderRequest) return
    const normalizedSource = compressSourceImage(image, image.naturalWidth, image.naturalHeight)
    savedSourceImage.value = normalizedSource
    if (sourceUrl.value.startsWith('blob:')) {
      URL.revokeObjectURL(sourceUrl.value)
      sourceUrl.value = normalizedSource
    }
    scrollPreviewOnMobile()
    if (colorSource.value === 'personal' && !enabledPalette.value.length) {
      patternUrl.value = ''
      beads.value = []
      error.value = ''
      showToast('个人色库还没有可用颜色，请先添加并启用至少一种拼豆颜色。')
      return
    }
    const w = Math.max(1, Math.min(256, Math.round(columns.value)))
    const h = Math.max(1, Math.round(w * image.height / image.width))
    const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, w, h)
    ctx.drawImage(image, 0, 0, w, h)
    const pixels = ctx.getImageData(0, 0, w, h).data
    const cellColors: string[] = []
    for (let i = 0; i < pixels.length; i += 4) {
      if (pixels[i + 3]! < 255) {
        const alpha = pixels[i + 3]! / 255
        pixels[i] = Math.round(pixels[i]! * alpha + 255 * (1 - alpha))
        pixels[i + 1] = Math.round(pixels[i + 1]! * alpha + 255 * (1 - alpha))
        pixels[i + 2] = Math.round(pixels[i + 2]! * alpha + 255 * (1 - alpha))
        pixels[i + 3] = 255
      }
    }
    const activePalette: PaletteColor[] = colorSource.value === 'personal'
      ? enabledPalette.value
      : (() => {
          const histogram = new Map<string, number>()
          for (let i = 0; i < pixels.length; i += 4) {
            const rgb: [number, number, number] = [
              Math.min(255, Math.round(pixels[i]! / 8) * 8),
              Math.min(255, Math.round(pixels[i + 1]! / 8) * 8),
              Math.min(255, Math.round(pixels[i + 2]! / 8) * 8)
            ]
            const key = rgb.map(value => value.toString(16).padStart(2, '0')).join('').toUpperCase()
            histogram.set(key, (histogram.get(key) ?? 0) + 1)
          }
          return [...histogram.entries()].sort((a, b) => b[1] - a[1]).slice(0, colorLimit.value).map(([hex], index) => ({
            id: `image-${hex}`,
            code: `IMG-${String(index + 1).padStart(2, '0')}`,
            name: `图片色 ${index + 1}`,
            hex: `#${hex}`,
            enabled: true
          }))
        })()
    if (!activePalette.length) {
      patternUrl.value = ''; beads.value = []; error.value = '当前没有可用于转换的颜色，请启用色板颜色或提高图片颜色上限。'; return
    }
    const paletteColors = activePalette.map(color => ({ color, rgb: hexToRgb(color.hex) }))
    const overrides = colorOverrides.value.map(item => ({
      item,
      rgb: hexToRgb(item.sourceHex)
    }))
    for (let i = 0; i < pixels.length; i += 4) {
      let closestOverride: ColorOverride | undefined
      let overrideDistance = 18 ** 2 * 9
      for (const override of colorSource.value === 'personal' ? overrides : []) {
        const [r, g, b] = override.rgb
        const distance = 2 * (pixels[i]! - r) ** 2 + 4 * (pixels[i + 1]! - g) ** 2 + 3 * (pixels[i + 2]! - b) ** 2
        if (distance < overrideDistance) { overrideDistance = distance; closestOverride = override.item }
      }
      const manualTarget = closestOverride && activePalette.find(color => color.hex === closestOverride!.targetHex)
      let best = manualTarget ?? activePalette[0]!
      let distance = manualTarget ? 0 : Infinity
      if (distance === Infinity) for (const candidate of paletteColors) {
        const [r, g, b] = candidate.rgb
        const d = 2 * (pixels[i]! - r) ** 2 + 4 * (pixels[i + 1]! - g) ** 2 + 3 * (pixels[i + 2]! - b) ** 2
        if (d < distance) { distance = d; best = candidate.color }
      }
      cellColors.push(best.hex)
    }
    patternCells.value = cellColors
    patternWidth.value = w
    patternHeight.value = h
    if (selectedCell.value && (selectedCell.value.row > h || selectedCell.value.column > w)) selectedCell.value = null
    const paletteByHex = new Map(activePalette.map(color => [color.hex, color]))
    const counts = new Map<string, number>()
    for (const hex of cellColors) counts.set(hex, (counts.get(hex) ?? 0) + 1)
    beads.value = [...counts].flatMap(([hex, count]) => {
      const color = paletteByHex.get(hex)
      return color ? [{ ...color, count }] : []
    }).sort((a, b) => b.count - a.count)
    const renderedHexes = new Set(beads.value.map(bead => bead.hex))
    hiddenColors.value = hiddenColors.value.filter(hex => renderedHexes.has(hex))
    patternUrl.value = createPatternDataUrl(cellColors, w, h)
    saveWorkspace()
  }
  image.onerror = () => { if (request === renderRequest) error.value = '图片读取失败，请换一张图片。' }
  if (typeof createImageBitmap === 'function') {
    void createImageBitmap(file, { imageOrientation: 'from-image' }).then(bitmap => {
      try {
        if (request !== renderRequest) {
          URL.revokeObjectURL(fileUrl)
          return
        }
        const normalizedSource = compressSourceImage(bitmap, bitmap.width, bitmap.height)
        URL.revokeObjectURL(fileUrl)
        sourceUrl.value = normalizedSource
        image.src = normalizedSource
      } catch {
        if (request === renderRequest) image.src = fileUrl
        else URL.revokeObjectURL(fileUrl)
      } finally {
        bitmap.close()
      }
    }).catch(() => {
      if (request === renderRequest) image.src = fileUrl
      else URL.revokeObjectURL(fileUrl)
    })
  } else {
    image.src = fileUrl
  }
}

function compressSourceImage(image: CanvasImageSource, width: number, height: number) {
  const ratio = Math.min(1, 1200 / Math.max(width, height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(width * ratio))
  canvas.height = Math.max(1, Math.round(height * ratio))
  const context = canvas.getContext('2d')!
  context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/jpeg', 0.82)
}

function loadAuthorAvatar() {
  const image = new Image()
  image.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = 96; canvas.height = 96
    const context = canvas.getContext('2d')
    if (!context) return
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    try { authorAvatarDataUrl.value = canvas.toDataURL('image/jpeg', 0.86) } catch { /* keep the initials fallback */ }
  }
  image.src = profile.avatarImage
}

function createPatternDataUrl(cells: string[], width: number, height: number) {
  const scale = Math.max(6, Math.min(18, Math.floor(900 / width)))
  const canvas = document.createElement('canvas'); canvas.width = width * scale; canvas.height = height * scale
  const context = canvas.getContext('2d')!; context.imageSmoothingEnabled = false
  context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height)
  if (showBeadStyle.value) drawBeadCells(context, cells, width, scale)
  else cells.forEach((color, index) => {
    context.fillStyle = color
    context.fillRect((index % width) * scale, Math.floor(index / width) * scale, scale, scale)
  })
  if (showGrid.value) {
    context.strokeStyle = 'rgba(38,59,71,.2)'; context.lineWidth = 1
    for (let x = 0; x <= width; x++) { context.beginPath(); context.moveTo(x * scale, 0); context.lineTo(x * scale, canvas.height); context.stroke() }
    for (let y = 0; y <= height; y++) { context.beginPath(); context.moveTo(0, y * scale); context.lineTo(canvas.width, y * scale); context.stroke() }
  }
  return canvas.toDataURL('image/png')
}

function drawBeadCells(context: CanvasRenderingContext2D, cells: string[], width: number, scale: number, offsetX = 0, offsetY = 0, hidden = new Set<string>()) {
  cells.forEach((color, index) => {
    if (hidden.has(color)) return
    const centerX = offsetX + (index % width + 0.5) * scale
    const centerY = offsetY + (Math.floor(index / width) + 0.5) * scale
    const radius = scale * 0.42
    context.beginPath(); context.arc(centerX, centerY, radius, 0, Math.PI * 2)
    context.fillStyle = color; context.fill()
    context.lineWidth = Math.max(0.6, scale * 0.045); context.strokeStyle = 'rgba(38,59,71,.38)'; context.stroke()
    context.beginPath(); context.arc(centerX, centerY, scale * 0.16, 0, Math.PI * 2)
    context.fillStyle = '#fff'; context.fill()
    context.lineWidth = Math.max(0.5, scale * 0.025); context.strokeStyle = 'rgba(38,59,71,.22)'; context.stroke()
  })
}

function saveWorkspace() {
  const hasPattern = patternCells.value.length > 0
  const saved: SavedWorkspace = {
    version: 1, cleared: !hasPattern,
    width: hasPattern ? patternWidth.value : 0, height: hasPattern ? patternHeight.value : 0,
    cells: hasPattern ? patternCells.value : [], beads: hasPattern ? beads.value : [],
    sourceImage: hasPattern ? savedSourceImage.value : '', colorSource: colorSource.value,
    columns: columns.value, colorLimit: colorLimit.value, showGrid: showGrid.value,
    showBeadStyle: showBeadStyle.value, showAuthorMark: showAuthorMark.value,
    exportFormat: exportFormat.value, colorFormat: colorFormat.value,
    colorOverrides: colorOverrides.value, hiddenColors: hiddenColors.value, fullScreenFit: fullScreenFit.value,
    zoom: zoom.value, panX: panX.value, panY: panY.value, beadLabelMode: beadLabelMode.value,
    selectedCell: selectedCell.value ? { row: selectedCell.value.row, column: selectedCell.value.column } : null
  }
  try { localStorage.setItem('abin-bead-workspace-v1', JSON.stringify(saved)) }
  catch { error.value = '当前图案无法完整保存在本地，请尝试降低图案宽度。' }
}

async function restoreWorkspace() {
  try {
    const raw = localStorage.getItem('abin-bead-workspace-v1')
    if (!raw) return
    const saved = JSON.parse(raw) as SavedWorkspace
    if (saved.version !== 1) return
    columns.value = saved.columns
    colorSource.value = saved.colorSource
    colorLimit.value = saved.colorLimit
    showGrid.value = saved.showGrid
    showBeadStyle.value = saved.showBeadStyle
    showAuthorMark.value = saved.showAuthorMark !== false
    exportFormat.value = saved.exportFormat
    colorFormat.value = saved.colorFormat
    colorOverrides.value = saved.colorOverrides ?? []
    hiddenColors.value = saved.hiddenColors ?? []
    fullScreenFit.value = saved.fullScreenFit ?? 'contain'
    zoom.value = Math.min(5, Math.max(1, saved.zoom ?? 1))
    panX.value = saved.panX ?? 0
    panY.value = saved.panY ?? 0
    beadLabelMode.value = saved.beadLabelMode ?? 'export'
    if (saved.cleared) return
    if (!Number.isInteger(saved.width) || !Number.isInteger(saved.height) ||
      saved.width < 1 || saved.height < 1 || !Array.isArray(saved.cells) || saved.cells.length !== saved.width * saved.height ||
      saved.cells.some(color => typeof color !== 'string' || !/^#[\da-f]{6}$/i.test(color)) || !Array.isArray(saved.beads)) return
    selectedCell.value = saved.selectedCell && saved.selectedCell.row >= 1 && saved.selectedCell.row <= saved.height && saved.selectedCell.column >= 1 && saved.selectedCell.column <= saved.width
      ? { ...saved.selectedCell, label: `${excelColumn(saved.selectedCell.column)}${saved.selectedCell.row}` }
      : null
    patternWidth.value = saved.width
    patternHeight.value = saved.height
    patternCells.value = saved.cells
    beads.value = saved.beads
    savedSourceImage.value = saved.sourceImage ?? ''
    patternUrl.value = createPatternDataUrl(saved.cells, saved.width, saved.height)
    if (savedSourceImage.value) {
      const blob = await (await fetch(savedSourceImage.value)).blob()
      const file = new File([blob], 'saved-pattern-source.jpg', { type: 'image/jpeg' })
      selectedFile.value = file
      sourceUrl.value = URL.createObjectURL(file)
    }
  } catch { error.value = '上次保存的拼豆图无法读取；个人色板仍保留在本地。' }
}

async function enterBeadMode() {
  if (!patternCells.value.length) return
  beadMode.value = true
  updateFullscreenSvg()
  let fullscreenRequest: Promise<void> | undefined
  try { fullscreenRequest = document.documentElement.requestFullscreen?.() } catch { /* fixed viewport mode remains available */ }
  await nextTick()
  updateFullscreenLayout()
  try { await fullscreenRequest } catch { /* fixed viewport mode remains available */ }
  updateFullscreenLayout()
}

async function exitBeadMode() {
  beadMode.value = false
  if (document.fullscreenElement) {
    try { await document.exitFullscreen() } catch { /* mode is already closed */ }
  }
}

function onFullscreenChange() {
  if (!document.fullscreenElement) beadMode.value = false
}

function onBeadModeKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && toastMessage.value) { toastMessage.value = ''; return }
  if (event.key === 'Escape' && infoDialogOpen.value) { infoDialogOpen.value = false; return }
  if (event.key === 'Escape' && beadMode.value && !document.fullscreenElement) beadMode.value = false
}

function resetLocalData() {
  if (!window.confirm('这会清除本工具保存的个人色板、当前拼豆图和设置，是否继续？')) return
  try {
    localStorage.removeItem('abin-bead-palette-v1')
    localStorage.removeItem('abin-bead-workspace-v1')
    window.location.reload()
  } catch { error.value = '清除本地数据失败，请检查浏览器的站点存储设置。' }
}

function clearImage() {
  renderRequest++
  if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value)
  if (fullscreenSvgUrl.value) URL.revokeObjectURL(fullscreenSvgUrl.value)
  sourceUrl.value = ''
  fullscreenSvgUrl.value = ''
  selectedFile.value = null
  savedSourceImage.value = ''
  patternUrl.value = ''
  patternCells.value = []
  beads.value = []
  patternWidth.value = 0
  patternHeight.value = 0
  selectedCell.value = null
  hoveredCell.value = null
  samplingColor.value = ''
  samplingMode.value = false
  error.value = ''
  toastMessage.value = ''
  saveWorkspace()
}

function toggleHiddenColor(hex: string) {
  hiddenColors.value = hiddenColors.value.includes(hex)
    ? hiddenColors.value.filter(color => color !== hex)
    : [...hiddenColors.value, hex]
}

function updateFullscreenSvg() {
  if (fullscreenSvgUrl.value) URL.revokeObjectURL(fullscreenSvgUrl.value)
  const svg = createFullscreenSvg(patternCells.value, patternWidth.value, patternHeight.value, hiddenColors.value)
  fullscreenSvgUrl.value = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }))
}

function createFullscreenSvg(cells: string[], width: number, height: number, hidden: string[]) {
  const unit = 12, hiddenSet = new Set(hidden)
  const shapes = cells.map((color, index) => {
    if (hiddenSet.has(color)) return ''
    const x = index % width, y = Math.floor(index / width)
    if (showBeadStyle.value) {
      const cx = (x + 0.5) * unit, cy = (y + 0.5) * unit
      return `<circle cx="${cx}" cy="${cy}" r="${unit * .42}" fill="${color}" stroke="#263b4761" stroke-width=".55"/><circle cx="${cx}" cy="${cy}" r="${unit * .16}" fill="#fff" stroke="#263b4738" stroke-width=".3"/>`
    }
    return `<rect x="${x * unit}" y="${y * unit}" width="${unit}" height="${unit}" fill="${color}"/>`
  }).join('')
  const grid = showGrid.value
    ? `<path d="${Array.from({ length: width + 1 }, (_, i) => `M${i * unit} 0v${height * unit}`).join(' ')} ${Array.from({ length: height + 1 }, (_, i) => `M0 ${i * unit}h${width * unit}`).join(' ')}" fill="none" stroke="#263b4740" stroke-width=".5"/>`
    : ''
  const renderMode = showBeadStyle.value ? 'geometricPrecision' : 'crispEdges'
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width * unit}" height="${height * unit}" viewBox="0 0 ${width * unit} ${height * unit}"><rect width="100%" height="100%" fill="#fff"/><g shape-rendering="${renderMode}">${shapes}${grid}</g></svg>`
}

function showAllFullscreenColors() { hiddenColors.value = [] }
function hideAllFullscreenColors() { hiddenColors.value = beads.value.map(bead => bead.hex) }

function excelColumn(column: number) {
  let value = column, label = ''
  while (value > 0) { value--; label = String.fromCharCode(65 + value % 26) + label; value = Math.floor(value / 26) }
  return label
}

function coordinateAt(clientX: number, clientY: number): CellCoordinate | null {
  const bounds = fullscreenViewport.value?.getBoundingClientRect()
  const imageWidth = fullscreenImageSize.value.width * zoom.value
  const imageHeight = fullscreenImageSize.value.height * zoom.value
  if (!bounds || !imageWidth || !imageHeight) return null
  const imageLeft = bounds.width / 2 + panX.value - imageWidth / 2
  const imageTop = bounds.height / 2 + panY.value - imageHeight / 2
  const column = Math.floor((clientX - bounds.left - imageLeft) / imageWidth * patternWidth.value) + 1
  const row = Math.floor((clientY - bounds.top - imageTop) / imageHeight * patternHeight.value) + 1
  if (row < 1 || row > patternHeight.value || column < 1 || column > patternWidth.value) return null
  return { row, column, label: `${excelColumn(column)}${row}` }
}

function makeColumnTicks() {
  const bounds = fullscreenViewport.value?.getBoundingClientRect(), imageWidth = fullscreenImageSize.value.width * zoom.value
  if (!bounds || !imageWidth || !patternWidth.value) return []
  const cellSize = imageWidth / patternWidth.value
  const imageLeft = bounds.width / 2 + panX.value - imageWidth / 2
  const ticks = []
  for (let column = 1; column <= patternWidth.value; column++) {
    const left = imageLeft + (column - 0.5) * cellSize
    if (left >= -cellSize / 2 && left <= bounds.width + cellSize / 2) ticks.push({ column, left, label: excelColumn(column) })
  }
  return ticks
}

function makeRowTicks() {
  const bounds = fullscreenViewport.value?.getBoundingClientRect(), imageHeight = fullscreenImageSize.value.height * zoom.value
  if (!bounds || !imageHeight || !patternHeight.value) return []
  const cellSize = imageHeight / patternHeight.value
  const imageTop = bounds.height / 2 + panY.value - imageHeight / 2
  const ticks = []
  for (let row = 1; row <= patternHeight.value; row++) {
    const top = imageTop + (row - 0.5) * cellSize
    if (top >= -cellSize / 2 && top <= bounds.height + cellSize / 2) ticks.push({ row, top })
  }
  return ticks
}

function moveToMinimap(event: PointerEvent) {
  const bounds = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const scale = Math.min(bounds.width / patternWidth.value, bounds.height / patternHeight.value)
  const imageWidth = patternWidth.value * scale, imageHeight = patternHeight.value * scale
  const left = bounds.width / 2 - imageWidth / 2, top = bounds.height / 2 - imageHeight / 2
  const x = Math.max(0, Math.min(1, (event.clientX - bounds.left - left) / imageWidth))
  const y = Math.max(0, Math.min(1, (event.clientY - bounds.top - top) / imageHeight))
  panX.value = (0.5 - x) * fullscreenImageSize.value.width * zoom.value
  panY.value = (0.5 - y) * fullscreenImageSize.value.height * zoom.value
  clampPan()
  saveWorkspace()
}

function setFullscreenFit(mode: 'contain' | 'cover') {
  fullScreenFit.value = mode
  zoom.value = 1
  panX.value = 0
  panY.value = 0
  nextTick(updateFullscreenLayout)
}

function clampPan() {
  const bounds = fullscreenViewport.value?.getBoundingClientRect()
  if (!bounds || !fullscreenImageSize.value.width || !fullscreenImageSize.value.height) return
  const maxX = Math.max(0, (fullscreenImageSize.value.width * zoom.value - bounds.width) / 2)
  const maxY = Math.max(0, (fullscreenImageSize.value.height * zoom.value - bounds.height) / 2)
  panX.value = Math.max(-maxX, Math.min(maxX, panX.value))
  panY.value = Math.max(-maxY, Math.min(maxY, panY.value))
}

function updateFullscreenLayout() {
  const bounds = fullscreenViewport.value?.getBoundingClientRect()
  if (!bounds || !bounds.width || !bounds.height || !patternWidth.value || !patternHeight.value) return
  const scaleX = bounds.width / patternWidth.value, scaleY = bounds.height / patternHeight.value
  const scale = fullScreenFit.value === 'contain' ? Math.min(scaleX, scaleY) : Math.max(scaleX, scaleY)
  fullscreenImageSize.value = { width: patternWidth.value * scale, height: patternHeight.value * scale }
  clampPan()
}

function setZoom(nextZoom: number, anchor?: { x: number; y: number }) {
  const next = Math.max(1, Math.min(5, nextZoom))
  const ratio = next / zoom.value
  if (anchor && fullscreenViewport.value) {
    const bounds = fullscreenViewport.value.getBoundingClientRect()
    const focusX = anchor.x - bounds.left - bounds.width / 2
    const focusY = anchor.y - bounds.top - bounds.height / 2
    panX.value = panX.value * ratio + focusX * (1 - ratio)
    panY.value = panY.value * ratio + focusY * (1 - ratio)
  }
  zoom.value = next
  clampPan()
}
function onZoomInput(event: Event) { setZoom(Number((event.target as HTMLInputElement).value)) }
function resetZoom() { zoom.value = 1; panX.value = 0; panY.value = 0 }

let dragStart: { x: number; y: number; panX: number; panY: number } | undefined
const isPanning = ref(false)
function startPan(event: PointerEvent) {
  if (event.button !== 0 && event.pointerType === 'mouse') return
  dragStart = { x: event.clientX, y: event.clientY, panX: panX.value, panY: panY.value }
  isPanning.value = true
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}
function movePan(event: PointerEvent) {
  if (!dragStart) { hoveredCell.value = coordinateAt(event.clientX, event.clientY); return }
  panX.value = dragStart.panX + event.clientX - dragStart.x
  panY.value = dragStart.panY + event.clientY - dragStart.y
  clampPan()
}
function endPan(event: PointerEvent) {
  if (!dragStart) return
  const moved = Math.hypot(event.clientX - dragStart.x, event.clientY - dragStart.y)
  if (event.type === 'pointerup' && moved < 5) {
    selectedCell.value = coordinateAt(event.clientX, event.clientY)
    saveWorkspace()
  }
  dragStart = undefined
  isPanning.value = false
  saveWorkspace()
}
function clearHoveredCell() { hoveredCell.value = null }
function zoomAtPointer(event: WheelEvent) {
  setZoom(zoom.value * (event.deltaY < 0 ? 1.12 : 1 / 1.12), { x: event.clientX, y: event.clientY })
}

function readSavedPalette(): PaletteColor[] {
  try {
    const saved = localStorage.getItem('abin-bead-palette-v1')
    if (!saved) return []
    const parsed = JSON.parse(saved)
    return Array.isArray(parsed) ? parsed.filter((color): color is PaletteColor =>
      typeof color?.id === 'string' && typeof color.code === 'string' && typeof color.name === 'string' &&
      /^#[\da-f]{6}$/i.test(color.hex) && typeof color.enabled === 'boolean'
    ) : []
  } catch { return [] }
}

function savePalette() {
  try { localStorage.setItem('abin-bead-palette-v1', JSON.stringify(palette.value)) }
  catch { error.value = '无法保存色板，请检查浏览器本地存储空间。' }
}

function addPaletteColor() {
  const hex = newColorHex.value.trim().startsWith('#') ? newColorHex.value.trim() : `#${newColorHex.value.trim()}`
  const code = newColorCode.value.trim()
  if (!/^#[\da-f]{6}$/i.test(hex)) { error.value = '颜色值请填写 6 位 HEX，例如 #C77878。'; return }
  if (!code) { error.value = '请填写这颗豆子的色号或自定义标签。'; return }
  if (palette.value.some(color => color.id !== editingColorId.value && color.code.toLowerCase() === code.toLowerCase())) { error.value = '这个色号已存在，请换一个色号。'; return }
  if (palette.value.some(color => color.id !== editingColorId.value && color.hex.toLowerCase() === hex.toLowerCase())) { error.value = '这个 HEX 颜色已经在色板中。'; return }
  const normalized = hex.toUpperCase()
  if (editingColorId.value) {
    const previous = palette.value.find(color => color.id === editingColorId.value)
    palette.value = palette.value.map(color => color.id === editingColorId.value ? { ...color, code, name: newColorName.value.trim() || code, hex: normalized } : color)
    if (previous && previous.hex !== normalized) colorOverrides.value = colorOverrides.value.map(item => item.targetHex === previous.hex ? { ...item, targetHex: normalized } : item)
  } else palette.value.push({ id: crypto.randomUUID(), code, name: newColorName.value.trim() || code, hex: normalized, enabled: true })
  editingColorId.value = ''
  newColorCode.value = ''
  newColorName.value = ''
  error.value = ''
}

function removePaletteColor(id: string) {
  const item = palette.value.find(color => color.id === id)
  if (!item) return
  palette.value = palette.value.filter(color => color.id !== id)
  colorOverrides.value = colorOverrides.value.filter(override => override.targetHex !== item.hex)
  if (editingColorId.value === id) cancelColorEdit()
}

function editPaletteColor(color: PaletteColor) {
  editingColorId.value = color.id
  newColorHex.value = color.hex
  newColorCode.value = color.code
  newColorName.value = color.name
}

function cancelColorEdit() {
  editingColorId.value = ''
  newColorHex.value = '#c77878'
  newColorCode.value = ''
  newColorName.value = ''
}

function exportPalette() {
  const payload = { format: 'abin-bead-palette', version: 1, colors: palette.value.map(({ code, name, hex, enabled }) => ({ code, name, hex, enabled })) }
  saveFile(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }), 'abin-bead-palette.json')
}

function importPalette(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result))
      const source = Array.isArray(parsed) ? parsed : parsed?.colors
      if (!Array.isArray(source) || !source.length) throw new Error('文件里没有颜色数据。')
      const imported: PaletteColor[] = source.map((color: Record<string, unknown>, index: number) => {
        const code = String(color.code ?? color.id ?? '').trim()
        const hex = String(color.hex ?? '').trim()
        if (!code || !/^#[\da-f]{6}$/i.test(hex)) throw new Error(`第 ${index + 1} 个颜色缺少色号，或 HEX 格式不正确。`)
        return { id: crypto.randomUUID(), code, name: String(color.name ?? code), hex: hex.toUpperCase(), enabled: color.enabled !== false }
      })
      const codes = imported.map(color => color.code.toLowerCase())
      if (new Set(codes).size !== codes.length) throw new Error('导入文件中有重复色号，请先整理后再导入。')
      const hexes = imported.map(color => color.hex.toLowerCase())
      if (new Set(hexes).size !== hexes.length) throw new Error('导入文件中有重复 HEX 颜色，请先整理后再导入。')
      palette.value = imported
      cancelColorEdit()
      colorOverrides.value = []
      error.value = ''
    } catch (cause) { error.value = cause instanceof Error ? cause.message : '色板文件读取失败。' }
    ;(event.target as HTMLInputElement).value = ''
  }
  reader.onerror = () => { error.value = '色板文件读取失败。' }
  reader.readAsText(file)
}

function toggleSampling() {
  if (!patternUrl.value) { error.value = '请先上传图片，再从原图取色。'; return }
  samplingMode.value = !samplingMode.value
  if (samplingMode.value) error.value = '点击右侧原图中的一个位置，取样后再点选对应的现有豆色。'
  else error.value = ''
}

function setColorSource(source: 'personal' | 'image') {
  colorSource.value = source
  samplingMode.value = false
  samplingColor.value = ''
  if (source === 'personal' && enabledPalette.value.length === 0) showToast('个人色库还没有可用颜色，请先添加并启用至少一种拼豆颜色。')
  else toastMessage.value = ''
}

function showToast(message: string) {
  toastMessage.value = message
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toastMessage.value = '' }, 4500)
}

function pickImageColor(event: MouseEvent) {
  if (!samplingMode.value || !sourceUrl.value) return
  const imageElement = event.currentTarget as HTMLImageElement
  const bounds = imageElement.getBoundingClientRect()
  const x = Math.max(0, Math.min(imageElement.naturalWidth - 1, Math.floor((event.clientX - bounds.left) / bounds.width * imageElement.naturalWidth)))
  const y = Math.max(0, Math.min(imageElement.naturalHeight - 1, Math.floor((event.clientY - bounds.top) / bounds.height * imageElement.naturalHeight)))
  const sampleImage = new Image()
  sampleImage.onload = () => {
    const canvas = document.createElement('canvas'); canvas.width = 1; canvas.height = 1
    const context = canvas.getContext('2d', { willReadFrequently: true })!
    context.fillStyle = '#fff'; context.fillRect(0, 0, 1, 1)
    context.drawImage(sampleImage, x, y, 1, 1, 0, 0, 1, 1)
    const sampledPixels = context.getImageData(0, 0, 1, 1).data
    const [r, g, b] = [sampledPixels[0]!, sampledPixels[1]!, sampledPixels[2]!]
    samplingColor.value = `#${[r, g, b].map(value => value.toString(16).padStart(2, '0')).join('').toUpperCase()}`
    samplingMode.value = false
    error.value = ''
  }
  sampleImage.src = sourceUrl.value
}

function assignSampleTo(color: PaletteColor) {
  if (!samplingColor.value) return
  colorOverrides.value = [...colorOverrides.value.filter(item => item.sourceHex !== samplingColor.value), { sourceHex: samplingColor.value, targetHex: color.hex }]
  samplingColor.value = ''
}

function clearSampleMapping(sourceHex: string) {
  colorOverrides.value = colorOverrides.value.filter(item => item.sourceHex !== sourceHex)
}

function escapeXml(value: string) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;')
}

function onFile(event: Event) { const file = (event.target as HTMLInputElement).files?.[0]; if (file) { selectedFile.value = file; loadImage(file) } }
function scrollPreviewOnMobile() {
  if (!window.matchMedia('(max-width: 760px)').matches) return
  nextTick(() => requestAnimationFrame(() => previewElement.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })))
}
function hexToRgb(hex: string): [number, number, number] {
  const match = /^#([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex)
  return match ? [parseInt(match[1]!, 16), parseInt(match[2]!, 16), parseInt(match[3]!, 16)] : [0, 0, 0]
}
function formatColor(hex: string) { const rgb=hex.slice(1).match(/.{2}/g)!.map(v=>parseInt(v,16)); return colorFormat.value==='rgb'?`RGB(${rgb.join(', ')})`:colorFormat.value==='hexhash'?hex.toUpperCase():`0x${hex.slice(1).toUpperCase()}` }
function beadLabel(bead: Bead) { return beadLabelMode.value === 'name' ? bead.name : beadLabelMode.value === 'code' ? bead.code : formatColor(bead.hex) }
function download() {
  if (!patternUrl.value) return
  error.value = ''
  const header = showAuthorMark.value ? 96 : 72, rowHeight = 28, legendColumns = 3, scale = Math.max(6, Math.min(18, Math.floor(900 / patternWidth.value)))
  const titleY = showAuthorMark.value ? 36 : 38
  const detailsY = showAuthorMark.value ? 58 : 61
  const patternPixelWidth = patternWidth.value * scale
  const patternPixelHeight = patternHeight.value * scale
  const legendRows = Math.ceil(beads.value.length / legendColumns)
  const exportHeight = header + patternPixelHeight + legendRows * rowHeight + 30
  const authorMarkSvg = !showAuthorMark.value ? '' : authorAvatarDataUrl.value
    ? `<defs><clipPath id="author-avatar-clip"><circle cx="${patternPixelWidth - 91}" cy="78" r="11"/></clipPath></defs><image href="${authorAvatarDataUrl.value}" x="${patternPixelWidth - 102}" y="67" width="22" height="22" preserveAspectRatio="xMidYMid slice" clip-path="url(#author-avatar-clip)"/><circle cx="${patternPixelWidth - 91}" cy="78" r="11" fill="none" stroke="#263b4724"/>`
    : `<circle cx="${patternPixelWidth - 91}" cy="78" r="11" fill="#6a90a6"/><text x="${patternPixelWidth - 91}" y="82" text-anchor="middle" fill="#fff" font-size="11">A</text>`
  const authorLabelSvg = showAuthorMark.value ? `<text x="${patternPixelWidth - 75}" y="82" fill="#78858a" font-family="sans-serif" font-size="11">${escapeXml(profile.name)}</text>` : ''
  if (exportFormat.value === 'svg') {
    const cellRects=showBeadStyle.value
      ? patternCells.value.map((color,i)=>{
          const cx=(i%patternWidth.value+.5)*scale,cy=(Math.floor(i/patternWidth.value)+.5)*scale+header
          return `<circle cx="${cx}" cy="${cy}" r="${scale*.42}" fill="${color}" stroke="#263b4761" stroke-width="${Math.max(.6,scale*.045)}"/><circle cx="${cx}" cy="${cy}" r="${scale*.16}" fill="#fff" stroke="#263b4738" stroke-width="${Math.max(.5,scale*.025)}"/>`
        }).join('')
      : patternCells.value.map((color,i)=>`<rect x="${(i%patternWidth.value)*scale}" y="${Math.floor(i/patternWidth.value)*scale+header}" width="${scale}" height="${scale}" fill="${color}"/>`).join('')
    const grid=showGrid.value?`<path d="${Array.from({length:patternWidth.value+1},(_,i)=>`M${i*scale} ${header}v${patternPixelHeight}`).join(' ')} ${Array.from({length:patternHeight.value+1},(_,i)=>`M0 ${header+i*scale}h${patternPixelWidth}`).join(' ')}" fill="none" stroke="#263b4740" stroke-width="1"/>`:''
    const legendY = header + patternPixelHeight + 26
    const legend = beads.value.map((bead,index)=>{
      const x = (index % legendColumns) * (patternPixelWidth / legendColumns) + 16
      const y = legendY + Math.floor(index / legendColumns) * rowHeight
      return `<rect x="${x}" y="${y-12}" width="16" height="16" fill="${bead.hex}" stroke="#263b4740"/><text x="${x+24}" y="${y+1}" fill="#263b47">${escapeXml(bead.code)} · ${formatColor(bead.hex)} · ${bead.count} 颗</text>`
    }).join('')
    const sourceLabel = colorSource.value === 'personal' ? '个人色库' : '图片原色'
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${patternPixelWidth}" height="${exportHeight}" viewBox="0 0 ${patternPixelWidth} ${exportHeight}"><rect width="100%" height="100%" fill="#fffaf8"/><text x="24" y="${titleY}" fill="#263b47" font-family="sans-serif" font-size="26" font-weight="bold">拼豆图</text><text x="24" y="${detailsY}" fill="#6a90a6" font-family="sans-serif" font-size="14">${patternWidth.value} × ${patternHeight.value} 颗 · ${totalBeads.value} 颗 · ${beads.value.length} 色 · ${sourceLabel}</text>${authorMarkSvg}${authorLabelSvg}<g shape-rendering="${showBeadStyle.value ? 'geometricPrecision' : 'crispEdges'}">${cellRects}${grid}</g><g font-family="sans-serif" font-size="13">${legend}</g></svg>`
    saveFile(new Blob([svg],{type:'image/svg+xml'}),'abin-bead-pattern.svg'); return
  }
  const pattern = new Image(); pattern.onload = () => {
    const canvas = document.createElement('canvas'); canvas.width = pattern.width; canvas.height = exportHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) { error.value = '无法创建导出画布，请刷新页面后重试。'; return }
    ctx.fillStyle = '#fffaf8'; ctx.fillRect(0,0,canvas.width,canvas.height)
    ctx.fillStyle='#263b47'; ctx.font='bold 26px sans-serif'; ctx.fillText('拼豆图',24,titleY)
    const sourceLabel = colorSource.value === 'personal' ? '个人色库' : '图片原色'
    ctx.fillStyle='#6a90a6'; ctx.font='14px sans-serif'; ctx.fillText(`${patternWidth.value} × ${patternHeight.value} 颗 · ${totalBeads.value} 颗 · ${beads.value.length} 色 · ${sourceLabel}`,24,detailsY)
    const avatarX = canvas.width - 102, avatarY = 67
    const finishExport = () => {
      if (!showAuthorMark.value) { finishPatternExport(); return }
      ctx.save(); ctx.beginPath(); ctx.arc(avatarX + 11, avatarY + 11, 11, 0, Math.PI * 2); ctx.clip()
      if (authorAvatarDataUrl.value) {
        const authorAvatar = new Image()
        authorAvatar.onload = () => {
          ctx.drawImage(authorAvatar, avatarX, avatarY, 22, 22); ctx.restore()
          finishPatternExport()
        }
        authorAvatar.onerror = () => { ctx.restore(); drawAuthorFallback(ctx, avatarX, avatarY); finishPatternExport() }
        authorAvatar.src = authorAvatarDataUrl.value
        return
      }
      ctx.restore(); drawAuthorFallback(ctx, avatarX, avatarY)
      finishPatternExport()
    }
    const drawAuthorFallback = (context: CanvasRenderingContext2D, x: number, y: number) => {
      context.beginPath(); context.arc(x + 11, y + 11, 11, 0, Math.PI * 2); context.fillStyle = '#6a90a6'; context.fill()
      context.fillStyle = '#fff'; context.font = '11px sans-serif'; context.textAlign = 'center'; context.fillText('A', x + 11, y + 15); context.textAlign = 'start'
    }
    const finishPatternExport = () => {
      if (showAuthorMark.value) {
        ctx.strokeStyle='#263b4724'; ctx.lineWidth=1; ctx.beginPath(); ctx.arc(avatarX + 11, avatarY + 11, 11, 0, Math.PI * 2); ctx.stroke()
        ctx.fillStyle='#78858a'; ctx.font='11px sans-serif'; ctx.fillText(profile.name,avatarX + 27,82)
      }
      ctx.drawImage(pattern,0,header)
      const y0=header+pattern.height+26, cellW=canvas.width/legendColumns
      ctx.font='13px sans-serif'; beads.value.forEach((bead,index)=>{const x=(index%legendColumns)*cellW+16,y=y0+Math.floor(index/legendColumns)*rowHeight;ctx.fillStyle=bead.hex;ctx.fillRect(x,y-12,16,16);ctx.strokeStyle='#263b4740';ctx.strokeRect(x,y-12,16,16);ctx.fillStyle='#263b47';ctx.fillText(`${bead.code} · ${formatColor(bead.hex)} · ${bead.count} 颗`,x+24,y+1)})
      if(exportFormat.value==='pdf'){
        canvas.toBlob(async jpegBlob => {
          if (!jpegBlob) { error.value = 'PDF 图像编码失败，请稍后重试。'; return }
          try {
            const jpegBytes = new Uint8Array(await jpegBlob.arrayBuffer())
            saveFile(createPdfBlob(canvas.width, canvas.height, jpegBytes), 'abin-bead-pattern.pdf')
          } catch { error.value = 'PDF 生成失败，请稍后重试。' }
        }, 'image/jpeg', 0.94)
        return
      }
      canvas.toBlob(blob=>{
        if(blob) saveFile(blob,'abin-bead-pattern.png')
        else error.value = 'PNG 生成失败，请稍后重试。'
      },'image/png')
    }
    finishExport()
  }
  pattern.onerror = () => { error.value = '无法读取当前拼豆图，请重新生成图案后再导出。' }
  pattern.src=patternUrl.value
}

function createPdfBlob(width: number, height: number, jpegBytes: Uint8Array) {
  const encoder = new TextEncoder()
  const pageWidth = 595.28
  const pageHeight = pageWidth * height / width
  const content = encoder.encode(`q\n${pageWidth} 0 0 ${pageHeight} 0 0 cm\n/Im0 Do\nQ`)
  const chunks: Uint8Array[] = []
  const offsets = [0]
  let byteOffset = 0
  const append = (chunk: Uint8Array) => { chunks.push(chunk); byteOffset += chunk.byteLength }
  const appendObject = (objectNumber: number, body: Uint8Array[]) => {
    offsets[objectNumber] = byteOffset
    body.forEach(append)
  }
  append(encoder.encode('%PDF-1.4\n%\xE2\xE3\xCF\xD3\n'))
  appendObject(1, [encoder.encode('1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')])
  appendObject(2, [encoder.encode('2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')])
  appendObject(3, [encoder.encode(`3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>\nendobj\n`)])
  appendObject(4, [
    encoder.encode(`4 0 obj\n<< /Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.byteLength} >>\nstream\n`),
    jpegBytes,
    encoder.encode('\nendstream\nendobj\n')
  ])
  appendObject(5, [encoder.encode(`5 0 obj\n<< /Length ${content.byteLength} >>\nstream\n`), content, encoder.encode('\nendstream\nendobj\n')])
  const xrefOffset = byteOffset
  const xref = `xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(offset => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`
  append(encoder.encode(xref))
  const pdfBytes = new Uint8Array(byteOffset)
  let cursor = 0
  for (const chunk of chunks) { pdfBytes.set(chunk, cursor); cursor += chunk.byteLength }
  return new Blob([pdfBytes.buffer], { type: 'application/pdf' })
}

function saveFile(blob:Blob,name:string){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.style.display='none';document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1000)}
</script>

<template>
  <div class="bead-app">
    <header><RouterLink to="/?section=diy" class="brand"><img :src="profile.avatarImage" alt=""/><span class="brand-name">{{ profile.name }}</span><span class="brand-divider">·</span><span class="brand-label">DIY STUDIO</span></RouterLink><div class="header-actions"><button type="button" class="header-action info-action" @click="infoDialogOpen = true">功能简介</button><button type="button" class="header-action reset-action" @click="resetLocalData">清除缓存并重置</button><span class="local-note">图片与设置保存在本机</span><RouterLink to="/?section=diy" class="header-back">← 返回 DIY 功能</RouterLink></div></header>
    <main>
      <section class="intro"><p>IMAGE TO BEADS</p><h1>把喜欢的图片，<em>织成拼豆。</em></h1><span>{{ colorSource === 'personal' ? '用你手头的拼豆色板匹配图片，并生成对应的用量清单。' : '保留图片的主要色彩，并生成颜色用量清单。' }}</span></section>
      <section class="workspace">
        <aside class="controls">
          <label class="upload"><input type="file" accept="image/*" @change="onFile"/><b>＋</b><strong>{{ selectedFile ? '图片已选择' : '选择一张图片' }}</strong><small class="upload-file-name" :title="selectedFile?.name">{{ selectedFile?.name ?? 'PNG、JPG、WebP 等格式' }}</small></label>
          <button v-if="sourceUrl || patternUrl || selectedFile" class="clear-image-button" type="button" @click="clearImage">清除图片</button>
          <div class="setting"><span>颜色来源</span><div class="source-switch" role="group" aria-label="图案颜色来源"><button type="button" :class="{ active: colorSource === 'image' }" @click="setColorSource('image')">图片原色</button><button type="button" :class="{ active: colorSource === 'personal' }" @click="setColorSource('personal')">个人色库</button></div><small class="source-hint">{{ colorSource === 'personal' ? '只使用你启用的实物豆色。' : '从图片提取主要颜色，不保证对应手头的豆子。' }}</small></div>
          <label class="setting"><span>图案宽度</span><div class="range-row"><input v-model.number="columns" type="range" min="16" max="256"/><input v-model.number="columns" class="number-input" type="number" min="16" max="256" aria-label="图案宽度数值" @change="columns = Math.max(16, Math.min(256, columns || 16))"/><span>颗</span></div></label>
          <label v-if="colorSource === 'image'" class="setting"><span>图片颜色数量</span><div class="range-row"><input v-model.number="colorLimit" type="range" min="4" max="128"/><input v-model.number="colorLimit" class="number-input" type="number" min="4" max="128" aria-label="图片颜色数量" @change="colorLimit = Math.max(4, Math.min(128, Math.round(colorLimit || 4)))"/><span>色</span></div></label>
          <div class="setting active-colors"><span>{{ colorSource === 'personal' ? '当前可用豆色' : '图片颜色上限' }}</span><b>{{ colorSource === 'personal' ? enabledPalette.length : colorLimit }} 色</b><small>{{ colorSource === 'personal' ? '图案只会使用下方启用的颜色' : '实际用色数以图案中出现的颜色为准' }}</small></div>
          <label class="check"><input v-model="showGrid" type="checkbox"/>显示拼豆网格</label>
          <label class="check bead-style-check"><input v-model="showBeadStyle" type="checkbox"/><span>显示拼豆颗粒<small>圆形豆粒，白色中心孔</small></span></label>
          <fieldset class="export-format"><legend>导出格式</legend><div class="format-options"><label><input v-model="exportFormat" type="radio" value="png"/><span class="format-card"><b>PNG</b><small>方便分享<br/>兼容性好</small></span></label><label><input v-model="exportFormat" type="radio" value="pdf"/><span class="format-card"><b>PDF</b><small>适合打印<br/>纸质参考</small></span></label><label><input v-model="exportFormat" type="radio" value="svg"/><span class="format-card"><b>SVG</b><small>矢量图形<br/>平板放大清晰</small></span></label></div></fieldset>
          <fieldset class="export-format"><legend>色值格式</legend><div class="format-options"><label><input v-model="colorFormat" type="radio" value="hexhash"/><span class="format-card"><b>#HEX</b><small>#RRGGBB<br/>默认 · 网页常用</small></span></label><label><input v-model="colorFormat" type="radio" value="rgb"/><span class="format-card"><b>RGB</b><small>RGB(r, g, b)<br/>通道值</small></span></label><label><input v-model="colorFormat" type="radio" value="hex0x"/><span class="format-card"><b>0x</b><small>0xRRGGBB<br/>十六进制</small></span></label></div></fieldset>
          <label class="check author-mark-toggle"><input v-model="showAuthorMark" type="checkbox"/><span>导出时显示我的头像和名字<small>在图案角落留下轻量署名</small></span></label>
          <button v-if="patternUrl" class="bead-mode-button" type="button" @click="enterBeadMode">进入拼豆模式 ⛶</button>
          <button class="download" :disabled="!patternUrl" @click="download">导出拼豆图 ↓</button>
          <p v-if="error" class="error">{{ error }}</p>
        </aside>
        <section ref="previewElement" class="preview"><div v-if="patternUrl || sourceUrl" class="images"><figure class="generated-figure"><figcaption>生成图{{ patternUrl ? ` · ${renderedColumns} × ${rows}${showBeadStyle ? ' · 拼豆颗粒示意' : ''}` : '' }}</figcaption><img v-if="patternUrl" :src="patternUrl" alt="生成的拼豆格图"/><div v-else class="pattern-unavailable"><span>▦</span><b>暂时无法生成图案</b><small>{{ colorSource === 'personal' ? '请先在下方色板中添加并启用至少一种拼豆颜色。' : '图片正在处理中，请稍候。' }}</small></div></figure><figure v-if="sourceUrl"><figcaption>原始图片 <button v-if="colorSource === 'personal'" type="button" class="sample-button" :class="{ active: samplingMode }" @click="toggleSampling">{{ samplingMode ? '点击图片取色中…' : '从原图取色' }}</button></figcaption><img :src="sourceUrl" alt="上传的原始图片" :class="{ sampling: samplingMode }" @click="pickImageColor"/></figure></div><div v-else class="empty"><span>▦</span><b>你的拼豆图会出现在这里</b><small>上传图片开始制作</small></div>
          <div v-if="samplingColor" class="mapping-tools"><p><i :style="{ background: samplingColor }"></i> 原图颜色 {{ samplingColor }}，选择你手头最接近的豆色：</p><div class="mapping-swatches"><button v-for="color in enabledPalette" :key="color.id" type="button" @click="assignSampleTo(color)"><i :style="{ background: color.hex }"></i>{{ color.code }}</button></div></div>
          <div v-if="colorSource === 'personal' && colorOverrides.length" class="mapping-tools saved-mappings"><strong>手动颜色映射</strong><span v-for="mapping in colorOverrides" :key="mapping.sourceHex" class="mapping-chip"><i :style="{ background: mapping.sourceHex }"></i>{{ mapping.sourceHex }} → <i :style="{ background: palette.find(color => color.hex === mapping.targetHex)?.hex }"></i>{{ palette.find(color => color.hex === mapping.targetHex)?.code }}<button type="button" :aria-label="`移除 ${mapping.sourceHex} 映射`" @click="clearSampleMapping(mapping.sourceHex)">×</button></span></div>
        </section>
      </section>
      <section v-if="colorSource === 'personal'" class="palette-manager">
        <div class="palette-heading"><div><p>MY BEAD COLORS</p><h2>我的拼豆色板 <small>{{ enabledPalette.length }} 种可用于生成</small></h2><span>色号用来认实物，HEX 颜色用来匹配图片。色板保存在当前浏览器中。</span></div><div class="palette-actions"><button type="button" @click="exportPalette" :disabled="!palette.length">导出色板</button><label class="import-button">导入 JSON<input type="file" accept="application/json,.json" @change="importPalette"/></label></div></div>
        <form class="add-color" @submit.prevent="addPaletteColor"><label class="picker-field"><span>{{ editingColorId ? '修改颜色' : '颜色' }}</span><input v-model="newColorHex" type="color" aria-label="选择豆子颜色"/><input v-model="newColorHex" class="hex-input" type="text" placeholder="#C77878" maxlength="7"/></label><label><span>实物色号</span><input v-model="newColorCode" type="text" placeholder="例如 A12" maxlength="24"/></label><label><span>名称（可选）</span><input v-model="newColorName" type="text" placeholder="例如 樱花粉" maxlength="32"/></label><div class="form-actions"><button type="submit" class="add-color-button">{{ editingColorId ? '保存修改' : '＋ 添加到色板' }}</button><button v-if="editingColorId" type="button" class="cancel-edit" @click="cancelColorEdit">取消</button></div></form>
        <div class="palette-tools"><label class="palette-search">⌕<input v-model="paletteSearch" type="search" placeholder="搜索色号、名称或 HEX"/></label><label class="only-enabled"><input v-model="showEnabledOnly" type="checkbox"/>只看启用颜色</label><span>点击色卡可启用/停用</span></div>
        <div v-if="filteredPalette.length" class="swatch-grid"><article v-for="color in filteredPalette" :key="color.id" class="swatch-card" :class="{ disabled: !color.enabled }"><label class="swatch-toggle"><input v-model="color.enabled" type="checkbox"/><i :style="{ background: color.hex }"></i><span><b>{{ color.code }}</b><small>{{ color.name }}</small><small>{{ color.hex }}</small></span></label><div class="swatch-actions"><button type="button" @click="editPaletteColor(color)">编辑</button><button v-if="samplingColor && color.enabled" type="button" @click="assignSampleTo(color)">映射到此色</button><button type="button" class="delete-swatch" @click="removePaletteColor(color.id)">删除</button></div></article></div>
        <div v-else class="palette-empty">{{ palette.length ? '没有符合条件的颜色。' : '还没有色卡。用上面的颜色选择器添加手头有的豆色，或导入已有色板。' }}</div>
      </section>
      <section v-if="beads.length" class="palette"><h2>拼豆用量清单 <small>共 {{ totalBeads }} 颗 · {{ renderedColumns }} × {{ rows }} 格</small></h2><span v-for="bead in beads" :key="bead.code"><i :style="{background:bead.hex}"></i>{{ bead.code }} · {{ bead.name }} · {{ formatColor(bead.hex) }} · {{ bead.count }} 颗</span></section>
    </main>
    <footer><span class="tool-footer-brand">{{ profile.name }} · DIY Studio</span><div class="tool-footer-links"><a :href="`mailto:${profile.email}`">{{ profile.email }}</a><a :href="`mailto:${profile.email}?subject=${encodeURIComponent('拼豆工具改进建议 / 问题反馈')}`">改进建议 · 问题反馈 ↗</a><RouterLink to="/?section=diy">返回功能目录</RouterLink></div></footer>
    <div v-if="toastMessage" class="tool-toast" role="status" aria-live="polite"><span>{{ toastMessage }}</span><button type="button" aria-label="关闭提示" @click="toastMessage = ''">×</button></div>
    <div v-if="infoDialogOpen" class="info-backdrop" role="presentation" @click.self="infoDialogOpen = false">
      <section class="info-dialog" role="dialog" aria-modal="true" aria-labelledby="info-title">
        <header class="info-dialog-heading"><div><p>TOOL GUIDE</p><h2 id="info-title">图片转拼豆 · 功能简介</h2></div><button type="button" aria-label="关闭功能简介" @click="infoDialogOpen = false">×</button></header>
        <div class="info-dialog-content">
          <section><h3>制作图案</h3><ul><li>上传图片，在浏览器本机处理，不会上传到服务器。</li><li>调整图案宽度，选择“个人色库”或“图片原色”作为图案颜色来源。</li><li>个人色库模式只使用已启用的豆色；图片原色模式可选择最多 128 种主要颜色。</li><li>可选择显示网格，或以圆形颗粒和白色中心孔预览拼豆外观。</li></ul></section>
          <section><h3>管理颜色</h3><ul><li>建立个人色板，录入实物色号、名称和 HEX 颜色；支持启用、停用、搜索、编辑和删除。</li><li>色板可导出或导入 JSON，并保存在当前浏览器中。</li><li>个人色库模式可以从原图取样，再指定由哪种已有豆色替代。</li><li>颜色用量按最终图案格子统计；导出色值支持 #HEX、RGB 和 0x 格式。</li></ul></section>
          <section><h3>拼豆模式</h3><ul><li>进入全屏 SVG 参考画面，支持完整显示或铺满屏幕。</li><li>使用滑块、加减按钮或滚轮缩放；拖动画面平移，也可通过小地图快速定位。</li><li>逐色隐藏或显示，支持搜索和一键显示/隐藏；可选择色卡显示导出色值、颜色名称或实物色号。</li><li>每行和每列都有坐标；指向或点选格子可查看如 D12 的坐标及该格颜色。</li><li>拼豆模式也可随时切换网格和圆形颗粒效果。</li></ul></section>
          <section><h3>导出与保存</h3><ul><li>支持导出 PNG、PDF 和 SVG；图案附颜色图例与每种颜色的用量。</li><li>当前拼豆图、原图副本和主要设置会自动保存在本机，重新打开页面可恢复。</li><li>“清除缓存并重置”会清除本工具保存的个人色板、图案及设置，不影响浏览器中其他网站的数据。</li></ul></section>
        </div>
        <footer class="info-dialog-footer"><span>提示：更换浏览器或设备时，可通过 JSON 导入/导出迁移个人色板。</span><button type="button" @click="infoDialogOpen = false">知道了</button></footer>
      </section>
    </div>
    <section v-if="beadMode" class="bead-mode" aria-label="拼豆模式">
      <div class="bead-mode-toolbar">
        <div class="bead-mode-top">
          <button type="button" class="leave-mode" @click="exitBeadMode">退出拼豆模式 ×</button>
          <strong>{{ patternWidth }} × {{ patternHeight }} 格 · {{ totalBeads }} 颗</strong><span class="cell-coordinate"><span>{{ activeCell ? `${activeCell.label} · 第 ${activeCell.row} 行，第 ${activeCell.column} 列` : '指向格子查看坐标' }}</span><span v-if="activeCellBead" class="coordinate-bead" :class="{ hidden: hiddenColors.includes(activeCellBead.hex) }" :title="`${activeCellBead.code} · ${activeCellBead.name} · ${formatColor(activeCellBead.hex)}`"><i :style="{ background: activeCellBead.hex }"></i>{{ beadLabel(activeCellBead) }}{{ hiddenColors.includes(activeCellBead.hex) ? '（已隐藏）' : '' }}</span></span>
          <div class="fit-options"><button type="button" title="完整显示图案，可能留白" :class="{ active: fullScreenFit === 'contain' }" @click="setFullscreenFit('contain')">完整显示</button><button type="button" title="铺满可视区域，边缘可能被裁切" :class="{ active: fullScreenFit === 'cover' }" @click="setFullscreenFit('cover')">铺满屏幕</button></div>
          <div class="bead-mode-view-options"><label><input v-model="showGrid" type="checkbox"/><span>网格</span></label><label><input v-model="showBeadStyle" type="checkbox"/><span>拼豆颗粒</span></label></div>
          <div class="zoom-controls"><button type="button" aria-label="缩小" @click="setZoom(zoom - 0.2)">−</button><input v-model.number="zoom" type="range" min="1" max="5" step="0.1" aria-label="缩放拼豆图" @input="onZoomInput"/><output>{{ Math.round(zoom * 100) }}%</output><button type="button" aria-label="放大" @click="setZoom(zoom + 0.2)">＋</button><button type="button" class="reset-zoom" @click="resetZoom">重置</button></div>
        </div>
        <div class="fullscreen-color-tools"><button class="color-panel-toggle" type="button" :aria-expanded="colorsPanelOpen" @click="colorsPanelOpen = !colorsPanelOpen">颜色显示 {{ beads.length - hiddenColors.length }}/{{ beads.length }} 色 <span>{{ colorsPanelOpen ? '收起' : '选择颜色' }}</span></button>
          <div v-if="colorsPanelOpen" class="fullscreen-color-panel"><div class="color-panel-actions"><label class="fullscreen-color-search">⌕<input v-model="fullscreenColorSearch" type="search" placeholder="搜索色号、名称或 HEX"/></label><button type="button" @click="showAllFullscreenColors">一键显示</button><button type="button" @click="hideAllFullscreenColors">一键隐藏</button></div><fieldset class="bead-label-format"><legend>色卡显示</legend><label><input v-model="beadLabelMode" type="radio" value="export"/><span>导出色值</span></label><label><input v-model="beadLabelMode" type="radio" value="name"/><span>颜色名称</span></label><label><input v-model="beadLabelMode" type="radio" value="code"/><span>实物色号</span></label></fieldset><div class="color-selector-grid"><button v-for="bead in fullscreenBeads" :key="bead.hex" type="button" :class="{ hidden: hiddenColors.includes(bead.hex) }" :aria-pressed="!hiddenColors.includes(bead.hex)" :title="`${bead.code} · ${bead.name} · ${formatColor(bead.hex)} · ${bead.count} 颗`" @click="toggleHiddenColor(bead.hex)"><i :style="{ background: bead.hex }"></i><span><b>{{ beadLabel(bead) }}</b><small>{{ bead.count }} 颗</small></span></button></div></div>
        </div>
      </div>
      <div ref="fullscreenViewport" class="bead-mode-viewport" :class="{ panning: isPanning }" @pointerdown="startPan" @pointermove="movePan" @pointerup="endPan" @pointercancel="endPan" @pointerleave="clearHoveredCell" @wheel.prevent="zoomAtPointer">
        <img class="bead-mode-image" :src="fullscreenSvgUrl" :style="fullscreenImageStyle" alt="全屏拼豆 SVG 参考图" draggable="false"/>
        <div class="coordinate-ruler-top" aria-hidden="true"><span v-for="tick in columnTicks" :key="tick.column" :style="{ left: `${tick.left}px` }">{{ tick.label }}</span></div>
        <div class="coordinate-ruler-left" aria-hidden="true"><span v-for="tick in rowTicks" :key="tick.row" :style="{ top: `${tick.top}px` }">{{ tick.row }}</span></div>
        <div v-if="activeCell" class="coordinate-marker" :style="coordinateMarkerStyle" aria-hidden="true"></div>
        <div v-if="zoom > 1.2 || fullScreenFit === 'cover'" ref="minimapElement" class="overview-map" title="点击小地图移动到该区域" @pointerdown.stop="moveToMinimap"><img :src="fullscreenSvgUrl" :style="minimapStyle.image" alt="拼豆图全图缩略图"/><div class="overview-window" :style="minimapStyle.view"></div></div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.bead-app{min-height:100vh;background:#fffaf8;color:#263b47}.bead-app header,.bead-app footer{height:72px;padding:0 max(24px,calc((100% - 1160px)/2));display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #263b471c}.brand{font:600 19px Georgia,serif}.brand span,.local-note{margin-left:10px;color:#6a90a6;font:10px monospace;letter-spacing:.1em}.local-note{margin:0}.bead-app main{width:min(1160px,calc(100% - 40px));margin:auto;padding:60px 0}.intro p{color:#6a90a6;font:11px monospace;letter-spacing:.15em}.intro h1{font:600 clamp(32px,5vw,56px) Georgia,serif;margin:12px 0}.intro h1 em{color:#6a90a6;font-style:normal}.intro>span{color:#728077}.workspace{display:grid;grid-template-columns:280px 1fr;gap:24px;margin-top:36px}.controls,.preview{padding:22px;border:1px solid #263b4720;border-radius:18px;background:white}.upload{height:150px;border:1px dashed #6a90a6;border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;cursor:pointer}.upload input{display:none}.upload b{font-size:26px;color:#6a90a6}.upload small,.empty small{color:#77877c;font-size:12px}.setting{display:block;margin-top:24px;font-size:13px}.range-row{display:flex;align-items:center;gap:8px;margin-top:10px}.range-row input[type=range]{min-width:0;flex:1;margin:0;accent-color:#6a90a6}.range-row span{color:#728077;font-size:12px}.number-input{width:68px;padding:6px 7px;border:1px solid #263b4728;border-radius:8px;background:#fffaf8;color:#263b47;text-align:center;font:13px monospace}.number-input:focus{outline:2px solid #6a90a655;border-color:#6a90a6}.check{display:flex;gap:8px;margin:22px 0;font-size:13px}.check input{accent-color:#6a90a6}.export-format{margin:20px 0;padding:0;border:0}.export-format legend{margin-bottom:10px;font-size:13px}.format-options{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.format-options label{cursor:pointer}.format-options input{position:absolute;opacity:0}.format-card{height:62px;padding:5px 4px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;border:1px solid #263b4728;border-radius:10px;background:#fff;color:#263b47}.format-card b{font:600 12px monospace}.format-card small{color:#627078;font-size:9px;line-height:1.2;text-align:center}.format-options input:checked+.format-card{border-color:#6a90a6;background:#edf2f3;box-shadow:inset 0 0 0 1px #6a90a6}.format-options input:focus-visible+.format-card{outline:2px solid #263b47;outline-offset:2px}.download{width:100%;padding:12px;border:0;border-radius:999px;background:#263b47;color:white}.download:disabled{opacity:.4;cursor:not-allowed}.preview{min-height:440px;display:grid;place-items:center;background:#edf2f3}.empty{display:flex;flex-direction:column;align-items:center;gap:12px;color:#6a90a6}.empty span{font-size:60px}.images{display:flex;gap:20px;align-items:flex-start;justify-content:center;width:100%;flex-wrap:wrap}.images figure{margin:0;max-width:48%;text-align:center}.images figcaption{margin-bottom:12px;font-size:12px}.images img{display:block;max-width:100%;max-height:420px;object-fit:contain;image-rendering:pixelated}.palette{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.palette h2{width:100%;font:600 20px Georgia,serif}.palette span{padding:8px 11px;border-radius:999px;background:#edf2f3;font:11px monospace}.palette i{display:inline-block;width:12px;height:12px;margin-right:7px;border-radius:50%;vertical-align:middle}.error{color:#b65e5e}footer{border-top:3px solid #f2b6b6;background:#263b47;color:#fff}footer a{color:#b7cbd2;font-size:13px}@media(max-width:760px){.workspace{grid-template-columns:1fr}.preview{min-height:300px}.bead-app main{padding:38px 0}.images figure{max-width:100%}.bead-app footer{padding:0 20px}}
.images img{image-rendering:auto}.images figure:first-child img{image-rendering:pixelated}.source-switch{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:9px;padding:4px;border-radius:999px;background:#edf2f3}.source-switch button{padding:8px 5px;border:0;border-radius:999px;background:transparent;color:#53646a;font-size:12px;cursor:pointer}.source-switch button.active{background:#263b47;color:#fff;box-shadow:0 2px 6px #263b4720}.source-hint{display:block;margin-top:7px;color:#77877c;font-size:11px;line-height:1.5}.active-colors{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.active-colors b{margin-left:auto;color:#6a90a6}.active-colors small{width:100%;color:#77877c;font-size:11px}.bead-style-check{align-items:flex-start}.bead-style-check span{display:flex;flex-direction:column;gap:5px}.bead-style-check small{color:#77877c;font-size:11px}
.sample-button{margin-left:8px;padding:5px 9px;border:1px solid #6a90a6;border-radius:999px;background:#fff;color:#52798e;font-size:11px;cursor:pointer}.sample-button.active{background:#263b47;color:#fff}.images img.sampling{cursor:crosshair;outline:2px solid #6a90a6;outline-offset:3px}
.mapping-tools{width:100%;padding:12px 14px;border:1px solid #6a90a644;border-radius:12px;background:#fff}.mapping-tools p,.mapping-tools strong{margin:0 0 10px;font-size:12px}.mapping-tools p{display:flex;align-items:center;gap:8px}.mapping-tools i,.mapping-chip i{display:inline-block;width:16px;height:16px;border:1px solid #263b4730;border-radius:50%;vertical-align:middle}.mapping-swatches{display:flex;gap:7px;flex-wrap:wrap}.mapping-swatches button{display:flex;align-items:center;gap:6px;padding:5px 9px;border:1px solid #263b4720;border-radius:999px;background:#edf2f3;color:#263b47;font-size:11px;cursor:pointer}.saved-mappings{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.saved-mappings strong{width:100%;margin:0}.mapping-chip{display:inline-flex;align-items:center;gap:5px;padding:5px 8px;border-radius:999px;background:#edf2f3;font:11px monospace}.mapping-chip button{border:0;background:none;color:#6c7780;font-size:16px;cursor:pointer}
.palette-manager{margin-top:28px;padding:24px;border:1px solid #263b4720;border-radius:18px;background:#fff}.palette-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}.palette-heading p{margin:0 0 8px;color:#6a90a6;font:10px monospace;letter-spacing:.14em}.palette-heading h2{margin:0 0 7px;font:600 24px Georgia,serif}.palette-heading h2 small{margin-left:8px;color:#6a90a6;font:12px sans-serif}.palette-heading>div>span,.palette-tools>span{color:#77877c;font-size:12px}.palette-actions{display:flex;gap:8px;flex-shrink:0}.palette-actions button,.import-button{padding:9px 12px;border:1px solid #263b4728;border-radius:999px;background:#fff;color:#263b47;font-size:12px;cursor:pointer}.palette-actions button:disabled{opacity:.45;cursor:not-allowed}.import-button{background:#edf2f3}.import-button input{display:none}.add-color{display:grid;grid-template-columns:1.1fr 1fr 1fr auto;align-items:end;gap:10px;margin-top:22px;padding:16px;border-radius:14px;background:#f6f8f8}.add-color>label{display:flex;flex-direction:column;gap:7px;color:#53646a;font-size:11px}.add-color input[type=text]{min-width:0;padding:9px 10px;border:1px solid #263b4720;border-radius:9px;background:#fff;color:#263b47;font-size:12px}.picker-field{display:grid!important;grid-template-columns:auto 40px 1fr;align-items:center}.picker-field input[type=color]{width:38px;height:36px;padding:3px;border:1px solid #263b4720;border-radius:8px;background:#fff}.add-color .hex-input{font-family:monospace}.form-actions{display:flex;gap:6px;flex-wrap:wrap}.add-color-button,.cancel-edit{padding:10px 14px;border:0;border-radius:999px;background:#263b47;color:#fff;font-size:12px;white-space:nowrap;cursor:pointer}.cancel-edit{border:1px solid #263b4728;background:#fff;color:#263b47}.palette-tools{display:flex;align-items:center;gap:14px;margin:18px 0 12px}.palette-search{display:flex;align-items:center;gap:8px;min-width:230px;padding:8px 10px;border:1px solid #263b4720;border-radius:999px;color:#6a90a6}.palette-search input{width:100%;border:0;outline:0;color:#263b47;font-size:12px}.only-enabled{display:flex;align-items:center;gap:6px;color:#53646a;font-size:12px}.only-enabled input,.swatch-toggle input{accent-color:#6a90a6}.swatch-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:9px}.swatch-card{min-width:0;padding:10px;border:1px solid #263b471a;border-radius:12px;background:#fff}.swatch-card:hover{border-color:#6a90a6}.swatch-card.disabled{opacity:.55;background:#f5f6f6}.swatch-toggle{display:flex;align-items:center;gap:9px;min-width:0;cursor:pointer}.swatch-toggle input{margin:0}.swatch-toggle>i{width:34px;height:34px;flex:none;border:1px solid #263b4730;border-radius:10px}.swatch-toggle span{display:flex;flex-direction:column;min-width:0;gap:2px}.swatch-toggle b{font-size:12px}.swatch-toggle small{overflow:hidden;color:#77877c;font:10px monospace;text-overflow:ellipsis;white-space:nowrap}.swatch-actions{display:flex;gap:6px;margin:8px 0 0 24px}.swatch-actions button{padding:4px 7px;border:1px solid #263b4720;border-radius:999px;background:#edf2f3;color:#52798e;font-size:10px;cursor:pointer}.swatch-actions .delete-swatch{margin-left:auto;color:#a65d5d}.palette-empty{padding:24px;border:1px dashed #6a90a644;border-radius:12px;color:#77877c;text-align:center;font-size:12px}.palette h2 small{margin-left:8px;color:#6a90a6;font:12px sans-serif}
@media(max-width:760px){.palette-manager{padding:17px}.palette-heading{flex-direction:column}.add-color{grid-template-columns:1fr 1fr}.form-actions{grid-column:1/-1}.palette-tools{flex-wrap:wrap}.palette-search{flex:1}.swatch-grid{grid-template-columns:repeat(auto-fill,minmax(145px,1fr))}}
.bead-mode-button{width:100%;margin:0 0 9px;padding:12px;border:1px solid #6a90a6;border-radius:999px;background:#edf2f3;color:#263b47;font-weight:600;cursor:pointer}.bead-mode{position:fixed;inset:0;z-index:10000;overflow:hidden;background:#fff}.bead-mode-image{position:absolute;top:104px;left:0;width:100%;height:calc(100% - 104px);object-position:center}.bead-mode-image.fit-contain{object-fit:contain}.bead-mode-image.fit-cover{object-fit:cover}.bead-mode-image.pixel-art{image-rendering:pixelated}.bead-mode-toolbar{position:absolute;z-index:1;top:0;left:0;right:0;padding:12px max(14px,env(safe-area-inset-left)) 10px;background:#fffaf8ef;box-shadow:0 3px 18px #263b4720;backdrop-filter:blur(12px)}.bead-mode-top{display:flex;align-items:center;gap:16px;min-width:0}.bead-mode-top>strong{font-size:13px;white-space:nowrap}.leave-mode,.fit-options button{padding:8px 11px;border:1px solid #263b4720;border-radius:999px;background:#fff;color:#263b47;font-size:12px;white-space:nowrap;cursor:pointer}.fit-options{display:flex;gap:5px;margin-left:auto}.fit-options button.active{border-color:#6a90a6;background:#263b47;color:#fff}.fullscreen-colors{display:flex;align-items:center;gap:7px;overflow-x:auto;margin-top:10px;padding-bottom:2px}.fullscreen-colors>span{position:sticky;left:0;flex:none;padding-right:4px;background:#fffaf8;font-size:11px;color:#6b7880}.fullscreen-colors button{display:flex;align-items:center;gap:5px;flex:none;padding:5px 8px;border:1px solid #263b4720;border-radius:999px;background:#fff;color:#263b47;font:11px monospace;cursor:pointer}.fullscreen-colors button.hidden{opacity:.4;text-decoration:line-through;filter:grayscale(1)}.fullscreen-colors i{width:13px;height:13px;border:1px solid #263b4730;border-radius:50%}.fullscreen-colors small{color:#77877c;font-size:9px}
@media(max-width:600px){.bead-mode-top{gap:7px;flex-wrap:wrap}.bead-mode-top>strong{margin-right:auto}.fit-options{margin-left:0}.bead-mode-toolbar{padding-top:max(9px,env(safe-area-inset-top))}.fullscreen-colors{margin-top:8px}.bead-mode-image{top:122px;height:calc(100% - 122px)}}
.bead-mode{display:flex;flex-direction:column}.bead-mode-toolbar{position:relative;top:auto;left:auto;right:auto;flex:none;padding:10px max(12px,env(safe-area-inset-left));background:#fffaf8f5}.bead-mode-top{flex-wrap:wrap;gap:9px}.bead-mode-top>strong{margin-right:auto}.fit-options{margin-left:0}.zoom-controls{display:flex;align-items:center;gap:6px}.zoom-controls button{width:30px;height:30px;border:1px solid #263b4720;border-radius:50%;background:#fff;color:#263b47;font-size:17px;cursor:pointer}.zoom-controls input{width:130px;accent-color:#6a90a6}.zoom-controls output{min-width:42px;color:#263b47;font:11px monospace;text-align:center}.zoom-controls .reset-zoom{width:auto;padding:0 9px;border-radius:999px;font-size:11px}.fullscreen-color-tools{margin-top:8px}.color-panel-toggle{display:flex;align-items:center;gap:8px;padding:6px 10px;border:1px solid #263b4720;border-radius:999px;background:#edf2f3;color:#263b47;font-size:11px;cursor:pointer}.color-panel-toggle span{color:#6a90a6}.fullscreen-color-panel{margin-top:8px;padding:9px;border:1px solid #263b4718;border-radius:12px;background:#fff}.color-panel-actions{display:flex;align-items:center;gap:7px;margin-bottom:8px}.fullscreen-color-search{display:flex;align-items:center;gap:6px;flex:1;min-width:140px;max-width:280px;padding:6px 9px;border:1px solid #263b4720;border-radius:999px;color:#6a90a6}.fullscreen-color-search input{width:100%;border:0;outline:0;color:#263b47;font-size:11px}.color-panel-actions>button{padding:7px 10px;border:1px solid #263b4720;border-radius:999px;background:#fff;color:#263b47;font-size:11px;white-space:nowrap;cursor:pointer}.color-selector-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px;max-height:min(26vh,210px);overflow:auto}.color-selector-grid button{display:flex;align-items:center;gap:8px;min-width:0;padding:7px;border:1px solid #263b4718;border-radius:9px;background:#fff;color:#263b47;text-align:left;cursor:pointer}.color-selector-grid button.hidden{opacity:.43;background:#eef0f0;filter:grayscale(1)}.color-selector-grid i{width:23px;height:23px;flex:none;border:1px solid #263b4730;border-radius:50%}.color-selector-grid span{display:flex;flex-direction:column;min-width:0;gap:2px}.color-selector-grid b{font:600 10px monospace}.color-selector-grid small{overflow:hidden;color:#6b7880;font-size:9px;text-overflow:ellipsis;white-space:nowrap}.bead-mode-viewport{position:relative;flex:1;min-height:0;overflow:hidden;background:#fff;touch-action:none;cursor:grab}.bead-mode-viewport.panning{cursor:grabbing}.bead-mode-image{position:absolute;inset:0;width:100%;height:100%;object-position:center;user-select:none;pointer-events:none}.bead-mode-image.fit-contain{object-fit:contain}.bead-mode-image.fit-cover{object-fit:cover}
@media(max-width:700px){.bead-mode-top{gap:6px}.bead-mode-top>strong{font-size:11px}.zoom-controls{width:100%;order:3}.zoom-controls input{flex:1}.fullscreen-color-panel{padding:7px}.color-panel-actions{flex-wrap:wrap}.fullscreen-color-search{max-width:none;flex-basis:100%}.color-selector-grid{grid-template-columns:repeat(auto-fill,minmax(125px,1fr));max-height:25vh}}
.bead-mode-viewport{position:relative;top:auto;right:auto;bottom:auto;left:auto;flex:1;min-height:0;overflow:hidden;background:#fff;touch-action:none;cursor:grab}.bead-mode-viewport.panning{cursor:grabbing}.bead-mode-image{position:absolute;inset:auto;top:50%;left:50%;width:auto;height:auto;max-width:none;max-height:none;object-fit:fill;transform:translate(calc(-50% + var(--pan-x)),calc(-50% + var(--pan-y))) scale(var(--zoom));transform-origin:center;user-select:none;pointer-events:none}.coordinate-ruler-top,.coordinate-ruler-left{position:absolute;z-index:1;pointer-events:none;color:#334b56;font:10px monospace;text-shadow:0 1px 2px white,0 -1px 2px white}.coordinate-ruler-top{top:0;left:0;right:0;height:18px}.coordinate-ruler-top span{position:absolute;top:2px;transform:translateX(-50%);padding:1px 3px;border-radius:3px;background:#fffaf8d9}.coordinate-ruler-left{top:0;bottom:0;left:0;width:25px}.coordinate-ruler-left span{position:absolute;left:2px;transform:translateY(-50%);padding:2px 3px;border-radius:3px;background:#fffaf8d9}.coordinate-marker{position:absolute;z-index:2;border:2px solid #e58ba2;box-shadow:inset 0 0 0 1px #fff,0 0 0 1px #263b47;pointer-events:none}.cell-coordinate{padding:5px 9px;border-radius:999px;background:#e9f0f2;color:#304f5d;font:11px monospace;white-space:nowrap}.overview-map{position:absolute;z-index:3;right:14px;bottom:14px;width:150px;height:90px;overflow:hidden;border:1px solid #263b4740;border-radius:8px;background:#fff;box-shadow:0 3px 16px #263b4730;cursor:crosshair;touch-action:none}.overview-map img{position:absolute;max-width:none;max-height:none;pointer-events:none}.overview-window{position:absolute;border:2px solid #e58ba2;background:#e58ba222;pointer-events:none}
@media(max-width:700px){.cell-coordinate{order:4;max-width:100%;overflow:hidden;text-overflow:ellipsis}.overview-map{right:8px;bottom:8px;width:120px;height:72px}.coordinate-ruler-top,.coordinate-ruler-left{font-size:9px}}
.cell-coordinate{display:flex;align-items:center;gap:7px}.coordinate-bead{display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border-radius:999px;background:#fff;color:#263b47}.coordinate-bead i{width:13px;height:13px;flex:none;border:1px solid #263b4730;border-radius:50%}.coordinate-bead.hidden{opacity:.58;text-decoration:line-through}.bead-label-format{display:flex;align-items:center;gap:6px;margin:0 0 8px;padding:0;border:0}.bead-label-format legend{margin-right:3px;color:#5e6d73;font-size:10px}.bead-label-format label{cursor:pointer}.bead-label-format input{position:absolute;opacity:0}.bead-label-format label span{display:block;padding:5px 8px;border:1px solid #263b4720;border-radius:999px;background:#fff;color:#46575e;font-size:10px}.bead-label-format input:checked+span{border-color:#6a90a6;background:#edf2f3;color:#263b47;box-shadow:inset 0 0 0 1px #6a90a6}.bead-label-format input:focus-visible+span{outline:2px solid #263b47;outline-offset:2px}
.bead-mode-view-options{display:flex;align-items:center;gap:6px}.bead-mode-view-options label{display:flex;align-items:center;gap:5px;padding:6px 9px;border:1px solid #263b4720;border-radius:999px;background:#fff;color:#334b56;font-size:11px;white-space:nowrap;cursor:pointer}.bead-mode-view-options input{margin:0;accent-color:#6a90a6}
.header-actions{display:flex;align-items:center;gap:9px}.header-back{color:#5e7580;font-size:13px;white-space:nowrap}.header-back:hover{color:#263b47}.header-action{padding:8px 12px;border:1px solid #263b4722;border-radius:999px;background:#fffaf8;color:#263b47;font-size:12px;cursor:pointer}.header-action:hover{border-color:#6a90a6;background:#edf2f3}.reset-action{color:#9a5d5d}.info-backdrop{position:fixed;inset:0;z-index:12000;display:grid;place-items:center;padding:16px;background:#17252dcc;backdrop-filter:blur(5px)}.info-dialog{display:flex;flex-direction:column;width:min(720px,100%);max-height:min(86vh,850px);overflow:hidden;border:1px solid #263b4720;border-radius:20px;background:#fffaf8;color:#263b47;box-shadow:0 24px 80px #101a1f55}.info-dialog-heading{height:auto!important;min-height:84px;padding:16px 22px!important;border-bottom:1px solid #263b471c;background:#fffaf8}.info-dialog-heading p{margin:0 0 5px;color:#6a90a6;font:10px monospace;letter-spacing:.14em}.info-dialog-heading h2{margin:0;font:600 23px Georgia,serif}.info-dialog-heading button{width:34px;height:34px;border:1px solid #263b4720;border-radius:50%;background:#fff;color:#52636a;font-size:23px;cursor:pointer}.info-dialog-content{overflow:auto;padding:4px 24px 12px}.info-dialog-content section{padding:14px 0;border-bottom:1px solid #263b4714}.info-dialog-content h3{margin:0 0 8px;color:#52798e;font-size:14px}.info-dialog-content ul{margin:0;padding-left:19px;color:#516168;font-size:12px;line-height:1.75}.info-dialog-footer{height:auto!important;min-height:64px;padding:11px 20px!important;border-top:1px solid #263b4718!important;background:#f1f5f5!important;color:#69777c!important}.info-dialog-footer span{font-size:11px;line-height:1.5}.info-dialog-footer button{padding:8px 15px;border:0;border-radius:999px;background:#263b47;color:#fff;font-size:12px;white-space:nowrap;cursor:pointer}
@media(max-width:760px){.header-actions{gap:5px}.header-back{font-size:12px}.header-action{padding:7px 9px;font-size:11px}.header-actions .local-note{display:none}.info-backdrop{padding:10px}.info-dialog-heading{padding:14px 16px!important}.info-dialog-content{padding:2px 17px 8px}.info-dialog-footer{align-items:flex-start!important;gap:10px;flex-direction:column}}
.brand{display:inline-flex;align-items:center;gap:9px;white-space:nowrap}.brand img{width:34px;height:34px;flex:none;border:2px solid #fff;border-radius:50%;object-fit:cover;box-shadow:0 2px 8px #263b4722}.brand .brand-name{margin:0;color:#263b47;font:600 17px Georgia,serif;letter-spacing:0}.brand .brand-divider{margin:0;color:#9aabb0;font:14px sans-serif}.brand .brand-label{margin:0;color:#6a90a6;font:10px monospace;letter-spacing:.1em}.bead-app footer{height:auto;min-height:72px;padding-top:15px;padding-bottom:15px;gap:16px}.tool-footer-brand{color:#fff;font:600 14px Georgia,serif}.tool-footer-links{display:flex;align-items:center;justify-content:flex-end;gap:18px;flex-wrap:wrap}.tool-footer-links a{color:#b7cbd2;font-size:12px}.tool-footer-links a:hover{color:#fff}.bead-app footer .router-link-active{color:#b7cbd2}
.author-mark-toggle{margin:10px 0 18px}.author-mark-toggle span{display:flex;flex-direction:column;gap:4px}.author-mark-toggle small{color:#77877c;font-size:11px}
.tool-toast{position:fixed;z-index:13000;top:calc(18px + env(safe-area-inset-top));left:50%;display:flex;align-items:center;gap:16px;width:max-content;max-width:min(560px,calc(100vw - 28px));padding:13px 15px 13px 18px;border:1px solid #6a90a655;border-radius:14px;background:#fffaf8;color:#263b47;box-shadow:0 12px 34px #17252d35;transform:translateX(-50%);animation:toast-in .2s ease-out}.tool-toast span{font-size:13px;line-height:1.5}.tool-toast button{width:25px;height:25px;flex:none;border:0;border-radius:50%;background:#edf2f3;color:#52636a;font-size:18px;line-height:1;cursor:pointer}@keyframes toast-in{from{opacity:0;transform:translate(-50%,-8px)}to{opacity:1;transform:translate(-50%,0)}}
.clear-image-button{width:100%;margin-top:9px;padding:8px 12px;border:1px solid #263b4720;border-radius:999px;background:#fff;color:#65737a;font-size:12px;cursor:pointer;transition:border-color .16s ease,background .16s ease,color .16s ease}.clear-image-button:hover{border-color:#c78383;background:#fff7f6;color:#9a5d5d}
.pattern-unavailable{width:100%;min-height:220px;padding:22px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;border:1px dashed #6a90a655;border-radius:14px;background:#fffaf8;color:#52636a;text-align:center}.pattern-unavailable>span{color:#9bb4bf;font-size:42px}.pattern-unavailable b{font-size:14px}.pattern-unavailable small{max-width:240px;color:#77877c;font-size:11px;line-height:1.6}.generated-figure{flex:1;min-width:220px}.generated-figure>img{width:100%;height:auto;max-height:420px;object-fit:contain}
.sample-button,.mapping-tools{display:none!important}
@media(max-width:760px){.bead-app header{height:auto;min-height:72px;padding:12px 16px;gap:10px;flex-wrap:wrap}.brand{gap:6px}.brand img{width:30px;height:30px}.brand .brand-name{font-size:15px}.brand .brand-label{font-size:9px}.bead-app footer{align-items:flex-start;flex-direction:column;padding:18px 20px}.tool-footer-links{justify-content:flex-start;gap:9px 16px}}
@media(max-width:520px){
  .bead-app header{padding:10px 12px;gap:8px}
  .bead-app .brand{max-width:100%;gap:5px}
  .bead-app .brand .brand-name{font-size:14px}
  .bead-app .brand .brand-label{font-size:8px;letter-spacing:.06em}
  .header-actions{width:100%;flex-wrap:wrap}
  .header-back{min-height:40px;display:inline-flex;align-items:center;padding:0 4px}
  .header-action{min-height:40px;padding:8px 10px}
  .bead-app main{width:calc(100% - 24px);padding:30px 0 42px}
  .intro h1{font-size:clamp(30px,8.5vw,42px);line-height:1.25}
  .intro>span{display:block;font-size:13px;line-height:1.65}
  .workspace{gap:14px;margin-top:24px}
  .controls,.preview{padding:14px;border-radius:14px}
  .upload{height:124px}
  .setting{margin-top:19px}
  .source-switch button{min-height:40px}
  .range-row{gap:6px}
  .number-input{width:58px;padding:8px 4px;font-size:16px}
  .check{min-height:40px;align-items:center;margin:15px 0}
  .format-options{gap:5px}
  .format-card{min-height:62px;height:auto;padding:7px 3px}
  .format-card small{font-size:8px}
  .download,.bead-mode-button{min-height:44px}
  .preview{min-height:250px}
  .images{flex-direction:column;align-items:center;gap:14px}
  .images figure,.generated-figure{width:100%;max-width:100%;min-width:0}
  .images img{max-height:360px;margin:0 auto}
  .palette-manager{margin-top:18px;padding:13px;border-radius:14px}
  .palette-heading{gap:12px}
  .palette-heading h2{font-size:21px}
  .palette-actions{width:100%;flex-wrap:wrap}
  .palette-actions button,.import-button{min-height:40px}
  .add-color{grid-template-columns:1fr;gap:12px;margin-top:15px;padding:12px}
  .add-color>label,.picker-field{min-width:0}
  .add-color input[type=text]{min-height:42px;font-size:16px}
  .form-actions{grid-column:auto}
  .form-actions button{min-height:42px;flex:1}
  .palette-tools{align-items:stretch;gap:10px}
  .palette-search{flex-basis:100%;min-height:42px}
  .palette-search input,.fullscreen-color-search input{font-size:16px}
  .only-enabled{min-height:40px}
  .swatch-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
  .swatch-card{padding:8px}
  .swatch-toggle{gap:6px}
  .swatch-toggle>i{width:28px;height:28px}
  .swatch-toggle b{font-size:11px}
  .swatch-toggle small{font-size:9px}
  .swatch-actions{margin-left:20px;flex-wrap:wrap}
  .swatch-actions button{min-height:34px}
  .info-backdrop{padding:8px}
  .info-dialog{max-height:calc(100dvh - 16px);border-radius:15px}
  .info-dialog-heading h2{font-size:20px}
  .info-dialog-content ul{font-size:13px}
  .info-dialog-footer button{min-height:40px}
  .tool-toast{max-width:calc(100vw - 20px);padding:10px 12px}
}
@media(max-width:380px){
  .bead-app header{padding-right:10px;padding-left:10px}
  .bead-app main{width:calc(100% - 20px)}
  .header-actions{display:grid;grid-template-columns:1fr 1fr}
  .header-action{padding:7px 5px;font-size:10px}
  .format-options{grid-template-columns:repeat(3,minmax(0,1fr))}
  .format-card b{font-size:11px}
  .swatch-grid{grid-template-columns:1fr}
  .color-selector-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .color-selector-grid button{gap:5px;padding:6px}
}
@media(max-width:700px){
  .bead-mode{height:100dvh;padding-bottom:env(safe-area-inset-bottom)}
  .bead-mode-toolbar{padding-right:max(10px,env(safe-area-inset-right));padding-left:max(10px,env(safe-area-inset-left))}
  .bead-mode-top>button,.bead-mode-view-options label,.fit-options button,.zoom-controls button{min-height:40px}
  .zoom-controls input{min-width:0}
  .fullscreen-colors button{min-height:38px}
  .color-panel-actions>button{min-height:40px}
  .color-selector-grid button{min-height:42px}
  .overview-map{width:104px;height:64px}
}
@media(max-width:760px) and (max-height:500px) and (orientation:landscape){
  .bead-mode-toolbar{max-height:58dvh;overflow-y:auto}
  .color-selector-grid{max-height:18dvh}
  .fullscreen-colors{max-height:12dvh}
}
.header-actions{justify-content:flex-end}
.header-action{min-height:36px;padding:8px 14px;border:1px solid transparent;border-radius:999px;font-weight:600;transition:background .18s ease,border-color .18s ease,box-shadow .18s ease,transform .18s ease}
.header-action:active{transform:translateY(1px)}
.header-action:focus-visible,.header-back:focus-visible{outline:2px solid #263b47;outline-offset:3px}
.info-action{border-color:#dbe6e8;background:linear-gradient(135deg,#f3f7f6,#eaf1f2);color:#365563;box-shadow:0 2px 6px #263b470d}
.info-action:hover{border-color:#a9c1c8;background:#e6eff0;box-shadow:0 4px 12px #263b4718}
.reset-action{border-color:#f0d7d4;background:#fff7f5;color:#a45650}
.reset-action:hover{border-color:#d8a8a2;background:#fbecea;box-shadow:0 4px 12px #87443b18}
.header-back{min-height:36px;display:inline-flex;align-items:center;padding:0 2px 0 8px;border-radius:999px;font-weight:600;text-decoration:none}
.header-back:hover{text-decoration:underline;text-underline-offset:3px}
.upload-file-name{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:760px){.preview{scroll-margin-top:16px}}
@media(max-width:380px){
  .header-actions{justify-content:stretch}
  .header-back{grid-column:2;justify-self:end}
}
</style>
