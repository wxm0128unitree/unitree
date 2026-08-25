import { useState } from 'react'
const NAMES = { stock_in: '增加数量', borrow: '借出', return: '归还', repair: '转维修', restore: '维修完成入库', migrate: '调出本部门', scrap: '减少数量' }
export default function InventoryActionModal({ item, action, onClose, onSubmit }) {
  const [form, setForm] = useState({ action, quantity: 1, item_ids: item.item_ids || [item.id], borrower: '', location: '', purpose: '', destination_department: '', destination_holder: '', expected_return_at: null, note: '' })
  const set = (k,v) => setForm(f => ({...f,[k]:v}))
  const after = action === 'stock_in' ? item.total_quantity + form.quantity : item.total_quantity - form.quantity
  return <div className="modal-mask" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}>
    <div className="modal-kicker">{NAMES[action]}</div><h3>{item.model}</h3>
    <div className="quantity-preview"><span>当前“{item.status}”数量 <b>{item.total_quantity}</b></span><span>操作后原状态剩余 <b>{Math.max(0, after)}</b></span></div>
    <div className="field"><label>数量 *</label><input type="number" min="1" max={action==='stock_in'?undefined:item.total_quantity} value={form.quantity} onChange={e => set('quantity', Number(e.target.value))} /></div>
    {action === 'borrow' && <><div className="field"><label>借用人 *</label><input value={form.borrower} onChange={e => set('borrower', e.target.value)} /></div><div className="field"><label>使用地点 *</label><input placeholder="同一借用人不同地点将分别统计" value={form.location} onChange={e => set('location', e.target.value)} /></div><div className="field"><label>用途</label><input value={form.purpose} onChange={e => set('purpose', e.target.value)} /></div><div className="field"><label>预计归还</label><input type="datetime-local" onChange={e => set('expected_return_at', e.target.value || null)} /></div></>}
    {action === 'repair' && <div className="field"><label>维修地点 / 送修去向 *</label><input value={form.location} onChange={e => set('location', e.target.value)} /></div>}
    {(action === 'return' || action === 'restore') && <div className="field"><label>入库位置</label><input placeholder="留空则合并回现有在库总量" value={form.location} onChange={e => set('location', e.target.value)} /></div>}
    {action === 'migrate' && <><p className="modal-note">调出后不再计入本部门库存，流水和接收信息会继续保留。</p><div className="field"><label>接收部门 *</label><input value={form.destination_department} onChange={e => set('destination_department', e.target.value)} /></div><div className="field"><label>接收人</label><input value={form.destination_holder} onChange={e => set('destination_holder', e.target.value)} /></div></>}
    {action === 'scrap' && <p className="form-hint">普通用户可以调整自己负责配件的数量，但只有管理员可以将总数量减到 0 并永久移除记录。</p>}
    <div className="field"><label>备注</label><input value={form.note} onChange={e => set('note', e.target.value)} /></div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className={action === 'migrate' || action === 'scrap' ? 'danger-solid' : 'primary'} onClick={() => onSubmit(form)}>确认{NAMES[action]}</button></div>
  </div></div>
}
