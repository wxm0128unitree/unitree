import { useState } from 'react'

export default function EditRobotModal({ robot, onClose, onSubmit, isAdmin = false, holders = [] }) {
  const [form, setForm] = useState({
    asset_code: robot.asset_code, model: robot.model,
    device_branch: robot.device_branch || (robot.model === '实训台' ? 'training_platform' : 'standard_robot'),
    owner_department: robot.owner_department || '', owner_name: robot.owner_name || '', holder: robot.holder || '',
    location: robot.location || '', remark: robot.remark || '',
  })
  const set = (key, value) => setForm(f => ({ ...f, [key]: value }))
  return <div className="modal-mask" onClick={onClose}><div className="modal modal-wide" onClick={e => e.stopPropagation()}>
    <h3>编辑设备资料 - [{robot.asset_code}]</h3>
    <div className="form-grid">
      <div className="field"><label>资产编号 *</label><input value={form.asset_code} onChange={e => set('asset_code', e.target.value)} /></div>
      <div className="field"><label>型号 *</label><input value={form.model} onChange={e => { set('model', e.target.value); set('device_branch', e.target.value === '实训台' ? 'training_platform' : 'standard_robot') }} /></div>
      <div className="field"><label>归属部门</label><input disabled={!isAdmin} value={form.owner_department} onChange={e => set('owner_department', e.target.value)} /></div>
      <div className="field"><label>资产负责人</label><input list="edit-owner-options" disabled={!isAdmin} value={form.owner_name} onChange={e => set('owner_name', e.target.value)} /><datalist id="edit-owner-options">{holders.filter(h=>h.phone).map(h=><option key={h.phone} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist></div>
      <div className="field"><label>当前持有人 *</label><input list="edit-holder-options" value={form.holder} onChange={e => set('holder', e.target.value)} /></div>
      <datalist id="edit-holder-options">{holders.map(h=><option key={h.phone||h.name} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist>
      <div className="field"><label>当前位置</label><input value={form.location} onChange={e => set('location', e.target.value)} /></div>
      <div className="field"><label>备注</label><input value={form.remark} onChange={e => set('remark', e.target.value)} /></div>
    </div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={() => onSubmit(form)}>保存</button></div>
  </div></div>
}
