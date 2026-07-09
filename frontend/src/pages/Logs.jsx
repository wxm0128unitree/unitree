import { useEffect, useState } from 'react'
import { api } from '../api'
import Toast from '../components/Toast'

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'error') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 2000)
  }

  useEffect(() => {
    (async () => {
      try {
        const data = await api.listLogs({ limit: 500 })
        setLogs(data)
      } catch (e) {
        showToast('加载失败: ' + e.message)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const fmt = (s) => s ? new Date(s).toLocaleString('zh-CN') : '-'

  return (
    <div className="logs-page">
      {loading ? (
        <div className="loading">加载中…</div>
      ) : logs.length === 0 ? (
        <div className="empty">
          <div className="icon">📋</div>
          <div>暂无操作记录</div>
        </div>
      ) : (
        logs.map(l => (
          <div key={l.id} className="log-item">
            <div className="top">
              <span>设备ID: #{l.robot_id}</span>
              <span>{fmt(l.created_at)}</span>
            </div>
            <div>
              <span className="action">[{l.action}]</span>
              {' '}操作人: {l.operator}
            </div>
            <div style={{ marginTop: 4, color: '#6b7280', fontSize: 12 }}>
              {l.before_status || '-'} → <b>{l.after_status}</b>
              {l.after_location && ` | 去向: ${l.after_location}`}
              {l.note && ` | 备注: ${l.note}`}
            </div>
          </div>
        ))
      )}
      {toast && <Toast message={toast.msg} type={toast.type} />}
    </div>
  )
}