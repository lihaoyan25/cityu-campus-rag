<script setup>
/** 模型配置：.env 中影响 RAG 质量的可调项，热更新即时生效 */
import { computed, onMounted, ref } from 'vue'
import { NSwitch, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { adminApi } from '../../api'
import { useAdminStore } from '../../stores/admin'

const { t } = useI18n()
const admin = useAdminStore()
const message = useMessage()

const groups = [
  {
    titleKey: 'groupDeepseek',
    fields: [
      { key: 'deepseek_api_key', type: 'password', hintKey: 'sensitive' },
      { key: 'deepseek_base_url', type: 'text' },
      { key: 'deepseek_model', type: 'text' },
      { key: 'deepseek_temperature', type: 'number', step: 0.1 },
      { key: 'deepseek_max_tokens', type: 'number', step: 1 },
      { key: 'deepseek_top_p', type: 'number', step: 0.1 },
    ],
  },
  {
    titleKey: 'groupGlm',
    fields: [
      { key: 'glm_api_key', type: 'password', hintKey: 'sensitive' },
      { key: 'glm_base_url', type: 'text' },
      { key: 'glm_model', type: 'text' },
      { key: 'glm_embedding_dimensions', type: 'number', step: 1, hintKey: 'dimHint' },
      { key: 'glm_embedding_batch_size', type: 'number', step: 1 },
    ],
  },
  {
    titleKey: 'groupRetrieval',
    fields: [
      { key: 'retrieval_top_k', type: 'number', step: 1 },
      { key: 'hybrid_enabled', type: 'switch' },
      { key: 'rrf_k', type: 'number', step: 1 },
      { key: 'rerank_enabled', type: 'switch' },
    ],
  },
  {
    titleKey: 'groupChunk',
    fields: [
      { key: 'chunk_size', type: 'number', step: 1 },
      { key: 'chunk_overlap', type: 'number', step: 1 },
      { key: 'doc_clean_enabled', type: 'switch' },
    ],
  },
  {
    titleKey: 'groupMemory',
    fields: [
      { key: 'memory_window_messages', type: 'number', step: 1 },
      { key: 'memory_summary_trigger', type: 'number', step: 1 },
    ],
  },
]

const configs = ref({}) // key -> {value, modified, sensitive}
const drafts = ref({})
const saving = ref(false)

const changedKeys = computed(() =>
  Object.keys(drafts.value).filter((k) => drafts.value[k] !== configs.value[k]?.value)
)

async function load() {
  const res = await adminApi.config(admin.token)
  configs.value = res.items
  // switch 字段后端返回字符串 "true"/"false"，转为布尔供 NSwitch 使用
  const switchKeys = new Set(
    groups.flatMap((g) => g.fields.filter((f) => f.type === 'switch').map((f) => f.key))
  )
  const d = {}
  for (const [k, v] of Object.entries(res.items)) {
    const boolVal = String(v.value).toLowerCase() === 'true'
    if (switchKeys.has(k)) {
      d[k] = boolVal
      v.value = boolVal
    } else {
      d[k] = v.value
    }
  }
  drafts.value = d
}

async function save() {
  if (!changedKeys.value.length) {
    message.info(t('model.noChange'))
    return
  }
  saving.value = true
  try {
    const values = Object.fromEntries(changedKeys.value.map((k) => [k, String(drafts.value[k])]))
    const res = await adminApi.updateConfig(values, admin.token)
    message.success(t('model.saved', { n: res.updated }))
    load()
  } catch (e) {
    message.error(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="model-config">
    <div class="head">
      <h2>{{ t('model.title') }}</h2>
      <button class="save-btn" :disabled="saving || !changedKeys.length" @click="save">
        {{ saving ? t('common.saving') : t('model.save', { n: changedKeys.length }) }}
      </button>
    </div>
    <p class="tip">{{ t('model.tip') }}</p>

    <div v-for="g in groups" :key="g.titleKey" class="group">
      <div class="g-title">{{ t('model.' + g.titleKey) }}</div>
      <div class="g-body">
        <div v-for="f in g.fields" :key="f.key" class="field">
          <div class="f-label">
            {{ t('model.' + f.key) }}
            <span v-if="configs[f.key]?.modified" class="mod-dot" :title="t('model.tip')"></span>
          </div>
          <div class="f-control">
            <n-switch v-if="f.type === 'switch'" v-model:value="drafts[f.key]">
              <template #checked>{{ t('model.on') }}</template>
              <template #unchecked>{{ t('model.off') }}</template>
            </n-switch>
            <input
              v-else
              v-model="drafts[f.key]"
              :type="f.type === 'number' ? 'number' : 'text'"
              :step="f.step"
              autocomplete="off"
            />
          </div>
          <div v-if="f.hintKey" class="f-hint">{{ t('model.' + f.hintKey) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.model-config { max-width: 960px; margin: 0 auto; }
.head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
h2 { margin: 0; font-size: 20px; }
.save-btn {
  height: 36px;
  padding: 0 20px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light));
  color: #fff;
  font-size: 13.5px;
  cursor: pointer;
}
.save-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.tip { font-size: 12.5px; color: var(--c-text-3); margin: 0 0 18px; }

.group {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-card);
  margin-bottom: 16px;
  overflow: hidden;
}
.g-title {
  padding: 13px 18px;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-primary);
  background: #f7faf9;
  border-bottom: 1px solid var(--c-border);
}
.g-body { padding: 6px 18px 12px; }
.field {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 14px;
  align-items: center;
  padding: 11px 0;
  border-bottom: 1px dashed var(--c-border);
}
.field:last-child { border-bottom: none; }
.f-label { font-size: 13.5px; color: var(--c-text); display: flex; align-items: center; gap: 6px; }
.mod-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--c-gold);
}
.f-control input {
  width: 100%;
  max-width: 460px;
  height: 36px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 0 12px;
  font-size: 13.5px;
  font-family: var(--font-mono);
  outline: none;
  background: #fbfdfc;
  transition: border-color 0.2s;
}
.f-control input:focus { border-color: var(--c-primary-light); }
.f-hint { grid-column: 2; font-size: 11.5px; color: var(--c-text-3); margin-top: -8px; }
</style>
