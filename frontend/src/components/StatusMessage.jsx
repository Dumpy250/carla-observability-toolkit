function StatusMessage({ children, error = false }) {
  return <p className={`status${error ? ' status-error' : ''}`}>{children}</p>
}

export default StatusMessage
