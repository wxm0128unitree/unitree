import { useEffect, useState } from 'react'
import { api } from '../api'
import InventoryItemModal from '../components/InventoryItemModal'
import InventoryActionModal from '../components/InventoryActionModal'
import Toast from '../components/Toast'
const ICONS = { Pico: '🥽', 灵巧手: '🖐️', 电池: '🔋', 遥控器: '🎮', 拓展坞: '🔌' }
export default function Inventory({ onStats }) {
  const [items,setItems]=useState([]), [showAdd,setShowAdd]=useState(false), [active,setActive]=useState(null), [toast,setToast]=useState(null)
  const say=(msg,type='success')=>{setToast({msg,type});setTimeout(()=>setToast(null),2200)}
  const load=async()=>{try{const [list,stats]=await Promise.all([api.listInventory(),api.getInventoryStats()]);setItems(list);onStats?.(stats)}catch(e){say(e.message,'error')}}
  useEffect(()=>{load()},[])
  const add=async data=>{try{await api.createInventory(data);setShowAdd(false);say('库存项目已创建');load()}catch(e){say(e.message,'error')}}
  const act=async data=>{try{await api.inventoryAction(active.item.id,data);setActive(null);say('库存数量已更新');load()}catch(e){say(e.message,'error')}}
  return <div className="inventory-page"><div className="section-heading"><div><span className="eyebrow">QUANTITY INVENTORY</span><h2>配件库存</h2><p>按型号管理数量，所有增减都会记录操作流水。</p></div><button className="primary-btn" onClick={()=>setShowAdd(true)}>＋ 新增库存</button></div>
    {items.length===0?<div className="empty polished"><div className="icon">📦</div><h3>还没有配件库存</h3><p>添加 Pico、灵巧手、电池、遥控器或拓展坞。</p></div>:<div className="inventory-grid">{items.map(item=><article className="inventory-card" key={item.id}>
      <div className="inventory-card-head"><span className="asset-icon">{ICONS[item.category]||'📦'}</span><div><span className="category-label">{item.subtype||item.category}</span><h3>{item.model}</h3></div><span className="unit-pill">{item.unit}</span></div>
      <div className="inventory-numbers"><div><b>{item.available_quantity}</b><span>当前库存</span></div><div><b>{item.loaned_quantity}</b><span>借出</span></div><div><b>{item.total_quantity}</b><span>部门总量</span></div></div>
      <div className="inventory-meta">📍 {item.location||'未设置位置'}{item.owner_name&&<span> · 👤 {item.owner_name}</span>}</div>
      <div className="inventory-actions"><button onClick={()=>setActive({item,action:'stock_in'})}>入库</button><button onClick={()=>setActive({item,action:'borrow'})}>借出</button><button onClick={()=>setActive({item,action:'return'})}>归还</button><button className="danger-link" onClick={()=>setActive({item,action:'migrate'})}>迁移</button></div>
    </article>)}</div>}
    {showAdd&&<InventoryItemModal onClose={()=>setShowAdd(false)} onSubmit={add}/>} {active&&<InventoryActionModal item={active.item} action={active.action} onClose={()=>setActive(null)} onSubmit={act}/>} {toast&&<Toast message={toast.msg} type={toast.type}/>}</div>
}
