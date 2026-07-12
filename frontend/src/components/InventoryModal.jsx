import { useState } from 'react'

export default function InventoryModal({ robot, onClose, onSubmit }) {
  const [location, setLocation] = useState(robot.location || '')
  const [note, setNote] = useState('')
  return <div className="modal-mask" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}>
    <h3>盘点确认 - [{robot.asset_code}]</h3>
    <div className="field"><label>盘点位置</label><input value={location} onChange={e => setLocation(e.target.value)} placeholder="设备实际所在位置" /></div>
    <div className="field"><label>盘点备注</label><input value={note} onChange={e => setNote(e.target.value)} placeholder="外观、附件或差异说明" /></div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={() => onSubmit({ location: location.trim(), note: note.trim() })}>确认盘点</button></div>
  </div></div>
}
