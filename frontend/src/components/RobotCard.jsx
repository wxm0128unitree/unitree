export default function RobotCard({ robot, onClick, onDelete }) {
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
        <span className={modelClass}>{robot.model}</span>
      </div>
      <div className="holder">
        <span className="holder-icon">👤</span>
        <span className="holder-text">{robot.holder || '未指定'}</span>
      </div>
      <div className={`status status-${robot.status}`}>
        {statusIcon[robot.status] || '⚪'} {robot.status}
      </div>
      <div className="location">
        {robot.location || <span style={{ color: '#bbb' }}>（无去向信息）</span>}
      </div>
      <div className="actions" onClick={e => e.stopPropagation()}>
        <button onClick={onClick}>修改状态</button>
        <button className="danger" onClick={onDelete}>删除</button>
      </div>
    </div>
  )
}
