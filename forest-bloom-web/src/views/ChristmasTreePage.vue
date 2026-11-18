<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

type Photo = {
  id: number
  name: string
  dataUrl: string
}

const MAX_PHOTOS = 13
const pageElement = ref<HTMLElement | null>(null)
const treeFrame = ref<HTMLIFrameElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const photos = ref<Photo[]>([])
const isImporting = ref(false)
const isExporting = ref(false)
const isFullscreen = ref(false)
const statusMessage = ref('把照片挂上树，再拖动照片调整挂点。')
const treeUrl = `${import.meta.env.BASE_URL}christmas-tree.html`
let nextPhotoId = 0

function syncPhotos() {
  treeFrame.value?.contentWindow?.postMessage(
    { type: 'christmas-photos', photos: photos.value.map((photo) => photo.dataUrl) },
    window.location.origin,
  )
}

function handleFrameLoad() {
  syncPhotos()
  updateFullscreenState()
}

function handleFrameMessage(event: MessageEvent) {
  if (event.source !== treeFrame.value?.contentWindow || event.origin !== window.location.origin) return
  if (event.data?.type === 'christmas-files-drop' && Array.isArray(event.data.files)) {
    void addFiles(event.data.files as File[])
    return
  }
  if (event.data?.type !== 'christmas-photo-remove' || !Number.isInteger(event.data.index)) return

  const index = event.data.index as number
  if (index < 0 || index >= photos.value.length) return
  photos.value.splice(index, 1)
  syncPhotos()
  statusMessage.value = `已移除照片，树上还有 ${photos.value.length} 张。`
}

function compressImage(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error(`${file.name}: 读取文件失败`))
    reader.onload = () => {
      if (typeof reader.result !== 'string') {
        reject(new Error(`${file.name}: 无法读取图片内容`))
        return
      }

      const image = new Image()
      image.onerror = () => reject(new Error(`${file.name}: 图片无法解码`))
      image.onload = () => {
        try {
          const scale = Math.min(1, 1280 / Math.max(image.naturalWidth, image.naturalHeight))
          const canvas = document.createElement('canvas')
          canvas.width = Math.max(1, Math.round(image.naturalWidth * scale))
          canvas.height = Math.max(1, Math.round(image.naturalHeight * scale))
          const context = canvas.getContext('2d')
          if (!context) {
            reject(new Error(`${file.name}: 无法处理图片`))
            return
          }

          context.fillStyle = '#07100d'
          context.fillRect(0, 0, canvas.width, canvas.height)
          context.drawImage(image, 0, 0, canvas.width, canvas.height)
          let quality = 0.84
          let dataUrl = canvas.toDataURL('image/jpeg', quality)
          for (let attempt = 0; dataUrl.length > 720 * 1024 && attempt < 4; attempt += 1) {
            quality -= 0.13
            dataUrl = canvas.toDataURL('image/jpeg', quality)
          }
          resolve(dataUrl)
        } catch {
          reject(new Error(`${file.name}: 图片格式不受支持`))
        }
      }
      image.src = reader.result
    }
    reader.readAsDataURL(file)
  })
}

async function addFiles(fileList: FileList | File[]) {
  const files = Array.from(fileList)
  if (!files.length) return
  isImporting.value = true
  let added = 0
  const errors: string[] = []

  try {
    for (const file of files) {
      if (photos.value.length >= MAX_PHOTOS) {
        errors.push(`最多只能挂 ${MAX_PHOTOS} 张照片`)
        break
      }
      if (!(file.type.startsWith('image/') || /\.(jpe?g|png|webp|gif|bmp|heic|heif|avif)$/i.test(file.name))) {
        errors.push(`${file.name}: 不是图片`)
        continue
      }
      if (file.size > 20 * 1024 * 1024) {
        errors.push(`${file.name}: 图片超过 20 MB`)
        continue
      }

      try {
        photos.value.push({
          id: nextPhotoId++,
          name: file.name,
          dataUrl: await compressImage(file),
        })
        added += 1
      } catch (error) {
        errors.push(error instanceof Error ? error.message : `${file.name}: 处理失败`)
      }
    }

    syncPhotos()
    statusMessage.value = errors.length
      ? `${added ? `已挂上 ${added} 张。` : ''}${errors.slice(0, 2).join('；')}${errors.length > 2 ? `；另有 ${errors.length - 2} 项未完成` : ''}`
      : `已挂上 ${added} 张照片；拖动可调整挂点，点击可查看大图。`
  } finally {
    isImporting.value = false
  }
}

