<script setup>
/** 知识库管理：文档列表 / 上传入库 / 内容预览(分片) / 删除 / 重试 */
import { onMounted, ref } from 'vue'
import { NTag, NDrawer, NPagination, NEmpty, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { adminApi } from '../../api'
import { useAdminStore } from '../../stores/admin'

const { t, te } = useI18n()
const admin = useAdminStore()
const message = useMessage()

const docs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const fileInput = ref(null)
const uploading = ref(false)

const drawer = ref(false)
const currentDoc = ref(null)
const chunks = ref([])
const chunkTotal = ref(0)
const chunkPage = ref(1)
const chunkPageSize = 20

function statusInfo(status) {
  return {
    label: te(`status.${status}`) ? t(`status.${status}`) : status,
    type: { done: 'success', failed: 'error' }[status] || 'info',
  }
}

function fmtSize(n) {
  if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
  if (n >= 1024) return (n / 1024).toFixed(1) + ' KB'
  return n + ' B'
}
function fmtTime(ts) {
  return ts ? ts.replace('T', ' ').slice(0, 19) : '-'
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.documents({ page: page.value, page_size: pageSize }, admin.token)
    docs.value = res.items
    total.value = res.total
  } catch (e) {
    message.error(e.message)
  } finally {
    loading.value = false
  }
}

function pickFiles() {
  fileInput.value?.click()
}

async function onFiles(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  uploading.value = true
  let ok = 0
  for (const f of files) {
    try {
      await adminApi.upload(f, admin.token)
      ok++
    } catch (err) {
      message.error(`${f.name}: ${err.message}`)
    }
  }
  uploading.value = false
  if (ok) message.success(t('knowledge.submitted', { n: ok }))
  load()
}

async function openDoc(doc) {
  currentDoc.value = doc
  drawer.value = true
  chunkPage.value = 1
  loadChunks()
}

async function loadChunks() {
  if (!currentDoc.value) return
  const res = await adminApi.chunks(
    currentDoc.value.id,
    { page: chunkPage.value, page_size: chunkPageSize },
    admin.token,
  )
  chunks.value = res.items
  chunkTotal.value = res.total
}

async function retry(doc) {
  try {
    await adminApi.retryDocument(doc.id, admin.token)
    message.success(t('knowledge.retried', { name: doc.filename }))
    load()
  } catch (e) {
    message.error(e.message)
  }
}

