<script setup>
/** 管理员登录弹窗 */
import { ref } from 'vue'
import { NModal, NButton, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { adminApi } from '../api'
import { useAdminStore } from '../stores/admin'

const { t } = useI18n()
const props = defineProps({ show: Boolean })
const emit = defineEmits(['update:show'])
const admin = useAdminStore()
const message = useMessage()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function login() {
  if (!username.value || !password.value) {
    message.warning(t('login.emptyWarn'))
    return
  }
  loading.value = true
  try {
    const res = await adminApi.login(username.value, password.value)
    admin.login(res.access_token)
    message.success(t('login.success'))
    emit('update:show', false)
    username.value = ''
    password.value = ''
  } catch (e) {
    message.error(e.message || t('login.failed'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <n-modal
    :show="props.show"
    @update:show="(v) => emit('update:show', v)"
  >
    <div class="login-card">
      <div class="head">
        <div class="badge">
          <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M11 2.5c.75 4.6 2.95 6.8 7.55 7.55-4.6.75-6.8 2.95-7.55 7.55-.75-4.6-2.95-6.8-7.55-7.55C8.05 9.3 10.25 7.1 11 2.5z" />
            <path d="M18.6 14.2c.4 2.5 1.55 3.65 4.05 4.05-2.5.4-3.65 1.55-4.05 4.05-.4-2.5-1.55-3.65-4.05-4.05 2.5-.4 3.65-1.55 4.05-4.05z" />
          </svg>
        </div>
        <h3>{{ t('login.title') }}</h3>
        <p>{{ t('login.subtitle') }}</p>
      </div>
      <div class="form">
        <input v-model="username" :placeholder="t('login.username')" @keyup.enter="login" />
        <input v-model="password" type="password" :placeholder="t('login.password')" @keyup.enter="login" />
        <n-button type="primary" block :loading="loading" @click="login">
          {{ t('login.submit') }}
        </n-button>
      </div>
    </div>
  </n-modal>
</template>

<style scoped>
.login-card {
  width: 360px;
  background: var(--c-card);
  border-radius: var(--r-lg);
  padding: 32px 30px 28px;
  box-shadow: var(--shadow-float);
}
.head { text-align: center; margin-bottom: 22px; }
.badge {
  width: 52px; height: 52px;
  margin: 0 auto 12px;
  color: var(--c-gold);
}
h3 { margin: 0 0 6px; color: var(--c-text); }
p { margin: 0; font-size: 12.5px; color: var(--c-text-3); }
.form { display: flex; flex-direction: column; gap: 12px; }
.form input {
  height: 42px;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 0 14px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  background: #fbfdfc;
}
.form input:focus { border-color: var(--c-primary-light); }
</style>
