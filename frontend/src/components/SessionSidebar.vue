<script setup>
/** 会话侧栏：新会话 + 会话列表 + 管理后台入口
 *  桌面端常驻; 窄屏(<=768px)为抽屉, 由父组件通过 open 控制, 选择后 emit('close') 收起 */
import { useI18n } from 'vue-i18n'
import { useChatStore } from '../stores/chat'
import { useAdminStore } from '../stores/admin'
import { useRouter } from 'vue-router'

const { t } = useI18n()
const chat = useChatStore()
const admin = useAdminStore()
const router = useRouter()

defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['admin-click', 'close'])

async function del(id, title) {
  if (confirm(t('sidebar.confirmDelete', { title }))) await chat.deleteSession(id)
}
function onNew() {
  chat.newSession()
  emit('close')
}
function onSelect(id) {
  chat.selectSession(id)
  emit('close')
}
function onAdmin() {
  emit('admin-click')
  emit('close')
}
function onAdminPanel() {
  router.push('/admin/dashboard')
  emit('close')
}
</script>

<template>
  <aside class="sidebar" :class="{ open }">
    <button class="new-chat-btn" @click="onNew">
      <span class="plus">＋</span> {{ t('sidebar.newChat') }}
    </button>

    <div class="session-list">
      <div
        v-for="s in chat.sessions"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === chat.currentSessionId }"
        @click="onSelect(s.id)"
      >
        <span class="dot"></span>
        <span class="title">{{ s.title }}</span>
        <span class="del" :title="t('common.delete')" @click.stop="del(s.id, s.title)">✕</span>
      </div>
      <div v-if="!chat.sessions.length" class="empty-tip">&nbsp;</div>
    </div>

    <div class="sidebar-footer">
      <button v-if="admin.isLoggedIn" class="admin-entry" @click="onAdminPanel">
        <span class="icon">⚙</span> {{ t('sidebar.adminPanel') }}
      </button>
      <button v-else class="admin-entry" @click="onAdmin">
        <span class="icon">⚙</span> {{ t('sidebar.adminLogin') }}
      </button>
      <div class="copyright">{{ t('sidebar.copyright') }}</div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 264px;
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(175deg, var(--c-sidebar-2) 0%, var(--c-sidebar-1) 100%);
  color: #dfe9e5;
}

.new-chat-btn {
  margin: 18px 14px 10px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid rgba(200, 165, 101, 0.55);
  background: rgba(200, 165, 101, 0.12);
  color: #e9d9b8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.new-chat-btn:hover { background: rgba(200, 165, 101, 0.25); }
.new-chat-btn .plus { margin-right: 6px; color: var(--c-gold); }

.session-list { flex: 1; overflow-y: auto; padding: 4px 10px; }
.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13.5px;
  color: #c3d4ce;
  margin-bottom: 2px;
  transition: background 0.15s;
}
.session-item:hover { background: rgba(255, 255, 255, 0.07); }
.session-item.active { background: rgba(200, 165, 101, 0.18); color: #fff; }
.session-item .dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #5d7a71; flex-shrink: 0;
}
.session-item.active .dot { background: var(--c-gold); }
.session-item .title {
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.session-item .del {
  opacity: 0; font-size: 11px; color: #8aa39b;
  padding: 2px 5px; border-radius: 4px; transition: all 0.15s;
}
.session-item:hover .del { opacity: 1; }
.session-item .del:hover { color: #f0b6ab; background: rgba(192, 72, 59, 0.2); }
.empty-tip { text-align: center; color: #5d7a71; font-size: 12.5px; padding: 24px 0; }

.sidebar-footer { padding: 12px 14px 14px; border-top: 1px solid rgba(255, 255, 255, 0.08); }
.admin-entry {
  width: 100%;
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #9db8b0;
  font-size: 13.5px;
  cursor: pointer;
  transition: all 0.15s;
}
.admin-entry:hover { background: rgba(255, 255, 255, 0.08); color: #fff; }
.admin-entry .icon { color: var(--c-gold); }
.copyright { text-align: center; font-size: 10.5px; color: #4c6660; margin-top: 10px; letter-spacing: 0.5px; }

/* ---- 窄屏: 抽屉模式 ---- */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0; left: 0; bottom: 0;
    z-index: 60;
    width: 286px;
    max-width: 84vw;
    transform: translateX(-100%);
    transition: transform 0.28s cubic-bezier(0.22, 0.61, 0.36, 1);
    box-shadow: 0 0 40px rgba(0, 0, 0, 0.35);
  }
  .sidebar.open { transform: translateX(0); }
  .session-item .del { opacity: 1; }  /* 触屏无 hover, 常显删除 */
}
</style>
