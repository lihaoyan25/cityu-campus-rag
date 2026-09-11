<script setup>
import { computed } from 'vue'
import { NConfigProvider, NGlobalStyle, NMessageProvider, dateEnUS, dateZhCN, dateZhTW, enUS, zhCN, zhTW } from 'naive-ui'
import { i18n } from './i18n'

const themeOverrides = {
  common: {
    primaryColor: '#00594a',
    primaryColorHover: '#0a7a63',
    primaryColorPressed: '#004538',
    primaryColorSuppl: '#0a7a63',
    infoColor: '#2f6f8f',
    successColor: '#3e8e6c',
    warningColor: '#c8a565',
    errorColor: '#c0483b',
    borderRadius: '8px',
    fontFamily: "'PingFang SC', 'Microsoft YaHei', 'Segoe UI', system-ui, sans-serif",
  },
}

// Naive UI 组件库语言跟随 i18n
const NAIVE_LOCALES = {
  'zh-CN': { locale: zhCN, date: dateZhCN },
  'zh-TW': { locale: zhTW, date: dateZhTW },
  en: { locale: enUS, date: dateEnUS },
}
const naive = computed(() => NAIVE_LOCALES[i18n.global.locale.value] ?? NAIVE_LOCALES['zh-CN'])
</script>

<template>
  <n-config-provider
    :theme-overrides="themeOverrides"
    :locale="naive.locale"
    :date-locale="naive.date"
  >
    <n-global-style />
    <n-message-provider>
      <!-- key 绑定语言: 切换时重挂视图树，保证所有组件文案刷新 -->
      <router-view :key="i18n.global.locale.value" />
    </n-message-provider>
  </n-config-provider>
</template>