async function remove(doc) {
  if (!confirm(t('knowledge.confirmDelete', { name: doc.filename }))) return
  try {
    await adminApi.deleteDocument(doc.id, admin.token)
    message.success(t('knowledge.deleted'))
    load()
  } catch (e) {
    message.error(e.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="kb">
    <div class="head">
      <h2>{{ t('knowledge.title') }}</h2>
      <button class="upload-btn" :disabled="uploading" @click="pickFiles">
        {{ uploading ? t('knowledge.uploading') : t('knowledge.upload') }}
      </button>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".pdf,.docx,.md,.markdown,.txt,.html,.htm"
        style="display: none"
        @change="onFiles"
      />
    </div>
    <p class="tip">{{ t('knowledge.tip') }}</p>

    <div class="table-card">
      <table>
        <thead>
          <tr>
            <th style="width: 34%">{{ t('knowledge.colFilename') }}</th>
            <th>{{ t('knowledge.colType') }}</th>
            <th>{{ t('knowledge.colStatus') }}</th>
            <th>{{ t('knowledge.colChunks') }}</th>
            <th>{{ t('knowledge.colSize') }}</th>
            <th>{{ t('knowledge.colTime') }}</th>
            <th style="width: 200px">{{ t('knowledge.colOps') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && !docs.length">
            <td colspan="7" class="empty">{{ t('knowledge.loadingRows') }}</td>
          </tr>
          <tr v-else-if="!docs.length">
            <td colspan="7" class="empty">{{ t('knowledge.empty') }}</td>
          </tr>
          <tr v-for="d in docs" :key="d.id">
            <td class="fname" :title="d.error || d.filename">
              {{ d.filename }}
              <div v-if="d.status === 'failed'" class="err">{{ d.error }}</div>
            </td>
            <td><span class="ftype">{{ d.file_type.toUpperCase() }}</span></td>
            <td>
              <n-tag :type="statusInfo(d.status).type" size="small" round>
                {{ statusInfo(d.status).label }}
              </n-tag>
            </td>
            <td>{{ d.chunk_count }}</td>
            <td>{{ fmtSize(d.size) }}</td>
            <td class="time">{{ fmtTime(d.created_at) }}</td>
            <td class="ops">
              <button class="op" @click="openDoc(d)">{{ t('knowledge.previewChunks') }}</button>
              <button v-if="d.status === 'failed' || d.status === 'done'" class="op" @click="retry(d)">
                {{ t('knowledge.reprocess') }}
              </button>
              <button class="op danger" @click="remove(d)">{{ t('knowledge.del') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pager">
        <n-pagination
          v-model:page="page"
          :page-size="pageSize"
          :item-count="total"
          @update:page="load"
        />
      </div>
    </div>

    <!-- 分片预览抽屉 -->
    <n-drawer v-model:show="drawer" :width="560">
      <div class="drawer-body">
        <div class="d-head">
          <div class="d-title">{{ currentDoc?.filename }}</div>
          <div class="d-sub">
            {{ t('knowledge.chunksOf', { n: currentDoc?.chunk_count ?? 0, chars: (currentDoc?.char_count ?? 0).toLocaleString() }) }}
          </div>
        </div>
        <n-empty v-if="!chunks.length" :description="t('knowledge.noChunks')" style="margin-top: 60px" />
        <div v-for="c in chunks" :key="c.id" class="chunk">
          <div class="c-head">
            <span class="c-idx">#{{ c.chunk_index }}</span>
            <span v-if="c.meta?.section" class="c-sec">{{ c.meta.section }}</span>
            <span class="c-len">{{ t('knowledge.chunkChars', { n: c.char_count }) }}</span>
          </div>
          <div class="c-content">{{ c.content }}</div>
        </div>
        <div class="pager" style="margin-top: 14px">
          <n-pagination
            v-model:page="chunkPage"
            :page-size="chunkPageSize"
            :item-count="chunkTotal"
            @update:page="loadChunks"
          />
        </div>
      </div>
    </n-drawer>
  </div>
</template>

<style scoped>
.kb { max-width: 1200px; margin: 0 auto; }
.head { display: flex; align-items: center; justify-content: space-between; }
h2 { margin: 0; font-size: 20px; }
.upload-btn {
  height: 38px;
  padding: 0 18px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--c-primary), var(--c-primary-light));
  color: #fff;
  font-size: 13.5px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.upload-btn:disabled { opacity: 0.6; cursor: wait; }
.upload-btn:hover:not(:disabled) { opacity: 0.9; }
.tip { font-size: 12.5px; color: var(--c-text-3); margin: 8px 0 16px; }

.table-card {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  overflow-x: auto;  /* 窄屏表格横向滚动(覆盖 hidden 的 x 轴) */
}
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
@media (max-width: 768px) {
  table { min-width: 720px; }  /* 窄屏撑开表格, 由 .table-card 横向滚动 */
}
th {
  text-align: left;
  padding: 12px 14px;
  background: #f7faf9;
  color: var(--c-text-2);
  font-weight: 500;
  border-bottom: 1px solid var(--c-border);
}
td { padding: 12px 14px; border-bottom: 1px solid var(--c-border); vertical-align: top; }
tbody tr:hover { background: #fafcfb; }
.fname { font-weight: 500; word-break: break-all; }
.err { color: var(--c-danger); font-size: 12px; margin-top: 4px; white-space: pre-wrap; }
.ftype {
  font-size: 11px; font-weight: 600;
  background: var(--c-primary-lighter); color: var(--c-primary);
  padding: 2px 8px; border-radius: 4px;
}
.time { color: var(--c-text-3); font-size: 12.5px; }
.ops { display: flex; gap: 6px; flex-wrap: wrap; }
.op {
  height: 26px; padding: 0 10px;
  border-radius: 6px;
  border: 1px solid var(--c-border);
  background: #fff; color: var(--c-text-2);
  font-size: 12px; cursor: pointer;
  transition: all 0.15s;
}
.op:hover { border-color: var(--c-primary-light); color: var(--c-primary); }
.op.danger:hover { border-color: var(--c-danger); color: var(--c-danger); }
.empty { text-align: center; color: var(--c-text-3); padding: 40px 0 !important; }
.pager { display: flex; justify-content: flex-end; padding: 12px 14px; }

.drawer-body { padding: 20px 22px; height: 100%; overflow-y: auto; }
.d-title { font-size: 16px; font-weight: 600; word-break: break-all; }
.d-sub { font-size: 12.5px; color: var(--c-text-3); margin-top: 4px; margin-bottom: 16px; }
.chunk {
  border: 1px solid var(--c-border);
  border-radius: 10px;
  margin-bottom: 12px;
  overflow: hidden;
}
.c-head {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  background: #f7faf9;
  font-size: 12px;
  color: var(--c-text-2);
}
.c-idx {
  background: var(--c-primary); color: #fff;
  padding: 1px 8px; border-radius: 4px; font-size: 11px;
}
.c-sec { color: var(--c-primary); }
.c-len { margin-left: auto; color: var(--c-text-3); }
.c-content {
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--c-text);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 260px;
  overflow-y: auto;
}
</style>
