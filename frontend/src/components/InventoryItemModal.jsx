import { useState } from 'react'
const CATEGORIES = ['Pico', '灵巧手', '电池', '遥控器', '拓展坞']
export default function InventoryItemModal({ onClose, onSubmit }) {
  const [form, setForm] = useState({ category: 'Pico', subtype: '', model: '', unit: '个', initial_quantity: 0, location: '', owner_department: '', owner_name: '', remark: '' })
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  return <div className="modal-mask" onClick={onClose}><div className="modal modal-wide" onClick={e => e.stopPropagation()}>
    <div className="modal-kicker">数量库存</div><h3>新增配件库存</h3><div className="form-grid">
      <div className="field"><label>资产分类 *</label><select value={form.category} onChange={e => set('category', e.target.value)}>{CATEGORIES.map(x => <option key={x}>{x}</option>)}</select></div>
      {form.category === '灵巧手' && <div className="field"><label>灵巧手类型 *</label><select value={form.subtype} onChange={e => set('subtype', e.target.value)}><option value="">请选择</option><option>夹爪</option><option>三指灵巧手</option></select></div>}
      <div className="field"><label>型号或规格 *</label><input value={form.model} onChange={e => set('model', e.target.value)} placeholder="如 Pico 4、G1 电池" /></div>
      <div className="field"><label>初始数量 *</label><input type="number" min="0" value={form.initial_quantity} onChange={e => set('initial_quantity', Number(e.target.value))} /></div>
      <div className="field"><label>单位</label><select value={form.unit} onChange={e => set('unit', e.target.value)}><option>个</option><option>块</option><option>套</option><option>台</option></select></div>
      <div className="field"><label>存放位置</label><input value={form.location} onChange={e => set('location', e.target.value)} /></div>
      <div className="field"><label>归属部门</label><input value={form.owner_department} onChange={e => set('owner_department', e.target.value)} /></div>
      <div className="field"><label>负责人</label><input value={form.owner_name} onChange={e => set('owner_name', e.target.value)} /></div>
    </div><div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={() => form.model.trim() && (form.category !== '灵巧手' || form.subtype) ? onSubmit({ ...form, model: form.model.trim() }) : alert('请完整填写分类和型号')}>创建库存</button></div>
  </div></div>
}
