<script setup>
/** 管理后台布局：顶栏 + 模块菜单 + 内容区 */
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAdminStore } from '../../stores/admin'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const admin = useAdminStore()

// 极简线性菜单图标 (stroke path, 24 viewBox)
const ICONS = {
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M14 14h7v7h-7z M3 14h7v7H3z',
  book: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z',
  edit: 'M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7 M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z',
  sliders: 'M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6',
}

const tabs = [
  { key: 'dashboard', icon: 'grid' },
  { key: 'knowledge', icon: 'book' },
  { key: 'prompts', icon: 'edit' },
  { key: 'model', icon: 'sliders' },
]
const active = ref(route.name)
watch(() => route.name, (n) => (active.value = n))

function go(key) {
  router.push(`/admin/${key}`)
}
function backHome() {
  router.push('/')
}
</script>

<template>
  <div class="admin-layout">
    <header class="admin-topbar">
      <nav class="menu">
        <button
          v-for="item in tabs"
          :key="item.key"
          class="menu-item"
          :class="{ active: active === item.key }"
          @click="go(item.key)"
        >
          <svg class="mi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path :d="ICONS[item.icon]" />
          </svg>
          {{ t('admin.' + item.key) }}
        </button>
      </nav>
      <div class="right">
        <button class="ghost" @click="backHome">{{ t('admin.backToChat') }}</button>
        <button class="ghost" @click="admin.logout(); backHome()">{{ t('admin.logout') }}</button>
      </div>
    </header>
    <main class="admin-body">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.admin-layout { height: 100%; display: flex; flex-direction: column; }
.admin-topbar {
  height: 60px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 26px;
  padding: 0 22px;
  background: linear-gradient(90deg, var(--c-sidebar-1), var(--c-sidebar-2));
  color: #dfe9e5;
}
.menu { display: flex; gap: 4px; flex: 1; }
.menu-item {
  height: 60px;
  padding: 0 18px;
  background: transparent;
  border: none;
  color: #9db8b0;
  font-size: 13.5px;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}
.menu-item:hover { color: #fff; }
.menu-item.active { color: var(--c-gold); }
.menu-item.active::after {
  content: '';
  position: absolute;
  left: 14px; right: 14px; bottom: 0;
  height: 3px;
  border-radius: 3px 3px 0 0;
  background: var(--c-gold);
}
.menu-item .mi-icon {
  width: 14px; height: 14px;
  vertical-align: -2px;
  margin-right: 5px;
}

.right { display: flex; gap: 10px; }
.ghost {
  height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  background: transparent;
  color: #b9cdc6;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.2s;
}
.ghost:hover { color: #fff; border-color: rgba(255, 255, 255, 0.5); }

.admin-body { flex: 1; overflow-y: auto; padding: 24px 28px; }

/* ---- 窄屏: 菜单横向滚动 + 收缩间距 ---- */
@media (max-width: 768px) {
  .admin-topbar { padding: 0 10px; gap: 8px; }
  .menu { overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
  .menu::-webkit-scrollbar { display: none; }
  .menu-item { padding: 0 12px; font-size: 12.5px; flex-shrink: 0; }
  .menu-item.active::after { left: 8px; right: 8px; }
  .right { gap: 6px; }
  .ghost { height: 30px; padding: 0 10px; font-size: 12px; flex-shrink: 0; }
  .admin-body { padding: 14px 12px; }
}
</style>
