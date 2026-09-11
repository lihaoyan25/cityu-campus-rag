/** 聊天会话状态：多会话 + 流式消息 + 深度思考开关 */
import { defineStore } from 'pinia'
import { i18n } from '../i18n'
import { chatApi, sseStream } from '../api'

const t = i18n.global.t

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    currentSessionId: null,
    messages: [], // {role, content, reasoning, sources, streaming}
    streaming: false,
    deepThinking: localStorage.getItem('cityu_deep_thinking') === '1',
    _abortController: null,
  }),
  getters: {
    hasMessages: (s) => s.messages.length > 0,
    currentSession: (s) => s.sessions.find((x) => x.id === s.currentSessionId) || null,
  },
  actions: {
    setDeepThinking(v) {
      this.deepThinking = v
      localStorage.setItem('cityu_deep_thinking', v ? '1' : '0')
    },
    async loadSessions() {
      const res = await chatApi.listSessions()
      this.sessions = res.items
    },
    async newSession() {
      this.stopStream()
      this.currentSessionId = null
      this.messages = []
    },
    async selectSession(id) {
      if (this.streaming) this.stopStream()
      this.currentSessionId = id
      const res = await chatApi.getMessages(id)
      this.messages = res.items.map((m) => ({ ...m, streaming: false }))
    },
    async deleteSession(id) {
      await chatApi.deleteSession(id)
      if (this.currentSessionId === id) {
        this.currentSessionId = null
        this.messages = []
      }
      await this.loadSessions()
    },
    stopStream() {
      this._abortController?.abort()
      this._abortController = null
      this.streaming = false
      this.messages = this.messages.map((m) => ({ ...m, streaming: false }))
    },

    /** 发送问题: 自动建会话 → SSE 流式接收 */
    async send(question) {
      if (this.streaming || !question.trim()) return
      if (!this.currentSessionId) {
        const s = await chatApi.createSession()
        this.currentSessionId = s.id
      }
      // 本地乐观追加用户消息与占位助手消息
      this.messages.push({ role: 'user', content: question, sources: null, reasoning: null })
      this.messages.push({
        role: 'assistant',
        content: '',
        reasoning: '',
        sources: null,
        streaming: true,
        thinkingDone: false,
      })
      // 关键: 从 reactive 数组取代理引用，直接改原始对象不会触发视图更新
      const assistantMsg = this.messages[this.messages.length - 1]
      this.streaming = true
      this._abortController = new AbortController()

      try {
        const events = sseStream(
          chatApi.streamUrl(this.currentSessionId),
          { question, deep_thinking: this.deepThinking },
          this._abortController.signal,
        )
        for await (const ev of events) {
          if (ev.type === 'thinking') {
            assistantMsg.reasoning += ev.content
          } else if (ev.type === 'delta') {
            assistantMsg.thinkingDone = true
            assistantMsg.content += ev.content
          } else if (ev.type === 'sources') {
            assistantMsg.sources = ev.sources
          } else if (ev.type === 'tool') {
            assistantMsg.toolName = ev.name
          } else if (ev.type === 'tool_result') {
            assistantMsg.toolName = null
          } else if (ev.type === 'done') {
            assistantMsg.sources = ev.sources ?? assistantMsg.sources
          } else if (ev.type === 'error') {
            assistantMsg.content += `\n\n> ${t('chat.streamError', { msg: ev.message })}`
          }
        }
      } catch (e) {
        if (e.name !== 'AbortError') {
          assistantMsg.content += `\n\n> ${t('chat.connLost', { msg: e.message })}`
        }
      } finally {
        assistantMsg.streaming = false
        this.streaming = false
        this._abortController = null
        this.loadSessions()
      }
    },
  },
})
