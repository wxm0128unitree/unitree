import { useState } from 'react'

export default function MigrationModal({ robot, onClose, onSubmit }) {
  const [department, setDepartment] = useState('')
  const [holder, setHolder] = useState('')
  const [reason, setReason] = useState('')
  return <div className="modal-mask" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}>
    <div className="modal-kicker">永久移出本部门</div><h3>迁移 · {robot.asset_code}</h3>
    <p className="modal-note">迁移后不再计入部门资产统计，但全部历史记录会保留。</p>
    <div className="field"><label>接收部门 *</label><input value={department} onChange={e => setDepartment(e.target.value)} placeholder="请输入接收部门" /></div>
    <div className="field"><label>接收人</label><input value={holder} onChange={e => setHolder(e.target.value)} placeholder="接收负责人" /></div>
    <div className="field"><label>迁移原因</label><input value={reason} onChange={e => setReason(e.target.value)} placeholder="项目调拨、部门调整等" /></div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="danger-solid" onClick={() => department.trim() ? onSubmit({ destination_department: department.trim(), destination_holder: holder.trim(), reason: reason.trim() }) : alert('请填写接收部门')}>确认迁移</button></div>
  </div></div>
}
