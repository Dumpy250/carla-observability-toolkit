function RunSelector({ id, label, value, onChange, disabled, runs, optionKeyPrefix = '' }) {
  return (
    <div className="run-selector-row">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
        {runs.map((run) => (
          <option key={`${optionKeyPrefix}${run.run_dir_name}`} value={run.run_dir_name}>
            {run.run_dir_name}
          </option>
        ))}
      </select>
    </div>
  )
}

export default RunSelector
