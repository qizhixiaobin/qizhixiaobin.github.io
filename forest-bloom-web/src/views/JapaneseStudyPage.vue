<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import JapaneseRubyText from '../components/JapaneseRubyText.vue'
import { profile } from '../data/profile'

type BookId = 'redbook' | 'greenbook' | 'bluebook'
type RecordKind = 'vocabulary' | 'grammar'
type StudyExample = { text?: string; ja?: string; zh?: string; tag?: string }
type StudyRecord = {
  id: string
  sourceId: string
  book: BookId
  level: string
  kind: RecordKind
  term: string
  reading: string
  writtenForms: string[]
  partOfSpeech: string[]
  sourcePartOfSpeech: string[]
  meaningZh: string
  pitchAccent?: string
  examples: StudyExample[]
  relatedTerms?: string[]
  homophones?: string[]
  connections?: string[]
  explanations?: string[]
  notes?: string[]
  search: { meaningZh: string[]; kana: string[]; written: string[] }
}

function validateDeck(payload: unknown): StudyRecord[] {
  if (!Array.isArray(payload) || !payload.every(isStudyRecord)) {
    throw new Error('The cleaned deck does not match the expected format.')
  }
  if (new Set(payload.map(record => record.id)).size !== payload.length) {
    throw new Error('The cleaned deck contains duplicate record IDs.')
  }
  return payload
}

const STORAGE_KEY = 'forest-bloom-japanese-study-progress-v1'
const SELECTION_STORAGE_KEY = 'forest-bloom-japanese-study-selection-v1'
const baseUrl = import.meta.env.BASE_URL
const bookOptions: Array<{ id: BookId; label: string }> = [
  { id: 'redbook', label: '红宝书' },
  { id: 'greenbook', label: '绿宝书' },
  { id: 'bluebook', label: '蓝宝书' },
]
const levelOptions = [1, 2, 3, 4, 5]
const selectedBook = ref<BookId>('redbook')
const bookSelectionExpanded = ref(true)
const selectedLevel = ref(1)
const pageMode = ref<'browse' | 'study'>('browse')
const categoryFilter = ref<'all' | RecordKind>('all')
const partOfSpeechFilter = ref('全部')
const searchMode = ref('全部')
const searchQuery = ref('')
const statusFilter = ref('全部')
const browseSortMode = ref<'ordered' | 'gojuon' | 'random'>('ordered')
const randomizedRecordIds = ref<string[]>([])
const records = ref<StudyRecord[]>([])
const selectedRecordId = ref('')
const mobileDetailOpen = ref(false)
const mobileDetailElement = ref<HTMLElement | null>(null)
const meaningHidden = ref(false)
const studyQueueIds = ref<string[]>([])
const studyCandidates = ref<StudyRecord[]>([])
const studySearchRecords = ref<StudyRecord[]>([])
const studyRecords = ref<StudyRecord[]>([])
const studySearchMode = ref('全部')
const studySearchQuery = ref('')
const studyPartOfSpeechFilter = ref('全部')
const studyBook = ref<BookId>('redbook')
const hasPersistedStudySelection = ref(false)
const studyBookSelectionExpanded = ref(false)
const studyLevel = ref(1)
const studyBookLoading = ref(false)
const studyError = ref('')
const studyIndex = ref(0)
const studyRandomOrder = ref(false)
const studyShowKana = ref(false)
const studyShowMeaning = ref(false)
const answerVisible = ref(false)
const knownIds = ref<string[]>([])
const unsureIds = ref<string[]>([])
const isLoading = ref(true)
const error = ref('')
const speechError = ref('')
const japaneseVoices = ref<SpeechSynthesisVoice[]>([])
const selectedVoiceURI = ref('')
const activeSpeechKey = ref('')
const speechStatus = ref<'starting' | 'speaking' | ''>('')
const resultLimit = ref(100)
let deckRequestId = 0
let studyDeckRequestId = 0
let activeUtterance: SpeechSynthesisUtterance | undefined
let speechStartTimeout: number | undefined
let clearingStudyProgress = false

const searchModes = ['全部', '中文意思', '假名', '汉字/单词', '通配符']
const selectedJapaneseVoice = computed(() =>
  japaneseVoices.value.find(voice => voice.voiceURI === selectedVoiceURI.value)
)
const japaneseCollator = new Intl.Collator('ja-JP', { sensitivity: 'base', numeric: true })
const browseWildcardPattern = computed(() => parseWildcardPattern(searchQuery.value))
const studyWildcardPattern = computed(() => parseWildcardPattern(studySearchQuery.value))
const browseSearchMode = computed(() =>
  searchMode.value === '全部' && isRepeatedWildcardFormat(searchQuery.value)
    ? '通配符'
    : searchMode.value
)
const studySearchModeForFiltering = computed(() =>
  studySearchMode.value === '全部' && isRepeatedWildcardFormat(studySearchQuery.value)
    ? '通配符'
    : studySearchMode.value
)
const selectedBookOption = computed(() => bookOptions.find(book => book.id === selectedBook.value)!)
const selectedStudyBookOption = computed(() => bookOptions.find(book => book.id === studyBook.value)!)
const studyPartOfSpeechOptions = computed(() => [
  '全部',
  ...[...new Set(studySearchRecords.value.flatMap(record => record.partOfSpeech))]
    .sort((left, right) => left.localeCompare(right, 'zh-CN')),
])
const partOfSpeechOptions = computed(() => [
  '全部',
  ...[...new Set(records.value.flatMap(record => record.partOfSpeech))]
    .sort((left, right) => left.localeCompare(right, 'zh-CN')),
])
const availableKinds = computed(() => [...new Set(records.value.map(record => record.kind))])
const filteredRecords = computed(() => {
  const query = normalizeQuery(searchQuery.value)
  return records.value.filter(record => {
    if (categoryFilter.value !== 'all' && record.kind !== categoryFilter.value) return false
    if (partOfSpeechFilter.value !== '全部' && !record.partOfSpeech.includes(partOfSpeechFilter.value)) return false
    const known = knownIds.value.includes(record.id)
    if (statusFilter.value === '已掌握' && !known) return false
    if (statusFilter.value === '待复习' && known) return false
    if (browseWildcardPattern.value.error) return false
    return (!query && browseSearchMode.value !== '通配符') ||
      matchesQuery(record, query, browseSearchMode.value, browseWildcardPattern.value.expression)
  })
})
const sortedRecords = computed(() => {
  if (browseSortMode.value === 'ordered') return filteredRecords.value
  if (browseSortMode.value === 'gojuon') {
    return [...filteredRecords.value].sort((left, right) =>
      japaneseCollator.compare(left.reading || left.term, right.reading || right.term)
    )
  }
  const positions = new Map(randomizedRecordIds.value.map((id, index) => [id, index]))
  return [...filteredRecords.value].sort((left, right) =>
    (positions.get(left.id) ?? Number.MAX_SAFE_INTEGER) -
    (positions.get(right.id) ?? Number.MAX_SAFE_INTEGER)
  )
})
const visibleRecords = computed(() => sortedRecords.value.slice(0, resultLimit.value))
const selectedRecord = computed(() =>
  filteredRecords.value.find(record => record.id === selectedRecordId.value) ?? filteredRecords.value[0]
)
const selectedRelatedTerms = computed(() => selectedRecord.value
  ? [...(selectedRecord.value.relatedTerms ?? []), ...(selectedRecord.value.homophones ?? [])]
  : []
)
const currentStudyRecord = computed(() => {
  const id = studyQueueIds.value[studyIndex.value]
  return studyRecords.value.find(record => record.id === id)
})
const studyFilteredRecords = computed(() => {
  const query = normalizeQuery(studySearchQuery.value)
  return studySearchRecords.value.filter(record => {
    if (studyPartOfSpeechFilter.value !== '全部' &&
      !record.partOfSpeech.includes(studyPartOfSpeechFilter.value)) return false
    if (studyWildcardPattern.value.error) return false
    return (!query && studySearchModeForFiltering.value !== '通配符') ||
      matchesQuery(record, query, studySearchModeForFiltering.value, studyWildcardPattern.value.expression)
  })
})
const knownCount = computed(() => records.value.filter(record => knownIds.value.includes(record.id)).length)
const studyProgress = computed(() => {
  const known = studyCandidates.value.filter(record => knownIds.value.includes(record.id)).length
  const unsure = studyCandidates.value.filter(record =>
    !knownIds.value.includes(record.id) && unsureIds.value.includes(record.id)
  ).length
  const unstudied = studyCandidates.value.length - known - unsure
  return {
    known,
    unsure,
    unstudied,
    total: studyCandidates.value.length,
    knownPercent: studyCandidates.value.length ? known / studyCandidates.value.length * 100 : 0,
    unsurePercent: studyCandidates.value.length ? unsure / studyCandidates.value.length * 100 : 0,
    unstudiedPercent: studyCandidates.value.length ? unstudied / studyCandidates.value.length * 100 : 0,
  }
})
const selectedBookProgressIds = computed(() => {
  const prefix = `${selectedBook.value}-n`
  return [...new Set([...knownIds.value, ...unsureIds.value])]
    .filter(id => id.startsWith(prefix))
})
const currentLevelProgressIds = computed(() => {
  const prefix = `${selectedBook.value}-n${selectedLevel.value}-`
  return [...new Set([...knownIds.value, ...unsureIds.value])]
    .filter(id => id.startsWith(prefix))
})
const progressPercent = computed(() => records.value.length
  ? Math.round(knownCount.value / records.value.length * 100)
  : 0)
const allStudyCandidatesKnown = computed(() =>
  studyCandidates.value.length > 0 &&
  studyCandidates.value.every(record => knownIds.value.includes(record.id))
)

loadSelection()

watch([selectedBook, selectedLevel], () => void loadDeck(), { immediate: true })
watch([selectedBook, selectedLevel, studyBook, studyLevel], saveSelection)
watch([filteredRecords, selectedRecordId], () => {
  if (!filteredRecords.value.some(record => record.id === selectedRecordId.value)) {
    selectedRecordId.value = filteredRecords.value[0]?.id ?? ''
  }
  meaningHidden.value = false
}, { immediate: true })
watch([filteredRecords, searchMode, searchQuery, categoryFilter, partOfSpeechFilter, statusFilter], () => {
  resultLimit.value = 100
})
watch(filteredRecords, filtered => {
  if (browseSortMode.value === 'random') {
    randomizedRecordIds.value = shuffleIds(filtered.map(record => record.id))
  }
})
watch(partOfSpeechOptions, options => {
  if (!options.includes(partOfSpeechFilter.value)) partOfSpeechFilter.value = '全部'
})
watch(studyPartOfSpeechOptions, options => {
  if (!options.includes(studyPartOfSpeechFilter.value)) studyPartOfSpeechFilter.value = '全部'
})
watch([knownIds, unsureIds], saveProgress, { flush: 'sync' })

loadProgress()

function refreshJapaneseVoices() {
  if (!('speechSynthesis' in window)) return
  japaneseVoices.value = window.speechSynthesis.getVoices()
    .filter(voice => /^ja(-|$)/i.test(voice.lang))
  if (selectedVoiceURI.value && !japaneseVoices.value.some(voice => voice.voiceURI === selectedVoiceURI.value)) {
    selectedVoiceURI.value = ''
  }
}

onMounted(() => {
  refreshJapaneseVoices()
  window.speechSynthesis?.addEventListener('voiceschanged', refreshJapaneseVoices)
})

function isSpeechActive(key: string) {
  return activeSpeechKey.value === key
}

function selectBook(book: BookId) {
  selectedBook.value = book
  bookSelectionExpanded.value = false
}

async function openRecordDetails(record: StudyRecord) {
  const isMobile = window.matchMedia('(max-width: 820px)').matches
  if (isMobile && mobileDetailOpen.value && selectedRecordId.value === record.id) {
    closeMobileDetails()
    return
  }
  selectedRecordId.value = record.id
  if (isMobile) {
    mobileDetailOpen.value = true
    await nextTick()
    mobileDetailElement.value?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'nearest',
    })
  }
}

