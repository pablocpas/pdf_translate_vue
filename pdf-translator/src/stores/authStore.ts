import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { z } from 'zod'

const tokenSchema = z.string().min(1, 'Token no puede estar vacío')

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('auth_token'))

  function setToken(newToken: string) {
    const parsedToken = tokenSchema.safeParse(newToken)
    if (!parsedToken.success) {
      throw new Error('Token inválido')
    }
    token.value = newToken
    localStorage.setItem('auth_token', newToken)
  }

  function clearToken() {
    token.value = null
    localStorage.removeItem('auth_token')
  }

  const isAuthenticated = computed(() => !!token.value)

  return {
    token,
    setToken,
    clearToken,
    isAuthenticated
  }
})
