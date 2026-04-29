import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function RunExplorer() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState('')
  const [runDetails, setRunDetails] = useState(null)
  const [runsLoading, setRunsLoading] = useState(true)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [runsError, setRunsError] = useState('')
  const [detailsError, setDetailsError] = useState('')
  const [metricVisibility, setMetricVisibility] = useState({
    speed_mps: true,
    throttle: true,
    brake: true,
    steering: true,
  })

  useEffect(() => {
    const fetchRuns = async () => {
      setRunsLoading(true)
      setRunsError('')
      try {
        const response = await fetch('/api/runs')
        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`)
        }

        const data = await response.json()
        const runList = Array.isArray(data) ? data : data?.runs
        const normalizedRuns = Array.isArray(runList) ? runList : []
        setRuns(normalizedRuns)
        setSelectedRun(normalizedRuns[0]?.run_dir_name ?? '')
      } catch (err) {
        setRunsError(err instanceof Error ? err.message : 'Failed to load runs')
      } finally {
        setRunsLoading(false)
      }
    }

    fetchRuns()
  }, [])

  useEffect(() => {
    if (!selectedRun) {
      setRunDetails(null)
      return
    }

    const fetchRunDetails = async () => {
      setDetailsLoading(true)
      setDetailsError('')
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(selectedRun)}`)
        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`)
        }

        const data = await response.json()
        setRunDetails(data)
      } catch (err) {
        setRunDetails(null)
        setDetailsError(err instanceof Error ? err.message : 'Failed to load selected run')
      } finally {
        setDetailsLoading(false)
      }
    }

    fetchRunDetails()
  }, [selectedRun])

  const metadata = runDetails?.metadata ?? {}
  const summary = runDetails?.summary ?? {}
  const metrics = Array.isArray(runDetails?.metrics) ? runDetails.metrics : []
  const events = Array.isArray(runDetails?.events) ? runDetails.events : []
  const firstValidSimTime = metrics.find((row) => typeof row.sim_time_s === 'number')?.sim_time_s ?? 0
  const chartData = metrics
    .map((row) => {
      const simTime = typeof row.sim_time_s === 'number' ? row.sim_time_s : null
      return {
        sim_time_s: simTime,
        chart_time_s: simTime === null ? null : simTime - firstValidSimTime,
        speed_mps: typeof row.speed_mps === 'number' ? row.speed_mps : null,
        throttle: typeof row.throttle === 'number' ? row.throttle : null,
        brake: typeof row.brake === 'number' ? row.brake : null,
        steering: typeof row.steering === 'number' ? row.steering : null,
      }
    })
    .filter((row) => row.chart_time_s !== null)
  const sortedEvents = [...events].sort((a, b) => {
    const aSim = typeof a.sim_time_s === 'number' ? a.sim_time_s : null
    const bSim = typeof b.sim_time_s === 'number' ? b.sim_time_s : null
    if (aSim !== null && bSim !== null) {
      return aSim - bSim
    }
    if (aSim !== null && bSim === null) {
      return -1
    }
    if (aSim === null && bSim !== null) {
      return 1
    }
    const aFrame = typeof a.frame === 'number' ? a.frame : Number.POSITIVE_INFINITY
    const bFrame = typeof b.frame === 'number' ? b.frame : Number.POSITIVE_INFINITY
    return aFrame - bFrame
  })

  const toggleMetric = (metricKey) => {
    setMetricVisibility((prev) => ({
      ...prev,
      [metricKey]: !prev[metricKey],
    }))
  }

  const getEventBadgeClass = (eventType) => {
    const normalized = String(eventType ?? '')
      .trim()
      .toLowerCase()
      .replace(/[\s-]+/g, '_')

    if (normalized.includes('collision')) {
      return 'event-badge event-collision'
    }
    if (normalized.includes('lane_invasion')) {
      return 'event-badge event-lane-invasion'
    }
    if (normalized.includes('run_started')) {
      return 'event-badge event-run-started'
    }
    return 'event-badge event-default'
  }

  return (
    <main className="dashboard">
      <section className="panel panel-header">
        <h1>React Dashboard (WIP)</h1>
        <div className="run-selector-row">
          <label htmlFor="run-a-select">Run A</label>
          <select
            id="run-a-select"
            value={selectedRun}
            onChange={(event) => setSelectedRun(event.target.value)}
            disabled={runsLoading || runs.length === 0}
          >
            {runs.map((run) => (
              <option key={run.run_dir_name} value={run.run_dir_name}>
                {run.run_dir_name}
              </option>
            ))}
          </select>
        </div>
      </section>

      {runsLoading ? <p className="status">Loading runs...</p> : null}
      {runsError ? <p className="status status-error">Error loading runs: {runsError}</p> : null}
      {!runsLoading && !runsError && runs.length === 0 ? <p className="status">No runs available.</p> : null}

      {detailsLoading ? <p className="status">Loading selected run...</p> : null}
      {detailsError ? (
        <p className="status status-error">Error loading selected run: {detailsError}</p>
      ) : null}

      {runDetails && !detailsLoading ? (
        <>
          <div className="panel-grid">
            <section className="panel">
              <h2>Metadata</h2>
              <dl className="kv-grid">
                <dt>run_id</dt>
                <dd>{metadata.run_id ?? 'N/A'}</dd>
                <dt>status</dt>
                <dd>{metadata.status ?? 'N/A'}</dd>
                <dt>started_at_utc</dt>
                <dd>{metadata.started_at_utc ?? 'N/A'}</dd>
                <dt>ended_at_utc</dt>
                <dd>{metadata.ended_at_utc ?? 'N/A'}</dd>
              </dl>
            </section>

            <section className="panel">
              <h2>Summary</h2>
              <dl className="kv-grid">
                <dt>max_speed_mps</dt>
                <dd>{summary.max_speed_mps ?? 'N/A'}</dd>
                <dt>avg_speed_mps</dt>
                <dd>{summary.avg_speed_mps ?? 'N/A'}</dd>
                <dt>total_collisions</dt>
                <dd>{summary.total_collisions ?? 'N/A'}</dd>
                <dt>run_duration_s</dt>
                <dd>{summary.run_duration_s ?? 'N/A'}</dd>
                <dt>metric_row_count</dt>
                <dd>{summary.metric_row_count ?? 'N/A'}</dd>
                <dt>event_count</dt>
                <dd>{summary.event_count ?? 'N/A'}</dd>
              </dl>
            </section>
          </div>

          <section className="panel panel-telemetry">
            <h2>Telemetry</h2>

            <div className="metric-toggle-row">
              <label>
                <input
                  type="checkbox"
                  checked={metricVisibility.speed_mps}
                  onChange={() => toggleMetric('speed_mps')}
                />
                Speed
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={metricVisibility.throttle}
                  onChange={() => toggleMetric('throttle')}
                />
                Throttle
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={metricVisibility.brake}
                  onChange={() => toggleMetric('brake')}
                />
                Brake
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={metricVisibility.steering}
                  onChange={() => toggleMetric('steering')}
                />
                Steering
              </label>
            </div>

            {chartData.length === 0 ? (
              <p className="status">No metrics available for selected run.</p>
            ) : (
              <div className="telemetry-chart-wrapper">
                <LineChart
                  width={1200}
                  height={420}
                  data={chartData}
                  margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="chart_time_s"
                    type="number"
                    label={{ value: 'Run Time (s)', position: 'insideBottom', offset: -4 }}
                  />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {metricVisibility.speed_mps ? (
                    <Line
                      type="monotone"
                      dataKey="speed_mps"
                      stroke="#1f77b4"
                      dot={false}
                      connectNulls={false}
                      name="Speed (m/s)"
                    />
                  ) : null}
                  {metricVisibility.throttle ? (
                    <Line
                      type="monotone"
                      dataKey="throttle"
                      stroke="#2ca02c"
                      dot={false}
                      connectNulls={false}
                      name="Throttle"
                    />
                  ) : null}
                  {metricVisibility.brake ? (
                    <Line
                      type="monotone"
                      dataKey="brake"
                      stroke="#d62728"
                      dot={false}
                      connectNulls={false}
                      name="Brake"
                    />
                  ) : null}
                  {metricVisibility.steering ? (
                    <Line
                      type="monotone"
                      dataKey="steering"
                      stroke="#9467bd"
                      dot={false}
                      connectNulls={false}
                      name="Steering"
                    />
                  ) : null}
                </LineChart>
              </div>
            )}
          </section>

          <section className="panel">
            <h2>Event Timeline</h2>
            {sortedEvents.length === 0 ? (
              <p className="status">No events found for this run.</p>
            ) : (
              <ul className="event-list">
                {sortedEvents.map((event, index) => (
                  <li
                    key={`${event.event_type ?? 'unknown'}-${event.frame ?? 'na'}-${event.sim_time_s ?? 'na'}-${index}`}
                    className="event-item"
                  >
                    <span className={getEventBadgeClass(event.event_type)}>
                      {event.event_type ?? 'unknown'}
                    </span>
                    <span>frame: {event.frame ?? 'N/A'}</span>
                    <span>
                      sim_time_s:{' '}
                      {typeof event.sim_time_s === 'number' ? event.sim_time_s : 'N/A'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      {!selectedRun && !runsLoading ? <p className="status">No selected run.</p> : null}
    </main>
  )
}

export default RunExplorer
