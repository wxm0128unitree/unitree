import { useState } from 'react'

export default function EditRobotModal({ robot, onClose, onSubmit }) {
  const [form, setForm] = useState({
    asset_code: robot.asset_code, model: robot.model,
    owner_department: robot.owner_department || '', owner_name: robot.owner_name || robot.holder || '',
    location: robot.location || '', remark: robot.remark || '',
  })
  const set = (key, value) => setForm(f => ({ ...f, [key]: value }))
  return <div className="modal-mask" onClick={onClose}><div className="modal modal-wide" onClick={e => e.stopPropagation()}>
    <h3>编辑设备资料 - [{robot.asset_code}]</h3>
    <div className="form-grid">
      <div className="field"><label>资产编号 *</label><input value={form.asset_code} onChange={e => set('asset_code', e.target.value)} /></div>
      <div className="field"><label>型号 *</label><input value={form.model} onChange={e => set('model', e.target.value)} /></div>
      <div className="field"><label>归属部门</label><input value={form.owner_department} onChange={e => set('owner_department', e.target.value)} /></div>
      <div className="field"><label>资产负责人</label><input value={form.owner_name} onChange={e => set('owner_name', e.target.value)} /></div>
      <div className="field"><label>当前位置</label><input value={form.location} onChange={e => set('location', e.target.value)} /></div>
      <div className="field"><label>备注</label><input value={form.remark} onChange={e => set('remark', e.target.value)} /></div>
    </div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={() => onSubmit(form)}>保存</button></div>
  </div></div>
}
