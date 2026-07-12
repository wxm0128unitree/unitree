import { useState } from 'react'
import { api, setAuth } from '../api'

export default function Login({ onSuccess, onSwitchToRegister }) {
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    if (!phone.trim() || !password) {
      setErr('请输入手机号和密码')
      return
    }
    setLoading(true)
    try {
      const data = await api.login(phone.trim(), password)
      setAuth(data.access_token, data.user)
      onSuccess(data.user)
    } catch (ex) {
      setErr(ex.message || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">🤖</div>
        <h2 className="auth-title">宇树机器人出入库管理</h2>
        <div className="auth-sub">登录后开始管理设备</div>

        <form onSubmit={submit} className="auth-form">
          <div className="auth-field">
            <label>手机号</label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="11 位手机号"
              autoFocus
              maxLength={11}
              autoComplete="username"
            />
          </div>
          <div className="auth-field">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="请输入密码"
              autoComplete="current-password"
            />
          </div>

          {err && <div className="auth-err">{err}</div>}

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? '登录中…' : '登录'}
          </button>

          <div className="auth-footer">
            还没有账号？
            <button type="button" className="link-button" onClick={onSwitchToRegister}>立即注册</button>
          </div>
        </form>
      </div>
    </div>
  )
}
