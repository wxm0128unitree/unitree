import { useEffect, useState } from 'react'
import { api } from '../api'
import InventoryItemModal from '../components/InventoryItemModal'
import InventoryActionModal from '../components/InventoryActionModal'
import Toast from '../components/Toast'

const ICONS = { Pico: '🥽', 夹爪: '🤏', 三指灵巧手: '🖐️', 电池: '🔋', 遥控器: '🎮', 拓展坞: '🔌' }
const INDIVIDUAL = new Set(['电池', '遥控器'])

export default function Inventory({ category, onBack, onStats, user, holders = [] }) {
  const [items,setItems]=useState([]), [showAdd,setShowAdd]=useState(false), [editing,setEditing]=useState(null), [active,setActive]=useState(null), [toast,setToast]=useState(null)
  const [filters,setFilters]=useState({status:'全部',holder:'全部',keyword:''})
  const say=(msg,type='success')=>{setToast({msg,type});setTimeout(()=>setToast(null),2200)}
  const load=async()=>{try{const params={category,status:filters.status,holder:filters.holder,keyword:filters.keyword};const [list,stats]=await Promise.all([api.listInventory(params),api.getInventoryStats()]);setItems(list);onStats?.(stats)}catch(e){say(e.message,'error')}}
  useEffect(()=>{load()},[category,filters.status])
  const add=async data=>{try{await api.createInventory(data);setShowAdd(false);say('配件已创建');load()}catch(e){say(e.message,'error')}}
  const edit=async data=>{try{await api.editInventory(editing.id,data);setEditing(null);say('配件资料已更新');load()}catch(e){say(e.message,'error')}}
  const remove=async item=>{if(!confirm(`永久删除“${item.model}${item.asset_code?` / ${item.asset_code}`:''}”？删除后无法恢复。`))return;try{await api.deleteInventory(item.id);say('配件已永久删除');load()}catch(e){say(e.message,'error')}}
  const act=async data=>{try{await api.inventoryAction(active.item.id,data);setActive(null);say('库存数量已更新');load()}catch(e){say(e.message,'error')}}
  const title=category||'全部配件'
  return <div className="inventory-page">
    <div className="section-heading"><div>{category&&<button className="text-btn" onClick={onBack}>← 返回资产总览</button>}<span className="eyebrow">ACCESSORY DETAIL</span><h2>{title}</h2><p>{category?`仅显示${category}，可按持有人、状态和编号检索。`:'按类别、持有人和状态管理全部配件。'}</p></div><button className="primary-btn" onClick={()=>setShowAdd(true)}>＋ 新增{category||'配件'}</button></div>
    <div className="toolbar">
      <select value={filters.status} onChange={e=>setFilters(f=>({...f,status:e.target.value}))}><option>全部</option><option>在库</option><option>借出</option><option>维修中</option></select>
      <input className="search" list="inventory-holder-options" placeholder="持有人姓名 / 账号 / 部门" value={filters.holder==='全部'?'':filters.holder} onChange={e=>setFilters(f=>({...f,holder:e.target.value||'全部'}))}/><datalist id="inventory-holder-options">{holders.map(h=><option key={h.phone||h.name} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist>
      <input className="search" placeholder="搜索型号 / 编号 / 位置" value={filters.keyword} onChange={e=>setFilters(f=>({...f,keyword:e.target.value}))} onKeyDown={e=>e.key==='Enter'&&load()}/><button onClick={load}>搜索</button>
    </div>
    {items.length===0?<div className="empty polished"><div className="icon">📦</div><h3>没有符合条件的{title}</h3><p>可新增配件或调整筛选条件。</p></div>:<div className="inventory-grid">{items.map(item=>{const displayCategory=item.subtype||item.category;const individual=INDIVIDUAL.has(item.category);return <article className="inventory-card" key={item.id}>
      <div className="inventory-card-head"><span className="asset-icon">{ICONS[displayCategory]||ICONS[item.category]||'📦'}</span><div><span className="category-label">{displayCategory}</span><h3>{item.model}</h3>{item.asset_code&&<small>编号：{item.asset_code}</small>}</div><span className={`inventory-status status-${item.status}`}>{item.status}</span><span className="unit-pill">{item.unit}</span></div>
      <div className="inventory-numbers">{individual?<div><b>1</b><span>单件管理</span></div>:<><div><b>{item.available_quantity}</b><span>当前库存</span></div><div><b>{item.loaned_quantity}</b><span>借出</span></div><div><b>{item.total_quantity}</b><span>持有人总量</span></div></>}</div>
      <div className="inventory-meta">负责人：{item.owner_name||'未指定'}{item.owner_department&&<span> · {item.owner_department}</span>}<span> · 持有人：{item.holder||'未指定'}</span><span> · 📍 {item.location||'未设置位置'}</span></div>
      <div className="inventory-actions">{!individual&&<><button onClick={()=>setActive({item,action:'stock_in'})}>增加数量</button><button onClick={()=>setActive({item,action:'scrap'})}>减少数量</button><button onClick={()=>setActive({item,action:'borrow'})}>借出</button><button onClick={()=>setActive({item,action:'return'})}>归还</button><button className="danger-link" onClick={()=>setActive({item,action:'migrate'})}>迁移</button></>}<button onClick={()=>setEditing(item)}>编辑资料/状态</button>{user?.is_admin===1&&<button className="danger-link" onClick={()=>remove(item)}>永久删除</button>}</div>
    </article>})}</div>}
    {showAdd&&<InventoryItemModal category={category} holders={holders} user={user} onClose={()=>setShowAdd(false)} onSubmit={add}/>} {editing&&<InventoryItemModal item={editing} holders={holders} user={user} onClose={()=>setEditing(null)} onSubmit={edit}/>} {active&&<InventoryActionModal item={active.item} action={active.action} onClose={()=>setActive(null)} onSubmit={act}/>} {toast&&<Toast message={toast.msg} type={toast.type}/>}</div>
}
