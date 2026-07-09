import { useState, useEffect } from 'react'

const DEFAULT_STATUSES = ['在库', '借出', '维修中']

export default function StatusModal({ robot, onClose, onSubmit }) {
  const [status, setStatus] = useState(robot.status || '在库')
  const [location, setLocation] = useState(robot.location || '')
  const [note, setNote] = useState('')

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
    onSubmit({ status, location: location.trim(), note: note.trim() })
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