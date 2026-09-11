<script setup>
/** 用户聊天主界面：首轮输入框居中，对话后输入框下沉到底部 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NDropdown } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useChatStore } from '../stores/chat'
import { useAdminStore } from '../stores/admin'
import { LANGS, setLang } from '../i18n'
import SessionSidebar from '../components/SessionSidebar.vue'
import MessageBubble from '../components/MessageBubble.vue'
import ChatInput from '../components/ChatInput.vue'
import AdminLoginModal from '../components/AdminLoginModal.vue'

const { t } = useI18n()
const chat = useChatStore()
const admin = useAdminStore()
const router = useRouter()

const showLogin = ref(false)
const scrollRef = ref(null)
const heroInput = ref(null)

const heroMode = computed(() => !chat.hasMessages)

/** 快捷提问卡片：填入输入框（不直接发送，便于修改） */
function useTip(q) {
  heroInput.value?.fill(q)
}

function scrollToBottom() {
  nextTick(() => {
    const el = scrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
watch(() => chat.messages.map((m) => (m.content || '') + (m.reasoning || '')).join('|'), scrollToBottom)
watch(() => chat.currentSessionId, scrollToBottom)
onMounted(() => chat.loadSessions())

function onAdminBtn() {
  if (admin.isLoggedIn) {
    router.push('/admin/dashboard')
  } else {
    showLogin.value = true
  }
}
function onLangPick(key) {
  setLang(key)
}
const langOptions = LANGS.map((l) => ({ label: l.label, key: l.value }))
const tips = computed(() => [
  { label: t('home.tip1'), q: t('home.q1') },
  { label: t('home.tip2'), q: t('home.q2') },
  { label: t('home.tip3'), q: t('home.q3') },
])
</script>

<template>
  <div class="home">
    <SessionSidebar @admin-click="showLogin = true" />

    <div class="main">
      <!-- 右上角悬浮按钮组：语言 + 管理员 -->
      <div class="float-actions">
        <n-dropdown :options="langOptions" trigger="click" @select="onLangPick">
          <button class="float-btn lang" :title="t('home.langTip')">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6">
              <circle cx="12" cy="12" r="9" />
              <path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.7-3.8-9S9.5 5.6 12 3z" />
            </svg>
          </button>
        </n-dropdown>
        <button class="float-btn" @click="onAdminBtn">
          <span class="lock">⚿</span> {{ admin.isLoggedIn ? t('home.adminPanel') : t('home.adminBtn') }}
        </button>
      </div>

      <!-- 对话区 -->
      <div ref="scrollRef" class="chat-area">
        <template v-if="heroMode">
          <div class="hero">
            <div class="hero-badge">
              <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M11 2.5c.75 4.6 2.95 6.8 7.55 7.55-4.6.75-6.8 2.95-7.55 7.55-.75-4.6-2.95-6.8-7.55-7.55C8.05 9.3 10.25 7.1 11 2.5z" />
                <path d="M18.6 14.2c.4 2.5 1.55 3.65 4.05 4.05-2.5.4-3.65 1.55-4.05 4.05-.4-2.5-1.55-3.65-4.05-4.05 2.5-.4 3.65-1.55 4.05-4.05z" />
              </svg>
            </div>
            <h1>{{ t('home.heroTitle') }}</h1>
            <p class="sub">{{ t('home.heroSub') }}</p>
            <div class="hero-input">
              <ChatInput ref="heroInput" />
            </div>
            <div class="hero-tips">
              <span v-for="tip in tips" :key="tip.q" class="tip" @click="useTip(tip.q)">{{ tip.label }}</span>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="msg-list">
            <MessageBubble v-for="(m, i) in chat.messages" :key="i" :msg="m" />
          </div>
        </template>
      </div>

      <!-- 底部输入框(对话态) -->
      <div v-if="!heroMode" class="input-dock">
        <div class="dock-inner">
          <ChatInput />
        </div>
      </div>
    </div>

    <AdminLoginModal v-model:show="showLogin" />
  </div>
</template>

<style scoped>
.home {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
}

/* ---- 右上角悬浮按钮 ---- */
.float-actions {
  position: absolute;
  top: 16px;
  right: 20px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 10px;
}
.float-btn {
  height: 36px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  color: var(--c-text-2);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: var(--shadow-card);
}
.float-btn:hover { border-color: var(--c-primary-light); color: var(--c-primary); }
.float-btn .lock { color: var(--c-gold); font-size: 14px; }
.float-btn.lang {
  width: 36px;
  padding: 0;
  justify-content: center;
}

.chat-area { flex: 1; overflow-y: auto; }

/* ---- Hero 首轮居中 ---- */
.hero {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 24px 6vh;
}
.hero-badge {
  width: 58px;
  height: 58px;
  color: var(--c-gold);
  margin-bottom: 18px;
  filter: drop-shadow(0 3px 10px rgba(200, 165, 101, 0.35));
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 30px;
  color: var(--c-text);
  letter-spacing: 1px;
}
.hero .sub { margin: 0 0 30px; color: var(--c-text-2); font-size: 15px; }
.hero-input { width: min(680px, 92%); }
.hero-tips { display: flex; gap: 10px; margin-top: 18px; flex-wrap: wrap; justify-content: center; }
.tip {
  font-size: 12.5px;
  color: var(--c-text-2);
  background: #fff;
  border: 1px solid var(--c-border);
  padding: 6px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
}
.tip:hover { color: var(--c-primary); border-color: var(--c-primary-light); }

/* ---- 对话态 ---- */
.msg-list {
  max-width: 860px;
  margin: 0 auto;
  padding: 60px 24px 10px;
}
.input-dock {
  padding: 8px 24px 18px;
  background: linear-gradient(to top, var(--c-bg) 65%, transparent);
}
.dock-inner { max-width: 860px; margin: 0 auto; }
</style>