function openPicker() {
  fileInput.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) void addFiles(input.files)
  input.value = ''
}

function clearPhotos() {
  photos.value = []
  syncPhotos()
  statusMessage.value = '照片已清空，可以重新挂上新的回忆。'
}

function updateFullscreenState() {
  isFullscreen.value = document.fullscreenElement === pageElement.value
  treeFrame.value?.contentWindow?.postMessage(
    { type: 'christmas-fullscreen', active: isFullscreen.value },
    window.location.origin,
  )
}

async function toggleFullscreen() {
  const page = pageElement.value
  if (!page) return

  try {
    if (document.fullscreenElement === page) {
      await document.exitFullscreen()
    } else {
      await page.requestFullscreen()
    }
  } catch (error) {
    statusMessage.value = error instanceof Error ? `无法切换全屏：${error.message}` : '无法切换全屏。'
  }
}

function safeJson(value: unknown) {
  return JSON.stringify(value).replace(/</g, '\\u003c')
}

async function exportPage() {
  if (!photos.value.length) {
    statusMessage.value = '先挂上至少一张照片，再打包分享网页。'
    return
  }

  isExporting.value = true
  try {
    const response = await fetch(treeUrl)
    if (!response.ok) throw new Error(`读取圣诞树页面失败（${response.status}）`)
    const originalHtml = await response.text()
    const bridgeTag = '<script id="christmas-photo-bridge">'
    if (!originalHtml.includes(bridgeTag)) throw new Error('圣诞树照片接口不存在，无法打包。')
    const bootstrap = `<script>window.__CHRISTMAS_PHOTOS__=${safeJson(photos.value.map((photo) => photo.dataUrl))};<\/script>\n`
    const html = originalHtml.replace(bridgeTag, `${bootstrap}${bridgeTag}`)
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'merry-christmas.html'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 30000)
    statusMessage.value = `网页已打包，${photos.value.length} 张照片已嵌入文件。`
  } catch (error) {
    statusMessage.value = error instanceof Error ? `打包失败：${error.message}` : '打包失败，请稍后重试。'
  } finally {
    isExporting.value = false
  }
}

onMounted(() => {
  window.addEventListener('message', handleFrameMessage)
  document.addEventListener('fullscreenchange', updateFullscreenState)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', handleFrameMessage)
  document.removeEventListener('fullscreenchange', updateFullscreenState)
  if (document.fullscreenElement === pageElement.value) void document.exitFullscreen()
})
</script>

<template>
  <main ref="pageElement" class="christmas-page">
    <iframe
      ref="treeFrame"
      class="tree-frame"
      :src="treeUrl"
      title="圣诞树展示"
      @load="handleFrameLoad"
    ></iframe>

    <input
      ref="fileInput"
      class="file-input"
      type="file"
      accept="image/*"
      multiple
      @change="handleFileChange"
    />

    <nav class="tree-tools" aria-label="圣诞树照片工具">
      <button type="button" :disabled="isImporting || photos.length >= MAX_PHOTOS" @click="openPicker">
        {{ isImporting ? '正在处理…' : `＋ 挂照片 · ${photos.length}/${MAX_PHOTOS}` }}
      </button>
      <button class="fullscreen-button" type="button" @click="toggleFullscreen">
        {{ isFullscreen ? '退出全屏' : '全屏' }}
      </button>
      <button type="button" :disabled="photos.length === 0" @click="clearPhotos">清空</button>
      <button class="export-button" type="button" :disabled="isExporting" @click="exportPage">
        {{ isExporting ? '正在打包…' : '打包网页' }}
      </button>
    </nav>

    <p class="tree-status" role="status" aria-live="polite">{{ statusMessage }}</p>
  </main>
