import { useEffect, useState } from 'react'
import { api } from '../api'
import Toast from '../components/Toast'
import { formatShanghaiDateTime } from '../utils/datetime'

const emptyDeviceFilters = { asset_code: '', operator: '', action: '', keyword: '', date_from: '', date_to: '' }
const emptyInventoryFilters = { asset_code: '', operator: '', action: '', keyword: '', date_from: '', date_to: '' }
const deviceActions = ['入库', '借出', '归还', '送修', '修好入库', '转移', '状态变更', '资料编辑', '盘点', '归档', '恢复', '迁移', '撤销迁移']
const inventoryActionNames = { stock_in: '入库', borrow: '借出', return: '归还', repair: '送修', restore: '维修完成入库', migrate: '调出本部门', scrap: '数量减少', void: '作废记录' }

const withEndOfDay = source => ({ ...source, date_to: source.date_to ? source.date_to + 'T23:59:59' : '' })

export default function Logs() {
  const [deviceData, setDeviceData] = useState({ items: [], total: 0, page: 1, page_size: 50 })
  const [inventoryData, setInventoryData] = useState({ items: [], total: 0, page: 1, page_size: 50 })
  const [deviceFilters, setDeviceFilters] = useState(emptyDeviceFilters)
  const [inventoryFilters, setInventoryFilters] = useState(emptyInventoryFilters)
  const [activeDeviceCode, setActiveDeviceCode] = useState('')
  const [loadingDevice, setLoadingDevice] = useState(true)
  const [loadingInventory, setLoadingInventory] = useState(true)
  const [toast, setToast] = useState(null)
  const showError = msg => { setToast({ msg, type: 'error' }); setTimeout(() => setToast(null), 2500) }

  const loadDevices = async (page = 1, source = deviceFilters) => {
    setLoadingDevice(true)
    const code = source.asset_code.trim()
    try {
      const query = { ...withEndOfDay(source), page, page_size: 50 }
      delete query.asset_code
      setDeviceData(code ? await api.getDeviceHistory(code, query) : await api.listLogs(query))
      setActiveDeviceCode(code)
    } catch (e) {
      setDeviceData({ items: [], total: 0, page: 1, page_size: 50 }); setActiveDeviceCode(code); showError('设备日志查询失败: ' + e.message)
    } finally { setLoadingDevice(false) }
  }

  const loadInventory = async (page = 1, source = inventoryFilters) => {
    setLoadingInventory(true)
    try { setInventoryData(await api.listInventoryTransactions({ ...withEndOfDay(source), page, page_size: 50 })) }
    catch (e) { setInventoryData({ items: [], total: 0, page: 1, page_size: 50 }); showError('配件流水查询失败: ' + e.message) }
    finally { setLoadingInventory(false) }
  }

  useEffect(() => { loadDevices(1, emptyDeviceFilters); loadInventory(1, emptyInventoryFilters) }, [])
  const devicePages = Math.max(1, Math.ceil(deviceData.total / deviceData.page_size))
  const inventoryPages = Math.max(1, Math.ceil(inventoryData.total / inventoryData.page_size))

  return <div className="logs-page">
    <div className="page-heading"><div><span className="eyebrow">ASSET TRACE</span><h2>资产操作审计</h2><p>设备与配件分别查询、分页和导出，完整追溯每一次业务操作。</p></div><span className="page-count">设备 {deviceData.total} · 配件 {inventoryData.total}</span></div>

    <section className="device-trace-panel" aria-labelledby="device-trace-title"><div className="device-trace-copy"><span className="eyebrow">设备主查询</span><label id="device-trace-title" htmlFor="device-trace-code">设备编号</label><p>输入完整资产编号，查看该设备从入库至今的全部流转记录。</p></div><div className="device-trace-controls"><input id="device-trace-code" placeholder="例如：GO2-12700" value={deviceFilters.asset_code} onChange={e => setDeviceFilters(f => ({ ...f, asset_code: e.target.value }))} onKeyDown={e => e.key === 'Enter' && loadDevices(1)} /><button className="primary-btn" onClick={() => loadDevices(1)}>查询设备全流程</button></div></section>
    <section className="log-filter-panel"><div className="log-filter-heading"><div><b>设备日志筛选</b><span>按操作人、动作、日期、位置或备注缩小范围。</span></div><button className="text-btn" onClick={() => { setDeviceFilters(emptyDeviceFilters); setActiveDeviceCode(''); loadDevices(1, emptyDeviceFilters) }}>清空条件</button></div><div className="toolbar log-filters">
      <label className="log-filter-field"><span>操作人</span><input value={deviceFilters.operator} onChange={e => setDeviceFilters(f => ({ ...f, operator: e.target.value }))} /></label>
      <label className="log-filter-field"><span>操作类型</span><select value={deviceFilters.action} onChange={e => setDeviceFilters(f => ({ ...f, action: e.target.value }))}><option value="">全部操作</option>{deviceActions.map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="log-filter-field keyword"><span>位置或备注</span><input value={deviceFilters.keyword} onChange={e => setDeviceFilters(f => ({ ...f, keyword: e.target.value }))} /></label>
      <label className="log-filter-field"><span>开始日期</span><input type="date" value={deviceFilters.date_from} onChange={e => setDeviceFilters(f => ({ ...f, date_from: e.target.value }))} /></label>
      <label className="log-filter-field"><span>结束日期</span><input type="date" value={deviceFilters.date_to} onChange={e => setDeviceFilters(f => ({ ...f, date_to: e.target.value }))} /></label>
      <div className="log-filter-actions"><button onClick={() => loadDevices(1)}>应用筛选</button><button className="ghost" onClick={() => api.exportLogs(withEndOfDay(deviceFilters)).catch(e => showError(e.message))}>导出设备日志</button></div>
    </div></section>
    {activeDeviceCode && <div className="filter-summary">当前设备：<b>{activeDeviceCode}</b><span>以下为该设备完整操作记录</span></div>}
    {loadingDevice ? <div className="loading">加载设备日志…</div> : deviceData.items.length === 0 ? <div className="empty">暂无设备操作记录</div> : deviceData.items.map(row => <div key={row.id} className="log-item"><div className="top"><span className="log-device-name"><small>设备编号</small><b>{row.device_name || row.asset_code || '未编号设备'}</b></span><span>{formatShanghaiDateTime(row.created_at)}</span></div><div><span className="action">{row.action}</span><span className="log-operator">操作人：<b>{row.operator}</b></span></div><div className="log-detail"><span>状态：{row.before_status || '-'} → <b>{row.after_status || '-'}</b></span>{(row.before_location || row.after_location) && <span>位置：{row.before_location || '-'} → <b>{row.after_location || '-'}</b></span>}{row.note && <span>备注：{row.note}</span>}</div></div>)}
    <div className="pagination"><button disabled={deviceData.page <= 1} onClick={() => loadDevices(deviceData.page - 1)}>上一页</button><span>第 {deviceData.page} / {devicePages} 页，共 {deviceData.total} 条</span><button disabled={deviceData.page >= devicePages} onClick={() => loadDevices(deviceData.page + 1)}>下一页</button></div>

    <div className="section-heading compact"><div><h2>配件库存流水</h2><p>可独立按配件编号、操作人、动作和日期查询。</p></div></div>
    <section className="log-filter-panel"><div className="log-filter-heading"><div><b>配件流水筛选</b></div><button className="text-btn" onClick={() => { setInventoryFilters(emptyInventoryFilters); loadInventory(1, emptyInventoryFilters) }}>清空条件</button></div><div className="toolbar log-filters">
      <label className="log-filter-field"><span>配件编号</span><input value={inventoryFilters.asset_code} onChange={e => setInventoryFilters(f => ({ ...f, asset_code: e.target.value }))} /></label>
      <label className="log-filter-field"><span>操作人</span><input value={inventoryFilters.operator} onChange={e => setInventoryFilters(f => ({ ...f, operator: e.target.value }))} /></label>
      <label className="log-filter-field"><span>操作类型</span><select value={inventoryFilters.action} onChange={e => setInventoryFilters(f => ({ ...f, action: e.target.value }))}><option value="">全部操作</option>{Object.entries(inventoryActionNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label className="log-filter-field keyword"><span>借用人、用途或备注</span><input value={inventoryFilters.keyword} onChange={e => setInventoryFilters(f => ({ ...f, keyword: e.target.value }))} /></label>
      <label className="log-filter-field"><span>开始日期</span><input type="date" value={inventoryFilters.date_from} onChange={e => setInventoryFilters(f => ({ ...f, date_from: e.target.value }))} /></label>
      <label className="log-filter-field"><span>结束日期</span><input type="date" value={inventoryFilters.date_to} onChange={e => setInventoryFilters(f => ({ ...f, date_to: e.target.value }))} /></label>
      <div className="log-filter-actions"><button onClick={() => loadInventory(1)}>应用筛选</button><button className="ghost" onClick={() => api.exportInventoryLogs(withEndOfDay(inventoryFilters)).catch(e => showError(e.message))}>导出配件流水</button></div>
    </div></section>
    {loadingInventory ? <div className="loading">加载配件流水…</div> : inventoryData.items.length === 0 ? <div className="empty">暂无配件操作记录</div> : inventoryData.items.map(row => <div key={`i-${row.id}`} className="log-item inventory-log"><div className="top"><span className="log-device-name"><small>{row.asset_code ? '配件编号' : '配件名称'}</small><b>{row.item_name || '未识别配件'}</b></span><span>{formatShanghaiDateTime(row.created_at)}</span></div><div><span className="action">{inventoryActionNames[row.action] || row.action}</span><span className="log-operator">操作人：<b>{row.operator}</b></span></div><div className="log-detail"><span>数量：{row.quantity} · 总量：{row.before_total} → <b>{row.after_total}</b></span>{row.borrower && <span>借用人：{row.borrower}</span>}{row.purpose && <span>用途：{row.purpose}</span>}{row.expected_return_at && <span>预计归还：{formatShanghaiDateTime(row.expected_return_at)}</span>}{row.destination_department && <span>接收部门：{row.destination_department}</span>}{row.note && <span>备注：{row.note}</span>}</div></div>)}
    <div className="pagination"><button disabled={inventoryData.page <= 1} onClick={() => loadInventory(inventoryData.page - 1)}>上一页</button><span>第 {inventoryData.page} / {inventoryPages} 页，共 {inventoryData.total} 条</span><button disabled={inventoryData.page >= inventoryPages} onClick={() => loadInventory(inventoryData.page + 1)}>下一页</button></div>
    {toast && <Toast message={toast.msg} type={toast.type} />}
  </div>
}
