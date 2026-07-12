import { useEffect, useState } from 'react'
import { api } from '../api'
import Toast from '../components/Toast'

export default function Logs() {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 50 })
  const [filters, setFilters] = useState({ operator: '', action: '', keyword: '', date_from: '', date_to: '' })
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const showToast = msg => { setToast({ msg, type: 'error' }); setTimeout(() => setToast(null), 2500) }
  const load = async (page = 1) => { setLoading(true); try { setData(await api.listLogs({ ...filters, date_to: filters.date_to ? filters.date_to + 'T23:59:59' : '', page, page_size: 50 })) } catch (e) { showToast('加载失败: ' + e.message) } finally { setLoading(false) } }
  useEffect(() => { load(1) }, [])
  const fmt = s => s ? new Date(s).toLocaleString('zh-CN') : '-'
  const pages = Math.max(1, Math.ceil(data.total / data.page_size))
  return <div className="logs-page">
    <div className="toolbar log-filters">
      <input placeholder="操作人" value={filters.operator} onChange={e => setFilters(f => ({ ...f, operator: e.target.value }))} />
      <select value={filters.action} onChange={e => setFilters(f => ({ ...f, action: e.target.value }))}><option value="">全部操作</option>{['入库','借出','归还','送修','转移','资料编辑','盘点','归档','恢复'].map(x => <option key={x}>{x}</option>)}</select>
      <input placeholder="位置/备注关键词" value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} />
      <input aria-label="开始日期" type="date" value={filters.date_from} onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} />
      <input aria-label="结束日期" type="date" value={filters.date_to} onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} />
      <button onClick={() => load(1)}>筛选</button><button className="ghost" onClick={() => api.exportLogs().catch(e => showToast(e.message))}>导出 CSV</button>
    </div>
    {loading ? <div className="loading">加载中…</div> : data.items.length === 0 ? <div className="empty"><div className="icon">📋</div><div>暂无操作记录</div></div> : data.items.map(l => <div key={l.id} className="log-item">
      <div className="top"><span>设备ID: #{l.robot_id}</span><span>{fmt(l.created_at)}</span></div>
      <div><span className="action">[{l.action}]</span> 操作人: {l.operator}</div>
      <div className="log-detail">{l.before_status || '-'} → <b>{l.after_status}</b>{l.after_location && ` | 去向: ${l.after_location}`}{l.note && ` | 备注: ${l.note}`}</div>
    </div>)}
    <div className="pagination"><button disabled={data.page <= 1} onClick={() => load(data.page - 1)}>上一页</button><span>第 {data.page} / {pages} 页，共 {data.total} 条</span><button disabled={data.page >= pages} onClick={() => load(data.page + 1)}>下一页</button></div>
    {toast && <Toast message={toast.msg} type={toast.type} />}
  </div>
}