</template>

<style scoped>
.christmas-page {
  position: fixed;
  z-index: 20;
  inset: 0;
  width: 100vw;
  height: 100vh;
  height: 100dvh;
  max-width: none;
  min-height: 0;
  margin: 0;
  padding: 0;
  overflow: hidden;
  background: #07100d;
}

.christmas-page:fullscreen {
  width: 100vw;
  height: 100vh;
  height: 100dvh;
}

.christmas-page:fullscreen .tree-tools button:not(.fullscreen-button),
.christmas-page:fullscreen .tree-status {
  display: none;
}

.tree-frame {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  background: #07100d;
}

.file-input {
  display: none;
}

.tree-tools {
  position: absolute;
  z-index: 4;
  right: max(16px, env(safe-area-inset-right));
  bottom: max(20px, env(safe-area-inset-bottom));
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
  max-width: min(560px, 74vw);
}

.tree-tools button {
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid rgba(241, 231, 208, 0.32);
  border-radius: 999px;
  background: rgba(7, 16, 13, 0.82);
  color: #f1e7d0;
  font: 11px "PingFang SC", "Microsoft YaHei", sans-serif;
  cursor: pointer;
  backdrop-filter: blur(8px);
}

.tree-tools button:hover:not(:disabled),
.tree-tools button:focus-visible {
  border-color: #d9b871;
  outline: none;
}

.tree-tools button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.tree-tools .export-button {
  border-color: rgba(217, 184, 113, 0.75);
  background: rgba(217, 184, 113, 0.93);
  color: #07100d;
}

.tree-status {
  position: absolute;
  z-index: 4;
  bottom: max(30px, env(safe-area-inset-bottom));
  left: max(18px, env(safe-area-inset-left));
  max-width: min(42vw, 540px);
  margin: 0;
  color: rgba(223, 226, 211, 0.7);
  font: 11px/1.5 "PingFang SC", "Microsoft YaHei", sans-serif;
  pointer-events: none;
  text-shadow: 0 1px 5px #07100d;
}

@media (max-width: 700px) {
  .tree-tools {
    right: max(12px, env(safe-area-inset-right));
    bottom: max(12px, env(safe-area-inset-bottom));
    left: max(12px, env(safe-area-inset-left));
    max-width: none;
    gap: 6px;
  }

  .tree-tools button {
    min-height: 34px;
    padding: 0 10px;
    font-size: 10px;
  }

  .tree-status {
    right: max(18px, env(safe-area-inset-right));
    bottom: calc(max(12px, env(safe-area-inset-bottom)) + 48px);
    left: max(18px, env(safe-area-inset-left));
    max-width: none;
    text-align: center;
    font-size: 10px;
  }
}

@media (max-width: 480px) {
  .tree-tools {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .tree-tools button {
    width: 100%;
    min-height: 38px;
    padding: 0 6px;
    font-size: 10px;
  }

  .tree-tools button:first-child {
    grid-column: 1 / -1;
  }

  .tree-status {
    bottom: calc(max(12px, env(safe-area-inset-bottom)) + 92px);
  }
}

@media (max-height: 500px) and (orientation: landscape) {
  .tree-tools {
    top: max(10px, env(safe-area-inset-top));
    right: max(10px, env(safe-area-inset-right));
    bottom: auto;
    left: auto;
    max-width: 70vw;
  }

  .tree-status {
    display: none;
  }
}
</style>
