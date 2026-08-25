import { formatShanghaiDate } from '../utils/datetime'

export default function RobotCard({ robot, onClick, onFlow, onDelete, onEdit, onInventory, onRestore, onMigrate, onUndoMigration, isAdmin }) {
  const statusIcon = {
    '在库': '🟢',
    '借出': '🔵',
    '维修中': '🟠',
  }
  const modelClass = `model-tag model-${robot.model}`
  const overdue = robot.status === '借出' && robot.expected_return_at && new Date(robot.expected_return_at) < new Date()
  const primaryLabel = robot.status === '在库' ? '办理借出' : robot.status === '借出' ? '办理归还' : '维修完成'

  return (
    <div className="robot-card" onClick={onClick}>
      <div className="row1">
        <span className="code">{robot.asset_code}</span>
        <span className={modelClass}>{robot.model}</span>
      </div>
      <div className="holder">
        <span className="holder-icon">👤</span>
        <span className="holder-text">负责人：{[robot.owner_department, robot.owner_name].filter(Boolean).join(' / ') || '未指定'}</span>
      </div>
      <div className="meta-line">持有人：{robot.holder || '未指定'}</div>
      <div className="status-row">
        <div className={`status status-${robot.status}`}>{statusIcon[robot.status] || '⚪'} {robot.status}</div>
        {overdue && <span className="overdue-badge">已逾期</span>}
      </div>
      <div className="location">
        {robot.location || <span style={{ color: '#bbb' }}>（无去向信息）</span>}
      </div>
      {robot.borrower && <div className="meta-line">借用人：{robot.borrower}{robot.expected_return_at ? ` · 预计 ${new Date(robot.expected_return_at).toLocaleDateString('zh-CN')} 归还` : ''}</div>}
      {robot.last_inventory_at && <div className="meta-line">最近盘点：{formatShanghaiDate(robot.last_inventory_at)} · {robot.last_inventory_by}</div>}
      <div className="actions" onClick={e => e.stopPropagation()}>
        {robot.lifecycle_status === 'migrated' ? isAdmin && <button onClick={onUndoMigration}>撤销迁移</button> : robot.is_archived ? isAdmin && <button onClick={onRestore}>恢复</button> : <>
          <button onClick={onFlow}>{primaryLabel}</button><button className="secondary" onClick={onInventory}>盘点</button><button className="secondary" onClick={onEdit}>资料</button>{isAdmin&&robot.status==='在库'&&<><button className="danger" onClick={onMigrate}>调出</button><button className="muted-action" onClick={onDelete}>归档</button></>}
        </>}
      </div>
    </div>
  )
}
