/** 后端 API 封装 + SSE 流解析 */

/* 匿名访客 ID: 首次访问生成并持久化，会话按访客隔离(互不可见) */
const VISITOR_KEY = 'cityu_visitor_id'
let _visitorId = localStorage.getItem(VISITOR_KEY)
if (!_visitorId) {
  _visitorId = crypto.randomUUID
    ? crypto.randomUUID()
    : 'v-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10)
  localStorage.setItem(VISITOR_KEY, _visitorId)
}
export const visitorId = _visitorId

function visitorHeaders() {
  return { 'X-Visitor-Id': _visitorId }
}

async function request(url, options = {}) {
  const resp = await fetch(url, {
    ...options,
    headers: { ...visitorHeaders(), ...(options.headers || {}) },
  })
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const body = await resp.json()
      detail = body.detail || detail
    } catch { /* ignore */ }
    const err = new Error(detail)
    err.status = resp.status
    throw err
  }
  return resp.json()
}

function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/* ---- SSE 流式问答: 逐事件 yield ---- */
export async function* sseStream(url, body, signal) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...visitorHeaders() },
    body: JSON.stringify(body),
    signal,
  })
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const j = await resp.json()
      detail = j.detail || detail
    } catch { /* ignore */ }
    throw new Error(detail)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop()
    for (const line of lines) {
      const t = line.trim()
      if (!t.startsWith('data: ')) continue
      const payload = t.slice(6)
      if (payload === '[DONE]') return
      try {
        yield JSON.parse(payload)
      } catch { /* 跳过无法解析的行 */ }
    }
  }
}

/* ---- 会话(开放) ---- */
export const chatApi = {
  createSession: () => request('/api/chat/sessions', { method: 'POST' }),
  listSessions: () => request('/api/chat/sessions'),
  getMessages: (sid) => request(`/api/chat/sessions/${sid}/messages`),
  deleteSession: (sid) => request(`/api/chat/sessions/${sid}`, { method: 'DELETE' }),
  streamUrl: (sid) => `/api/chat/sessions/${sid}/stream`,
}

/* ---- 管理端 ---- */
export const adminApi = {
  login: (username, password) =>
    request('/api/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),
  documents: (params = {}, token) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/admin/documents?${qs}`, { headers: authHeaders(token) })
  },
  document: (id, token) => request(`/api/admin/documents/${id}`, { headers: authHeaders(token) }),
  chunks: (id, params = {}, token) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/admin/documents/${id}/chunks?${qs}`, { headers: authHeaders(token) })
  },
  upload: (file, token) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/api/admin/documents/upload', { method: 'POST', body: fd, headers: authHeaders(token) })
  },
  deleteDocument: (id, token) =>
    request(`/api/admin/documents/${id}`, { method: 'DELETE', headers: authHeaders(token) }),
  retryDocument: (id, token) =>
    request(`/api/admin/documents/${id}/retry`, { method: 'POST', headers: authHeaders(token) }),
  prompts: (token) => request('/api/admin/prompts', { headers: authHeaders(token) }),
  updatePrompt: (key, content, token) =>
    request(`/api/admin/prompts/${key}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ content }),
    }),
  config: (token) => request('/api/admin/config', { headers: authHeaders(token) }),
  updateConfig: (values, token) =>
    request('/api/admin/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ values }),
    }),
  stats: (days = 7, token) =>
    request(`/api/admin/stats/overview?days=${days}`, { headers: authHeaders(token) }),
}
