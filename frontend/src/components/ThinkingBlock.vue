<script setup>
/** 思考过程折叠块：流式中显示"思考中"动画，结束后可展开查看 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

defineProps({
  reasoning: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
  thinkingActive: { type: Boolean, default: false },
})

const { t } = useI18n()
const open = ref(false)
</script>

<template>
  <div v-if="reasoning || thinkingActive" class="thinking-block" :class="{ open }">
    <button class="toggle" @click="open = !open">
      <span class="brain">✻</span>
      <span v-if="thinkingActive" class="label active">{{ t('chat.thinkingActive') }}<span class="ellipsis"><i>·</i><i>·</i><i>·</i></span></span>
      <span v-else class="label">{{ t('chat.thinkingDone') }}</span>
      <span class="arrow" :class="{ open }">▾</span>
    </button>
    <div v-show="open" class="content">{{ reasoning }}</div>
  </div>
</template>

<style scoped>
.thinking-block {
  border: 1px solid var(--c-border);
  border-radius: 10px;
  background: #f7faf9;
  overflow: hidden;
  margin-bottom: 8px;
}
.toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  color: var(--c-text-2);
}
.toggle:hover { background: rgba(0, 89, 74, 0.04); }
.brain { color: var(--c-gold); font-size: 14px; }
.label.active { color: var(--c-primary-light); }
.ellipsis i { animation: blink-dot 1.2s infinite; font-style: normal; }
.ellipsis i:nth-child(2) { animation-delay: 0.2s; }
.ellipsis i:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink-dot { 0%, 100% { opacity: 0.2; } 50% { opacity: 1; } }
.arrow { margin-left: auto; transition: transform 0.2s; font-size: 11px; color: var(--c-text-3); }
.arrow.open { transform: rotate(180deg); }
.content {
  padding: 10px 14px 12px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--c-text-2);
  white-space: pre-wrap;
  border-top: 1px dashed var(--c-border);
  max-height: 320px;
  overflow-y: auto;
}
</style>
