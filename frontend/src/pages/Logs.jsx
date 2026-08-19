import { useEffect, useState } from 'react'
import { api } from '../api'
import Toast from '../components/Toast'
import { formatShanghaiDateTime } from '../utils/datetime'

const emptyFilters = { asset_code: '', operator: '', action: '', keyword: '', date_from: '', date_to: '' }
const actionNames = ['入库', '借出', '归还', '送修', '修好入库', '转移', '状态变更', '资料编辑', '盘点', '归档', '恢复', '迁移', '撤销迁移']
const inventoryActionNames = { stock_in: '入库', borrow: '借出', return: '归还', migrate: '迁移', scrap: '报废' }

export default function Logs() {
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 50 })
  const [inventoryLogs, setInventoryLogs] = useState([])
  const [filters, setFilters] = useState(emptyFilters)
  const [activeDeviceCode, setActiveDeviceCode] = useState('')
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const showToast = msg => { setToast({ msg, type: 'error' }); setTimeout(() => setToast(null), 2500) }
  const requestFilters = source => ({ ...source, date_to: source.date_to ? source.date_to + 'T23:59:59' : '' })
  const load = async (page = 1, appliedFilters = filters) => {
    setLoading(true)
    const code = appliedFilters.asset_code.trim()
    try {
      const query = { ...requestFilters(appliedFilters), page, page_size: 50 }
      delete query.asset_code
      const [robotData, inventoryData] = await Promise.all([
        code ? api.getDeviceHistory(code, query) : api.listLogs(query),
        code ? Promise.resolve([]) : api.listInventoryTransactions(),
      ])
      setData(robotData)
      setInventoryLogs(inventoryData)
      setActiveDeviceCode(code)
    } catch (e) {
      setData({ items: [], total: 0, page: 1, page_size: 50 })
      setInventoryLogs([])
      setActiveDeviceCode(code)
      showToast('查询失败: ' + e.message)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load(1) }, [])
  const fmt = formatShanghaiDateTime
  const pages = Math.max(1, Math.ceil(data.total / data.page_size))
  const clearFilters = () => { setFilters(emptyFilters); setActiveDeviceCode(''); load(1, emptyFilters) }

  return <div className="logs-page">
    <div className="page-heading"><div><span className="eyebrow">ASSET TRACE</span><h2>设备全流程与操作审计</h2><p>先按设备编号定位资产，再核对何时、由谁、完成了什么操作。</p></div><span className="page-count">共 {data.total} 条设备记录</span></div>

    <section className="device-trace-panel" aria-labelledby="device-trace-title">
      <div className="device-trace-copy">
        <span className="eyebrow">设备主查询</span>
        <label id="device-trace-title" htmlFor="device-trace-code">设备编号</label>
        <p>输入资产标签上的完整编号，例如 GO2-12700，即可查看该设备从入库至今的全部流转记录。</p>
      </div>
      <div className="device-trace-controls">
        <input id="device-trace-code" aria-label="设备编号" placeholder="例如：GO2-12700" value={filters.asset_code} onChange={e => setFilters(f => ({ ...f, asset_code: e.target.value }))} onKeyDown={e => e.key === 'Enter' && load(1)} />
        <button className="primary-btn" onClick={() => load(1)}>查询设备全流程</button>
      </div>
    </section>

    <section className="log-filter-panel">
      <div className="log-filter-heading"><div><b>辅助筛选</b><span>在设备全流程中继续缩小范围，也可直接筛选全部日志。</span></div><button className="text-btn" onClick={clearFilters}>清空全部条件</button></div>
      <div className="toolbar log-filters">
        <label className="log-filter-field"><span>操作人</span><input placeholder="输入姓名" value={filters.operator} onChange={e => setFilters(f => ({ ...f, operator: e.target.value }))} /></label>
        <label className="log-filter-field"><span>操作类型</span><select value={filters.action} onChange={e => setFilters(f => ({ ...f, action: e.target.value }))}><option value="">全部操作</option>{actionNames.map(x => <option key={x}>{x}</option>)}</select></label>
        <label className="log-filter-field keyword"><span>位置或备注</span><input placeholder="输入关键词" value={filters.keyword} onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))} /></label>
        <label className="log-filter-field"><span>开始日期</span><input type="date" value={filters.date_from} onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} /></label>
        <label className="log-filter-field"><span>结束日期</span><input type="date" value={filters.date_to} onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} /></label>
        <div className="log-filter-actions"><button onClick={() => load(1)}>应用筛选</button><button className="ghost" onClick={() => api.exportLogs(requestFilters(filters)).catch(e => showToast(e.message))}>导出当前结果</button></div>
      </div>
    </section>

    {activeDeviceCode && <div className="filter-summary">当前设备：<b>{activeDeviceCode}</b><span>以下按时间倒序展示该设备的完整操作记录</span></div>}
    {loading ? <div className="loading">加载中…</div> : data.items.length === 0 ? <div className="empty"><div className="icon">📋</div><div>{activeDeviceCode ? `未找到设备 ${activeDeviceCode} 的操作记录` : '暂无操作记录'}</div></div> : data.items.map(l => <div key={l.id} className="log-item">
      <div className="top"><span className="log-device-name"><small>设备编号</small><b>{l.device_name || l.asset_code || '未编号设备'}</b></span><span>{fmt(l.created_at)}</span></div>
      <div><span className="action">{l.action}</span><span className="log-operator">操作人：<b>{l.operator}</b></span></div>
      <div className="log-detail"><span>状态：{l.before_status || '-'} → <b>{l.after_status || '-'}</b></span>{(l.before_location || l.after_location) && <span>位置：{l.before_location || '-'} → <b>{l.after_location || '-'}</b></span>}{l.note && <span>备注：{l.note}</span>}</div>
    </div>)}
    <div className="pagination"><button disabled={data.page <= 1} onClick={() => load(data.page - 1)}>上一页</button><span>第 {data.page} / {pages} 页，共 {data.total} 条</span><button disabled={data.page >= pages} onClick={() => load(data.page + 1)}>下一页</button></div>

    {!activeDeviceCode && inventoryLogs.length > 0 && <><div className="section-heading compact"><div><h2>配件库存流水</h2><p>按配件编号或“分类 · 型号”识别，不展示数据库内部 ID。</p></div></div>{inventoryLogs.map(l => <div key={`i-${l.id}`} className="log-item inventory-log"><div className="top"><span className="log-device-name"><small>{l.asset_code ? '配件编号' : '配件名称'}</small><b>{l.item_name || '未识别配件'}</b></span><span>{fmt(l.created_at)}</span></div><div><span className="action">{inventoryActionNames[l.action] || l.action}</span><span className="log-operator">操作人：<b>{l.operator}</b></span></div><div className="log-detail"><span>数量：{l.quantity} · 可用库存：{l.before_available} → <b>{l.after_available}</b></span>{l.destination_department && <span>接收部门：{l.destination_department}</span>}{l.note && <span>备注：{l.note}</span>}</div></div>)}</>}
    {toast && <Toast message={toast.msg} type={toast.type} />}
  </div>
}
