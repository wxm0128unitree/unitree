import { useState } from 'react'
const NAMES = { stock_in: '采购入库', borrow: '借出', return: '归还', migrate: '迁移', scrap: '报废' }
export default function InventoryActionModal({ item, action, onClose, onSubmit }) {
  const [form, setForm] = useState({ action, quantity: 1, borrower: '', purpose: '', destination_department: '', destination_holder: '', expected_return_at: null, note: '' })
  const set = (k,v) => setForm(f => ({...f,[k]:v}))
  const after = action === 'stock_in' || action === 'return' ? item.available_quantity + form.quantity : item.available_quantity - form.quantity
  return <div className="modal-mask" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}>
    <div className="modal-kicker">{NAMES[action]}</div><h3>{item.model}</h3>
    <div className="quantity-preview"><span>当前库存 <b>{item.available_quantity}</b></span><span>操作后 <b>{Math.max(0, after)}</b></span></div>
    <div className="field"><label>数量 *</label><input type="number" min="1" value={form.quantity} onChange={e => set('quantity', Number(e.target.value))} /></div>
    {action === 'borrow' && <><div className="field"><label>借用人 *</label><input value={form.borrower} onChange={e => set('borrower', e.target.value)} /></div><div className="field"><label>用途</label><input value={form.purpose} onChange={e => set('purpose', e.target.value)} /></div><div className="field"><label>预计归还</label><input type="datetime-local" onChange={e => set('expected_return_at', e.target.value || null)} /></div></>}
    {action === 'migrate' && <><div className="field"><label>接收部门 *</label><input value={form.destination_department} onChange={e => set('destination_department', e.target.value)} /></div><div className="field"><label>接收人</label><input value={form.destination_holder} onChange={e => set('destination_holder', e.target.value)} /></div></>}
    <div className="field"><label>备注</label><input value={form.note} onChange={e => set('note', e.target.value)} /></div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className={action === 'migrate' || action === 'scrap' ? 'danger-solid' : 'primary'} onClick={() => onSubmit(form)}>确认{NAMES[action]}</button></div>
  </div></div>
}