function closeMobileDetails() {
  mobileDetailOpen.value = false
}

function speakJapanese(text: string, key: string) {
  if (isSpeechActive(key)) {
    stopSpeech()
    return
  }

  if (!('speechSynthesis' in window) || !('SpeechSynthesisUtterance' in window)) {
    speechError.value = '该设备不支持播放语音。'
    return
  }

  const synthesis = window.speechSynthesis
  const content = text.trim()
  if (!content) {
    speechError.value = '没有可朗读的日文内容。'
    return
  }

  if (activeSpeechKey.value) stopSpeech()
  speechError.value = ''
  activeSpeechKey.value = key
  speechStatus.value = 'starting'

  const utterance = new SpeechSynthesisUtterance(content)
  utterance.lang = 'ja-JP'
  utterance.rate = 0.85
  utterance.volume = 1
  if (selectedJapaneseVoice.value) utterance.voice = selectedJapaneseVoice.value
  utterance.onstart = () => {
    if (activeUtterance === utterance) {
      if (speechStartTimeout !== undefined) window.clearTimeout(speechStartTimeout)
      speechStartTimeout = undefined
      speechStatus.value = 'speaking'
    }
  }
  utterance.onend = () => {
    if (activeUtterance === utterance) {
      activeUtterance = undefined
      activeSpeechKey.value = ''
      speechStatus.value = ''
    }
  }
  utterance.onerror = event => {
    if (activeUtterance === utterance) {
      activeUtterance = undefined
      activeSpeechKey.value = ''
      speechStatus.value = ''
    }
    if (event.error !== 'canceled' && event.error !== 'interrupted') {
      speechError.value = '该设备不支持播放语音。'
    }
  }
  activeUtterance = utterance
  try {
    if (synthesis.paused) synthesis.resume()
    synthesis.speak(utterance)
    speechStartTimeout = window.setTimeout(() => {
      if (activeUtterance !== utterance || speechStatus.value === 'speaking') return
      stopSpeech()
      speechError.value = '该设备不支持播放语音。'
    }, 10000)
  } catch (cause) {
    if (activeUtterance === utterance) {
      activeUtterance = undefined
      activeSpeechKey.value = ''
      speechStatus.value = ''
    }
    if (speechStartTimeout !== undefined) window.clearTimeout(speechStartTimeout)
    speechStartTimeout = undefined
    console.error('Unable to start browser Japanese speech synthesis.', cause)
    speechError.value = '该设备不支持播放语音。'
  }
}

function speakRecord(record: StudyRecord, key = `record:${record.id}`) {
  const text = record.reading.trim() || record.term.replace(
    /([一-龯々〆ヵヶ]+)[\[［(（]([ぁ-ゖァ-ヺー]+)[\]］)）]/gu,
    '$2',
  )
  speakJapanese(text, key)
}

function speakExample(example: StudyExample, key: string) {
  const source = example.ja || example.text || ''
  const japaneseText = (example.ja ? source : source.split('/')[0] ?? '')
    .replace(/[△▲]\s*/gu, '')
    .replace(
      /([一-龯々〆ヵヶ]+)[\[［(（]([ぁ-ゖァ-ヺー]+)[\]］)）]/gu,
      '$2',
    )
    .replace(/\s+/gu, ' ')
    .trim()

  if (japaneseText) speakJapanese(japaneseText, key)
}

function stopSpeech() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
  if (speechStartTimeout !== undefined) window.clearTimeout(speechStartTimeout)
  speechStartTimeout = undefined
  activeUtterance = undefined
  activeSpeechKey.value = ''
  speechStatus.value = ''
}

onBeforeUnmount(() => {
  stopSpeech()
  window.speechSynthesis?.removeEventListener('voiceschanged', refreshJapaneseVoices)
})

async function loadDeck() {
  const requestId = ++deckRequestId
  isLoading.value = true
  error.value = ''
  records.value = []
  selectedRecordId.value = ''
  categoryFilter.value = 'all'
  partOfSpeechFilter.value = '全部'
  searchQuery.value = ''
  try {
    const path = `${import.meta.env.BASE_URL}data/japanese/cleaned/${selectedBook.value}/N${selectedLevel.value}.json`
    const response = await fetch(path)
    if (!response.ok) throw new Error(`Deck request failed with status ${response.status}.`)
    const payload = validateDeck(await response.json())
    if (requestId !== deckRequestId) return
    records.value = payload
  } catch (cause) {
    if (requestId !== deckRequestId) return
    console.error('Unable to load the cleaned Japanese deck.', cause)
    error.value = `日语数据加载失败，请检查 public/data/japanese/cleaned/${selectedBook.value}/N${selectedLevel.value}.json。`
  } finally {
    if (requestId === deckRequestId) isLoading.value = false
  }
}

function isStudyRecord(value: unknown): value is StudyRecord {
  if (typeof value !== 'object' || value === null) return false
  return 'id' in value && typeof value.id === 'string' &&
    'sourceId' in value && typeof value.sourceId === 'string' &&
    'book' in value && typeof value.book === 'string' &&
    'level' in value && typeof value.level === 'string' &&
    'kind' in value && (value.kind === 'vocabulary' || value.kind === 'grammar') &&
    'term' in value && typeof value.term === 'string' &&
    'reading' in value && typeof value.reading === 'string' &&
    'partOfSpeech' in value && Array.isArray(value.partOfSpeech) &&
    'meaningZh' in value && typeof value.meaningZh === 'string' &&
    'examples' in value && Array.isArray(value.examples) &&
    'search' in value && typeof value.search === 'object' && value.search !== null &&
    'meaningZh' in value.search && Array.isArray(value.search.meaningZh) &&
    'kana' in value.search && Array.isArray(value.search.kana) &&
    'written' in value.search && Array.isArray(value.search.written)
}

function isBookId(value: unknown): value is BookId {
  return bookOptions.some(book => book.id === value)
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string')
}

function normalizeQuery(value: string) {
  return toHiragana(value.normalize('NFKC').trim().toLocaleLowerCase())
}

function toHiragana(value: string) {
  return [...value].map(character => {
    const code = character.codePointAt(0) ?? 0
    return code >= 0x30a1 && code <= 0x30f6
      ? String.fromCodePoint(code - 0x60)
      : character
  }).join('')
}

function parseWildcardPattern(query: string) {
  if (!query) return { expression: null, error: '' }
  try {
    const shape = query.trim()
    if (/^[A-Z]+$/u.test(shape) && new Set(shape).size < shape.length) {
      const captures = new Map<string, number>()
      let captureCount = 0
      const pattern = [...shape].map(symbol => {
        const existingCapture = captures.get(symbol)
        if (existingCapture !== undefined) return `\\${existingCapture}`
        captureCount += 1
        captures.set(symbol, captureCount)
        return '(.)'
      }).join('')
      return { expression: new RegExp(`^${pattern}$`, 'iu'), error: '' }
    }

    const escaped = normalizeQuery(query).replace(/[.+^${}()|[\]\\]/gu, '\\$&')
    return {
      expression: new RegExp(`^${escaped.replace(/\*/gu, '.*').replace(/\?/gu, '.')}$`, 'iu'),
      error: '',
    }
  } catch (cause) {
    if (cause instanceof SyntaxError) {
      return { expression: null, error: '通配符格式无效，请检查输入内容。' }
    }
    throw cause
  }
}

function isRepeatedWildcardFormat(query: string) {
  const shape = query.trim()
  return /^[A-Z]+$/u.test(shape) && new Set(shape).size < shape.length
}

function matchesQuery(record: StudyRecord, query: string, mode: string, expression: RegExp | null = null) {
  const includes = (values: string[]) => values.some(value => normalizeQuery(value).includes(query))
  const headwords = [...new Set([
    record.term,
    record.reading,
    ...record.writtenForms,
    ...record.search.kana,
    ...record.search.written,
  ].map(normalizeQuery).filter(Boolean))]
  if (mode === '中文意思') return includes(record.search.meaningZh)
  if (mode === '假名') return includes(record.search.kana)
  if (mode === '汉字/单词') return includes([...record.search.written, ...headwords])
  if (mode === '通配符') {
    if (!query) return true
    const japaneseFields = [
      record.term,
      record.reading,
      ...record.writtenForms,
      ...record.search.kana,
      ...record.search.written,
    ]
    return expression !== null &&
      japaneseFields.some(value => expression.test(normalizeQuery(value)))
  }
  return includes([
    ...record.search.meaningZh,
    ...record.search.kana,
    ...record.search.written,
    ...headwords,
    record.reading,
    record.meaningZh,
  ])
}

function loadProgress() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return
    const parsed: unknown = JSON.parse(saved)
    if (
      typeof parsed !== 'object' || parsed === null ||
      !('version' in parsed) || parsed.version !== 1 ||
      !('knownCardIds' in parsed)
    ) {
      throw new Error('Saved progress has an unsupported format.')
    }
    const savedKnownIds = parsed.knownCardIds
    const savedUnsureIds = 'unsureCardIds' in parsed ? parsed.unsureCardIds : []
    if (!isStringArray(savedKnownIds) || !isStringArray(savedUnsureIds)) {
      throw new Error('Saved progress has an unsupported format.')
    }
    knownIds.value = savedKnownIds
    unsureIds.value = savedUnsureIds.filter(id => !savedKnownIds.includes(id))
  } catch (cause) {
    console.error('Unable to restore Japanese study progress.', cause)
    error.value = '本地学习进度无法读取；搜索和浏览仍可正常使用。'
  }
}

function loadSelection() {
  try {
    const saved = localStorage.getItem(SELECTION_STORAGE_KEY)
    if (!saved) return
    const parsed: unknown = JSON.parse(saved)
    if (
      typeof parsed !== 'object' || parsed === null ||
      !('version' in parsed) || parsed.version !== 1 ||
      !('selectedBook' in parsed) || !isBookId(parsed.selectedBook) ||
      !('selectedLevel' in parsed) || typeof parsed.selectedLevel !== 'number' ||
      !levelOptions.includes(parsed.selectedLevel) ||
      !('studyBook' in parsed) || !isBookId(parsed.studyBook) ||
      !('studyLevel' in parsed) || typeof parsed.studyLevel !== 'number' ||
      !levelOptions.includes(parsed.studyLevel)
    ) {
      throw new Error('Saved Japanese study selection has an unsupported format.')
    }
    selectedBook.value = parsed.selectedBook
    selectedLevel.value = parsed.selectedLevel
    studyBook.value = parsed.studyBook
    studyLevel.value = parsed.studyLevel
    hasPersistedStudySelection.value = true
  } catch (cause) {
    console.error('Unable to restore Japanese study selection.', cause)
    error.value = '本地教材选择无法读取；已恢复默认选项。'
  }
}

function saveSelection() {
  try {
    localStorage.setItem(SELECTION_STORAGE_KEY, JSON.stringify({
      version: 1,
      selectedBook: selectedBook.value,
      selectedLevel: selectedLevel.value,
      studyBook: studyBook.value,
      studyLevel: studyLevel.value,
    }))
  } catch (cause) {
    console.error('Unable to save Japanese study selection.', cause)
    error.value = '浏览器无法保存教材选择，请检查本地存储空间。'
  }
}

function saveProgress() {
  if (clearingStudyProgress) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: 1,
      knownCardIds: knownIds.value,
      unsureCardIds: unsureIds.value,
    }))
  } catch (cause) {
    console.error('Unable to save Japanese study progress.', cause)
    error.value = '浏览器无法保存学习进度，请检查本地存储空间。'
  }
}

