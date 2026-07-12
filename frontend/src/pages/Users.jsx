import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Users({ currentUser }) {
  const [users, setUsers] = useState([])
  const [form, setForm] = useState({ name: '', phone: '', password: '', is_admin: 0 })
  const [message, setMessage] = useState('')
  const load = () => api.listUsers().then(setUsers).catch(e => setMessage(e.message))
  useEffect(load, [])
  const create = async e => { e.preventDefault(); try { await api.createUser(form); setForm({ name: '', phone: '', password: '', is_admin: 0 }); setMessage('用户已创建'); load() } catch (err) { setMessage(err.message) } }
  const update = async (id, data) => { try { await api.updateUser(id, data); setMessage('用户已更新'); load() } catch (err) { setMessage(err.message) } }
  return <div className="admin-page">
    <section className="panel"><h2>创建内部用户</h2><form className="inline-form" onSubmit={create}>
      <input aria-label="姓名" placeholder="真实姓名" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
      <input aria-label="手机号" placeholder="11 位手机号" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} required />
      <input aria-label="初始密码" type="password" placeholder="初始密码（至少 6 位）" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
      <label><input type="checkbox" checked={form.is_admin === 1} onChange={e => setForm(f => ({ ...f, is_admin: e.target.checked ? 1 : 0 }))} /> 管理员</label>
      <button>创建</button>
    </form></section>
    {message && <p className="notice">{message}</p>}
    <section className="panel"><h2>用户管理</h2><div className="table-wrap"><table><thead><tr><th>姓名</th><th>手机号</th><th>权限</th><th>状态</th><th>最后登录</th><th>操作</th></tr></thead><tbody>
      {users.map(u => <tr key={u.id}><td>{u.name}</td><td>{u.phone}</td><td>{u.is_admin ? '管理员' : '普通用户'}</td><td>{u.is_active ? '启用' : '停用'}</td><td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString('zh-CN') : '从未'}</td><td className="row-actions">
        <button onClick={() => update(u.id, { is_admin: u.is_admin ? 0 : 1 })}>{u.is_admin ? '取消管理员' : '设为管理员'}</button>
        <button disabled={u.id === currentUser.id} onClick={() => update(u.id, { is_active: u.is_active ? 0 : 1 })}>{u.is_active ? '停用' : '启用'}</button>
        <button onClick={() => { const password = prompt('输入新密码（至少 6 位）'); if (password) update(u.id, { password }) }}>重置密码</button>
      </td></tr>)}
    </tbody></table></div></section>
  </div>
}
