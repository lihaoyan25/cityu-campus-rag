/** vue-i18n 实例：语言切换 + localStorage 持久化 + html lang 同步 */
import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import zhTW from './locales/zh-TW'
import en from './locales/en'

export const LANGS = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'en', label: 'English' },
]

const STORAGE_KEY = 'cityu_lang'
const saved = localStorage.getItem(STORAGE_KEY)
export const DEFAULT_LANG = saved && ['zh-CN', 'zh-TW', 'en'].includes(saved) ? saved : 'zh-CN'

const i18n = createI18n({
  legacy: false,
  locale: DEFAULT_LANG,
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN, 'zh-TW': zhTW, en },
})

export function setLang(lang) {
  i18n.global.locale.value = lang
  localStorage.setItem(STORAGE_KEY, lang)
  document.documentElement.lang = lang === 'zh-CN' ? 'zh-CN' : lang === 'zh-TW' ? 'zh-TW' : 'en'
}

// 初始化 html lang
document.documentElement.lang = DEFAULT_LANG

export { i18n }
export default i18n
