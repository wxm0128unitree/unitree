import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import Login from './pages/Login'
import Register from './pages/Register'
import Toast from './components/Toast'
import { getToken, getStoredUser, clearAuth, api } from './api'

export default function App() {
  const [user, setUser] = useState(() => {
    const t = getToken()
    const u = getStoredUser()
    return t && u ? u : null
  })
  const [authMode, setAuthMode] = useState('login') // 'login' | 'register'
  const [tab, setTab] = useState('dashboard')
  const [bootstrapping, setBootstrapping] = useState(true)
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 2000)
  }

  // 启动时如果有 token 就验证一下有效性
  useEffect(() => {
    if (!getToken()) { setBootstrapping(false); return }
    api.me().then(u => {
      setUser(u)
      setBootstrapping(false)
    }).catch(() => {
      clearAuth()
      setUser(null)
      setBootstrapping(false)
    })
  }, [])

  // 监听全局 401 事件，踢回登录
  useEffect(() => {
    const handler = () => {
      clearAuth()
      setUser(null)
      setAuthMode('login')
      showToast('登录已过期，请重新登录', 'error')
    }
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [])

  if (bootstrapping) {
    return <div className="loading" style={{ marginTop: 80 }}>加载中…</div>
  }

  // 未登录：渲染登录/注册页
  if (!user) {
    return authMode === 'login' ? (
      <Login
        onSuccess={(u) => { setUser(u); showToast(`欢迎，${u.name}`) }}
        onSwitchToRegister={() => setAuthMode('register')}
      />
    ) : (
      <Register
        onSuccess={(u) => { setUser(u); showToast(`欢迎，${u.name}`) }}
        onSwitchToLogin={() => setAuthMode('login')}
      />
    )
  }

  // 已登录：渲染主界面
  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>🤖 宇树机器人出入库管理</h1>
        </div>
        <div className="header-user">
          <div className="user-info">
            <div className="user-name">
              {user.name}
              {user.is_admin === 1 && <span className="badge-admin">管理员</span>}
            </div>
            <div className="user-phone">{user.phone}</div>
          </div>
          <button className="logout-btn" onClick={() => {
            clearAuth()
            setUser(null)
            setAuthMode('login')
            showToast('已退出登录')
          }}>退出</button>
        </div>
      </header>

      <div className="tabs">
        <button className={tab === 'dashboard' ? 'active' : ''} onClick={() => setTab('dashboard')}>
          📊 设备看板
        </button>
        <button className={tab === 'logs' ? 'active' : ''} onClick={() => setTab('logs')}>
          📋 操作日志
        </button>
      </div>

      {tab === 'dashboard' && <Dashboard />}
      {tab === 'logs' && <Logs />}

      {toast && <Toast message={toast.msg} type={toast.type} />}
    </div>
  )
}