function clearAllStudyProgress() {
  if (!window.confirm('确定清除日语学习功能的全部学习进度和当前练习队列吗？只会删除本功能保存的日语学习进度，不会影响拼豆或其他数据。')) return
  try {
    localStorage.removeItem(STORAGE_KEY)
    clearingStudyProgress = true
    knownIds.value = []
    unsureIds.value = []
    studyQueueIds.value = []
    studyCandidates.value = []
    studySearchRecords.value = []
    studyRecords.value = []
    studySearchQuery.value = ''
    studySearchMode.value = '全部'
    studyPartOfSpeechFilter.value = '全部'
    studyIndex.value = 0
    answerVisible.value = false
    pageMode.value = 'browse'
    clearingStudyProgress = false
    error.value = ''
  } catch (cause) {
    clearingStudyProgress = false
    console.error('Unable to clear Japanese study progress.', cause)
    error.value = '清除日语学习进度失败，请检查浏览器的站点存储设置。'
  }
}

function clearBookProgress() {
  const bookPrefix = `${selectedBook.value}-n`
  const bookIds = new Set([...knownIds.value, ...unsureIds.value].filter(id => id.startsWith(bookPrefix)))
  if (!bookIds.size) return
  const bookLabel = bookOptions.find(book => book.id === selectedBook.value)?.label ?? selectedBook.value
  if (!window.confirm(`确定清除${bookLabel}所有等级的 ${bookIds.size} 条学习状态吗？其他教材不受影响。`)) return
  knownIds.value = knownIds.value.filter(id => !bookIds.has(id))
  unsureIds.value = unsureIds.value.filter(id => !bookIds.has(id))
  if (pageMode.value === 'study' && studyBook.value === selectedBook.value) updateStudyOrder()
}

function clearCurrentLevelProgress() {
  const levelPrefix = `${selectedBook.value}-n${selectedLevel.value}-`
  const levelIds = new Set([...knownIds.value, ...unsureIds.value].filter(id => id.startsWith(levelPrefix)))
  if (!levelIds.size) return
  const bookLabel = bookOptions.find(book => book.id === selectedBook.value)?.label ?? selectedBook.value
  if (!window.confirm(`确定清除${bookLabel} N${selectedLevel.value}的 ${levelIds.size} 条学习状态吗？其他教材和等级不受影响。`)) return
  knownIds.value = knownIds.value.filter(id => !levelIds.has(id))
  unsureIds.value = unsureIds.value.filter(id => !levelIds.has(id))
  if (pageMode.value === 'study' && studyBook.value === selectedBook.value && studyLevel.value === selectedLevel.value) {
    updateStudyOrder()
  }
}

function toggleKnown(record: StudyRecord) {
  const wasKnown = knownIds.value.includes(record.id)
  knownIds.value = wasKnown
    ? knownIds.value.filter(id => id !== record.id)
    : [...knownIds.value, record.id]
  unsureIds.value = unsureIds.value.filter(id => id !== record.id)
  if (studyCandidates.value.some(candidate => candidate.id === record.id)) updateStudyOrder()
}

function showMore() {
  resultLimit.value += 100
}

function setBrowseSortMode(mode: 'ordered' | 'gojuon' | 'random') {
  browseSortMode.value = mode
  if (mode === 'random') {
    randomizedRecordIds.value = shuffleIds(filteredRecords.value.map(record => record.id))
  }
}

function getStudyTerm(record: StudyRecord) {
  const candidates = [record.term, ...record.writtenForms]
  const writtenTerm = candidates.find(value => value.trim()) ?? record.term
  return writtenTerm.replace(
    /([一-龯々〆ヵヶ]+)[\[［(（][ぁ-ゖァ-ヺー]+[\]］)）]/gu,
    '$1',
  )
}

function shuffleIds(ids: string[]) {
  for (let index = ids.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    const currentId = ids[index]
    const swapId = ids[swapIndex]
    if (currentId === undefined || swapId === undefined) {
      throw new Error('Cannot shuffle an incomplete study queue.')
    }
    ids[index] = swapId
    ids[swapIndex] = currentId
  }
  return ids
}

function startStudy(
  candidates?: StudyRecord[],
  book: BookId = selectedBook.value,
  level = selectedLevel.value,
) {
  const sourceRecords = candidates ?? filteredRecords.value
  studyCandidates.value = [...sourceRecords]
  studyBook.value = book
  studyLevel.value = level
  studyRecords.value = [...studyCandidates.value]
  studyQueueIds.value = studyRecords.value
    .filter(record => !knownIds.value.includes(record.id))
    .map(record => record.id)
  if (studyRandomOrder.value) shuffleIds(studyQueueIds.value)
  studyIndex.value = 0
  answerVisible.value = false
  pageMode.value = 'study'
}

function applyStudySearch() {
  startStudy(studyFilteredRecords.value, studyBook.value, studyLevel.value)
}

function updateStudyOrder() {
  const completedAndCurrent = studyQueueIds.value.slice(0, studyIndex.value + 1)
  const completedIds = new Set(completedAndCurrent)
  let upcoming = studyQueueIds.value.slice(studyIndex.value + 1)
    .filter(id => !knownIds.value.includes(id))
  if (studyRandomOrder.value) {
    upcoming = shuffleIds(upcoming)
  } else {
    upcoming = studyRecords.value.filter(record =>
      !knownIds.value.includes(record.id) && !completedIds.has(record.id)
    ).map(record => record.id)
  }
  studyQueueIds.value = [...completedAndCurrent, ...upcoming]
}

function removeKnownUpcomingStudyCards() {
  const completedIds = studyQueueIds.value.slice(0, studyIndex.value)
  const upcomingIds = studyQueueIds.value.slice(studyIndex.value)
    .filter(id => !knownIds.value.includes(id))
  studyQueueIds.value = [...completedIds, ...upcomingIds]
}

function updateStudyDisplay() {
  answerVisible.value = false
}

function restartStudy() {
  startStudy(studyCandidates.value, studyBook.value, studyLevel.value)
}

function selectStudyBook(book: BookId) {
  if (book === studyBook.value) {
    studyBookSelectionExpanded.value = false
    return
  }
  void loadStudyDeck(book, studyLevel.value).then(loaded => {
    if (loaded) studyBookSelectionExpanded.value = false
  })
}

function onStudyLevelChange(event: Event) {
  const level = Number((event.currentTarget as HTMLSelectElement).value)
  if (levelOptions.includes(level) && level !== studyLevel.value) {
    void loadStudyDeck(studyBook.value, level)
  }
}

async function loadStudyDeck(book: BookId, level: number): Promise<boolean> {
  const requestId = ++studyDeckRequestId
  studyBookLoading.value = true
  studyError.value = ''
  try {
    const path = `${import.meta.env.BASE_URL}data/japanese/cleaned/${book}/N${level}.json`
    const response = await fetch(path)
    if (!response.ok) throw new Error(`Deck request failed with status ${response.status}.`)
    const payload = validateDeck(await response.json())
    if (requestId !== studyDeckRequestId) return false
    studySearchRecords.value = payload
    if (!studyPartOfSpeechOptions.value.includes(studyPartOfSpeechFilter.value)) {
      studyPartOfSpeechFilter.value = '全部'
    }
    startStudy(studyFilteredRecords.value, book, level)
    return true
  } catch (cause) {
    if (requestId !== studyDeckRequestId) return false
    console.error('Unable to load the selected Japanese study deck.', cause)
    studyError.value = `背词词库加载失败，请检查 ${book} N${level} 数据。`
    return false
  } finally {
    if (requestId === studyDeckRequestId) studyBookLoading.value = false
  }
}

async function enterStudy() {
  if (
    hasPersistedStudySelection.value &&
    (!studySearchRecords.value.length ||
      studySearchRecords.value[0]?.book !== studyBook.value ||
      studySearchRecords.value[0]?.level !== `N${studyLevel.value}`)
  ) {
    await loadStudyDeck(studyBook.value, studyLevel.value)
    return
  }
  if (!studyQueueIds.value.length) {
    studySearchRecords.value = [...filteredRecords.value]
    startStudy(studyFilteredRecords.value, selectedBook.value, selectedLevel.value)
    return
  }
  removeKnownUpcomingStudyCards()
  if (studyIndex.value >= studyQueueIds.value.length) restartStudy()
  pageMode.value = 'study'
}

function showStudyAnswer() {
  answerVisible.value = true
}

function advanceStudy() {
  if (!studyQueueIds.value.length) return
  studyIndex.value = Math.min(studyIndex.value + 1, studyQueueIds.value.length)
  answerVisible.value = false
}

function returnToPreviousStudyRecord() {
  if (studyIndex.value <= 0) return
  studyIndex.value -= 1
  answerVisible.value = false
}

function markStudyRecord(known: boolean) {
  const record = currentStudyRecord.value
  if (!record) return
  if (known) {
    knownIds.value = [...new Set([...knownIds.value, record.id])]
    unsureIds.value = unsureIds.value.filter(id => id !== record.id)
  } else {
    knownIds.value = knownIds.value.filter(id => id !== record.id)
    unsureIds.value = [...new Set([...unsureIds.value, record.id])]
  }
  updateStudyOrder()
  advanceStudy()
}

function previewMeaning(record: StudyRecord) {
  if (record.meaningZh) return record.meaningZh
  return record.explanations?.[0] ?? record.examples.find(example => example.zh)?.zh ?? '暂无中文释义'
}

