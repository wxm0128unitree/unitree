import { useState, useEffect } from 'react'

const DEFAULT_MODELS = ['G1', 'R1', 'Go2', 'A2', '其他']
const DEFAULT_STATUSES = ['在库', '借出', '维修中']

export default function AddRobotModal({ onClose, onSubmit, knownModels = [] }) {
  const [assetCode, setAssetCode] = useState('')
  const [model, setModel] = useState(knownModels[0] || 'G1')
  const [deviceBranch, setDeviceBranch] = useState('standard_robot')
  const [platformType, setPlatformType] = useState('humanoid')
  const [ownerDepartment, setOwnerDepartment] = useState('')
  const [ownerName, setOwnerName] = useState('')
  const [status, setStatus] = useState('在库')
  const [location, setLocation] = useState('')

  // 用户自定义的型号（持久化）
  const [customModels, setCustomModels] = useState(() => {
    try { return JSON.parse(localStorage.getItem('customModelsList') || '[]') }
    catch { return [] }
  })
  const [addingModel, setAddingModel] = useState(false)
  const [newModel, setNewModel] = useState('')

  // 自定义状态
  const [customStatuses, setCustomStatuses] = useState(() => {
    try { return JSON.parse(localStorage.getItem('customStatusesList') || '[]') }
    catch { return [] }
  })

  useEffect(() => {
    localStorage.setItem('customModelsList', JSON.stringify(customModels))
  }, [customModels])
  useEffect(() => {
    localStorage.setItem('customStatusesList', JSON.stringify(customStatuses))
  }, [customStatuses])

  const allModels = Array.from(new Set([...DEFAULT_MODELS, ...knownModels, ...customModels]))
  const allStatuses = Array.from(new Set([...DEFAULT_STATUSES, ...customStatuses]))

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
    onSubmit({
      asset_code: assetCode.trim(),
      model,
      device_branch: deviceBranch,
      platform_type: deviceBranch === 'training_platform' ? platformType : '',
      holder: ownerName.trim(),
      owner_department: ownerDepartment.trim(),
      owner_name: ownerName.trim(),
      status,
      location: location.trim(),
    })
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>新增设备</h3>
        <div className="field"><label>设备分支</label><div className="segmented"><button className={deviceBranch==='standard_robot'?'active':''} onClick={()=>setDeviceBranch('standard_robot')}>成品机器人</button><button className={deviceBranch==='training_platform'?'active':''} onClick={()=>setDeviceBranch('training_platform')}>实训台</button></div></div>

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
        </div>

        <div className="field">
          <label>资产归属部门</label>
          <input
            type="text"
            value={ownerDepartment}
            onChange={e => setOwnerDepartment(e.target.value)}
            placeholder="如：研发部"
          />
        </div>
        {deviceBranch === 'standard_robot' ? <div className="field">
          <label>资产负责人</label>
          <input type="text" value={ownerName} onChange={e => setOwnerName(e.target.value)} placeholder="如：张三" />
        </div> : <div className="field"><label>实训台类型</label><select value={platformType} onChange={e=>setPlatformType(e.target.value)} style={{width:'100%',padding:'10px 12px',border:'1px solid var(--border)',borderRadius:8}}><option value="humanoid">人形实训台</option><option value="quadruped">四足实训台</option></select></div>}

        <div className="field">
          <label>初始状态</label>
          <select value={status} onChange={e => setStatus(e.target.value)} style={{
            width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 8
          }}>
            {allStatuses.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="field">
          <label>初始去向（可选）</label>
          <input
            type="text"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="持有人/地点/故障描述"
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
