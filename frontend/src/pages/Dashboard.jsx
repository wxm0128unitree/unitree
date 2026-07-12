import { useEffect, useState } from 'react'
import { api } from '../api'
import RobotCard from '../components/RobotCard'
import StatusModal from '../components/StatusModal'
import AddRobotModal from '../components/AddRobotModal'
import FilterSelect from '../components/FilterSelect'
import Toast from '../components/Toast'
import EditRobotModal from '../components/EditRobotModal'
import InventoryModal from '../components/InventoryModal'

export default function Dashboard({ user }) {
  const [robots, setRobots] = useState([])
  const [stats, setStats] = useState({ total: 0, in_stock: 0, borrowed: 0, in_repair: 0 })
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ model: '全部', status: '全部', holder: '全部', keyword: '' })
  const [activeRobot, setActiveRobot] = useState(null)
  const [editingRobot, setEditingRobot] = useState(null)
  const [inventoryRobot, setInventoryRobot] = useState(null)
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
      const [list, st] = await Promise.all([
        api.listRobots({ ...filters, include_archived: includeArchived ? 'true' : '' }),
        api.getStats(),
      ])
      setRobots(list)
      setStats(st)
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

  // 从已有数据中动态提取所有出现过的型号 / 状态 / 持有人
  const allModels = Array.from(new Set(robots.map(r => r.model).filter(Boolean)))
  const allStatuses = Array.from(new Set(robots.map(r => r.status).filter(Boolean)))
  const allHolders = Array.from(new Set(robots.map(r => r.holder).filter(Boolean))).sort()

  return (
    <div>
      {/* 统计卡片 */}
      <div className="stats">
        <div className="stat-card total">
          <span className="num">{stats.total}</span>
          <div className="label">设备总数</div>
        </div>
        <div className="stat-card in-stock">
          <span className="num">{stats.in_stock}</span>
          <div className="label">🟢 在库</div>
        </div>
        <div className="stat-card borrowed">
          <span className="num">{stats.borrowed}</span>
          <div className="label">🔵 借出</div>
        </div>
        <div className="stat-card in-repair">
          <span className="num">{stats.in_repair}</span>
          <div className="label">🟠 维修</div>
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
          storageKey="customStatuses"
          placeholder="新状态，如 已发货 / 待验收"
        />
        <FilterSelect
          label="持有人"
          value={filters.holder}
          onChange={v => setFilters(f => ({ ...f, holder: v }))}
          options={allHolders}
          placeholder="搜索/添加持有人"
        />
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
        {user.is_admin === 1 && <label className="archive-toggle"><input type="checkbox" checked={includeArchived} onChange={e => setIncludeArchived(e.target.checked)} /> 显示归档</label>}
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
        />
      )}
      {editingRobot && <EditRobotModal robot={editingRobot} onClose={() => setEditingRobot(null)} onSubmit={handleEdit} />}
      {inventoryRobot && <InventoryModal robot={inventoryRobot} onClose={() => setInventoryRobot(null)} onSubmit={handleInventory} />}

      {toast && <Toast message={toast.msg} type={toast.type} />}
    </div>
  )
}
