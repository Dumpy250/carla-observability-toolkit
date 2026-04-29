import { Fragment, useEffect, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const COMPARISON_FIELDS = [
  { key: 'max_speed_mps', label: 'max_speed_mps', digits: 3 },
  { key: 'avg_speed_mps', label: 'avg_speed_mps', digits: 3 },
  { key: 'total_collisions', label: 'total_collisions', digits: 0 },
  { key: 'run_duration_s', label: 'run_duration_s', digits: 3 },
  { key: 'metric_row_count', label: 'metric_row_count', digits: 0 },
  { key: 'event_count', label: 'event_count', digits: 0 },
]

function CompareRuns() {
  const [runs, setRuns] = useState([])
  const [runsLoading, setRunsLoading] = useState(true)
  const [runsError, setRunsError] = useState('')

  const [runA, setRunA] = useState('')
  const [runB, setRunB] = useState('')

  const [detailsA, setDetailsA] = useState(null)
  const [detailsB, setDetailsB] = useState(null)
  const [detailsLoadingA, setDetailsLoadingA] = useState(false)
  const [detailsLoadingB, setDetailsLoadingB] = useState(false)
  const [detailsErrorA, setDetailsErrorA] = useState('')
  const [detailsErrorB, setDetailsErrorB] = useState('')
  const [metricVisibility, setMetricVisibility] = useState({
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
        setRunA(normalizedRuns[0]?.run_dir_name ?? '')
        setRunB(normalizedRuns[1]?.run_dir_name ?? normalizedRuns[0]?.run_dir_name ?? '')
      } catch (err) {
        setRunsError(err instanceof Error ? err.message : 'Failed to load runs')
      } finally {
        setRunsLoading(false)
      }
    }

    fetchRuns()
  }, [])

  useEffect(() => {
    if (!runA) {
      setDetailsA(null)
      return
    }

    const fetchRunA = async () => {
      setDetailsLoadingA(true)
      setDetailsErrorA('')
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(runA)}`)
        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`)
        }
        const data = await response.json()
        setDetailsA(data)
      } catch (err) {
        setDetailsA(null)
        setDetailsErrorA(err instanceof Error ? err.message : 'Failed to load Run A')
      } finally {
        setDetailsLoadingA(false)
      }
    }

    fetchRunA()
  }, [runA])

  useEffect(() => {
    if (!runB) {
      setDetailsB(null)
      return
    }

    const fetchRunB = async () => {
      setDetailsLoadingB(true)
      setDetailsErrorB('')
      try {
        const response = await fetch(`/api/runs/${encodeURIComponent(runB)}`)
        if (!response.ok) {
          throw new Error(`Request failed: ${response.status}`)
        }
        const data = await response.json()
        setDetailsB(data)
      } catch (err) {
        setDetailsB(null)
        setDetailsErrorB(err instanceof Error ? err.message : 'Failed to load Run B')
      } finally {
        setDetailsLoadingB(false)
      }
    }

    fetchRunB()
  }, [runB])

  const summaryA = detailsA?.summary ?? {}
  const summaryB = detailsB?.summary ?? {}
  const metadataA = detailsA?.metadata ?? {}
  const metadataB = detailsB?.metadata ?? {}
  const metricsA = Array.isArray(detailsA?.metrics) ? detailsA.metrics : []
  const metricsB = Array.isArray(detailsB?.metrics) ? detailsB.metrics : []

  const normalizeMetrics = (metrics) => {
    const firstValidSimTime = metrics.find((row) => typeof row.sim_time_s === 'number')?.sim_time_s ?? 0
    return metrics
      .map((row) => {
        const simTime =
          typeof row.sim_time_s === 'number' && Number.isFinite(row.sim_time_s) ? row.sim_time_s : null
        return {
          chart_time_s: simTime === null ? null : simTime - firstValidSimTime,
          speed_mps: typeof row.speed_mps === 'number' ? row.speed_mps : null,
          throttle: typeof row.throttle === 'number' ? row.throttle : null,
          brake: typeof row.brake === 'number' ? row.brake : null,
          steering: typeof row.steering === 'number' ? row.steering : null,
        }
      })
      .filter((row) => typeof row.chart_time_s === 'number' && Number.isFinite(row.chart_time_s))
      .sort((a, b) => a.chart_time_s - b.chart_time_s)
  }

  const chartDataA = normalizeMetrics(metricsA)
  const chartDataB = normalizeMetrics(metricsB)
  const combinedTimeDomainData = (() => {
    const uniqueTimes = new Set()
    chartDataA.forEach((row) => uniqueTimes.add(row.chart_time_s))
    chartDataB.forEach((row) => uniqueTimes.add(row.chart_time_s))
    return [...uniqueTimes].sort((a, b) => a - b).map((value) => ({ chart_time_s: value }))
  })()

  const formatValue = (value, digits = 3) => {
    if (value === null || value === undefined) {
      return 'N/A'
    }
    if (typeof value !== 'number') {
      return String(value)
    }
    return Number.isFinite(value) ? value.toFixed(digits) : 'N/A'
  }

  const formatDelta = (aValue, bValue, digits = 3) => {
    if (typeof aValue !== 'number' || typeof bValue !== 'number') {
      return 'N/A'
    }
    const delta = bValue - aValue
    const sign = delta > 0 ? '+' : ''
    return `${sign}${delta.toFixed(digits)}`
  }

  const toggleMetric = (metricKey) => {
    setMetricVisibility((prev) => ({
      ...prev,
      [metricKey]: !prev[metricKey],
    }))
  }

  const chartReady =
    !!detailsA &&
    !!detailsB &&
    !detailsLoadingA &&
    !detailsLoadingB &&
    !detailsErrorA &&
    !detailsErrorB

  const hasChartData = chartDataA.length > 0 && chartDataB.length > 0
  const lineProps = {
    dot: false,
    activeDot: false,
    connectNulls: false,
    strokeWidth: 2,
  }

  return (
    <main className="dashboard">
      <section className="panel panel-header">
        <h1>Compare Runs</h1>
        <div className="compare-selector-grid">
          <div className="run-selector-row">
            <label htmlFor="run-a-select">Run A</label>
            <select
              id="run-a-select"
              value={runA}
              onChange={(event) => setRunA(event.target.value)}
              disabled={runsLoading || runs.length === 0}
            >
              {runs.map((run) => (
                <option key={`a-${run.run_dir_name}`} value={run.run_dir_name}>
                  {run.run_dir_name}
                </option>
              ))}
            </select>
          </div>

          <div className="run-selector-row">
            <label htmlFor="run-b-select">Run B</label>
            <select
              id="run-b-select"
              value={runB}
              onChange={(event) => setRunB(event.target.value)}
              disabled={runsLoading || runs.length === 0}
            >
              {runs.map((run) => (
                <option key={`b-${run.run_dir_name}`} value={run.run_dir_name}>
                  {run.run_dir_name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {runsLoading ? <p className="status">Loading runs...</p> : null}
      {runsError ? <p className="status status-error">Error loading runs: {runsError}</p> : null}
      {!runsLoading && !runsError && runs.length === 0 ? <p className="status">No runs available.</p> : null}

      {detailsLoadingA ? <p className="status">Loading Run A...</p> : null}
      {detailsLoadingB ? <p className="status">Loading Run B...</p> : null}
      {detailsErrorA ? <p className="status status-error">Error loading Run A: {detailsErrorA}</p> : null}
      {detailsErrorB ? <p className="status status-error">Error loading Run B: {detailsErrorB}</p> : null}

      <div className="panel-grid">
        <section className="panel">
          <h2>Run A Summary</h2>
          <dl className="kv-grid">
            <dt>run_dir_name</dt>
            <dd>{runA || 'N/A'}</dd>
            <dt>run_id</dt>
            <dd>{metadataA.run_id ?? 'N/A'}</dd>
            <dt>status</dt>
            <dd>{metadataA.status ?? 'N/A'}</dd>
            {COMPARISON_FIELDS.map((field) => (
              <Fragment key={`a-${field.key}`}>
                <dt>{field.label}</dt>
                <dd>{formatValue(summaryA[field.key], field.digits)}</dd>
              </Fragment>
            ))}
          </dl>
        </section>

        <section className="panel">
          <h2>Run B Summary</h2>
          <dl className="kv-grid">
            <dt>run_dir_name</dt>
            <dd>{runB || 'N/A'}</dd>
            <dt>run_id</dt>
            <dd>{metadataB.run_id ?? 'N/A'}</dd>
            <dt>status</dt>
            <dd>{metadataB.status ?? 'N/A'}</dd>
            {COMPARISON_FIELDS.map((field) => (
              <Fragment key={`b-${field.key}`}>
                <dt>{field.label}</dt>
                <dd>{formatValue(summaryB[field.key], field.digits)}</dd>
              </Fragment>
            ))}
          </dl>
        </section>
      </div>

      <section className="panel">
        <h2>Summary Delta (Run B - Run A)</h2>
        <div className="compare-delta-grid">
          <div className="delta-header">Metric</div>
          <div className="delta-header">Run A</div>
          <div className="delta-header">Run B</div>
          <div className="delta-header">Delta</div>
          {COMPARISON_FIELDS.map((field) => (
            <div className="delta-row" key={`delta-${field.key}`}>
              <div>{field.label}</div>
              <div>{formatValue(summaryA[field.key], field.digits)}</div>
              <div>{formatValue(summaryB[field.key], field.digits)}</div>
              <div>{formatDelta(summaryA[field.key], summaryB[field.key], field.digits)}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel panel-telemetry">
        <h2>Speed Comparison</h2>
        {!chartReady ? (
          <p className="status">Load both runs to view telemetry comparison.</p>
        ) : !hasChartData ? (
          <p className="status">
            One or both selected runs have no metrics. Select runs with telemetry data.
          </p>
        ) : (
          <div className="telemetry-chart-wrapper compare-chart-wrapper">
            <LineChart
              width={1200}
              height={360}
              data={combinedTimeDomainData}
              margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="chart_time_s"
                label={{ value: 'Run Time (s)', position: 'insideBottom', offset: -4 }}
              />
              <YAxis label={{ value: 'Speed (m/s)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                data={chartDataA}
                dataKey="speed_mps"
                stroke="#3B82F6"
                name="Speed (A)"
                {...lineProps}
              />
              <Line
                type="monotone"
                data={chartDataB}
                dataKey="speed_mps"
                stroke="#F59E0B"
                strokeDasharray="8 4"
                name="Speed (B)"
                {...lineProps}
              />
            </LineChart>
          </div>
        )}
      </section>

      <section className="panel panel-telemetry">
        <h2>Control Inputs Comparison</h2>
        <div className="metric-toggle-row">
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

        {!chartReady ? (
          <p className="status">Load both runs to view telemetry comparison.</p>
        ) : !hasChartData ? (
          <p className="status">
            One or both selected runs have no metrics. Select runs with telemetry data.
          </p>
        ) : (
          <div className="telemetry-chart-wrapper compare-chart-wrapper">
            <LineChart
              width={1200}
              height={420}
              data={combinedTimeDomainData}
              margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey="chart_time_s"
                label={{ value: 'Run Time (s)', position: 'insideBottom', offset: -4 }}
              />
              <YAxis
                domain={[-1, 1]}
                label={{ value: 'Control Value', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip />
              <Legend />
              {metricVisibility.throttle ? (
                <>
                  <Line
                    type="monotone"
                    data={chartDataA}
                    dataKey="throttle"
                    stroke="#22C55E"
                    name="Throttle (A)"
                    {...lineProps}
                  />
                  <Line
                    type="monotone"
                    data={chartDataB}
                    dataKey="throttle"
                    stroke="#22C55E"
                    strokeDasharray="8 4"
                    name="Throttle (B)"
                    {...lineProps}
                  />
                </>
              ) : null}
              {metricVisibility.brake ? (
                <>
                  <Line
                    type="monotone"
                    data={chartDataA}
                    dataKey="brake"
                    stroke="#EF4444"
                    name="Brake (A)"
                    {...lineProps}
                  />
                  <Line
                    type="monotone"
                    data={chartDataB}
                    dataKey="brake"
                    stroke="#EF4444"
                    strokeDasharray="8 4"
                    name="Brake (B)"
                    {...lineProps}
                  />
                </>
              ) : null}
              {metricVisibility.steering ? (
                <>
                  <Line
                    type="monotone"
                    data={chartDataA}
                    dataKey="steering"
                    stroke="#A855F7"
                    name="Steering (A)"
                    {...lineProps}
                  />
                  <Line
                    type="monotone"
                    data={chartDataB}
                    dataKey="steering"
                    stroke="#A855F7"
                    strokeDasharray="8 4"
                    name="Steering (B)"
                    {...lineProps}
                  />
                </>
              ) : null}
            </LineChart>
          </div>
        )}
      </section>
    </main>
  )
}

export default CompareRuns
