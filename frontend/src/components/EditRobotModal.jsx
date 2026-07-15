import { useState } from 'react'

export default function EditRobotModal({ robot, onClose, onSubmit }) {
  const [form, setForm] = useState({
    asset_code: robot.asset_code, model: robot.model,
    device_branch: robot.device_branch || 'standard_robot', platform_type: robot.platform_type || 'humanoid',
    owner_department: robot.owner_department || '', owner_name: robot.owner_name || robot.holder || '',
    location: robot.location || '', remark: robot.remark || '',
  })
  const set = (key, value) => setForm(f => ({ ...f, [key]: value }))
  return <div className="modal-mask" onClick={onClose}><div className="modal modal-wide" onClick={e => e.stopPropagation()}>
    <h3>编辑设备资料 - [{robot.asset_code}]</h3>
    <div className="form-grid">
      <div className="field"><label>资产编号 *</label><input value={form.asset_code} onChange={e => set('asset_code', e.target.value)} /></div>
      <div className="field"><label>设备分支</label><select value={form.device_branch} onChange={e => set('device_branch', e.target.value)}><option value="standard_robot">成品机器人</option><option value="training_platform">实训台</option></select></div>
      {form.device_branch === 'standard_robot'
        ? <div className="field"><label>型号 *</label><input value={form.model} onChange={e => set('model', e.target.value)} /></div>
        : <div className="field"><label>实训台类型 *</label><select value={form.platform_type} onChange={e => set('platform_type', e.target.value)}><option value="humanoid">人形实训台</option><option value="quadruped">四足实训台</option></select></div>}
      <div className="field"><label>归属部门</label><input value={form.owner_department} onChange={e => set('owner_department', e.target.value)} /></div>
      <div className="field"><label>资产负责人</label><input value={form.owner_name} onChange={e => set('owner_name', e.target.value)} /></div>
      <div className="field"><label>当前位置</label><input value={form.location} onChange={e => set('location', e.target.value)} /></div>
      <div className="field"><label>备注</label><input value={form.remark} onChange={e => set('remark', e.target.value)} /></div>
    </div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={() => onSubmit({ ...form, model: form.device_branch === 'training_platform' ? '实训台' : form.model, platform_type: form.device_branch === 'training_platform' ? form.platform_type : '' })}>保存</button></div>
  </div></div>
}
