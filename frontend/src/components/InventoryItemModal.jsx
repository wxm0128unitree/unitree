import { useState } from 'react'
const CATEGORIES = ['Pico', '灵巧手', '电池', '遥控器', '拓展坞']
const INDIVIDUAL = new Set(['电池','遥控器'])
const normalizeCategory = value => ['夹爪','三指灵巧手'].includes(value) ? {category:'灵巧手',subtype:value} : {category:value||'Pico',subtype:''}

export default function InventoryItemModal({ item, category, holders = [], user, onClose, onSubmit }) {
  const editing = Boolean(item)
  const preset=normalizeCategory(category)
  const [form, setForm] = useState(item ? {
    category: item.category, subtype: item.subtype || '', model: item.model,
    asset_code: item.asset_code || '', status: item.status || '在库', unit: item.unit,
    location: item.location || '', owner_department: item.owner_department || '',
    owner_name: item.owner_name || '', holder: item.holder || item.owner_name || '', remark: item.remark || '',
  } : { ...preset, model: '', asset_code: '', status: '在库', unit: '个', initial_quantity: 1, location: '', owner_department: '', owner_name: user?.is_admin===1?'':user?.name||'', holder:user?.name||'', remark: '' })
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const individual=INDIVIDUAL.has(form.category)
  const submit=()=>{
    if(!form.model.trim()||!form.owner_name.trim()||!form.holder.trim()||(form.category==='灵巧手'&&!form.subtype)) return alert('请完整填写分类、型号、负责人和持有人')
    onSubmit({...form,model:form.model.trim(),asset_code:form.asset_code.trim(),owner_name:form.owner_name.trim(),holder:form.holder.trim(),initial_quantity:individual?1:form.initial_quantity})
  }
  return <div className="modal-mask" onClick={onClose}><div className="modal modal-wide" onClick={e => e.stopPropagation()}>
    <div className="modal-kicker">配件管理</div><h3>{editing ? '编辑配件' : '新增配件'}</h3><div className="form-grid">
      <div className="field"><label>资产分类 *</label><select disabled={Boolean(category)} value={form.category} onChange={e => {set('category',e.target.value);set('subtype','')}}>{CATEGORIES.map(x => <option key={x}>{x}</option>)}</select></div>
      {form.category === '灵巧手' && <div className="field"><label>灵巧手类型 *</label><select disabled={['夹爪','三指灵巧手'].includes(category)} value={form.subtype} onChange={e => set('subtype', e.target.value)}><option value="">请选择</option><option>夹爪</option><option>三指灵巧手</option></select></div>}
      <div className="field"><label>型号或规格 *</label><input value={form.model} onChange={e => set('model', e.target.value)} placeholder="如 G1 电池、遥控器" /></div>
      <div className="field"><label>编号（可选，全系统不可重复）</label><input value={form.asset_code} onChange={e => set('asset_code', e.target.value)} placeholder={individual?'如 1、2、BAT-003':'可留空'} /></div>
      <div className="field"><label>状态 *</label><select value={form.status} onChange={e => set('status', e.target.value)}><option>在库</option><option>借出</option><option>维修中</option></select></div>
      {!editing && !individual && <div className="field"><label>初始数量 *</label><input type="number" min="1" value={form.initial_quantity} onChange={e => set('initial_quantity', Math.max(1,Number(e.target.value)))} /></div>}
      {!editing&&individual&&<div className="field"><label>管理方式</label><input disabled value="逐件管理（数量固定为 1）"/></div>}
      <div className="field"><label>单位</label><select value={form.unit} onChange={e => set('unit', e.target.value)}><option>个</option><option>块</option><option>套</option><option>台</option></select></div>
      <div className="field"><label>存放位置</label><input value={form.location} onChange={e => set('location', e.target.value)} /></div>
      <div className="field"><label>归属部门</label><input value={form.owner_department} onChange={e => set('owner_department', e.target.value)} /></div>
      <div className="field"><label>负责人 *</label><input list="inventory-modal-owners" disabled={user?.is_admin!==1} value={form.owner_name} onChange={e => set('owner_name', e.target.value)} placeholder="必须是内部账号"/><datalist id="inventory-modal-owners">{holders.filter(h=>h.phone).map(h=><option key={h.phone} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist></div>
      <div className="field"><label>当前持有人 *</label><input list="inventory-modal-holders" value={form.holder} onChange={e => set('holder', e.target.value)} placeholder="当前实际保管人"/><datalist id="inventory-modal-holders">{holders.map(h=><option key={h.phone||h.name} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist></div>
      <div className="field"><label>备注</label><input value={form.remark} onChange={e=>set('remark',e.target.value)}/></div>
    </div><div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={submit}>{editing ? '保存修改' : '创建配件'}</button></div>
  </div></div>
}
