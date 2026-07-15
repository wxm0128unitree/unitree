import { useState } from 'react'
import { api, setAuth } from '../api'

export default function Register({ onSuccess, onSwitchToLogin }) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setErr('')
    if (!name.trim()) { setErr('请输入真实姓名'); return }
    if (!/^1[3-9]\d{9}$/.test(phone)) { setErr('手机号格式不正确'); return }
    if (password.length < 6) { setErr('密码至少 6 位'); return }
    if (password !== confirm) { setErr('两次密码不一致'); return }

    setLoading(true)
    try {
      const data = await api.register(name.trim(), phone.trim(), password)
      setAuth(data.access_token, data.user)
      onSuccess(data.user)
    } catch (ex) {
      setErr(ex.message || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo"><span>UT</span></div>
        <div className="auth-eyebrow">INTERNAL ASSET CENTER</div>
        <h2 className="auth-title">注册新账号</h2>
        <div className="auth-sub">填写真实姓名以便追溯操作记录</div>

        <form onSubmit={submit} className="auth-form">
          <div className="auth-field">
            <label>真实姓名</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="如：张三"
              autoFocus
              maxLength={32}
              autoComplete="name"
            />
          </div>
          <div className="auth-field">
            <label>手机号（登录账号）</label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="11 位手机号"
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
              placeholder="至少 6 位"
              autoComplete="new-password"
            />
          </div>
          <div className="auth-field">
            <label>确认密码</label>
            <input
              type="password"
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              placeholder="再次输入"
              autoComplete="new-password"
            />
          </div>

          {err && <div className="auth-err">{err}</div>}

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? '注册中…' : '注册并登录'}
          </button>

          <div className="auth-footer">
            已有账号？
            <button type="button" className="link-button" onClick={onSwitchToLogin}>立即登录</button>
          </div>
        </form>
      </div>
    </div>
  )
}
