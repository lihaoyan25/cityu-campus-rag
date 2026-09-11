/** 管理员登录态（localStorage 持久化） */
import { defineStore } from 'pinia'

const KEY = 'cityu_admin_token'

export const useAdminStore = defineStore('admin', {
  state: () => ({
    token: localStorage.getItem(KEY) || '',
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    login(token) {
      this.token = token
      localStorage.setItem(KEY, token)
    },
    logout() {
      this.token = ''
      localStorage.removeItem(KEY)
    },
  },
})
