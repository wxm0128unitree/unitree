import { useEffect, useState } from 'react'
import { api } from '../api'
import InventoryItemModal from '../components/InventoryItemModal'
import InventoryActionModal from '../components/InventoryActionModal'
import Toast from '../components/Toast'

const ICONS = { Pico: '🥽', 夹爪: '🤏', 三指灵巧手: '🖐️', 电池: '🔋', 遥控器: '🎮', 拓展坞: '🔌' }

export default function Inventory({ category, onBack, onStats, user, holders = [] }) {
  const [items,setItems]=useState([]), [showAdd,setShowAdd]=useState(false), [editing,setEditing]=useState(null), [active,setActive]=useState(null), [selectedGroup,setSelectedGroup]=useState(null), [toast,setToast]=useState(null)
  const [filters,setFilters]=useState({status:'全部',holder:'全部',keyword:''})
  const say=(msg,type='success')=>{setToast({msg,type});setTimeout(()=>setToast(null),2200)}
  const load=async()=>{try{const params={category,status:filters.status,holder:filters.holder,keyword:filters.keyword};const [list,stats]=await Promise.all([api.listInventory(params),api.getInventoryStats()]);setItems(list);onStats?.(stats)}catch(e){say(e.message,'error')}}
  useEffect(()=>{load()},[category,filters.status])
  const add=async data=>{try{await api.createInventory(data);setShowAdd(false);say('配件已创建');load()}catch(e){say(e.message,'error')}}
  const edit=async data=>{try{await api.editInventory(editing.id,data);setEditing(null);say('配件资料已更新');load()}catch(e){say(e.message,'error')}}
  const remove=async item=>{if(!confirm(`确认作废“${item.model}${item.asset_code?` / ${item.asset_code}`:''}”记录？数据和操作流水会保留，但不再计入库存。`))return;try{await api.deleteInventory(item.id);say('配件记录已作废');load()}catch(e){say(e.message,'error')}}
  const act=async data=>{try{await api.inventoryAction(active.item.id,data);setActive(null);say('库存数量已更新');load()}catch(e){say(e.message,'error')}}
  const title=category||'全部配件'
  const modelGroups=Object.values(items.reduce((result,item)=>{
    const displayCategory=item.subtype||item.category
    const key=[item.owner_name,displayCategory,item.model,item.unit].join('\u0001')
    if(!result[key]) result[key]={key,displayCategory,category:item.category,model:item.model,owner_name:item.owner_name,owner_department:item.owner_department,unit:item.unit,items:[],quantity:0,available:0,loaned:0,repairing:0}
    result[key].items.push(item)
    result[key].quantity+=item.total_quantity
    if(item.status==='在库') result[key].available+=item.total_quantity
    else if(item.status==='借出') result[key].loaned+=item.total_quantity
    else if(item.status==='维修中') result[key].repairing+=item.total_quantity
    return result
  },{})).sort((a,b)=>a.owner_name.localeCompare(b.owner_name,'zh-CN')||a.model.localeCompare(b.model,'zh-CN'))
  const detail=selectedGroup&&modelGroups.find(group=>group.key===selectedGroup)
  const batches=detail?Object.values(detail.items.reduce((result,item)=>{
    const key=[item.status,item.holder,item.location||'',item.asset_code||''].join('\u0001')
    if(!result[key]) result[key]={...item,key,item_ids:[],total_quantity:0}
    result[key].item_ids.push(item.id);result[key].total_quantity+=item.total_quantity
    return result
  },{})).sort((a,b)=>a.status.localeCompare(b.status,'zh-CN')||a.holder.localeCompare(b.holder,'zh-CN')||a.location.localeCompare(b.location,'zh-CN')):[]
  return <div className="inventory-page">
    <div className="section-heading"><div>{category&&<button className="text-btn" onClick={onBack}>← 返回资产总览</button>}<span className="eyebrow">ACCESSORY DETAIL</span><h2>{title}</h2><p>{category?`仅显示${category}，可按持有人、状态和编号检索。`:'按类别、持有人和状态管理全部配件。'}</p></div><button className="primary-btn" onClick={()=>setShowAdd(true)}>＋ 新增{category||'配件'}</button></div>
    <div className="toolbar">
      <select value={filters.status} onChange={e=>setFilters(f=>({...f,status:e.target.value}))}><option>全部</option><option>在库</option><option>借出</option><option>维修中</option></select>
      <input className="search" list="inventory-holder-options" placeholder="持有人姓名 / 账号 / 部门" value={filters.holder==='全部'?'':filters.holder} onChange={e=>setFilters(f=>({...f,holder:e.target.value||'全部'}))}/><datalist id="inventory-holder-options">{holders.map(h=><option key={h.phone||h.name} value={h.name}>{[h.phone,h.department].filter(Boolean).join(' · ')}</option>)}</datalist>
      <input className="search" placeholder="搜索型号 / 编号 / 位置" value={filters.keyword} onChange={e=>setFilters(f=>({...f,keyword:e.target.value}))} onKeyDown={e=>e.key==='Enter'&&load()}/><button onClick={load}>搜索</button>
    </div>
    {items.length===0?<div className="empty polished"><div className="icon">📦</div><h3>没有符合条件的{title}</h3><p>可新增配件或调整筛选条件。</p></div>:detail?<div><button className="text-btn" onClick={()=>setSelectedGroup(null)}>← 返回配件卡片</button><div className="section-heading compact"><div><h2>{detail.owner_name} · {detail.model}</h2><p>总量 {detail.quantity}{detail.unit}，按库存状态、借用人和地点分批展示。</p></div></div><div className="inventory-grid">{batches.map(item=><article className="inventory-card" key={item.key}><div className="inventory-card-head"><span className="asset-icon">{ICONS[detail.displayCategory]||'📦'}</span><div><span className="category-label">{item.status==='在库'?'库存总量':item.status==='借出'?'借出批次':'维修批次'}</span><h3>{item.asset_code||item.holder||detail.model}</h3></div><span className={`inventory-status status-${item.status}`}>{item.status}</span></div><div className="inventory-numbers"><div><b>{item.total_quantity}</b><span>{item.unit}</span></div></div><div className="inventory-meta">{item.status==='在库'?'保管人':'当前负责人'}：{item.holder}<span> · 📍 {item.location||'未设置地点'}</span>{item.current_purpose&&<span> · 用途：{item.current_purpose}</span>}{item.current_expected_return_at&&<span> · 预计归还 {new Date(item.current_expected_return_at).toLocaleDateString('zh-CN')}</span>}</div><div className="inventory-actions">{item.status==='在库'&&<><button onClick={()=>setActive({item,action:'stock_in'})}>增加数量</button><button onClick={()=>setActive({item,action:'borrow'})}>按数量借出</button><button onClick={()=>setActive({item,action:'repair'})}>按数量送修</button><button onClick={()=>setActive({item,action:'migrate'})}>调出</button><button onClick={()=>setActive({item,action:'scrap'})}>减少数量</button></>}{item.status==='借出'&&<><button onClick={()=>setActive({item,action:'return'})}>按数量归还</button><button onClick={()=>setActive({item,action:'repair'})}>按数量转维修</button></>}{item.status==='维修中'&&<button onClick={()=>setActive({item,action:'restore'})}>按数量完成维修</button>}{item.item_ids.length===1&&<button onClick={()=>setEditing(item)}>编辑资料</button>}{user?.is_admin===1&&item.status==='在库'&&item.item_ids.length===1&&<button className="danger-link" onClick={()=>remove(item)}>作废记录</button>}</div></article>)}</div></div>:<div className="inventory-grid">{modelGroups.map(group=><article className="inventory-card" key={group.key} onClick={()=>setSelectedGroup(group.key)}><div className="inventory-card-head"><span className="asset-icon">{ICONS[group.displayCategory]||ICONS[group.category]||'📦'}</span><div><span className="category-label">{group.displayCategory}</span><h3>{group.model}</h3></div><span className="unit-pill">{group.unit}</span></div><div className="inventory-numbers"><div><b>{group.quantity}</b><span>总量</span></div><div><b>{group.available}</b><span>在库</span></div><div><b>{group.loaned}</b><span>借出</span></div><div><b>{group.repairing}</b><span>维修</span></div></div><div className="inventory-meta">负责人：{group.owner_name||'未指定'}{group.owner_department&&<span> · {group.owner_department}</span>}</div><div className="inventory-actions"><button onClick={e=>{e.stopPropagation();setSelectedGroup(group.key)}}>查看数量批次</button></div></article>)}</div>}
    {showAdd&&<InventoryItemModal category={category} holders={holders} user={user} onClose={()=>setShowAdd(false)} onSubmit={add}/>} {editing&&<InventoryItemModal item={editing} holders={holders} user={user} onClose={()=>setEditing(null)} onSubmit={edit}/>} {active&&<InventoryActionModal item={active.item} action={active.action} onClose={()=>setActive(null)} onSubmit={act}/>} {toast&&<Toast message={toast.msg} type={toast.type}/>}</div>
}
