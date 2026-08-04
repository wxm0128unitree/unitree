import { useEffect, useState } from 'react'
import { api } from '../api'
import RobotCard from '../components/RobotCard'
import StatusModal from '../components/StatusModal'
import AddRobotModal from '../components/AddRobotModal'
import FilterSelect from '../components/FilterSelect'
import Toast from '../components/Toast'
import EditRobotModal from '../components/EditRobotModal'
import InventoryModal from '../components/InventoryModal'
import MigrationModal from '../components/MigrationModal'
import Inventory from './Inventory'

export default function Dashboard({ user }) {
  const [view, setView] = useState('overview')
  const [robots, setRobots] = useState([])
  const [stats, setStats] = useState({ total: 0, in_stock: 0, borrowed: 0, in_repair: 0 })
  const [inventoryStats, setInventoryStats] = useState({ total: 0, available: 0, loaned: 0, categories: {} })
  const [inventoryCategory, setInventoryCategory] = useState(null)
  const [holders, setHolders] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ model: '全部', status: '全部', holder: '全部', keyword: '' })
  const [activeRobot, setActiveRobot] = useState(null)
  const [editingRobot, setEditingRobot] = useState(null)
  const [inventoryRobot, setInventoryRobot] = useState(null)
  const [migratingRobot, setMigratingRobot] = useState(null)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 2000)
  }

  const load = async () => {
    setLoading(true)
    try {
      const [list, st, inv, holderList] = await Promise.all([
        api.listRobots({ ...filters, include_archived: includeArchived ? 'true' : '' }),
        api.getStats(),
        api.getInventoryStats(),
        api.listHolders(),
      ])
      setRobots(list)
      setStats(st)
      setInventoryStats(inv)
      setHolders(holderList)
    } catch (e) {
      showToast('加载失败: ' + e.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filters.model, filters.status, includeArchived])

  const handleSearch = () => load()

  const handleUpdate = async (payload) => {
    try {
      await api.updateStatus(activeRobot.id, payload)
      showToast('状态已更新')
      setActiveRobot(null)
      load()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleAdd = async (payload) => {
    try {
      await api.createRobot(payload)
      showToast('设备已添加')
      setShowAdd(false)
      load()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleDelete = async (robot) => {
    if (!confirm(`确认归档设备 ${robot.asset_code}？设备和全部日志都会保留，可由管理员恢复。`)) return
    try {
      await api.deleteRobot(robot.id)
      showToast('设备已归档')
      load()
    } catch (e) {
      showToast(e.message, 'error')
    }
  }

  const handleEdit = async payload => {
    try { await api.editRobot(editingRobot.id, payload); setEditingRobot(null); showToast('设备资料已更新'); load() }
    catch (e) { showToast(e.message, 'error') }
  }
  const handleInventory = async payload => {
    try { await api.inventoryRobot(inventoryRobot.id, payload); setInventoryRobot(null); showToast('盘点已记录'); load() }
    catch (e) { showToast(e.message, 'error') }
  }
  const handleRestore = async robot => {
    try { await api.restoreRobot(robot.id); showToast('设备已恢复'); load() }
    catch (e) { showToast(e.message, 'error') }
  }
  const handleMigrate = async payload => {
    try { await api.migrateRobot(migratingRobot.id, payload); setMigratingRobot(null); showToast('设备已迁出本部门'); load() }
    catch (e) { showToast(e.message, 'error') }
  }
  const handleUndoMigration = async robot => {
    try { await api.undoRobotMigration(robot.id); showToast('迁移已撤销'); load() } catch(e) { showToast(e.message,'error') }
  }

  // 从已有数据中动态提取所有出现过的型号 / 状态 / 持有人
  const allModels = Array.from(new Set(robots.map(r => r.model).filter(Boolean)))
  const allStatuses = Array.from(new Set(robots.map(r => r.status).filter(Boolean)))
  const preferredModels = ['G1', 'R1', 'Go2', 'A2']
  const modelsWithAssets = Object.entries(stats.by_model || {})
    .filter(([, value]) => value.total > 0)
    .map(([model]) => model)
    .sort((a, b) => {
      const ai = preferredModels.indexOf(a), bi = preferredModels.indexOf(b)
      if (ai === -1 && bi === -1) return a.localeCompare(b, 'zh-CN')
      if (ai === -1) return 1
      if (bi === -1) return -1
      return ai - bi
    })
  const preferredCategories = ['Pico','夹爪','三指灵巧手','电池','遥控器','拓展坞']
  const categoriesWithAssets = Object.keys(inventoryStats.categories || {})
    .filter(name => (inventoryStats.categories[name]?.total || 0) > 0)
    .sort((a,b)=>{
      const ai=preferredCategories.indexOf(a), bi=preferredCategories.indexOf(b)
      if(ai===-1&&bi===-1)return a.localeCompare(b,'zh-CN')
      if(ai===-1)return 1
      if(bi===-1)return -1
      return ai-bi
    })
  const modelTone = { G1: 'blue', R1: 'indigo', Go2: 'cyan', A2: 'slate' }
  const openInventoryCategory = category => {
    setInventoryCategory(category)
    setView('inventory')
  }

  return (
    <div>
      <div className="dashboard-switch" role="tablist">
        <button className={view==='overview'?'active':''} onClick={()=>setView('overview')}>总览</button>
        <button className={view==='robots'?'active':''} onClick={()=>setView('robots')}>设备管理</button>
        <button className={view==='inventory'?'active':''} onClick={()=>{setInventoryCategory(null);setView('inventory')}}>配件库存</button>
      </div>
      {view === 'overview' && <div className="overview-page">
        <div className="hero-summary"><div><span className="eyebrow">DEPARTMENT ASSETS</span><h2>部门资产一览</h2><p>机器人、实训台与配件库存集中管理，关键状态一目了然。</p></div><div className="hero-total"><span>当前资产总量</span><div><b>{stats.total + inventoryStats.total}</b><em>件</em></div><small>仅统计本部门在管资产</small></div></div>
        <div className="section-heading compact"><div><h2>机器人设备</h2><p>机器人与实训台统一按设备型号管理。</p></div><button className="text-btn" onClick={()=>setView('robots')}>查看全部 →</button></div>
        <div className="asset-stat-grid">{modelsWithAssets.map(model=>{const s=stats.by_model[model];return <button className={`asset-stat tone-${modelTone[model]||'blue'}`} key={model} onClick={()=>{setFilters(f=>({...f,model}));setView('robots')}}><span className="asset-accent"/><span className="asset-stat-top"><span className="asset-model-badge">{model}</span><span className="asset-kind">设备型号</span></span><span className="asset-stat-value"><b>{s.total}</b><em>台</em></span><span className="asset-status-line"><i className="dot stock"/>在库 {s.in_stock}<i className="dot loan"/>借出 {s.borrowed}<i className="dot repair"/>维修 {s.in_repair}</span></button>})}
          </div>
        <div className="section-heading compact"><div><h2>配件库存</h2><p>大数字为部门当前总量。</p></div><button className="text-btn" onClick={()=>setView('inventory')}>管理库存 →</button></div>
        <div className="category-stat-grid">{categoriesWithAssets.map(name=>{const icons={Pico:'🥽',夹爪:'🤏',三指灵巧手:'🖐️',电池:'🔋',遥控器:'🎮',拓展坞:'🔌'};const s=inventoryStats.categories[name];return <button key={name} className="category-stat" onClick={()=>openInventoryCategory(name)}><span className="asset-icon">{icons[name]||'📦'}</span><span>{name}</span><b>{s.total}</b><small>库存 {s.available} · 借出 {s.loaned}</small></button>})}</div>
      </div>}
      {view === 'inventory' && <Inventory key={inventoryCategory||'all'} category={inventoryCategory} onBack={()=>{setInventoryCategory(null);setView('overview')}} onStats={setInventoryStats} user={user} holders={holders} />}
      {view === 'robots' && <>
      {/* 统计卡片 */}
      <div className="stats">
        <div className="stat-card total">
          <span className="stat-icon">∑</span><div><span className="num">{stats.total}</span><div className="label">设备总数</div></div>
        </div>
        <div className="stat-card in-stock">
          <span className="stat-icon">✓</span><div><span className="num">{stats.in_stock}</span><div className="label">当前在库</div></div>
        </div>
        <div className="stat-card borrowed">
          <span className="stat-icon">↗</span><div><span className="num">{stats.borrowed}</span><div className="label">当前借出</div></div>
        </div>
        <div className="stat-card in-repair">
          <span className="stat-icon">!</span><div><span className="num">{stats.in_repair}</span><div className="label">维修处理中</div></div>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="toolbar">
        <FilterSelect
          label="型号"
          value={filters.model}
          onChange={v => setFilters(f => ({ ...f, model: v }))}
          options={allModels}
          storageKey="customModels"
          placeholder="新型号，如 B2 / H1"
        />
        <FilterSelect
          label="状态"
          value={filters.status}
          onChange={v => setFilters(f => ({ ...f, status: v }))}
          options={allStatuses}
        />
        <input className="search" list="holder-options" placeholder="持有人姓名 / 账号 / 部门"
          value={filters.holder === '全部' ? '' : filters.holder}
          onChange={e => setFilters(f => ({ ...f, holder: e.target.value || '全部' }))} />
        <datalist id="holder-options">{holders.map(h=><option key={h.phone||h.name} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist>
        <input
          className="search"
          placeholder="搜索资产编号 / 去向"
          value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
        />
        <button onClick={handleSearch}>搜索</button>
        <button className="ghost" onClick={() => setShowAdd(true)}>+ 新增设备</button>
        <button className="ghost" onClick={() => api.exportRobots().catch(e => showToast(e.message, 'error'))}>导出 CSV</button>
        {user.is_admin === 1 && <label className="archive-toggle"><input type="checkbox" checked={includeArchived} onChange={e => setIncludeArchived(e.target.checked)} /> 显示迁移/归档</label>}
      </div>

      {/* 设备列表 */}
      {loading ? (
        <div className="loading">加载中…</div>
      ) : robots.length === 0 ? (
        <div className="empty">
          <div className="icon">📦</div>
          <div>暂无设备数据</div>
          <button style={{ marginTop: 16 }} onClick={() => setShowAdd(true)}>+ 添加第一台设备</button>
        </div>
      ) : (
        <div className="list">
          {robots.map(r => (
            <RobotCard
              key={r.id}
              robot={r}
              onClick={() => setActiveRobot(r)}
              onDelete={() => handleDelete(r)}
              onEdit={() => setEditingRobot(r)}
              onInventory={() => setInventoryRobot(r)}
              onRestore={() => handleRestore(r)}
              onMigrate={() => setMigratingRobot(r)}
              onUndoMigration={() => handleUndoMigration(r)}
              isAdmin={user.is_admin === 1}
            />
          ))}
        </div>
      )}

      {activeRobot && (
        <StatusModal
          robot={activeRobot}
          onClose={() => setActiveRobot(null)}
          onSubmit={handleUpdate}
        />
      )}

      {showAdd && (
        <AddRobotModal
          onClose={() => setShowAdd(false)}
          onSubmit={handleAdd}
          knownModels={allModels}
          holders={holders}
          user={user}
        />
      )}
      {editingRobot && <EditRobotModal robot={editingRobot} isAdmin={user.is_admin===1} holders={holders} onClose={() => setEditingRobot(null)} onSubmit={handleEdit} />}
      {inventoryRobot && <InventoryModal robot={inventoryRobot} onClose={() => setInventoryRobot(null)} onSubmit={handleInventory} />}
      {migratingRobot && <MigrationModal robot={migratingRobot} onClose={() => setMigratingRobot(null)} onSubmit={handleMigrate} />}
      </>}

      {toast && <Toast message={toast.msg} type={toast.type} />}
    </div>
  )
}
