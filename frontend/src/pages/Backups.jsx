import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Backups() {
  const [groups, setGroups] = useState({ daily: [], weekly: [], manual: [] })
  const [message, setMessage] = useState('')
  const load = () => api.listBackups().then(setGroups).catch(e => setMessage(e.message))
  useEffect(load, [])
  const run = async () => { try { await api.runBackup(); setMessage('备份已创建'); load() } catch (e) { setMessage(e.message) } }
  const restore = async (kind, name) => {
    if (!confirm(`确认从 ${name} 恢复数据库？系统会先自动创建安全备份。`)) return
    const typed = prompt('高风险操作：请输入 RESTORE 确认')
    if (typed !== 'RESTORE') return
    try { const r = await api.restoreBackup(kind, name); setMessage(r.message); load() } catch (e) { setMessage(e.message) }
  }
  return <div className="admin-page"><section className="panel"><div className="panel-title"><div><h2>备份与恢复</h2><p>恢复前会校验备份并自动保存当前数据库。Render 重新部署可能清空临时文件，请及时下载备份。</p></div><button onClick={run}>立即备份</button></div>
    {message && <p className="notice">{message}</p>}
    {Object.entries(groups).map(([kind, files]) => <div key={kind}><h3>{({ daily: '每日', weekly: '每周', manual: '手动' })[kind]}备份</h3>
      {files.length === 0 ? <p className="muted">暂无备份</p> : <div className="backup-list">{files.map(f => <div key={f.name}><span>{f.name}（{Math.ceil(f.size / 1024)} KB）</span><span className="row-actions"><button onClick={() => api.downloadBackup(kind, f.name).catch(e => setMessage(e.message))}>下载</button><button className="danger-text" onClick={() => restore(kind, f.name)}>恢复</button></span></div>)}</div>}
    </div>)}</section></div>
}
