import { useEffect, useState } from 'react'
import { api } from '../api'
import InventoryItemModal from '../components/InventoryItemModal'
import InventoryActionModal from '../components/InventoryActionModal'
import Toast from '../components/Toast'

const ICONS = { Pico: '🥽', 夹爪: '🤏', 三指灵巧手: '🖐️', 电池: '🔋', 遥控器: '🎮', 拓展坞: '🔌' }
const INDIVIDUAL = new Set(['电池', '遥控器'])

export default function Inventory({ category, onBack, onStats, user, holders = [] }) {
  const [items,setItems]=useState([]), [showAdd,setShowAdd]=useState(false), [editing,setEditing]=useState(null), [active,setActive]=useState(null), [selectedGroup,setSelectedGroup]=useState(null), [toast,setToast]=useState(null)
  const [filters,setFilters]=useState({status:'全部',holder:'全部',keyword:''})
  const say=(msg,type='success')=>{setToast({msg,type});setTimeout(()=>setToast(null),2200)}
  const load=async()=>{try{const params={category,status:filters.status,holder:filters.holder,keyword:filters.keyword};const [list,stats]=await Promise.all([api.listInventory(params),api.getInventoryStats()]);setItems(list);onStats?.(stats)}catch(e){say(e.message,'error')}}
  useEffect(()=>{load()},[category,filters.status])
  const add=async data=>{try{await api.createInventory(data);setShowAdd(false);say('配件已创建');load()}catch(e){say(e.message,'error')}}
  const edit=async data=>{try{await api.editInventory(editing.id,data);setEditing(null);say('配件资料已更新');load()}catch(e){say(e.message,'error')}}
  const remove=async item=>{if(!confirm(`永久删除“${item.model}${item.asset_code?` / ${item.asset_code}`:''}”？删除后无法恢复。`))return;try{await api.deleteInventory(item.id);say('配件已永久删除');load()}catch(e){say(e.message,'error')}}
  const act=async data=>{try{await api.inventoryAction(active.item.id,data);setActive(null);say('库存数量已更新');load()}catch(e){say(e.message,'error')}}
  const title=category||'全部配件'
  const groups=Object.values(items.reduce((result,item)=>{
    const displayCategory=item.subtype||item.category
    const key=[item.owner_name,displayCategory,item.model,item.status].join('\u0001')
    if(!result[key]) result[key]={key,displayCategory,category:item.category,model:item.model,status:item.status,owner_name:item.owner_name,owner_department:item.owner_department,unit:item.unit,items:[],quantity:0,numbered:0}
    result[key].items.push(item)
    result[key].quantity+=item.total_quantity
    if(item.asset_code) result[key].numbered+=item.total_quantity
    return result
  },{})).sort((a,b)=>a.owner_name.localeCompare(b.owner_name,'zh-CN')||a.model.localeCompare(b.model,'zh-CN')||a.status.localeCompare(b.status,'zh-CN'))
  const detail=selectedGroup&&groups.find(group=>group.key===selectedGroup)
  return <div className="inventory-page">
    <div className="section-heading"><div>{category&&<button className="text-btn" onClick={onBack}>← 返回资产总览</button>}<span className="eyebrow">ACCESSORY DETAIL</span><h2>{title}</h2><p>{category?`仅显示${category}，可按持有人、状态和编号检索。`:'按类别、持有人和状态管理全部配件。'}</p></div><button className="primary-btn" onClick={()=>setShowAdd(true)}>＋ 新增{category||'配件'}</button></div>
    <div className="toolbar">
      <select value={filters.status} onChange={e=>setFilters(f=>({...f,status:e.target.value}))}><option>全部</option><option>在库</option><option>借出</option><option>维修中</option></select>
      <input className="search" list="inventory-holder-options" placeholder="持有人姓名 / 账号 / 部门" value={filters.holder==='全部'?'':filters.holder} onChange={e=>setFilters(f=>({...f,holder:e.target.value||'全部'}))}/><datalist id="inventory-holder-options">{holders.map(h=><option key={h.phone||h.name} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist>
      <input className="search" placeholder="搜索型号 / 编号 / 位置" value={filters.keyword} onChange={e=>setFilters(f=>({...f,keyword:e.target.value}))} onKeyDown={e=>e.key==='Enter'&&load()}/><button onClick={load}>搜索</button>
    </div>
    {items.length===0?<div className="empty polished"><div className="icon">📦</div><h3>没有符合条件的{title}</h3><p>可新增配件或调整筛选条件。</p></div>:detail?<div><button className="text-btn" onClick={()=>setSelectedGroup(null)}>← 返回配件卡片</button><div className="section-heading compact"><div><h2>{detail.owner_name} · {detail.model}</h2><p>{detail.status} · 共{detail.quantity}{detail.unit} · 已编号{detail.numbered}{detail.unit} · 待编号{detail.quantity-detail.numbered}{detail.unit}</p></div></div><div className="inventory-grid">{detail.items.map(item=>{const individual=INDIVIDUAL.has(item.category);return <article className="inventory-card" key={item.id}><div className="inventory-card-head"><span className="asset-icon">{ICONS[detail.displayCategory]||'📦'}</span><div><span className="category-label">{detail.displayCategory}</span><h3>{item.asset_code||'暂未编号'}</h3></div><span className={`inventory-status status-${item.status}`}>{item.status}</span></div><div className="inventory-meta">本记录数量：{item.total_quantity}{item.unit}<span> · 持有人：{item.holder}</span><span> · 📍 {item.location||'未设置位置'}</span></div><div className="inventory-actions">{!individual&&<>{item.status==='在库'&&<><button onClick={()=>setActive({item,action:'stock_in'})}>增加数量</button><button onClick={()=>setActive({item,action:'borrow'})}>借出部分</button><button onClick={()=>setActive({item,action:'repair'})}>部分转维修</button><button onClick={()=>setActive({item,action:'scrap'})}>减少数量</button></>}{item.status==='借出'&&<><button onClick={()=>setActive({item,action:'return'})}>归还部分</button><button onClick={()=>setActive({item,action:'repair'})}>部分转维修</button></>}{item.status==='维修中'&&<button onClick={()=>setActive({item,action:'restore'})}>维修完成入库</button>}</>}<button onClick={()=>setEditing(item)}>编辑资料/状态</button>{user?.is_admin===1&&<button className="danger-link" onClick={()=>remove(item)}>永久删除</button>}</div></article>})}</div></div>:<div className="inventory-grid">{groups.map(group=><article className="inventory-card" key={group.key} onClick={()=>setSelectedGroup(group.key)}><div className="inventory-card-head"><span className="asset-icon">{ICONS[group.displayCategory]||ICONS[group.category]||'📦'}</span><div><span className="category-label">{group.displayCategory}</span><h3>{group.model}</h3></div><span className={`inventory-status status-${group.status}`}>{group.status}</span><span className="unit-pill">{group.unit}</span></div><div className="inventory-numbers"><div><b>{group.quantity}</b><span>该状态数量</span></div><div><b>{group.numbered}</b><span>已编号</span></div><div><b>{group.quantity-group.numbered}</b><span>待编号</span></div></div><div className="inventory-meta">负责人：{group.owner_name||'未指定'}{group.owner_department&&<span> · {group.owner_department}</span>}</div><div className="inventory-actions"><button onClick={e=>{e.stopPropagation();setSelectedGroup(group.key)}}>查看明细</button></div></article>)}</div>}
    {showAdd&&<InventoryItemModal category={category} holders={holders} user={user} onClose={()=>setShowAdd(false)} onSubmit={add}/>} {editing&&<InventoryItemModal item={editing} holders={holders} user={user} onClose={()=>setEditing(null)} onSubmit={edit}/>} {active&&<InventoryActionModal item={active.item} action={active.action} onClose={()=>setActive(null)} onSubmit={act}/>} {toast&&<Toast message={toast.msg} type={toast.type}/>}</div>
}
