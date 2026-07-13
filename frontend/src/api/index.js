// API 基础封装：自动从 localStorage 注入 token，401 自动跳登录
// 生产环境会被 Vite 替换为绝对 URL（见 .env.production）
// VITE_API_BASE 默认空字符串 = 同源访问（本地开发 / 单机部署）
const BASE = (import.meta.env.VITE_API_BASE || '') + '/api'

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function getStoredUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY)) }
  catch { return null }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

function notify401() {
  // 触发全局跳登录
  window.dispatchEvent(new Event('auth:logout'))
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const token = getToken()
  if (token) headers['Authorization'] = 'Bearer ' + token

  const res = await fetch(BASE + path, {
    ...options,
    headers,
  })

  if (res.status === 401) {
    notify401()
    let detail = '未登录'
    try { detail = (await res.json()).detail || detail } catch {}
    throw new Error(detail)
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const data = await res.json()
      msg = data.detail || msg
    } catch {}
    throw new Error(msg)
  }
  return res.json()
}

async function download(path, filename) {
  const token = getToken()
  const res = await fetch(BASE + path, { headers: token ? { Authorization: 'Bearer ' + token } : {} })
  if (res.status === 401) { notify401(); throw new Error('未登录') }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`)
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

export const api = {
  // ===== 认证 =====
  login: (phone, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ phone, password }) }),
  register: (name, phone, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ name, phone, password }) }),
  me: () => request('/auth/me'),

  // ===== 设备 =====
  listRobots: (params = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v && v !== '全部' && v !== '') q.set(k, v)
    })
    const qs = q.toString()
    return request(`/robots${qs ? '?' + qs : ''}`)
  },
  createRobot: (data) => request('/robots', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id, data) =>
    request(`/robots/${id}/status`, { method: 'POST', body: JSON.stringify(data) }),
  editRobot: (id, data) => request(`/robots/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  inventoryRobot: (id, data) => request(`/robots/${id}/inventory`, { method: 'POST', body: JSON.stringify(data) }),
  deleteRobot: (id) => request(`/robots/${id}`, { method: 'DELETE' }),
  restoreRobot: (id) => request(`/robots/${id}/restore`, { method: 'POST' }),
  migrateRobot: (id, data) => request(`/robots/${id}/migrate`, { method: 'POST', body: JSON.stringify(data) }),
  undoRobotMigration: (id) => request(`/robots/${id}/undo-migration`, { method: 'POST' }),
  getStats: () => request('/stats'),
  listInventory: (params = {}) => request(`/inventory/items?${new URLSearchParams(params)}`),
  createInventory: data => request('/inventory/items', { method: 'POST', body: JSON.stringify(data) }),
  inventoryAction: (id, data) => request(`/inventory/items/${id}/action`, { method: 'POST', body: JSON.stringify(data) }),
  getInventoryStats: () => request('/inventory/stats'),
  listInventoryTransactions: () => request('/inventory/transactions'),
  listLogs: (params = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v) })
    const qs = q.toString()
    return request(`/logs${qs ? '?' + qs : ''}`)
  },

  // ===== 用户管理 =====
  listUsers: () => request('/users'),
  createUser: (data) => request('/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  listBackups: () => request('/backup/list'),
  runBackup: () => request('/backup/run', { method: 'POST' }),
  restoreBackup: (kind, name) => request(`/backup/restore?${new URLSearchParams({ kind, name, confirm: 'RESTORE' })}`, { method: 'POST' }),
  downloadBackup: (kind, name) => download(`/backup/download?${new URLSearchParams({ kind, name })}`, name),
  exportRobots: () => download('/export/robots.csv', '设备清单.csv'),
  exportLogs: () => download('/export/logs.csv', '操作日志.csv'),
}
