import { useState, useEffect } from 'react'

const DEFAULT_MODELS = ['G1', 'R1', 'Go2', 'A2', '实训台', '其他']

export default function AddRobotModal({ onClose, onSubmit, knownModels = [], holders = [], user }) {
  const [assetCode, setAssetCode] = useState('')
  const robotModels = knownModels.filter(Boolean)
  const [model, setModel] = useState(robotModels[0] || 'G1')
  const [deviceType, setDeviceType] = useState('standard_robot')
  const [ownerDepartment, setOwnerDepartment] = useState('')
  const [ownerName, setOwnerName] = useState(user?.is_admin === 1 ? '' : user?.name || '')
  const [holder, setHolder] = useState(user?.name || '')
  const status = '在库'
  const [location, setLocation] = useState('')

  // 用户自定义的型号（持久化）
  const [customModels, setCustomModels] = useState(() => {
    try { return JSON.parse(localStorage.getItem('customModelsList') || '[]') }
    catch { return [] }
  })
  const [addingModel, setAddingModel] = useState(false)
  const [newModel, setNewModel] = useState('')

  useEffect(() => {
    localStorage.setItem('customModelsList', JSON.stringify(customModels))
  }, [customModels])

  const allModels = Array.from(new Set([...DEFAULT_MODELS, ...knownModels, ...customModels]))

  const addNewModel = () => {
    const v = newModel.trim()
    if (!v) return
    if (!allModels.includes(v)) {
      setCustomModels(prev => [...prev, v])
    }
    setModel(v)
    setNewModel('')
    setAddingModel(false)
  }

  const submit = () => {
    if (!assetCode.trim()) {
      alert('请填写资产编号')
      return
    }
    if(!ownerName.trim()||!holder.trim()){alert('负责人和持有人不能为空');return}
    onSubmit({
      asset_code: assetCode.trim(),
      model: deviceType === 'training_platform' ? '实训台' : model,
      device_branch: deviceType,
      platform_type: '',
      holder: holder.trim(),
      owner_department: ownerDepartment.trim(),
      owner_name: ownerName.trim(),
      borrower: status === '借出' ? holder.trim() : '',
      status,
      location: location.trim(),
    })
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>新增设备</h3>
        <div className="field">
          <label>资产编号 *</label>
          <input
            type="text"
            value={assetCode}
            onChange={e => setAssetCode(e.target.value)}
            placeholder="如：R-2024-G1-001"
            autoFocus
          />
        </div>

        <div className="field">
          <label>设备类型</label>
          <select value={deviceType} onChange={e=>setDeviceType(e.target.value)}><option value="standard_robot">机器人</option><option value="training_platform">实训台</option></select>
        </div>

        {deviceType === 'standard_robot' && <div className="field">
          <label>型号</label>
          <select value={model} onChange={e => setModel(e.target.value)} style={{
            width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 8
          }}>
            {allModels.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          {addingModel ? (
            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <input
                type="text"
                autoFocus
                value={newModel}
                onChange={e => setNewModel(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') addNewModel()
                  if (e.key === 'Escape') { setAddingModel(false); setNewModel('') }
                }}
                placeholder="新型号名，回车确认"
              />
              <button type="button" onClick={addNewModel} style={{ padding: '0 14px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}>确定</button>
              <button type="button" onClick={() => { setAddingModel(false); setNewModel('') }} style={{ padding: '0 14px', background: '#f5f5f5', border: 'none', borderRadius: 8, cursor: 'pointer' }}>取消</button>
            </div>
          ) : (
            <button type="button" onClick={() => setAddingModel(true)} style={{
              marginTop: 6, padding: '6px 12px', background: 'transparent',
              color: '#1677ff', border: '1px dashed #1677ff', borderRadius: 6, cursor: 'pointer', fontSize: 13
            }}>+ 新增型号</button>
          )}
        </div>}

        <div className="field">
          <label>资产归属部门</label>
          <input
            type="text"
            value={ownerDepartment}
            onChange={e => setOwnerDepartment(e.target.value)}
            placeholder="如：研发部"
          />
        </div>
        <div className="field">
          <label>资产负责人</label>
          <input type="text" list="add-holder-options" disabled={user?.is_admin!==1} value={ownerName} onChange={e => setOwnerName(e.target.value)} placeholder="如：张三" />
          <datalist id="add-holder-options">{holders.filter(h=>h.phone).map(h=><option key={h.phone} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist>
        </div>
        <div className="field"><label>当前持有人 *</label><input list="add-current-holder-options" value={holder} onChange={e=>setHolder(e.target.value)} placeholder="当前实际保管设备的人"/><datalist id="add-current-holder-options">{holders.map(h=><option key={h.phone||h.name} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist></div>

        <div className="field"><label>初始状态</label><input disabled value="在库" /><div className="hint">新增设备先完成入库，之后再办理借出或送修。</div></div>

        <div className="field">
          <label>入库存放位置（可选）</label>
          <input
            type="text"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="如：一号仓 A-03 货架"
          />
        </div>

        <div className="actions">
          <button className="cancel" onClick={onClose}>取消</button>
          <button className="primary" onClick={submit}>确定</button>
        </div>
      </div>
    </div>
  )
}
