import { formatShanghaiDate } from '../utils/datetime'

export default function RobotCard({ robot, onClick, onDelete, onEdit, onInventory, onRestore, onMigrate, onUndoMigration }) {
  const statusIcon = {
    '在库': '🟢',
    '借出': '🔵',
    '维修中': '🟠',
  }
  const modelClass = `model-tag model-${robot.model}`

  return (
    <div className="robot-card" onClick={onClick}>
      <div className="row1">
        <span className="code">{robot.asset_code}</span>
        <span className={modelClass}>{robot.device_branch === 'training_platform' || robot.model === '实训台' ? '实训台' : robot.model}</span>
      </div>
      <div className="holder">
        <span className="holder-icon">👤</span>
        <span className="holder-text">{[robot.owner_department, robot.owner_name || robot.holder].filter(Boolean).join(' / ') || '未指定归属'}</span>
      </div>
      <div className={`status status-${robot.status}`}>
        {statusIcon[robot.status] || '⚪'} {robot.status}
      </div>
      <div className="location">
        {robot.location || <span style={{ color: '#bbb' }}>（无去向信息）</span>}
      </div>
      {robot.borrower && <div className="meta-line">借用人：{robot.borrower}{robot.expected_return_at ? ` · 预计 ${new Date(robot.expected_return_at).toLocaleDateString('zh-CN')} 归还` : ''}</div>}
      {robot.last_inventory_at && <div className="meta-line">最近盘点：{formatShanghaiDate(robot.last_inventory_at)} · {robot.last_inventory_by}</div>}
      <div className="actions" onClick={e => e.stopPropagation()}>
        {robot.lifecycle_status === 'migrated' ? <button onClick={onUndoMigration}>撤销迁移</button> : robot.is_archived ? <button onClick={onRestore}>恢复</button> : <>
          <button onClick={onClick}>状态</button><button className="secondary" onClick={onEdit}>编辑</button><button className="secondary" onClick={onInventory}>盘点</button><button className="danger" onClick={onMigrate}>迁移</button><button className="muted-action" onClick={onDelete}>归档</button>
        </>}
      </div>
    </div>
  )
}
