<script setup>
/** 单条消息：用户/助手气泡 + Markdown + 思考块 + 来源引用 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import python from 'highlight.js/lib/languages/python'
import json from 'highlight.js/lib/languages/json'
import xml from 'highlight.js/lib/languages/xml'
import bash from 'highlight.js/lib/languages/bash'
import sql from 'highlight.js/lib/languages/sql'
import ThinkingBlock from './ThinkingBlock.vue'

const { t } = useI18n()

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('json', json)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sql', sql)

const props = defineProps({ msg: { type: Object, required: true } })

const md = new MarkdownIt({
  html: false,
  linkify: true,
  highlight(code, lang) {
    let highlighted
    try {
      highlighted =
        lang && hljs.getLanguage(lang)
          ? hljs.highlight(code, { language: lang }).value
          : md.utils.escapeHtml(code)
    } catch {
      highlighted = md.utils.escapeHtml(code)
    }
    // 代码原文经 encodeURIComponent 存入属性，点击时还原
    const encoded = encodeURIComponent(code)
    return (
      `<div class="code-wrap">` +
      `<button class="code-copy" data-code="${encoded}">复制代码</button>` +
      `<pre><code class="hljs">${highlighted}</code></pre></div>`
    )
  },
})

const html = computed(() => md.render(props.msg.content || ''))
const isUser = computed(() => props.msg.role === 'user')
const thinkingActive = computed(
  () => props.msg.streaming && !props.msg.thinkingDone && (props.msg.reasoning || '').length > 0
)
const previewOpen = ref(false)

/** 写剪贴板（带降级方案），并给按钮一个"已复制"反馈 */
async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    ta.remove()
  }
  if (btn) {
    if (!btn.dataset.label) btn.dataset.label = btn.textContent
    btn.classList.add('copied')
    btn.textContent = '✓ ' + t('common.copied')
    clearTimeout(btn._t)
    btn._t = setTimeout(() => {
      btn.textContent = btn.dataset.label
      btn.classList.remove('copied')
    }, 1600)
  }
}

/** 事件委托: 处理 markdown 内代码块的复制按钮(v-html 动态内容) */
function onBubbleClick(e) {
  const btn = e.target.closest('.code-copy')
  if (btn && btn.dataset.code !== undefined) {
    copyText(decodeURIComponent(btn.dataset.code), btn)
  }
}
</script>

<template>
  <div class="msg-row" :class="{ user: isUser }">
    <template v-if="isUser">
      <div class="bubble user-bubble">{{ msg.content }}</div>
      <div class="avatar user-avatar" :title="t('common.me')">
        <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 12.2c2.8 0 5-2.3 5-5.1S14.8 2 12 2 7 4.3 7 7.1s2.2 5.1 5 5.1zm0 2.5c-3.3 0-10 1.7-10 5V22h20v-2.3c0-3.3-6.7-5-10-5z" />
        </svg>
      </div>
    </template>
    <template v-else>
      <div class="avatar ai-avatar" title="城大智能助手">
        <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M11 2.5c.75 4.6 2.95 6.8 7.55 7.55-4.6.75-6.8 2.95-7.55 7.55-.75-4.6-2.95-6.8-7.55-7.55C8.05 9.3 10.25 7.1 11 2.5z" />
          <path d="M18.6 14.2c.4 2.5 1.55 3.65 4.05 4.05-2.5.4-3.65 1.55-4.05 4.05-.4-2.5-1.55-3.65-4.05-4.05 2.5-.4 3.65-1.55 4.05-4.05z" />
        </svg>
      </div>
      <div class="content-col">
        <div class="bubble ai-bubble" @click="onBubbleClick">
          <ThinkingBlock
            :reasoning="msg.reasoning || ''"
            :streaming="msg.streaming"
            :thinking-active="thinkingActive"
          />
          <div class="md-body" v-html="html"></div>
          <!-- 等待首字: 三点跳动 + 提示语 -->
          <div
            v-if="msg.streaming && !msg.content"
            class="waiting"
            v-show="thinkingActive || !msg.reasoning"
          >
            <span class="typing-dots"><i></i><i></i><i></i></span>
            <span class="waiting-text">{{ t('chat.waiting') }}</span>
          </div>
          <span v-else-if="msg.streaming" class="stream-caret"></span>
        </div>

        <!-- 生成结束后的操作条：复制 + 引用来源(气泡外) -->
        <div v-if="!msg.streaming" class="msg-footer">
          <button class="footer-btn" :title="t('common.copy')" @click="copyText(msg.content || '', $event.target)">{{ t('common.copy') }}</button>
          <button
            v-if="msg.sources && msg.sources.length"
            class="footer-btn"
            @click="previewOpen = !previewOpen"
          >
            {{ t('chat.sources', { n: msg.sources.length }) }}
            <span class="arrow" :class="{ open: previewOpen }">▾</span>
          </button>
          <div v-if="previewOpen && msg.sources?.length" class="source-list">
            <div v-for="(s, i) in msg.sources" :key="i" class="source-item">
              <span class="idx">{{ i + 1 }}</span>
              <span class="name">{{ s.filename }}</span>
              <span v-if="s.section" class="section">{{ s.section }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 22px;
  animation: fade-up 0.25s ease both;
}
/* 用户消息整行靠右: 气泡在左、头像在最右, 与 AI 消息镜像对称 */
.msg-row.user { justify-content: flex-end; }

.avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600;
}
.user-avatar {
  background: transparent;
  color: #7d958d;
}
.user-avatar svg {
  width: 30px; height: 30px;
}
.ai-avatar {
  background: transparent;
  color: var(--c-gold);
}
.ai-avatar svg {
  width: 30px; height: 30px;
}

.bubble { max-width: 82%; border-radius: 14px; }

/* 手机上气泡占满整行(头像+间隙外), 提升长回答阅读宽度 */
@media (max-width: 768px) {
  .msg-row { gap: 8px; margin-bottom: 16px; }
  .avatar { width: 27px; height: 27px; }
  .user-avatar svg, .ai-avatar svg { width: 21px; height: 21px; }
  .bubble { max-width: 100%; }
  .ai-bubble { padding: 12px 14px; }
  .user-bubble { padding: 9px 14px; }
}
.user-bubble {
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light));
  color: #fff;
  padding: 10px 16px;
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
  border-bottom-right-radius: 4px;
}
.ai-bubble {
  position: relative;
  background: var(--c-card);
  border: 1px solid var(--c-border);
  box-shadow: var(--shadow-card);
  padding: 14px 18px;
  border-top-left-radius: 4px;
}

/* 气泡外操作条（复制 / 引用来源） */
.content-col {
  min-width: 0;
  max-width: calc(100% - 48px);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.msg-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
  animation: fade-up 0.25s ease both;
}
.footer-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: var(--c-text-2);
  background: #fff;
  border: 1px solid var(--c-border);
  border-radius: 999px;
  padding: 4px 13px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.footer-btn:hover { color: var(--c-primary); border-color: var(--c-primary-light); }
.footer-btn.copied { color: #2e8e6a; border-color: rgba(46, 142, 106, 0.45); }
.arrow { font-size: 10px; transition: transform 0.2s; }
.arrow.open { transform: rotate(180deg); }
.source-list {
  width: 100%;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.source-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 12.5px; color: var(--c-text-2);
  background: #f7faf9; border: 1px solid var(--c-border);
  border-radius: 8px; padding: 6px 10px;
}
.source-item .idx {
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--c-primary); color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 10.5px; flex-shrink: 0;
}
.source-item .name { font-weight: 500; color: var(--c-text); }
.source-item .section { color: var(--c-text-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 等待首字: 三点 + 提示语 */
.waiting {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 210px;
  padding: 4px 0 2px;
}
.typing-dots {
  display: inline-flex;
  gap: 5px;
}
.typing-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-primary-light);
  animation: dot-bounce 1.2s infinite ease-in-out;
}
.typing-dots i:nth-child(2) { animation-delay: 0.15s; }
.typing-dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
  30% { transform: translateY(-4px); opacity: 1; }
}
.waiting-text {
  font-size: 13px;
  color: var(--c-text-3);
}
</style>
