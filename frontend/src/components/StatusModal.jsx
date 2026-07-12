import { useState, useEffect } from 'react'

const DEFAULT_STATUSES = ['在库', '借出', '维修中']

export default function StatusModal({ robot, onClose, onSubmit }) {
  const [status, setStatus] = useState(robot.status || '在库')
  const [location, setLocation] = useState(robot.location || '')
  const [note, setNote] = useState('')
  const [borrower, setBorrower] = useState(robot.borrower || '')
  const [purpose, setPurpose] = useState(robot.purpose || '')
  const [expectedReturnAt, setExpectedReturnAt] = useState(robot.expected_return_at ? robot.expected_return_at.slice(0, 16) : '')
  const [repairDescription, setRepairDescription] = useState(robot.repair_description || '')

  // 用户自定义的状态（持久化）
  const [customStatuses, setCustomStatuses] = useState(() => {
    try { return JSON.parse(localStorage.getItem('customStatusesList') || '[]') }
    catch { return [] }
  })
  const [addingStatus, setAddingStatus] = useState(false)
  const [newStatus, setNewStatus] = useState('')

  useEffect(() => {
    localStorage.setItem('customStatusesList', JSON.stringify(customStatuses))
  }, [customStatuses])

  useEffect(() => {
    setStatus(robot.status || '在库')
    setLocation(robot.location || '')
    setNote('')
  }, [robot.id])

  const allStatuses = Array.from(new Set([...DEFAULT_STATUSES, ...customStatuses]))

  const addNewStatus = () => {
    const v = newStatus.trim()
    if (!v) return
    if (allStatuses.includes(v)) {
      setStatus(v)
    } else {
      setCustomStatuses(prev => [...prev, v])
      setStatus(v)
    }
    setNewStatus('')
    setAddingStatus(false)
  }

  const removeCustom = (v) => {
    setCustomStatuses(prev => prev.filter(x => x !== v))
    if (status === v) setStatus('在库')
  }

  const submit = () => {
    if (status !== '在库' && !location.trim()) {
      alert('请填写去向信息（持有人/地点/故障原因）')
      return
    }
    if (status === '借出' && !borrower.trim()) { alert('请填写当前借用人'); return }
    onSubmit({ status, location: location.trim(), note: note.trim(), borrower: borrower.trim(), purpose: purpose.trim(),
      expected_return_at: expectedReturnAt || null, repair_description: repairDescription.trim() })
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h3>修改状态 - [{robot.asset_code}]</h3>

        <div className="field">
          <label>1. 选择状态</label>
          <div className="radio-group">
            {allStatuses.map(s => (
              <div
                key={s}
                className={`radio-item ${status === s ? 'active' : ''}`}
                onClick={() => setStatus(s)}
              >
                <input type="radio" checked={status === s} onChange={() => setStatus(s)} />
                <span style={{ flex: 1 }}>{s}</span>
                {customStatuses.includes(s) && (
                  <span
                    className="del"
                    title="移除该自定义状态"
                    onClick={(e) => { e.stopPropagation(); removeCustom(s) }}
                  >×</span>
                )}
              </div>
            ))}

            {addingStatus ? (
              <div className="radio-item" onClick={e => e.stopPropagation()}>
                <input
                  type="text"
                  autoFocus
                  value={newStatus}
                  onChange={e => setNewStatus(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') addNewStatus()
                    if (e.key === 'Escape') { setAddingStatus(false); setNewStatus('') }
                  }}
                  placeholder="新状态名，回车确认"
                  style={{ flex: 1, border: 'none', outline: 'none', background: 'transparent' }}
                />
                <button type="button" onClick={addNewStatus} style={{ padding: '2px 10px', border: 'none', borderRadius: 6, background: '#1677ff', color: '#fff', cursor: 'pointer' }}>确定</button>
              </div>
            ) : (
              <div className="radio-item" style={{ color: '#1677ff', borderStyle: 'dashed' }} onClick={() => setAddingStatus(true)}>
                <span>+ 新增状态</span>
              </div>
            )}
          </div>
        </div>

        {status === '借出' && <>
          <div className="field"><label>当前借用人 *</label><input value={borrower} onChange={e => setBorrower(e.target.value)} placeholder="实际使用设备的人" /></div>
          <div className="field"><label>借用用途</label><input value={purpose} onChange={e => setPurpose(e.target.value)} placeholder="测试、演示、项目名称等" /></div>
          <div className="field"><label>预计归还时间</label><input type="datetime-local" value={expectedReturnAt} onChange={e => setExpectedReturnAt(e.target.value)} /></div>
        </>}
        {status === '维修中' && <div className="field"><label>维修故障描述</label><input value={repairDescription} onChange={e => setRepairDescription(e.target.value)} placeholder="故障现象、维修单位等" /></div>}

        <div className="field">
          <label>2. 填写去向 {status !== '在库' && <span style={{ color: '#ff4d4f' }}>*</span>}</label>
          <input
            type="text"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder={
              status === '在库' ? '（在库无需填写）'
              : status === '借出' ? '持有人姓名 / 地点，如：王五、二楼实验室'
              : status === '维修中' ? '故障描述，如：左腿电机故障'
              : '持有人 / 地点 / 描述'
            }
            disabled={status === '在库'}
          />
          <div className="hint">
            {status === '借出' && '💡 借出后修改状态保持「借出」可实现转移'}
            {status === '维修中' && '💡 这里显示的内容会出现在列表「去向/持有人」栏'}
          </div>
        </div>

        <div className="field">
          <label>备注（可选）</label>
          <input
            type="text"
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="如：测试用、已发顺丰…"
          />
        </div>

        <div className="actions">
          <button className="cancel" onClick={onClose}>取消</button>
          <button className="primary" onClick={submit}>确定</button>
        </div>
      </div>
    </div>
  )
}
