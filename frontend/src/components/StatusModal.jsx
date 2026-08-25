import { useEffect, useState } from 'react'

const TRANSITIONS = {
  '在库': ['借出', '维修中'],
  '借出': ['在库', '维修中', '借出'],
  '维修中': ['在库'],
}

const ACTION_LABELS = {
  '在库': { '借出': '办理借出', '维修中': '送修' },
  '借出': { '在库': '归还入库', '维修中': '转入维修', '借出': '转交他人' },
  '维修中': { '在库': '维修完成入库' },
}

export default function StatusModal({ robot, onClose, onSubmit }) {
  const allowedStatuses = TRANSITIONS[robot.status] || []
  const initialStatus = allowedStatuses.includes(robot._suggestedStatus) ? robot._suggestedStatus : allowedStatuses[0]
  const [status, setStatus] = useState(initialStatus)
  const [location, setLocation] = useState(robot.location || '')
  const [note, setNote] = useState('')
  const [borrower, setBorrower] = useState(robot.borrower || '')
  const [holder, setHolder] = useState(robot.holder || robot.owner_name || '')
  const [purpose, setPurpose] = useState(robot.purpose || '')
  const [expectedReturnAt, setExpectedReturnAt] = useState(robot.expected_return_at ? robot.expected_return_at.slice(0, 16) : '')
  const [repairDescription, setRepairDescription] = useState(robot.repair_description || '')

  const chooseStatus = value => {
    setStatus(value)
    if (value === '在库') setHolder(robot.owner_name || '')
    if (value === '维修中' && robot.status === '借出') setHolder(robot.holder || robot.borrower || '')
  }

  useEffect(() => {
    const choices = TRANSITIONS[robot.status] || []
    setStatus(choices.includes(robot._suggestedStatus) ? robot._suggestedStatus : choices[0])
    setLocation(robot.location || '')
    setNote('')
    setBorrower(robot.borrower || '')
    setHolder(robot.holder || robot.owner_name || '')
    setPurpose(robot.purpose || '')
    setExpectedReturnAt(robot.expected_return_at ? robot.expected_return_at.slice(0, 16) : '')
    setRepairDescription(robot.repair_description || '')
  }, [robot.id])

  const submit = () => {
    if (!status) return
    if (status !== '在库' && !location.trim()) { alert('请填写设备当前实际位置'); return }
    if (status === '借出' && !borrower.trim()) { alert('请填写当前借用人'); return }
    if (status === '维修中' && !repairDescription.trim()) { alert('请填写故障或维修说明'); return }
    const finalHolder = status === '借出' ? borrower.trim() : (status === '在库' ? robot.owner_name : holder.trim())
    if (!finalHolder) { alert('请填写当前持有人'); return }
    onSubmit({
      status,
      location: status === '在库' ? '' : location.trim(),
      note: note.trim(),
      borrower: status === '借出' ? borrower.trim() : '',
      purpose: status === '借出' ? purpose.trim() : '',
      expected_return_at: status === '借出' ? (expectedReturnAt || null) : null,
      repair_description: status === '维修中' ? repairDescription.trim() : '',
      holder: finalHolder,
    })
  }

  const actionTitle = robot.status === '在库' ? '办理设备出库或送修' : robot.status === '借出' ? '办理归还、转交或送修' : '办理维修完成入库'

  return <div className="modal-mask" onClick={onClose}><div className="modal" onClick={e => e.stopPropagation()}>
    <div className="modal-kicker">设备状态流转</div><h3>{actionTitle}</h3>
    <div className="flow-device"><b>{robot.asset_code}</b><span>{robot.model} · 当前{robot.status}</span></div>
    <div className="field"><label>本次操作</label><div className="radio-group">{allowedStatuses.map(nextStatus => <div key={nextStatus} className={`radio-item ${status === nextStatus ? 'active' : ''}`} onClick={() => chooseStatus(nextStatus)}><input type="radio" checked={status === nextStatus} onChange={() => chooseStatus(nextStatus)} /><span style={{ flex: 1 }}>{ACTION_LABELS[robot.status]?.[nextStatus] || nextStatus}</span></div>)}</div></div>
    {status === '借出' && <><div className="field"><label>当前借用人 *</label><input value={borrower} onChange={e => setBorrower(e.target.value)} placeholder="实际使用设备的人" /></div><div className="field"><label>借用用途</label><input value={purpose} onChange={e => setPurpose(e.target.value)} placeholder="测试、演示、项目名称等" /></div><div className="field"><label>预计归还时间</label><input type="datetime-local" value={expectedReturnAt} onChange={e => setExpectedReturnAt(e.target.value)} /></div></>}
    {status === '维修中' && <div className="field"><label>故障或维修说明 *</label><input value={repairDescription} onChange={e => setRepairDescription(e.target.value)} placeholder="故障现象、送修原因等" /></div>}
    <div className="field"><label>当前持有人 *</label><input value={status === '借出' ? borrower : status === '在库' ? robot.owner_name : holder} disabled={status !== '维修中'} onChange={e => setHolder(e.target.value)} /><div className="hint">借出时与借用人一致；归还或维修完成后自动回到资产负责人。</div></div>
    <div className="field"><label>当前实际位置 {status !== '在库' && <span style={{ color: '#ff4d4f' }}>*</span>}</label><input value={status === '在库' ? '' : location} onChange={e => setLocation(e.target.value)} placeholder={status === '借出' ? '如：二楼实验室、赛事现场' : status === '维修中' ? '如：维修间、外部维修单位' : '归还入库后不再填写外部位置'} disabled={status === '在库'} />{status === '维修中' && <div className="hint">故障写在维修说明中，这里只填写设备实际所在地点。</div>}</div>
    <div className="field"><label>操作备注（可选）</label><input value={note} onChange={e => setNote(e.target.value)} placeholder="交接、验收或其他补充说明" /></div>
    <div className="actions"><button className="cancel" onClick={onClose}>取消</button><button className="primary" onClick={submit}>确认办理</button></div>
  </div></div>
}
