<script setup>
/** 系统提示词在线编辑：保存即时生效 */
import { onMounted, ref } from 'vue'
import { NTag, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { adminApi } from '../../api'
import { useAdminStore } from '../../stores/admin'

const { t } = useI18n()
const admin = useAdminStore()
const message = useMessage()

const prompts = ref([])
const draft = ref({})
const saving = ref({})
const expanded = ref('agent_system')

async function load() {
  const res = await adminApi.prompts(admin.token)
  prompts.value = res.items
  draft.value = Object.fromEntries(res.items.map((p) => [p.key, p.content]))
}

async function save(p) {
  saving.value[p.key] = true
  try {
    await adminApi.updatePrompt(p.key, draft.value[p.key], admin.token)
    message.success(t('prompts.saved'))
    load()
  } catch (e) {
    message.error(e.message)
  } finally {
    saving.value[p.key] = false
  }
}

function resetDraft(p) {
  draft.value[p.key] = ''
  save({ ...p, key: p.key })
}

onMounted(load)
</script>

<template>
  <div class="prompts">
    <div class="head">
      <h2>{{ t('prompts.title') }}</h2>
      <span class="tip">{{ t('prompts.tip') }}</span>
    </div>

    <div v-for="p in prompts" :key="p.key" class="prompt-card">
      <div class="card-head" @click="expanded = expanded === p.key ? '' : p.key">
        <span class="key-badge">{{ p.key }}</span>
        <n-tag v-if="p.modified" size="small" type="warning" round>{{ t('prompts.modified') }}</n-tag>
        <n-tag v-else size="small" type="default" round>{{ t('prompts.default') }}</n-tag>
        <span v-if="p.updated_at" class="time">
          {{ t('prompts.updatedAt', { time: p.updated_at.replace('T', ' ').slice(0, 19) }) }}
        </span>
        <span class="arrow" :class="{ open: expanded === p.key }">▾</span>
      </div>
      <div v-show="expanded === p.key" class="card-body">
        <textarea v-model="draft[p.key]" rows="14" spellcheck="false"></textarea>
        <div class="ops">
          <button class="btn reset" @click="resetDraft(p)">{{ t('prompts.restore') }}</button>
          <button class="btn primary" :disabled="saving[p.key]" @click="save(p)">
            {{ saving[p.key] ? t('prompts.saving') : t('prompts.save') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.prompts { max-width: 960px; margin: 0 auto; }
.head { margin-bottom: 16px; }
h2 { margin: 0 0 6px; font-size: 20px; }
.tip { font-size: 12.5px; color: var(--c-text-3); }
.tip b { color: var(--c-text-2); }

.prompt-card {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-card);
  margin-bottom: 14px;
  overflow: hidden;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 16px;
  cursor: pointer;
}
.card-head:hover { background: #fafcfb; }
.key-badge {
  font-family: var(--font-mono);
  font-size: 12.5px;
  background: var(--c-primary-lighter);
  color: var(--c-primary);
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 600;
}
.time { font-size: 12px; color: var(--c-text-3); margin-left: auto; }
.arrow { color: var(--c-text-3); font-size: 12px; transition: transform 0.2s; }
.arrow.open { transform: rotate(180deg); }

.card-body { padding: 0 16px 16px; }
textarea {
  width: 100%;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.7;
  font-family: inherit;
  color: var(--c-text);
  resize: vertical;
  outline: none;
  background: #fbfdfc;
}
textarea:focus { border-color: var(--c-primary-light); }
.ops { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
.btn {
  height: 34px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn.primary {
  border: none;
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light));
  color: #fff;
}
.btn.primary:disabled { opacity: 0.6; }
.btn.reset {
  border: 1px solid var(--c-border);
  background: #fff;
  color: var(--c-text-2);
}
.btn.reset:hover { border-color: var(--c-danger); color: var(--c-danger); }
</style>
