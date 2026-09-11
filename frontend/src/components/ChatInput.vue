<script setup>
/** 输入框：自适应高度 + 深度思考开关 + 发送/停止 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useChatStore } from '../stores/chat'

const { t } = useI18n()
const chat = useChatStore()
const text = ref('')
const taRef = ref(null)

function autoResize() {
  const ta = taRef.value
  if (!ta) return
  ta.style.height = 'auto'
  ta.style.height = Math.min(ta.scrollHeight, 160) + 'px'
}
watch(text, autoResize)

function send() {
  const q = text.value.trim()
  if (!q || chat.streaming) return
  text.value = ''
  autoResize()
  chat.send(q)
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}

/** 供外部(快捷提问卡片)填入问题并聚焦，不直接发送 */
function fill(q) {
  text.value = q
  autoResize()
  taRef.value?.focus()
}
defineExpose({ fill })
</script>

<template>
  <div class="chat-input">
    <div class="input-card">
      <textarea
        ref="taRef"
        v-model="text"
        rows="1"
        :placeholder="t('chat.inputPlaceholder')"
        @keydown="onKeydown"
      ></textarea>
      <div class="toolbar">
        <div class="left">
          <button
            class="think-btn"
            :class="{ on: chat.deepThinking }"
            :title="t('chat.deepThinking')"
            @click="chat.setDeepThinking(!chat.deepThinking)"
          >
            <span class="icon">✻</span> {{ t('chat.deepThinking') }}
            <span class="state">{{ chat.deepThinking ? t('chat.on') : t('chat.off') }}</span>
          </button>
        </div>
        <div class="right">
          <button
            v-if="chat.streaming"
            class="send-btn stop"
            :title="t('chat.stopTitle')"
            @click="chat.stopStream()"
          >
            <span class="stop-icon">■</span>
          </button>
          <button
            v-else
            class="send-btn"
            :disabled="!text.trim()"
            :title="t('chat.sendTitle')"
            @click="send"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
    <div class="disclaimer">{{ t('home.disclaimer') }}</div>
  </div>
</template>

<style scoped>
.chat-input { width: 100%; }
.input-card {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: 16px;
  box-shadow: var(--shadow-float);
  padding: 12px 14px 10px;
  transition: border-color 0.2s;
}
.input-card:focus-within { border-color: var(--c-primary-light); }
textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  font-family: inherit;
  color: var(--c-text);
  background: transparent;
  max-height: 160px;
}
textarea::placeholder { color: var(--c-text-3); }

.toolbar { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.think-btn {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 13px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: #f7faf9;
  color: var(--c-text-2);
  cursor: pointer;
  transition: all 0.2s;
}
.think-btn .icon { font-size: 14px; color: var(--c-text-3); }
.think-btn:hover { border-color: var(--c-gold); }
.think-btn.on {
  background: var(--c-gold-soft);
  border-color: var(--c-gold);
  color: #8a6c33;
}
.think-btn.on .icon { color: var(--c-gold); }
.think-btn .state { font-size: 11px; opacity: 0.75; }

.send-btn {
  width: 36px; height: 36px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light));
  color: #fff;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex; align-items: center; justify-content: center;
}
.send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.send-btn:not(:disabled):hover { transform: scale(1.06); }
.send-btn.stop { background: var(--c-danger); }
.stop-icon { font-size: 12px; }

.disclaimer {
  text-align: center;
  font-size: 11.5px;
  color: var(--c-text-3);
  margin-top: 8px;
}
</style>
