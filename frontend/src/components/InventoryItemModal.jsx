import { useState } from 'react'
const CATEGORIES = ['Pico', '灵巧手', '电池', '遥控器', '拓展坞']
export default function InventoryItemModal({ item, onClose, onSubmit }) {
  const editing = Boolean(item)
  const [form, setForm] = useState(item ? {
    category: item.category, subtype: item.subtype || '', model: item.model,
    asset_code: item.asset_code || '', status: item.status || '在库', unit: item.unit,
    location: item.location || '', owner_department: item.owner_department || '',
    owner_name: item.owner_name || '', remark: item.remark || '',
  } : { category: 'Pico', subtype: '', model: '', asset_code: '', status: '在库', unit: '个', initial_quantity: 0, location: '', owner_department: '', owner_name: '', remark: '' })
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  return <div className="modal-mask" onClick={onClose}><div className="modal modal-wide" onClick={e => e.stopPropagation()}>
    <div className="modal-kicker">数量库存</div><h3>{editing ? '编辑配件库存' : '新增配件库存'}</h3><div className="form-grid">
      <div className="field"><label>资产分类 *</label><select value={form.category} onChange={e => set('category', e.target.value)}>{CATEGORIES.map(x => <option key={x}>{x}</option>)}</select></div>
      {form.category === '灵巧手' && <div className="field"><label>灵巧手类型 *</label><select value={form.subtype} onChange={e => set('subtype', e.target.value)}><option value="">请选择</option><option>夹爪</option><option>三指灵巧手</option></select></div>}
      <div className="field"><label>型号或规格 *</label><input value={form.model} onChange={e => set('model', e.target.value)} placeholder="如 Pico 4、G1 电池" /></div>
      <div className="field"><label>编号（可选）</label><input value={form.asset_code} onChange={e => set('asset_code', e.target.value)} placeholder="如 PJ-001；多个编号可用逗号分隔" /></div>
      <div className="field"><label>状态 *</label><select value={form.status} onChange={e => set('status', e.target.value)}><option>在库</option><option>借出</option><option>维修中</option><option>停用</option></select></div>
      {!editing && <div className="field"><label>初始数量 *</label><input type="number" min="0" value={form.initial_quantity} onChange={e => set('initial_quantity', Number(e.target.value))} /></div>}
      <div className="field"><label>单位</label><select value={form.unit} onChange={e => set('unit', e.target.value)}><option>个</option><option>块</option><option>套</option><option>台</option></select></div>
      <div className="field"><label>存放位置</label><input value={form.location} onChange={e => set('location', e.target.value)} /></div>
      <div className="field"><label>归属部门</label><input value={form.owner_department} onChange={e => set('owner_department', e.target.value)} /></div>
      <div className="field"><label>负责人</label><input value={form.owner_name} onChange={e => set('owner_name', e.target.value)} /></div>
    </div><div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={() => form.model.trim() && (form.category !== '灵巧手' || form.subtype) ? onSubmit({ ...form, model: form.model.trim(), asset_code: form.asset_code.trim() }) : alert('请完整填写分类和型号')}>{editing ? '保存修改' : '创建库存'}</button></div>
  </div></div>
}
