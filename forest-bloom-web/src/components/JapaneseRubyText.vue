<script setup lang="ts">
import { computed } from 'vue'

type RubyPart = { text: string; reading?: string }

const props = defineProps<{
  text: string
  reading?: string
}>()

function toHiragana(value: string) {
  return [...value].map(character => {
    const code = character.codePointAt(0) ?? 0
    return code >= 0x30a1 && code <= 0x30f6
      ? String.fromCodePoint(code - 0x60)
      : character
  }).join('')
}

function annotateKanji(text: string, reading: string): RubyPart[] | undefined {
  const runs = [...text.matchAll(/[一-龯々〆ヵヶ]+|[ぁ-ゖァ-ヺー]+/gu)]
  if (!runs.some(run => /^[一-龯々〆ヵヶ]+$/u.test(run[0]))) return undefined

  const normalizedReading = toHiragana(reading)
  let readingIndex = 0
  let textIndex = 0
  const result: RubyPart[] = []

  runs.forEach((run, index) => {
    const runIndex = run.index ?? 0
    if (runIndex > textIndex) result.push({ text: text.slice(textIndex, runIndex) })

    const isKanji = /^[一-龯々〆ヵヶ]+$/u.test(run[0])
    if (!isKanji) {
      result.push({ text: run[0] })
      const kana = toHiragana(run[0])
      const kanaIndex = normalizedReading.indexOf(kana, readingIndex)
      if (kanaIndex !== -1) readingIndex = kanaIndex + kana.length
      textIndex = runIndex + run[0].length
      return
    }

    const nextKana = runs.slice(index + 1).find(candidate =>
      /^[ぁ-ゖァ-ヺー]+$/u.test(candidate[0])
    )
    const nextKanaText = nextKana ? toHiragana(nextKana[0]) : ''
    const hasLaterKanji = runs.slice(index + 1).some(candidate =>
      /^[一-龯々〆ヵヶ]+$/u.test(candidate[0])
    )
    const trailingKanaIndex = nextKanaText && !hasLaterKanji
      ? normalizedReading.lastIndexOf(nextKanaText)
      : -1
    const nextKanaIndex = trailingKanaIndex >= readingIndex &&
      trailingKanaIndex + nextKanaText.length === normalizedReading.length
      ? trailingKanaIndex
      : nextKanaText
      ? normalizedReading.indexOf(nextKanaText, readingIndex)
      : -1
    if (nextKanaText && nextKanaIndex === -1) {
      result.push({ text: run[0] })
      textIndex = runIndex + run[0].length
      return
    }
    const rubyEnd = nextKanaIndex === -1 ? normalizedReading.length : nextKanaIndex
    const rubyReading = normalizedReading.slice(readingIndex, rubyEnd)
    if (rubyReading) result.push({ text: run[0], reading: rubyReading })
    else result.push({ text: run[0] })
    readingIndex = rubyEnd
    textIndex = runIndex + run[0].length
  })

  if (textIndex < text.length) result.push({ text: text.slice(textIndex) })
  return result
}

const parts = computed(() => {
  const result: RubyPart[] = []
  const rubyPattern = /([一-龯々〆ヵヶ]+)[\[［(（]([ぁ-ゖァ-ヺー]+)[\]］)）]/gu
  let lastIndex = 0

  for (const match of props.text.matchAll(rubyPattern)) {
    const index = match.index ?? 0
    if (index > lastIndex) result.push({ text: props.text.slice(lastIndex, index) })
    const text = match[1]
    const reading = match[2]
    if (text && reading) result.push({ text, reading })
    lastIndex = index + match[0].length
  }

  if (lastIndex < props.text.length) {
    result.push({ text: props.text.slice(lastIndex) })
  }

  if (!result.some(part => part.reading) && props.reading) {
    return annotateKanji(props.text, props.reading) ?? (result.length ? result : [{ text: props.text }])
  }

  return result.length ? result : [{ text: props.text }]
})
</script>

<template>
  <span class="japanese-ruby">
    <template v-for="(part, index) in parts" :key="index">
      <ruby v-if="part.reading">{{ part.text }}<rt>{{ part.reading }}</rt></ruby>
      <span v-else>{{ part.text }}</span>
    </template>
  </span>
</template>

<style scoped>
.japanese-ruby { ruby-position: over; }
.japanese-ruby ruby { ruby-position: over; }
.japanese-ruby rt { color: #6a90a6; font-size: .48em; font-weight: 400; line-height: 1; }
</style>
