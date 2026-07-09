import { useState, useRef, useEffect } from 'react'

/**
 * 支持新增的可筛选下拉框
 *
 * props:
 *   label       - 前缀文字 (如 "型号:")
 *   value       - 当前选中值
 *   onChange    - (newValue) => void
 *   options     - 候选值数组（如 ['G1','R1']）
 *   allLabel    - "全部" 选项的显示文字，默认 "全部"
 *   storageKey  - localStorage key，用于持久化用户新增的选项
 */
export default function FilterSelect({
  label,
  value,
  onChange,
  options = [],
  allLabel = '全部',
  storageKey,
  placeholder = '输入并回车添加',
}) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const wrapRef = useRef(null)
  const inputRef = useRef(null)

  // 持久化用户自定义选项
  const [custom, setCustom] = useState(() => {
    if (!storageKey) return []
    try {
      return JSON.parse(localStorage.getItem(storageKey) || '[]')
    } catch {
      return []
    }
  })

  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(storageKey, JSON.stringify(custom))
    }
  }, [custom, storageKey])

  // 合并所有选项
  const all = [allLabel, ...Array.from(new Set([...options, ...custom]))]

  // 点击外部关闭
  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const addCustom = () => {
    const v = draft.trim()
    if (!v) return
    if (v === allLabel) {
      setDraft('')
      return
    }
    if (!all.includes(v)) {
      setCustom(prev => [...prev, v])
    }
    onChange(v)
    setDraft('')
    setOpen(false)
  }

  const removeCustom = (v) => {
    setCustom(prev => prev.filter(x => x !== v))
    if (value === v) onChange(allLabel)
  }

  return (
    <div className="filter-select" ref={wrapRef}>
      <div
        className="filter-select-trigger"
        onClick={() => { setOpen(o => !o); setTimeout(() => inputRef.current?.focus(), 50) }}
      >
        <span>{label}{value !== allLabel ? `: ${value}` : `: ${allLabel}`}</span>
        <span className="caret">{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="filter-select-dropdown">
          {all.map(opt => (
            <div
              key={opt}
              className={`filter-select-item ${value === opt ? 'active' : ''}`}
              onClick={() => { onChange(opt); setOpen(false) }}
            >
              <span>{opt}</span>
              {custom.includes(opt) && (
                <span
                  className="del"
                  title="移除该自定义项"
                  onClick={(e) => { e.stopPropagation(); removeCustom(opt) }}
                >×</span>
              )}
            </div>
          ))}

          <div className="filter-select-add">
            <input
              ref={inputRef}
              type="text"
              value={draft}
              onChange={e => setDraft(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') { e.preventDefault(); addCustom() }
                if (e.key === 'Escape') setOpen(false)
              }}
              placeholder={placeholder}
            />
            <button type="button" onClick={addCustom}>添加</button>
          </div>
        </div>
      )}
    </div>
  )
}