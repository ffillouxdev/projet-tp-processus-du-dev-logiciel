import { computed, ref } from 'vue'
import { $fetch, type FetchOptions } from 'ofetch'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const AUTH_STORAGE_KEY = 'tournament-auth'

export interface User {
  id: number
  email: string
  username: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface AuthResponse {
  user: User
  tokens: TokenResponse
}

export interface UserMembership {
  user_id: number
  association_id: number
  role_id: number
  role: {
    id: number
    name: string
  }
}

export interface RegisterRequest {
  email: string
  username: string
  full_name?: string | null
  password: string
}

export interface LoginRequest {
  identifier: string
  password: string
}

interface StoredAuth {
  user: User
  tokens: TokenResponse
}

interface MessageResponse {
  message: string
}

function readStoredAuth(): StoredAuth | null {
  if (typeof localStorage === 'undefined') return null

  const storedAuth = localStorage.getItem(AUTH_STORAGE_KEY)
  if (!storedAuth) return null

  try {
    return JSON.parse(storedAuth) as StoredAuth
  } catch (error) {
    if (error instanceof SyntaxError) {
      localStorage.removeItem(AUTH_STORAGE_KEY)
      return null
    }
    throw error
  }
}

const storedAuth = readStoredAuth()
const user = ref<User | null>(storedAuth?.user ?? null)
const tokens = ref<TokenResponse | null>(storedAuth?.tokens ?? null)

const api = $fetch.create({
  baseURL: API_BASE_URL,
})

function persistAuth(auth: StoredAuth): void {
  user.value = auth.user
  tokens.value = auth.tokens
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth))
}

function clearAuth(): void {
  user.value = null
  tokens.value = null
  localStorage.removeItem(AUTH_STORAGE_KEY)
}

function updateTokens(nextTokens: TokenResponse): void {
  if (!user.value) {
    tokens.value = nextTokens
    return
  }

  persistAuth({
    user: user.value,
    tokens: nextTokens,
  })
}

async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await api<AuthResponse>('/auth/register', {
    method: 'POST',
    body: data,
  })

  persistAuth(response)
  return response
}

async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await api<AuthResponse>('/auth/login', {
    method: 'POST',
    body: data,
  })

  persistAuth(response)
  return response
}

let refreshPromise: Promise<TokenResponse> | null = null

async function refreshToken(
  refreshTokenValue = tokens.value?.refresh_token,
): Promise<TokenResponse> {
  if (!refreshTokenValue) {
    throw new Error('Aucun refresh token disponible.')
  }

  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = api<TokenResponse>('/auth/refresh', {
    method: 'POST',
    body: {
      refresh_token: refreshTokenValue,
    },
  })
    .then((response) => {
      updateTokens(response)
      return response
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

async function logout(): Promise<MessageResponse | undefined> {
  const refreshTokenValue = tokens.value?.refresh_token

  if (!refreshTokenValue) {
    clearAuth()
    return undefined
  }

  try {
    return await api<MessageResponse>('/auth/logout', {
      method: 'POST',
      body: {
        refresh_token: refreshTokenValue,
      },
    })
  } finally {
    clearAuth()
  }
}

async function fetchWithAuth<T>(
  url: string,
  options?: FetchOptions<'json'>,
): Promise<T> {
  const token = tokens.value?.access_token
  if (!token) {
    throw new Error('Vous devez être connecté.')
  }

  const headers = {
    ...(options?.headers as Record<string, string>),
    Authorization: `Bearer ${token}`,
  }

  try {
    return await api<T>(url, {
      ...options,
      headers,
    })
  } catch (error) {
    const is401 =
      typeof error === 'object' &&
      error !== null &&
      'status' in error &&
      error.status === 401

    if (is401 && tokens.value?.refresh_token) {
      try {
        const nextTokens = await refreshToken()
        return await api<T>(url, {
          ...options,
          headers: {
            ...(options?.headers as Record<string, string>),
            Authorization: `Bearer ${nextTokens.access_token}`,
          },
        })
      } catch {
        clearAuth()
        throw new Error('Votre session a expiré. Veuillez vous reconnecter.')
      }
    }

    if (is401) {
      clearAuth()
      throw new Error('Votre session a expiré. Veuillez vous reconnecter.')
    }

    throw error
  }
}

async function fetchMyMemberships(): Promise<UserMembership[]> {
  const token = tokens.value?.access_token
  if (!token) return []

  try {
    return await fetchWithAuth<UserMembership[]>('/auth/me/memberships')
  } catch {
    return []
  }
}

export function useAuth() {
  return {
    user,
    tokens,
    accessToken: computed(() => tokens.value?.access_token ?? null),
    isAuthenticated: computed(() => Boolean(tokens.value?.access_token)),
    register,
    login,
    refreshToken,
    logout,
    fetchWithAuth,
    fetchMyMemberships,
  }
}
