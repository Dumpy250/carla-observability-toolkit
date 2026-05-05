function MetricToggleRow({ metrics, visibility, onToggle }) {
  return (
    <div className="metric-toggle-row">
      {metrics.map((metric) => (
        <label key={metric.key}>
          <input
            type="checkbox"
            checked={Boolean(visibility[metric.key])}
            onChange={() => onToggle(metric.key)}
          />
          {metric.label}
        </label>
      ))}
    </div>
  )
}

export default MetricToggleRow