function exportBackup() {
  const rows = [
    ['ID', '书籍', '等级', '类型', '词条', '读音', '词义', '已掌握'],
    ...records.value.map(record => [
      record.id,
      bookOptions.find(book => book.id === record.book)?.label ?? record.book,
      record.level,
      record.kind === 'grammar' ? '语法' : '词汇',
      record.term,
      record.reading,
      previewMeaning(record),
      knownIds.value.includes(record.id) ? '是' : '否',
    ]),
  ]
  const content = rows.map(row =>
    row.map(value => `"${value.replaceAll('"', '""')}"`).join(',')
  ).join('\r\n')
  const blob = new Blob(['\uFEFF', content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'japanese-study-progress.csv'
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
</script>

<template>
  <div class="study-page">
    <header class="study-header">
      <RouterLink class="brand" to="/?section=diy">
        <img :src="profile.avatarImage" alt="" />
        <span><strong>Abin</strong><small>JAPANESE LIBRARY</small></span>
      </RouterLink>
      <RouterLink class="back-link" to="/?section=diy">← 返回 DIY 功能</RouterLink>
    </header>

    <main class="study-main">
      <section class="study-intro">
        <p class="eyebrow">JAPANESE · LOOK UP & LEARN</p>
        <h1>把日语，<em>查得清楚，记得长久。</em></h1>
        <p>按教材、等级和词性浏览，或从汉字、假名、中文意思与词形开始搜索。</p>
      </section>

      <div v-if="error" class="notice error-notice" role="alert">{{ error }}</div>
      <div v-if="speechError" class="notice error-notice" role="alert">{{ speechError }}</div>
      <div v-if="studyError" class="notice error-notice" role="alert">{{ studyError }}</div>

      <nav class="mode-switch" aria-label="日语学习模式">
        <button :class="{ active: pageMode === 'browse' }" @click="pageMode = 'browse'">词库浏览</button>
        <button :class="{ active: pageMode === 'study' }" :disabled="!records.length && !studyRecords.length" @click="enterStudy">背词练习</button>
        <button class="clear-all-progress-nav" :disabled="!knownIds.length && !unsureIds.length" @click="clearAllStudyProgress">清除全部进度</button>
      </nav>
      <label class="voice-picker">
        <span><span class="voice-picker-icon" aria-hidden="true">♫</span>朗读音色</span>
        <select v-model="selectedVoiceURI" :disabled="!japaneseVoices.length" aria-label="选择日语朗读音色">
          <option value="">浏览器默认声音</option>
          <option v-for="voice in japaneseVoices" :key="voice.voiceURI" :value="voice.voiceURI">{{ voice.name }} · {{ voice.lang }}</option>
        </select>
        <small>{{ japaneseVoices.length ? `可选 ${japaneseVoices.length} 种日语声音` : '由浏览器提供可用声音' }}</small>
      </label>

      <section v-if="pageMode === 'browse'" class="browse-panel">
        <div v-if="bookSelectionExpanded" class="book-picker">
          <div class="book-picker-heading">
            <div><p class="eyebrow">CHOOSE YOUR BOOK</p><h2>选择教材</h2></div>
            <div class="book-picker-actions">
              <span>选择后可随时更换</span>
              <button class="clear-study-progress" :disabled="!selectedBookProgressIds.length" @click="clearBookProgress">清除本书进度</button>
            </div>
          </div>
          <div class="book-card-grid">
            <button
              v-for="book in bookOptions"
              :key="book.id"
              type="button"
              class="book-card"
              :class="[`book-${book.id}`, { selected: selectedBook === book.id }]"
              :aria-pressed="selectedBook === book.id"
              @click="selectBook(book.id)"
            >
              <img v-if="book.id !== 'greenbook'" :src="`${baseUrl}images/book/${book.id}face.png`" :alt="`${book.label}封面`" />
              <span v-else class="greenbook-cover" aria-hidden="true"><b>緑宝書</b><small>日本語能力試験</small></span>
              <span class="book-card-caption"><strong>{{ book.label }}</strong><small>{{ book.id === 'bluebook' ? '语法汇总' : '词汇学习' }}</small></span>
              <span v-if="selectedBook === book.id" class="book-selected-mark" aria-label="当前选择">✓</span>
            </button>
          </div>
        </div>
        <div v-else class="selected-book-bar">
          <img v-if="selectedBook !== 'greenbook'" :src="`${baseUrl}images/book/${selectedBook}face.png`" :alt="`${selectedBookOption.label}封面`" />
          <span v-else class="selected-greenbook-mark" aria-hidden="true">緑</span>
          <span><small>当前教材</small><strong>{{ selectedBookOption.label }}</strong></span>
          <button type="button" class="clear-study-progress" :disabled="!selectedBookProgressIds.length" @click="clearBookProgress">清除本书进度</button>
          <button type="button" @click="bookSelectionExpanded = true">更换教材</button>
        </div>
        <div class="control-row">
          <label>JLPT 等级
            <select v-model.number="selectedLevel" aria-label="选择 JLPT 等级">
              <option v-for="level in levelOptions" :key="level" :value="level">N{{ level }}</option>
            </select>
          </label>
          <label>搜索范围
            <select v-model="searchMode" aria-label="选择搜索范围">
              <option v-for="mode in searchModes" :key="mode" :value="mode">{{ mode }}</option>
            </select>
          </label>
          <label>学习状态
            <select v-model="statusFilter" aria-label="按学习状态筛选">
              <option>全部</option><option>待复习</option><option>已掌握</option>
            </select>
          </label>
        </div>
        <div class="search-box">
          <span aria-hidden="true">⌕</span>
          <input v-model="searchQuery" type="search" :placeholder="browseSearchMode === '通配符' ? '例如 *あ*、あ*、AABB、ABAB' : '输入中文意思、假名或汉字…'" aria-label="搜索日语词条" />
          <button v-if="searchQuery" class="clear-search" aria-label="清空搜索" @click="searchQuery = ''">清空</button>
        </div>
        <div class="filter-row">
          <div class="filter-group" aria-label="词条类型筛选">
            <span>类型</span>
            <button :class="{ active: categoryFilter === 'all' }" @click="categoryFilter = 'all'">全部</button>
            <button v-if="availableKinds.includes('vocabulary')" :class="{ active: categoryFilter === 'vocabulary' }" @click="categoryFilter = 'vocabulary'">词汇</button>
            <button v-if="availableKinds.includes('grammar')" :class="{ active: categoryFilter === 'grammar' }" @click="categoryFilter = 'grammar'">语法</button>
          </div>
          <label class="pos-filter">词性
            <select v-model="partOfSpeechFilter" aria-label="按词性分类">
              <option v-for="item in partOfSpeechOptions" :key="item">{{ item }}</option>
            </select>
          </label>
          <label class="pos-filter">排序
            <select :value="browseSortMode" aria-label="词库浏览排序" @change="setBrowseSortMode(($event.currentTarget as HTMLSelectElement).value as 'ordered' | 'gojuon' | 'random')">
              <option value="ordered">顺序</option>
              <option value="gojuon">五十音</option>
              <option value="random">随机</option>
            </select>
          </label>
          <div class="progress-summary">
            <span>本级已掌握 <strong>{{ knownCount }}</strong> / {{ records.length }}</span>
            <div class="progress-track" role="progressbar" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100">
              <span :style="{ width: `${progressPercent}%` }"></span>
            </div>
            <button class="export-button" :disabled="!records.length" @click="exportBackup">导出进度</button>
            <button class="clear-study-progress" :disabled="!currentLevelProgressIds.length" @click="clearCurrentLevelProgress">清除本级进度</button>
          </div>
        </div>
        <p v-if="browseSearchMode === '通配符'" class="study-search-hint wildcard-search-hint">* 匹配任意长度字符，? 匹配单个字符；大写字母可表示重复字符格式，如 AABB、ABAB；按完整词条匹配。a*b* 表示以 a 开头且后面包含 b，要匹配任意位置请在前后加 *。</p>
      </section>

      <template v-if="pageMode === 'study'">
        <div class="study-session-controls">
          <div class="study-book-picker-panel">
            <div v-if="studyBookSelectionExpanded" class="book-picker study-book-picker-expanded">
              <div class="book-picker-heading">
                <div><p class="eyebrow">CHOOSE YOUR BOOK</p><h2>选择练习教材</h2></div>
                <span>选择后继续练习</span>
              </div>
              <div class="book-card-grid">
                <button
                  v-for="book in bookOptions"
                  :key="book.id"
                  type="button"
                  class="book-card"
                  :class="[`book-${book.id}`, { selected: studyBook === book.id }]"
                  :aria-pressed="studyBook === book.id"
                  :disabled="studyBookLoading"
                  @click="selectStudyBook(book.id)"
                >
                  <img v-if="book.id !== 'greenbook'" :src="`${baseUrl}images/book/${book.id}face.png`" :alt="`${book.label}封面`" />
                  <span v-else class="greenbook-cover" aria-hidden="true"><b>緑宝書</b><small>日本語能力試験</small></span>
                  <span class="book-card-caption"><strong>{{ book.label }}</strong><small>{{ book.id === 'bluebook' ? '语法汇总' : '词汇学习' }}</small></span>
                  <span v-if="studyBook === book.id" class="book-selected-mark" aria-label="当前选择">✓</span>
                </button>
              </div>
            </div>
            <div v-else class="selected-book-bar">
              <img v-if="studyBook !== 'greenbook'" :src="`${baseUrl}images/book/${studyBook}face.png`" :alt="`${selectedStudyBookOption.label}封面`" />
              <span v-else class="selected-greenbook-mark" aria-hidden="true">緑</span>
              <span><small>练习教材</small><strong>{{ selectedStudyBookOption.label }}</strong></span>
              <button type="button" :disabled="studyBookLoading" @click="studyBookSelectionExpanded = true">更换教材</button>
            </div>
          </div>
          <label class="study-book-picker study-level-picker">JLPT 等级
            <select :value="studyLevel" :disabled="studyBookLoading" aria-label="选择背词 JLPT 等级" @change="onStudyLevelChange">
              <option v-for="level in levelOptions" :key="level" :value="level">N{{ level }}</option>
            </select>
          </label>
          <div class="study-search" role="search">
            <label class="study-search-mode">搜索范围
              <select v-model="studySearchMode" :disabled="studyBookLoading" aria-label="选择背词搜索范围">
                <option v-for="mode in searchModes" :key="mode" :value="mode">{{ mode }}</option>
              </select>
            </label>
            <label class="study-search-mode">词性
              <select v-model="studyPartOfSpeechFilter" :disabled="studyBookLoading" aria-label="按词性筛选背词">
                <option v-for="partOfSpeech in studyPartOfSpeechOptions" :key="partOfSpeech" :value="partOfSpeech">{{ partOfSpeech }}</option>
              </select>
            </label>
            <div class="study-search-content">
              <div class="search-box">
                <span aria-hidden="true">⌕</span>
                <input
                  v-model="studySearchQuery"
                  type="search"
                  :disabled="studyBookLoading"
                  :placeholder="studySearchMode === '通配符' ? '例如 *あ*、あ*、AABB、ABAB' : '输入中文意思、假名或汉字…'"
                  aria-label="搜索背词词条"
                  @keydown.enter="applyStudySearch"
                />
                <button v-if="studySearchQuery" class="clear-search" aria-label="清空背词搜索" @click="studySearchQuery = ''">清空</button>
              </div>
              <button class="apply-study-search" :disabled="studyBookLoading || !studyFilteredRecords.length" @click="applyStudySearch">
                按搜索结果练习 · {{ studyFilteredRecords.length }}
              </button>
            </div>
            <p class="study-search-hint">
              搜索只针对当前练习教材和等级；支持中文、假名、汉字/单词检索，或使用 *、? 和 AABB/ABAB 格式匹配日文词条、读音和书写形式。大写重复格式可在「全部」或「通配符」模式中直接搜索。
            </p>
          </div>
          <fieldset class="study-display-options">
            <legend>练习选项</legend>
            <label><input v-model="studyShowKana" type="checkbox" @change="updateStudyDisplay" />显示假名</label>
            <label><input v-model="studyShowMeaning" type="checkbox" @change="updateStudyDisplay" />显示汉义</label>
            <label title="随机排列当前题目之后的词条；重新开始时会为整轮重新随机"><input v-model="studyRandomOrder" type="checkbox" @change="updateStudyOrder" />随机顺序</label>
          </fieldset>
        </div>
        <div v-if="isLoading || studyBookLoading" class="empty-state" role="status">正在准备背词练习…</div>
        <section v-else-if="currentStudyRecord" class="memorize-panel">
          <div class="memorize-heading">
            <div>
              <p class="panel-kicker">ACTIVE RECALL · N{{ studyLevel }}</p>
              <h2>想一想，再揭晓答案。</h2>
            </div>
            <div class="study-progress" role="group" :aria-label="`学习进度：已掌握 ${studyProgress.known}，还不熟 ${studyProgress.unsure}，未背诵 ${studyProgress.unstudied}`">
              <div
                class="study-progress-track"
                role="progressbar"
                :aria-valuenow="studyProgress.known + studyProgress.unsure"
                :aria-valuemin="0"
                :aria-valuemax="studyProgress.total"
                aria-label="当前筛选词条学习进度"
              >
                <span class="study-progress-known" :style="{ width: `${studyProgress.knownPercent}%` }"></span>
                <span class="study-progress-unsure" :style="{ width: `${studyProgress.unsurePercent}%` }"></span>
                <span class="study-progress-unstudied" :style="{ width: `${studyProgress.unstudiedPercent}%` }"></span>
              </div>
              <div class="study-progress-legend">
                <span><i class="known-dot"></i>已掌握 {{ studyProgress.known }}</span>
                <span><i class="unsure-dot"></i>还不熟 {{ studyProgress.unsure }}</span>
                <span><i class="unstudied-dot"></i>未背诵 {{ studyProgress.unstudied }}</span>
              </div>
            </div>
          </div>
          <div class="memorize-card">
            <div class="detail-tags">
              <span>{{ currentStudyRecord.kind === 'grammar' ? '语法' : currentStudyRecord.partOfSpeech.join(' · ') || '词汇' }}</span>
              <span v-if="currentStudyRecord.pitchAccent">音调 {{ currentStudyRecord.pitchAccent }}</span>
            </div>
            <p class="kana-question-hint">{{ studyShowKana && studyShowMeaning ? '阅读单词并熟悉词义。' : studyShowKana ? '请回想这个单词的中文意思。' : studyShowMeaning ? '请回想这个单词的假名读音。' : '请回想这个单词的假名读音和中文意思。' }}</p>
            <div class="speech-row">
              <p class="memorize-term" lang="ja">{{ getStudyTerm(currentStudyRecord) }}</p>
              <span class="speech-control">
                <button class="speech-button" :class="{ active: isSpeechActive(`record:${currentStudyRecord.id}`) }" :aria-label="isSpeechActive(`record:${currentStudyRecord.id}`) ? '停止朗读' : `朗读 ${currentStudyRecord.term}`" @click="speakRecord(currentStudyRecord)"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="speaker-body" d="M4 10v4h4l5 4V6l-5 4H4Z" /><path class="speaker-wave" d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12" /><rect class="speaker-stop" x="16" y="8" width="3" height="8" rx="1" /></svg></button>
                <span v-if="isSpeechActive(`record:${currentStudyRecord.id}`)" class="speech-playing" role="status"><i></i>{{ speechStatus === 'starting' ? '正在启动' : '播放中' }}</span>
              </span>
            </div>
            <p v-if="studyShowKana || (answerVisible && !studyShowKana)" class="kana-answer" lang="ja">{{ currentStudyRecord.reading || '暂无假名读音' }}</p>
            <p v-if="studyShowMeaning || (answerVisible && !studyShowMeaning)" class="memorize-meaning">{{ previewMeaning(currentStudyRecord) }}</p>
            <button v-if="!answerVisible" class="reveal-answer" @click="showStudyAnswer">显示答案和例句</button>
            <template v-if="answerVisible">
              <div v-if="currentStudyRecord.connections?.length" class="memorize-connections">
                <strong>接续</strong><span v-for="connection in currentStudyRecord.connections" :key="connection">{{ connection }}</span>
              </div>
              <article v-for="(example, index) in currentStudyRecord.examples.slice(0, 2)" :key="index" class="memorize-example">
                <div v-if="example.ja || example.text" class="example-japanese-row">
                  <p lang="ja"><JapaneseRubyText :text="example.ja || example.text || ''" /></p>
                  <span class="speech-control">
                    <button class="speech-button" :class="{ active: isSpeechActive(`example:${currentStudyRecord.id}:${index}`) }" :aria-label="isSpeechActive(`example:${currentStudyRecord.id}:${index}`) ? '停止朗读例句' : `朗读例句 ${index + 1}`" @click="speakExample(example, `example:${currentStudyRecord.id}:${index}`)"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="speaker-body" d="M4 10v4h4l5 4V6l-5 4H4Z" /><path class="speaker-wave" d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12" /><rect class="speaker-stop" x="16" y="8" width="3" height="8" rx="1" /></svg></button>
                    <span v-if="isSpeechActive(`example:${currentStudyRecord.id}:${index}`)" class="speech-playing" role="status"><i></i>{{ speechStatus === 'starting' ? '正在启动' : '播放中' }}</span>
                  </span>
                </div>
                <p v-if="example.zh">{{ example.zh }}</p>
              </article>
              <div class="recall-actions">
                <button class="recall-again" @click="markStudyRecord(false)">还不熟 · 再复习</button>
                <button class="recall-known" @click="markStudyRecord(true)">记住了 ✓</button>
              </div>
            </template>
          </div>
          <div class="memorize-navigation">
            <button :disabled="studyIndex <= 0" @click="returnToPreviousStudyRecord">← 上一条</button>
            <button @click="advanceStudy">跳过这条</button>
            <button @click="pageMode = 'browse'">返回词库</button>
            <button @click="restartStudy">按本轮词条重新开始</button>
          </div>
        </section>
        <div v-else class="empty-state">
          <span aria-hidden="true">あ</span>
          <h3>{{ studyQueueIds.length ? '本轮练习完成' : allStudyCandidatesKnown ? '筛选词条都已掌握' : '当前筛选下没有可练习的词条' }}</h3>
          <p>{{ studyQueueIds.length ? '做得好！可以再练一轮，或返回词库继续查找。' : allStudyCandidatesKnown ? '已掌握的词条不会重复加入练习；可在词库中取消掌握状态，或清除对应进度后再练习。' : '调整书本、等级或筛选条件后再开始。' }}</p>
          <button v-if="studyQueueIds.length" class="reveal-answer" @click="restartStudy">再练一轮</button>
          <button v-else class="reveal-answer" @click="pageMode = 'browse'">返回词库</button>
        </div>
      </template>

      <template v-else>
      <div class="results-heading">
        <div>
          <p class="panel-kicker">{{ bookOptions.find(book => book.id === selectedBook)?.label }} · N{{ selectedLevel }}</p>
          <h2>{{ searchQuery ? '搜索结果' : '词库浏览' }} <span>{{ filteredRecords.length }}</span></h2>
        </div>
        <p v-if="searchQuery">搜索内容：<strong>{{ searchQuery }}</strong></p>
      </div>

      <div v-if="isLoading" class="empty-state" role="status">正在加载词库…</div>
      <div v-else-if="!filteredRecords.length" class="empty-state">
        <span aria-hidden="true">あ</span>
        <h3>{{ records.length ? '没有找到匹配词条' : '这个等级暂时没有词条' }}</h3>
        <p>试试更短的关键词，或调整书本、词性和搜索范围。</p>
      </div>
      <section v-else class="study-workspace">
        <div class="results-panel">
          <article v-for="record in visibleRecords" :key="record.id" class="result-item" :class="{ selected: selectedRecord?.id === record.id }">
            <button class="result-open" @click="openRecordDetails(record)">
              <span class="result-meta">
                <span>{{ record.kind === 'grammar' ? '语法' : record.partOfSpeech.join(' · ') || '词汇' }}</span>
                <span v-if="record.pitchAccent">音调 {{ record.pitchAccent }}</span>
              </span>
              <strong lang="ja"><JapaneseRubyText :text="record.term" :reading="record.reading" /></strong>
              <span class="result-meaning">{{ meaningHidden ? '释义已隐藏 · 先试着回想一下' : previewMeaning(record) }}</span>
            </button>
            <span class="speech-control">
              <button class="speech-button" :class="{ active: isSpeechActive(`record:${record.id}`) }" :aria-label="isSpeechActive(`record:${record.id}`) ? '停止朗读' : `朗读 ${record.term}`" @click="speakRecord(record)"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="speaker-body" d="M4 10v4h4l5 4V6l-5 4H4Z" /><path class="speaker-wave" d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12" /><rect class="speaker-stop" x="16" y="8" width="3" height="8" rx="1" /></svg></button>
              <span v-if="isSpeechActive(`record:${record.id}`)" class="speech-playing" role="status"><i></i>{{ speechStatus === 'starting' ? '正在启动' : '播放中' }}</span>
            </span>
            <button class="known-toggle" :class="{ known: knownIds.includes(record.id) }" :aria-label="knownIds.includes(record.id) ? '标记为待复习' : '标记为已掌握'" @click="toggleKnown(record)">
              {{ knownIds.includes(record.id) ? '已掌握 ✓' : '记住了' }}
            </button>
            <section
              v-if="mobileDetailOpen && selectedRecord?.id === record.id"
              ref="mobileDetailElement"
              class="mobile-inline-detail"
              aria-label="词条详细内容"
            >
              <button class="mobile-detail-close" aria-label="收起词条详情" @click="closeMobileDetails">收起详情 ↑</button>
              <div class="detail-topline">
                <span>{{ record.kind === 'grammar' ? '语法点' : '单词' }} · {{ record.level }}</span>
                <div class="detail-actions">
                  <button class="self-test-toggle" @click="meaningHidden = !meaningHidden">{{ meaningHidden ? '显示释义' : '遮住释义自测' }}</button>
                  <button class="known-toggle detail-known" :class="{ known: knownIds.includes(record.id) }" @click="toggleKnown(record)">
                    {{ knownIds.includes(record.id) ? '已掌握 ✓' : '标记已掌握' }}
                  </button>
                </div>
              </div>
              <div class="mobile-detail-title-row">
                <h2 lang="ja"><JapaneseRubyText :text="record.term" :reading="record.reading" /></h2>
                <span class="speech-control">
                  <button class="speech-button" :class="{ active: isSpeechActive(`record:${record.id}`) }" :aria-label="isSpeechActive(`record:${record.id}`) ? '停止朗读' : `朗读 ${record.term}`" @click="speakRecord(record)"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="speaker-body" d="M4 10v4h4l5 4V6l-5 4H4Z" /><path class="speaker-wave" d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12" /><rect class="speaker-stop" x="16" y="8" width="3" height="8" rx="1" /></svg></button>
                  <span v-if="isSpeechActive(`record:${record.id}`)" class="speech-playing" role="status"><i></i>{{ speechStatus === 'starting' ? '正在启动' : '播放中' }}</span>
                </span>
              </div>
              <div class="detail-tags">
                <span v-for="tag in record.partOfSpeech" :key="tag">{{ tag }}</span>
                <span v-if="record.pitchAccent">音调 {{ record.pitchAccent }}</span>
              </div>
              <section v-if="record.meaningZh" class="detail-section">
                <h3>{{ record.kind === 'grammar' ? '语法概要' : '中文释义' }}</h3>
                <p v-if="!meaningHidden" class="detail-meaning">{{ record.meaningZh }}</p>
                <p v-else class="hidden-meaning">释义已隐藏，试着先回想一下。</p>
              </section>
              <section v-if="record.connections?.length" class="detail-section">
                <h3>接续方式</h3>
                <ul class="connection-list"><li v-for="connection in record.connections" :key="connection">{{ connection }}</li></ul>
              </section>
              <section v-if="record.explanations?.length" class="detail-section">
                <h3>用法说明</h3>
                <p v-for="(explanation, index) in record.explanations" v-show="!meaningHidden" :key="index">{{ explanation }}</p>
              </section>
              <section v-if="record.examples.length" class="detail-section">
                <h3>例句 <span>{{ record.examples.length }}</span></h3>
                <article v-for="(example, index) in record.examples" :key="index" class="example-item">
                  <div v-if="example.ja || example.text" class="example-japanese-row">
                    <p class="example-japanese" lang="ja"><JapaneseRubyText :text="example.ja || example.text || ''" /></p>
                    <button class="speech-button" :class="{ active: isSpeechActive(`example:${record.id}:${index}`) }" :aria-label="isSpeechActive(`example:${record.id}:${index}`) ? '停止朗读例句' : `朗读例句 ${index + 1}`" @click="speakExample(example, `example:${record.id}:${index}`)"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="speaker-body" d="M4 10v4h4l5 4V6l-5 4H4Z" /><path class="speaker-wave" d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12" /><rect class="speaker-stop" x="16" y="8" width="3" height="8" rx="1" /></svg></button>
                  </div>
                  <p v-if="example.zh && !meaningHidden" class="example-chinese">{{ example.zh }}</p>
                  <small v-if="example.tag">{{ example.tag }}</small>
                </article>
              </section>
              <section v-if="record.relatedTerms?.length || record.homophones?.length" class="detail-section">
                <h3>关联词条</h3>
                <p v-for="item in [...(record.relatedTerms ?? []), ...(record.homophones ?? [])]" :key="item">{{ item }}</p>
              </section>
              <section v-if="record.notes?.length" class="detail-section">
                <h3>补充笔记</h3>
                <p v-for="(note, index) in record.notes" :key="index">{{ note }}</p>
              </section>
            </section>
          </article>
          <button v-if="visibleRecords.length < filteredRecords.length" class="show-more-button" @click="showMore">
            加载更多（{{ visibleRecords.length }} / {{ filteredRecords.length }}）
          </button>
        </div>

        <aside v-if="selectedRecord" class="detail-panel" aria-label="词条详细内容">
          <div class="detail-topline">
            <span>{{ selectedRecord.kind === 'grammar' ? '语法点' : '单词' }} · {{ selectedRecord.level }}</span>
            <div class="detail-actions">
              <button class="self-test-toggle" @click="meaningHidden = !meaningHidden">{{ meaningHidden ? '显示释义' : '遮住释义自测' }}</button>
              <span class="speech-control">
                <button class="speech-button" :class="{ active: isSpeechActive(`record:${selectedRecord.id}`) }" :aria-label="isSpeechActive(`record:${selectedRecord.id}`) ? '停止朗读' : `朗读 ${selectedRecord.term}`" @click="speakRecord(selectedRecord)"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="speaker-body" d="M4 10v4h4l5 4V6l-5 4H4Z" /><path class="speaker-wave" d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12" /><rect class="speaker-stop" x="16" y="8" width="3" height="8" rx="1" /></svg></button>
                <span v-if="isSpeechActive(`record:${selectedRecord.id}`)" class="speech-playing" role="status"><i></i>{{ speechStatus === 'starting' ? '正在启动' : '播放中' }}</span>
              </span>
              <button class="known-toggle detail-known" :class="{ known: knownIds.includes(selectedRecord.id) }" @click="toggleKnown(selectedRecord)">
                {{ knownIds.includes(selectedRecord.id) ? '已掌握 ✓' : '标记已掌握' }}
              </button>
            </div>
          </div>
          <h2 lang="ja"><JapaneseRubyText :text="selectedRecord.term" :reading="selectedRecord.reading" /></h2>
          <div class="detail-tags">
            <span v-for="tag in selectedRecord.partOfSpeech" :key="tag">{{ tag }}</span>
            <span v-if="selectedRecord.pitchAccent">音调 {{ selectedRecord.pitchAccent }}</span>
          </div>

          <section v-if="selectedRecord.meaningZh" class="detail-section">
            <h3>{{ selectedRecord.kind === 'grammar' ? '语法概要' : '中文释义' }}</h3>
            <p v-if="!meaningHidden" class="detail-meaning">{{ selectedRecord.meaningZh }}</p>
            <p v-else class="hidden-meaning">释义已隐藏，试着先回想一下。</p>
          </section>
          <section v-if="selectedRecord.connections?.length" class="detail-section">
            <h3>接续方式</h3>
            <ul class="connection-list"><li v-for="connection in selectedRecord.connections" :key="connection">{{ connection }}</li></ul>
          </section>
          <section v-if="selectedRecord.explanations?.length" class="detail-section">
            <h3>用法说明</h3>
            <p v-for="(explanation, index) in selectedRecord.explanations" v-show="!meaningHidden" :key="index">{{ explanation }}</p>
          </section>
          <section v-if="selectedRecord.examples.length" class="detail-section">
            <h3>例句 <span>{{ selectedRecord.examples.length }}</span></h3>
            <article v-for="(example, index) in selectedRecord.examples" :key="index" class="example-item">
              <div v-if="example.ja || example.text" class="example-japanese-row">
                <p class="example-japanese" lang="ja"><JapaneseRubyText :text="example.ja || example.text || ''" /></p>
                <span class="speech-control">
                  <button class="speech-button" :class="{ active: isSpeechActive(`example:${selectedRecord.id}:${index}`) }" :aria-label="isSpeechActive(`example:${selectedRecord.id}:${index}`) ? '停止朗读例句' : `朗读例句 ${index + 1}`" @click="speakExample(example, `example:${selectedRecord.id}:${index}`)"><svg viewBox="0 0 24 24" aria-hidden="true"><path class="speaker-body" d="M4 10v4h4l5 4V6l-5 4H4Z" /><path class="speaker-wave" d="M16 9a5 5 0 0 1 0 6m2-9a9 9 0 0 1 0 12" /><rect class="speaker-stop" x="16" y="8" width="3" height="8" rx="1" /></svg></button>
                  <span v-if="isSpeechActive(`example:${selectedRecord.id}:${index}`)" class="speech-playing" role="status"><i></i>{{ speechStatus === 'starting' ? '正在启动' : '播放中' }}</span>
                </span>
              </div>
              <p v-if="example.zh && !meaningHidden" class="example-chinese">{{ example.zh }}</p>
              <small v-if="example.tag">{{ example.tag }}</small>
            </article>
          </section>
          <section v-if="selectedRecord.relatedTerms?.length || selectedRecord.homophones?.length" class="detail-section">
            <h3>关联词条</h3>
            <p v-for="item in selectedRelatedTerms" :key="item">{{ item }}</p>
          </section>
          <section v-if="selectedRecord.notes?.length" class="detail-section">
            <h3>补充笔记</h3>
            <p v-for="(note, index) in selectedRecord.notes" :key="index">{{ note }}</p>
          </section>
        </aside>
      </section>
      </template>
    </main>

    <footer class="study-footer">
      <span>Made for steady learning · Abin</span>
      <a :href="`mailto:${profile.email}?subject=日语学习工具反馈`">反馈或建议 ↗</a>
    </footer>
  </div>
</template>

<style scoped>
.study-page { min-height: 100vh; color: #263b47; background: #f7f8f6; }
.study-header { height: 76px; padding: 0 max(24px, calc((100% - 1220px) / 2)); display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(38,59,71,.1); background: rgba(255,250,248,.92); }
.brand { display: flex; align-items: center; gap: 10px; color: inherit; text-decoration: none; }.brand img { width: 40px; height: 40px; border: 2px solid white; border-radius: 50%; object-fit: cover; box-shadow: 0 2px 8px #263b4720; }.brand strong,.brand small { display: block; }.brand strong { font: 600 16px 'Noto Serif SC',serif; }.brand small { margin-top: 3px; color: #7b8b8d; font: 9px 'DM Mono',monospace; letter-spacing: .1em; }.back-link,.study-footer a { color: #5e7580; font-size: 13px; }.back-link:hover,.study-footer a:hover { color: #263b47; }
.study-main { width: min(1220px, calc(100% - 40px)); margin: auto; padding: 48px 0 76px; }.study-intro { max-width: 760px; margin-bottom: 28px; }.eyebrow,.panel-kicker { color: #6a90a6; font: 10px 'DM Mono',monospace; letter-spacing: .12em; }.eyebrow { margin: 0 0 11px; }.study-intro h1 { margin: 0; font: 600 clamp(32px,4.5vw,48px)/1.3 'Noto Serif SC',serif; letter-spacing: -.04em; }.study-intro h1 em { color: #6a90a6; font-style: normal; }.study-intro > p:last-child { color: #6e7c7d; font-size: 14px; line-height: 1.8; }
.notice { margin: 14px 0; padding: 12px 16px; border: 1px solid #e7bdb7; border-radius: 12px; color: #8d4e49; background: #fff2ef; font-size: 13px; }
.mode-switch { width: 100%; margin: 20px 0 0; padding: 4px; display: flex; align-items: center; gap: 4px; border: 1px solid #e3e9e6; border-radius: 999px; background: #eef2ef; }.mode-switch button { padding: 9px 18px; border: 0; border-radius: 999px; color: #758381; background: transparent; font-size: 12px; }.mode-switch button.active { color: #fff; background: #6a90a6; box-shadow: 0 2px 6px #263b471c; }.mode-switch button:disabled { opacity: .45; cursor: not-allowed; }.mode-switch .clear-all-progress-nav { margin-left: auto; border: 1px solid #ead4cf; color: #9c6259; background: #fff7f4; }.mode-switch .clear-all-progress-nav:hover:not(:disabled) { background: #ffede8; }
.voice-picker { width: fit-content; max-width: 100%; margin: 12px 0 16px auto; padding: 8px 10px 8px 12px; display: flex; align-items: center; gap: 9px; border: 1px solid #e4ebe7; border-radius: 11px; color: #63777c; background: rgba(255,253,251,.9); box-shadow: 0 3px 12px rgba(38,59,71,.035); font-size: 11px; }.voice-picker > span { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }.voice-picker-icon { color: #6a90a6; font-size: 16px; line-height: 1; }.voice-picker select { min-width: 150px; max-width: min(320px,45vw); padding: 7px 26px 7px 9px; border: 1px solid #dce5e3; border-radius: 8px; color: #354d58; background: #fff; font: inherit; }.voice-picker select:focus-visible { outline: 2px solid #6a90a6; outline-offset: 2px; }.voice-picker select:disabled { opacity: .65; }.voice-picker small { color: #94a09f; font-size: 10px; white-space: nowrap; }
.study-session-controls { margin-top: 16px; padding: 16px 18px; display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 20px; border: 1px solid rgba(38,59,71,.1); border-radius: 16px; background: #fffdfb; box-shadow: 0 8px 24px rgba(38,59,71,.03); }.study-book-picker-panel { flex: 1; min-width: 0; }.study-book-picker-expanded { margin: 0; padding: 0; border: 0; }.study-book-picker-expanded .book-picker-heading { margin-bottom: 9px; }.study-book-picker-expanded .book-card-grid { max-width: 410px; grid-template-columns: repeat(3,minmax(0,115px)); gap: 8px; }.study-book-picker-expanded .book-card { padding: 6px; gap: 5px; }.study-book-picker-expanded .book-card>img,.study-book-picker-expanded .greenbook-cover { width: min(100%,66px); }.study-book-picker-expanded .book-card-caption { width: min(100%,66px); }.study-book-picker-expanded .book-card-caption strong { font-size: 10px; }.study-book-picker-expanded .book-card-caption small { font-size: 8px; }.study-book-picker-expanded .book-selected-mark { top: 8px; right: 8px; width: 18px; height: 18px; font-size: 10px; }.study-session-controls .selected-book-bar { width: fit-content; min-width: 210px; margin: 0; }.study-book-picker { display: flex; align-items: center; gap: 8px; color: #718181; font-size: 11px; }.study-book-picker select { min-width: 112px; padding: 8px 10px; border: 1px solid #dce5e3; border-radius: 9px; color: #354d58; background: #fff; font: inherit; }.study-book-picker select:focus-visible { outline: 2px solid #6a90a6; outline-offset: 2px; }.study-book-picker select:disabled { opacity: .6; }.study-level-picker { flex: none; flex-direction: column; align-items: flex-start; gap: 6px; min-width: 130px; }.study-level-picker select { width: 100%; }.study-search { order: 2; flex: 1 1 100%; display: grid; grid-template-columns: minmax(150px,220px) minmax(0,1fr); align-items: end; gap: 10px 14px; }.study-search-mode { display: grid; gap: 6px; color: #718181; font-size: 11px; }.study-search-mode select { width: 100%; min-width: 0; padding: 10px 11px; border: 1px solid #dce5e3; border-radius: 9px; color: #354d58; background: #fff; font: inherit; }.study-search-content { min-width: 0; display: flex; align-items: center; gap: 10px; }.study-search-content .search-box { flex: 1; min-width: 0; margin: 0; }.apply-study-search { flex: none; padding: 11px 15px; border: 1px solid #bfd2d2; border-radius: 10px; color: #527589; background: #f5faf8; font-size: 12px; white-space: nowrap; }.apply-study-search:hover:not(:disabled) { background: #eaf4f1; }.apply-study-search:disabled { opacity: .55; cursor: not-allowed; }.study-search-hint { grid-column: 2; margin: -4px 0 0; color: #7d8b8b; font-size: 11px; }.wildcard-search-hint { margin: 8px 0 0; }.study-display-options { order: 1; }.memorize-panel { margin-top: 16px; padding: 24px; border: 1px solid rgba(38,59,71,.1); border-radius: 20px; background: #fffdfb; box-shadow: 0 10px 32px rgba(38,59,71,.035); }.memorize-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.memorize-heading h2 { margin: 0; font: 600 21px 'Noto Serif SC',serif; }.study-counter { color: #789099; font: 12px 'DM Mono',monospace; }.memorize-card { width: min(720px,100%); min-height: 340px; margin: 22px auto 0; padding: clamp(24px,5vw,46px); display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid #e7ece8; border-radius: 18px; background: linear-gradient(145deg,#f3f7f5,#fbf7f2); text-align: center; }.direction-switch { margin-bottom: 20px; padding: 4px; display: flex; gap: 4px; border-radius: 999px; background: #e9efec; }.direction-switch button { padding: 7px 12px; border: 0; border-radius: 999px; color: #718181; background: transparent; font-size: 10px; }.direction-switch button.active { color: white; background: #6a90a6; }.memorize-term { margin: 18px 0 0; color: #304a56; font: 600 clamp(32px,6vw,52px)/1.5 'Noto Serif SC',serif; overflow-wrap: anywhere; }.memorize-reading { margin: 4px 0 0; color: #6a90a6; font-size: 15px; }.memorize-meaning { max-width: 580px; margin: 24px 0 0; color: #405861; font: 500 17px/1.9 'Noto Serif SC',serif; white-space: pre-wrap; }.reveal-answer { margin-top: 27px; padding: 11px 20px; border: 1px solid #bfd2d2; border-radius: 999px; color: #527589; background: #fff; font-size: 12px; }.memorize-connections { width: 100%; margin-top: 16px; display: flex; justify-content: center; flex-wrap: wrap; gap: 7px; color: #718181; font-size: 11px; }.memorize-connections strong { color: #6a90a6; }.memorize-example { width: 100%; margin-top: 13px; padding: 12px 15px; border-radius: 10px; background: #fffdfb; text-align: left; }.memorize-example p { margin: 0; color: #405861; font-size: 12px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }.memorize-example p + p { margin-top: 5px; color: #778585; }.recall-actions { width: 100%; margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }.recall-actions button { padding: 11px; border: 1px solid #e4d7d2; border-radius: 10px; color: #9c6962; background: #fff9f6; font-size: 12px; }.recall-actions .recall-known { border-color: #c9dcd4; color: #4b7869; background: #eff7f2; }.memorize-navigation { width: min(720px,100%); margin: 14px auto 0; display: flex; justify-content: space-between; gap: 8px; }.memorize-navigation button { padding: 8px 10px; border: 0; border-radius: 8px; color: #68808a; background: transparent; font-size: 11px; }.memorize-navigation button:hover:not(:disabled) { background: #edf4f3; }.memorize-navigation button:disabled { opacity: .4; cursor: not-allowed; }
.study-display-options { min-width: 210px; margin: 0; padding: 8px 11px 9px; display: flex; align-items: center; gap: 12px; border: 1px solid #e4ebe7; border-radius: 10px; background: #f8faf8; }.study-display-options legend { padding: 0 4px; color: #718181; font-size: 10px; }.study-display-options label { display: inline-flex; align-items: center; gap: 5px; color: #52666d; font-size: 11px; white-space: nowrap; cursor: pointer; }.study-display-options input { margin: 0; accent-color: #6a90a6; }.study-display-options input:focus-visible { outline: 2px solid #6a90a6; outline-offset: 2px; }
.kana-question-hint { margin: 12px 0 -12px; color: #718181; font-size: 13px; }.kana-answer { margin: 10px 0 0; color: #6a90a6; font: 500 clamp(20px,4vw,27px)/1.6 'Noto Serif SC',serif; letter-spacing: .08em; }
.speech-row { display: flex; align-items: center; justify-content: center; gap: 10px; }.speech-control { flex: none; display: inline-flex; align-items: center; gap: 7px; }.speech-button { position: relative; z-index: 0; width: 38px; height: 38px; padding: 0; display: inline-grid; place-items: center; border: 1px solid #d9e5e2; border-radius: 50%; color: #52798a; background: linear-gradient(145deg,#fff,#f2f7f5); box-shadow: 0 2px 6px rgba(38,59,71,.08),inset 0 1px 0 #fff; cursor: pointer; transition: transform .18s ease,border-color .18s ease,color .18s ease,background .18s ease,box-shadow .18s ease; }.speech-button:hover { transform: translateY(-1px); border-color: #a8c3c4; color: #3d7180; background: #f1f8f6; box-shadow: 0 4px 10px rgba(38,59,71,.12); }.speech-button:active { transform: scale(.94); }.speech-button:focus-visible { outline: 3px solid rgba(106,144,166,.4); outline-offset: 3px; }.speech-button svg { width: 19px; height: 19px; overflow: visible; }.speaker-body { fill: currentColor; }.speaker-wave { fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; transition: opacity .16s ease; }.speaker-stop { display: none; fill: currentColor; }.speech-button.active { border-color: #a7c7bc; color: #3d786b; background: linear-gradient(145deg,#eff8f3,#dcefe5); box-shadow: 0 0 0 3px rgba(105,157,137,.12),0 3px 8px rgba(38,59,71,.08); }.speech-button.active::after { position: absolute; z-index: -1; inset: -4px; border: 1px solid rgba(105,157,137,.42); border-radius: 50%; content: ''; animation: speech-ring 1.5s ease-out infinite; }.speech-button.active .speaker-wave { display: none; }.speech-button.active .speaker-stop { display: block; }.speech-row .memorize-term,.speech-row .kana-answer { margin: 10px 0 0; }.speech-playing { display: inline-flex; align-items: center; gap: 5px; color: #4b7869; font-size: 10px; white-space: nowrap; }.speech-playing i { width: 7px; height: 7px; border-radius: 50%; background: #6aab91; box-shadow: 0 0 0 3px rgba(106,171,145,.14); animation: speech-pulse .8s ease-in-out infinite alternate; }@keyframes speech-pulse { to { opacity: .35; transform: scale(.7); } }@keyframes speech-ring { to { transform: scale(1.16); opacity: 0; } }
.example-japanese-row { display: flex; align-items: flex-start; gap: 10px; }.example-japanese-row > p { flex: 1; min-width: 0; }.example-japanese-row .speech-button { width: 34px; height: 34px; margin-top: 1px; }
.browse-panel,.results-panel,.detail-panel { border: 1px solid rgba(38,59,71,.1); border-radius: 18px; background: #fffdfb; box-shadow: 0 10px 32px rgba(38,59,71,.035); }.browse-panel { padding: 20px; }.control-row { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 12px; }.control-row label,.pos-filter { display: grid; gap: 6px; color: #68787d; font-size: 11px; }.control-row select,.pos-filter select { min-width: 0; width: 100%; padding: 10px 11px; border: 1px solid #dce3e2; border-radius: 9px; color: #354d58; background: white; font: inherit; }
.book-picker { margin-bottom: 18px; padding-bottom: 18px; border-bottom: 1px solid #e8eeea; }.book-picker-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; margin-bottom: 13px; }.book-picker-heading .eyebrow { margin-bottom: 5px; }.book-picker-heading h2 { margin: 0; color: #304a56; font: 600 19px 'Noto Serif SC',serif; }.book-picker-heading>span { color: #899593; font-size: 11px; }.book-card-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; max-width: 610px; }.book-card { position: relative; min-width: 0; padding: 9px; display: flex; flex-direction: column; align-items: center; gap: 8px; border: 1px solid #e2e8e4; border-radius: 13px; color: #354d58; background: #fff; text-align: left; cursor: pointer; transition: border-color .18s ease,background .18s ease,box-shadow .18s ease,transform .18s ease; }.book-card:hover { border-color: #9cb8c0; background: #f8fbf9; transform: translateY(-2px); }.book-card.selected { border-color: #6a90a6; background: #f0f6f4; box-shadow: 0 0 0 2px #6a90a622; }.book-card>img,.greenbook-cover { width: min(100%,126px); aspect-ratio: 2 / 3; border-radius: 5px; object-fit: cover; box-shadow: 0 4px 10px #263b4720; }.greenbook-cover { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 9px; background: linear-gradient(145deg,#71917a,#dce5c8 48%,#718c67); color: #fffdf4; text-align: center; }.greenbook-cover b { font: 700 20px 'Noto Serif SC',serif; writing-mode: vertical-rl; letter-spacing: .12em; }.greenbook-cover small { font-size: 8px; }.book-card-caption { width: min(100%,126px); display: flex; flex-direction: column; gap: 3px; }.book-card-caption strong { font: 600 13px 'Noto Serif SC',serif; }.book-card-caption small { color: #879391; font-size: 10px; }.book-selected-mark { position: absolute; top: 14px; right: 14px; width: 22px; height: 22px; display: grid; place-items: center; border: 2px solid #fff; border-radius: 50%; color: #fff; background: #527d72; box-shadow: 0 2px 6px #263b4733; font-size: 13px; }.selected-book-bar { min-height: 54px; margin-bottom: 15px; padding: 7px 10px; display: flex; align-items: center; gap: 10px; border: 1px solid #e5ebe7; border-radius: 11px; background: #f7f9f6; }.selected-book-bar>img { width: 27px; height: 38px; border-radius: 3px; object-fit: cover; box-shadow: 0 2px 5px #263b471a; }.selected-greenbook-mark { width: 27px; height: 38px; display: grid; place-items: center; border-radius: 3px; color: #fff; background: #78927a; font: 600 14px 'Noto Serif SC',serif; writing-mode: vertical-rl; }.selected-book-bar>span:not(.selected-greenbook-mark) { display: flex; flex-direction: column; gap: 2px; }.selected-book-bar small { color: #879391; font-size: 9px; }.selected-book-bar strong { color: #354d58; font: 600 12px 'Noto Serif SC',serif; }.selected-book-bar button { margin-left: auto; padding: 7px 11px; border: 1px solid #d7e3df; border-radius: 999px; color: #527589; background: #fff; font-size: 11px; cursor: pointer; }.selected-book-bar button:hover { border-color: #9cb8c0; background: #edf4f2; }.book-card:focus-visible,.selected-book-bar button:focus-visible { outline: 2px solid #527d72; outline-offset: 3px; }
.search-box { min-height: 48px; margin-top: 15px; padding: 0 14px; display: flex; align-items: center; gap: 10px; border: 1px solid #dce3e2; border-radius: 11px; background: white; }.search-box > span { color: #6a90a6; font-size: 24px; }.search-box input { flex: 1; min-width: 0; border: 0; outline: 0; color: #304a56; background: transparent; font: inherit; font-size: 13px; }.search-box input::placeholder { color: #9aa5a4; }.clear-search,.export-button { padding: 6px 10px; border: 0; border-radius: 7px; color: #648291; background: #edf4f3; font-size: 11px; }
.clear-study-progress,.clear-record-progress { padding: 6px 10px; border: 1px solid #ead4cf; border-radius: 7px; color: #9c6259; background: #fff7f4; font-size: 11px; }.clear-study-progress:hover:not(:disabled),.clear-record-progress:hover { background: #ffede8; }.clear-study-progress:disabled { opacity: .5; cursor: not-allowed; }.clear-record-progress { white-space: nowrap; }
.book-picker-actions { display: flex; align-items: center; gap: 10px; }.book-picker-actions > span { color: #82908f; font-size: 11px; }.book-picker-actions .clear-study-progress { white-space: nowrap; }
.filter-row { margin-top: 15px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }.filter-group { display: flex; align-items: center; gap: 7px; }.filter-group > span { margin-right: 3px; color: #788687; font-size: 11px; }.filter-group button { padding: 7px 12px; border: 0; border-radius: 999px; color: #728184; background: #f1f3f1; font-size: 11px; }.filter-group button.active { color: white; background: #6a90a6; }.pos-filter { display: flex; align-items: center; gap: 8px; }.pos-filter select { width: auto; min-width: 118px; padding: 7px 10px; }.progress-summary { margin-left: auto; display: flex; align-items: center; gap: 10px; color: #748183; font-size: 11px; }.progress-summary strong { color: #4b7869; }.progress-track { width: 84px; height: 6px; overflow: hidden; border-radius: 999px; background: #edf0ed; }.progress-track span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg,#6a90a6,#a9c5c6); }.export-button:disabled { opacity: .4; cursor: not-allowed; }
.results-heading { margin: 26px 0 13px; display: flex; align-items: end; justify-content: space-between; gap: 12px; }.panel-kicker { margin: 0 0 6px; }.results-heading h2 { margin: 0; font: 600 21px 'Noto Serif SC',serif; }.results-heading h2 span { margin-left: 6px; color: #8a9998; font: 12px 'DM Mono',monospace; }.results-heading > p { color: #899593; font-size: 11px; }.results-heading > p strong { color: #527589; }.study-workspace { display: grid; grid-template-columns: minmax(0,1.05fr) minmax(0,.95fr); align-items: start; gap: 16px; }.results-panel { padding: 8px 18px; }.result-item { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid #edf0ed; }.result-item:last-of-type { border-bottom: 0; }.result-item.selected { margin: 0 -10px; padding-right: 10px; padding-left: 10px; border-radius: 10px; background: #f4f7f5; }.result-open { flex: 1; min-width: 0; padding: 0; display: grid; justify-items: start; gap: 5px; border: 0; color: inherit; background: transparent; text-align: left; cursor: pointer; }.result-meta { display: flex; flex-wrap: wrap; gap: 8px; color: #799096; font-size: 10px; }.result-open strong { max-width: 100%; overflow-wrap: anywhere; color: #304a56; font: 600 18px/1.5 'Noto Serif SC',serif; }.result-reading { color: #6a90a6; font-size: 11px; }.result-meaning { display: -webkit-box; overflow: hidden; color: #748183; font-size: 11px; line-height: 1.6; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }.known-toggle { flex: none; padding: 7px 10px; border: 1px solid #dce5e3; border-radius: 999px; color: #6b8586; background: white; font-size: 10px; }.known-toggle.known { border-color: #c9dcd4; color: #4b7869; background: #eef6f1; }.show-more-button { width: 100%; margin: 10px 0; padding: 10px; border: 1px solid #dce5e3; border-radius: 10px; color: #587887; background: #f7faf8; font-size: 12px; }
.detail-panel { position: sticky; top: 18px; max-height: calc(100vh - 36px); overflow: auto; padding: 22px; }.detail-topline { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: #7a8a8b; font-size: 10px; }.detail-actions { display: flex; align-items: center; gap: 7px; }.self-test-toggle { padding: 7px 9px; border: 1px solid #dce5e3; border-radius: 999px; color: #648291; background: white; font-size: 10px; }.hidden-meaning { padding: 10px 12px; border-radius: 9px; color: #648291 !important; background: #edf4f3; }.detail-panel h2 { margin: 20px 0 3px; overflow-wrap: anywhere; color: #304a56; font: 600 clamp(24px,3vw,34px)/1.5 'Noto Serif SC',serif; }.detail-reading { margin: 0; color: #6a90a6; font-size: 14px; }.detail-tags { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px; }.detail-tags span { padding: 5px 9px; border-radius: 999px; color: #587887; background: #edf4f3; font-size: 10px; }.detail-section { margin-top: 22px; padding-top: 17px; border-top: 1px solid #edf0ed; }.detail-section h3 { margin: 0 0 10px; color: #6a90a6; font: 11px 'DM Mono',monospace; letter-spacing: .06em; }.detail-section h3 span { margin-left: 5px; color: #9aa5a4; }.detail-section > p,.detail-meaning,.connection-list { margin: 7px 0 0; color: #52666d; font-size: 13px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }.connection-list { padding-left: 19px; }.example-item { margin-top: 10px; padding: 12px; border-radius: 10px; background: #f7f8f6; }.example-japanese,.example-chinese { margin: 0; color: #405861; font-size: 13px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }.example-chinese { margin-top: 5px; color: #778585; font-size: 12px; }.example-item small { display: block; margin-top: 5px; color: #98a2a0; font-size: 10px; }.empty-state { padding: 48px 18px; border: 1px dashed #dce3e2; border-radius: 16px; color: #81908f; background: rgba(255,253,251,.7); text-align: center; }.empty-state > span { color: #83a2ae; font: 32px 'Noto Serif SC',serif; }.empty-state h3 { margin: 10px 0 5px; color: #52666d; font: 600 17px 'Noto Serif SC',serif; }.empty-state p { margin: 0; font-size: 12px; line-height: 1.7; }
.mobile-detail-close { display: none; }
.mobile-inline-detail { grid-column: 1 / -1; width: 100%; margin-top: 8px; padding: 18px; border: 1px solid #dfe9e5; border-radius: 14px; background: linear-gradient(145deg,#fffdfb,#f5f8f5); box-shadow: inset 0 1px 0 #fff,0 6px 18px rgba(38,59,71,.06); }.mobile-detail-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.mobile-detail-title-row h2 { min-width: 0; margin: 15px 0 3px; overflow-wrap: anywhere; color: #304a56; font: 600 clamp(24px,6vw,32px)/1.5 'Noto Serif SC',serif; }
.study-footer { min-height: 70px; padding: 0 max(24px, calc((100% - 1220px) / 2)); display: flex; align-items: center; justify-content: space-between; border-top: 1px solid rgba(38,59,71,.1); color: #8b9694; font-size: 11px; }
.study-search { grid-template-columns: minmax(140px,190px) minmax(140px,190px) minmax(0,1fr); }
.study-search-hint { grid-column: 1 / -1; }
@media (max-width: 820px) {
  .study-workspace { grid-template-columns: 1fr; }
  .study-workspace > .detail-panel { display: none; }
  .mobile-inline-detail .mobile-detail-close { width: fit-content; margin: 0 0 12px auto; padding: 7px 10px; display: block; border: 1px solid #dce5e3; border-radius: 999px; color: #587887; background: #fff; font-size: 11px; }
  .control-row { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .progress-summary { width: 100%; margin-left: 0; }
  .memorize-heading { flex-wrap: wrap; }.study-book-picker { margin-left: auto; }.study-counter { flex-basis: 100%; }
  .study-session-controls { align-items: flex-start; }
  .study-search { grid-template-columns: minmax(120px,170px) minmax(120px,170px) minmax(0,1fr); }
}
@media (max-width: 520px) {
  .study-header { height: 62px; padding: 0 14px; }
  .brand { gap: 7px; }.brand img { width: 34px; height: 34px; }.brand strong { font-size: 14px; }.brand small { font-size: 8px; }
  .back-link { font-size: 11px; }
  .study-main { width: calc(100% - 24px); padding: 28px 0 44px; }
  .study-intro { margin-bottom: 20px; }.study-intro h1 { font-size: clamp(29px,8vw,38px); }.study-intro > p:last-child { font-size: 13px; }
  .voice-picker { width: 100%; margin: 10px 0 12px; flex-wrap: wrap; }.voice-picker select { flex: 1; min-width: 0; max-width: none; }.voice-picker small { width: 100%; padding-left: 22px; }
  .browse-panel { padding: 12px; border-radius: 14px; }
  .book-picker { margin-bottom: 13px; padding-bottom: 13px; }.book-picker-heading h2 { font-size: 17px; }.book-picker-heading>span { font-size: 10px; }.book-card-grid { gap: 7px; }.book-card { padding: 6px; gap: 6px; border-radius: 10px; }.book-card>img,.greenbook-cover { width: min(100%,96px); }.book-card-caption { width: min(100%,96px); }.book-card-caption strong { font-size: 11px; }.book-card-caption small { font-size: 9px; }.book-selected-mark { top: 10px; right: 10px; width: 19px; height: 19px; font-size: 11px; }
  .selected-book-bar { margin-bottom: 12px; }
  .study-session-controls { flex-direction: column; gap: 12px; padding: 12px; }.study-book-picker-panel,.study-session-controls .selected-book-bar,.study-level-picker { width: 100%; min-width: 0; }.study-book-picker-expanded .book-card-grid { width: 100%; max-width: none; grid-template-columns: repeat(3,minmax(0,1fr)); }.study-book-picker-expanded .book-card>img,.study-book-picker-expanded .greenbook-cover { width: min(100%,74px); }.study-book-picker-expanded .book-card-caption { width: min(100%,74px); }
  .study-search { width: 100%; grid-template-columns: 1fr; gap: 8px; }.study-search-content { align-items: stretch; flex-direction: column; }.study-search-hint { grid-column: 1; margin: 0; }.apply-study-search { width: 100%; }
  .control-row { gap: 8px; }.control-row label { font-size: 10px; }.control-row select { padding: 9px 8px; font-size: 12px; }
  .search-box { min-height: 44px; padding: 0 10px; gap: 7px; }.search-box input { font-size: 12px; }.search-box input::placeholder { font-size: 11px; }.clear-search { padding: 6px 7px; }
  .filter-row { align-items: flex-start; gap: 12px; }.filter-group { flex-wrap: wrap; }.filter-group button { padding: 7px 10px; }.pos-filter { width: 100%; justify-content: space-between; }.pos-filter select { flex: 1; min-width: 0; }
  .progress-summary { display: grid; grid-template-columns: 1fr auto; gap: 8px; }.progress-track { width: 100%; grid-column: 1; grid-row: 2; }.export-button { grid-column: 2; grid-row: 1 / span 2; align-self: center; }
  .mode-switch { width: 100%; flex-wrap: wrap; border-radius: 14px; }.mode-switch > button:not(.clear-all-progress-nav) { flex: 1; padding: 9px 10px; }.mode-switch .clear-all-progress-nav { flex: 1 1 100%; margin-left: 0; }
  .memorize-panel { padding: 14px; border-radius: 15px; }.memorize-heading { align-items: flex-start; }.memorize-heading h2 { font-size: 18px; }.memorize-heading .panel-kicker { font-size: 9px; }.study-counter { flex: none; padding-top: 3px; }
  .memorize-heading .study-book-picker { width: 100%; margin: 0; justify-content: space-between; }.study-book-picker select { flex: 1; }
  .study-display-options { width: 100%; min-width: 0; justify-content: flex-start; }.memorize-card { width: 100%; min-height: 300px; margin-top: 14px; padding: 20px 14px; }
  .memorize-term { max-width: 100%; font-size: clamp(30px,9vw,42px); }.memorize-meaning { margin-top: 18px; font-size: 15px; }.kana-question-hint { font-size: 12px; }
  .recall-actions { gap: 7px; }.recall-actions button { padding: 10px 6px; font-size: 11px; }.memorize-navigation { flex-wrap: wrap; justify-content: center; }.memorize-navigation button { padding: 9px 8px; }
  .results-heading { align-items: flex-start; flex-direction: column; gap: 4px; }.results-panel { padding: 6px 12px; }
  .result-item { display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 7px; }.result-open { grid-column: 1; grid-row: 1 / span 2; }.result-open strong { font-size: 17px; }.result-item > .speech-control { grid-column: 2; grid-row: 1; }.result-item > .known-toggle { grid-column: 2; grid-row: 2; padding: 7px 8px; }
  .detail-panel { padding: 14px; border-radius: 14px; }.detail-topline { align-items: flex-start; flex-direction: column; }.detail-actions { width: 100%; flex-wrap: wrap; }.detail-panel h2 { margin-top: 14px; }
  .example-item { padding: 10px; }.example-japanese-row { align-items: flex-start; }.example-japanese-row > p { overflow-wrap: anywhere; }
  .study-footer { min-height: 64px; padding: 12px 14px; gap: 10px; font-size: 10px; }.study-footer a { font-size: 11px; }
}
@media (max-width: 360px) {
  .study-header { padding: 0 10px; }.back-link { font-size: 10px; }.study-main { width: calc(100% - 20px); }
  .control-row { grid-template-columns: 1fr; }.progress-summary { grid-template-columns: 1fr auto; }
  .memorize-panel { padding: 11px; }.memorize-card { padding-right: 10px; padding-left: 10px; }.speech-playing { font-size: 9px; }
}
@media (prefers-reduced-motion: reduce) {
  .speech-button,.speech-button::after,.speech-playing i { animation: none; transition: none; }
}
.study-progress { width: min(390px, 52vw); display: grid; gap: 7px; }
.study-progress-track { height: 9px; display: flex; overflow: hidden; border-radius: 999px; background: #e8eeeb; }
.study-progress-track span { height: 100%; transition: width .25s ease; }
.study-progress-known { background: #6f9c87; }
.study-progress-unsure { background: #d3a26b; }
.study-progress-unstudied { background: #dfe7e3; }
.study-progress-legend { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 4px 11px; color: #788887; font-size: 10px; }
.study-progress-legend span { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
.study-progress-legend i { width: 7px; height: 7px; border-radius: 50%; }
.study-progress-legend .known-dot { background: #6f9c87; }
.study-progress-legend .unsure-dot { background: #d3a26b; }
.study-progress-legend .unstudied-dot { background: #dfe7e3; }
@media (max-width: 640px) {
  .study-progress { width: 100%; }
  .study-progress-legend { justify-content: flex-start; }
}
</style>
