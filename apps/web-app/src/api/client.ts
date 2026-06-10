import type {
  RecipeCreate,
  RecipeResponse,
  RecipeSummary,
  RecipeUpdate,
  TagResponse,
  TokenResponse,
  UserResponse,
} from './types'

const BASE = '/api/v1'
const TOKEN_KEY = 'pantry.token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw Object.assign(new Error(err), { status: res.status })
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function devLogin(email: string, display_name = 'Dev User'): Promise<TokenResponse> {
  return apiFetch<TokenResponse>('/auth/dev', {
    method: 'POST',
    body: JSON.stringify({ email, display_name }),
  })
}

export async function getMe(): Promise<UserResponse> {
  return apiFetch<UserResponse>('/users/me')
}

export async function getRecipes(params?: Record<string, string | string[]>): Promise<RecipeSummary[]> {
  const qs = params ? '?' + buildQuery(params) : ''
  return apiFetch<RecipeSummary[]>(`/recipes/${qs}`)
}

export async function getRecipe(id: string): Promise<RecipeResponse> {
  return apiFetch<RecipeResponse>(`/recipes/${id}`)
}

export async function createRecipe(body: RecipeCreate): Promise<RecipeResponse> {
  return apiFetch<RecipeResponse>('/recipes/', { method: 'POST', body: JSON.stringify(body) })
}

export async function updateRecipe(id: string, body: RecipeUpdate): Promise<RecipeResponse> {
  return apiFetch<RecipeResponse>(`/recipes/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
}

export async function deleteRecipe(id: string): Promise<void> {
  return apiFetch<void>(`/recipes/${id}`, { method: 'DELETE' })
}

export async function getTags(): Promise<TagResponse[]> {
  return apiFetch<TagResponse[]>('/tags/')
}

export async function createTag(name: string): Promise<TagResponse> {
  return apiFetch<TagResponse>('/tags/', { method: 'POST', body: JSON.stringify({ name }) })
}

function buildQuery(params: Record<string, string | string[]>): string {
  const parts: string[] = []
  for (const [key, val] of Object.entries(params)) {
    if (Array.isArray(val)) {
      val.forEach(v => parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(v)}`))
    } else if (val !== '' && val !== undefined) {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(val)}`)
    }
  }
  return parts.join('&')
}
