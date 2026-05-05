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
import KeyValueGrid from '../components/KeyValueGrid.jsx'
import MetricToggleRow from '../components/MetricToggleRow.jsx'
import RunSelector from '../components/RunSelector.jsx'
import StatusMessage from '../components/StatusMessage.jsx'
import { fetchRunDetails, fetchRunsList } from '../services/runsApi.js'
import { normalizeRunExplorerMetrics, sortEventsByTimeline } from '../utils/chartData.js'
import { formatCount, formatFixed } from '../utils/formatters.js'

const EXPLORER_METRICS = [
  { key: 'speed_mps', label: 'Speed' },
  { key: 'throttle', label: 'Throttle' },
  { key: 'brake', label: 'Brake' },
  { key: 'steering', label: 'Steering' },
]

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
        const normalizedRuns = await fetchRunsList()
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

    const loadRunDetails = async () => {
      setDetailsLoading(true)
      setDetailsError('')
      try {
        const data = await fetchRunDetails(selectedRun)
        setRunDetails(data)
      } catch (err) {
        setRunDetails(null)
        setDetailsError(err instanceof Error ? err.message : 'Failed to load selected run')
      } finally {
        setDetailsLoading(false)
      }
    }

    loadRunDetails()
  }, [selectedRun])

  const metadata = runDetails?.metadata ?? {}
  const summary = runDetails?.summary ?? {}
  const metrics = Array.isArray(runDetails?.metrics) ? runDetails.metrics : []
  const events = Array.isArray(runDetails?.events) ? runDetails.events : []
  const chartData = normalizeRunExplorerMetrics(metrics)
  const sortedEvents = sortEventsByTimeline(events)

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
        <h1>Run Explorer</h1>
        <RunSelector
          id="run-a-select"
          label="Run A"
          value={selectedRun}
          onChange={setSelectedRun}
          disabled={runsLoading || runs.length === 0}
          runs={runs}
        />
      </section>

      {runsLoading ? <StatusMessage>Loading runs...</StatusMessage> : null}
      {runsError ? <StatusMessage error>Error loading runs: {runsError}</StatusMessage> : null}
      {!runsLoading && !runsError && runs.length === 0 ? <StatusMessage>No runs available.</StatusMessage> : null}

      {detailsLoading ? <StatusMessage>Loading selected run...</StatusMessage> : null}
      {detailsError ? <StatusMessage error>Error loading selected run: {detailsError}</StatusMessage> : null}

      {runDetails && !detailsLoading ? (
        <>
          <div className="panel-grid">
            <section className="panel">
              <h2>Metadata</h2>
              <KeyValueGrid
                entries={[
                  { key: 'run_id', label: 'run_id', value: metadata.run_id ?? 'N/A' },
                  { key: 'status', label: 'status', value: metadata.status ?? 'N/A' },
                  { key: 'started_at_utc', label: 'started_at_utc', value: metadata.started_at_utc ?? 'N/A' },
                  { key: 'ended_at_utc', label: 'ended_at_utc', value: metadata.ended_at_utc ?? 'N/A' },
                ]}
              />
            </section>

            <section className="panel">
              <h2>Summary</h2>
              <KeyValueGrid
                entries={[
                  { key: 'max_speed_mps', label: 'max_speed_mps', value: formatFixed(summary.max_speed_mps) },
                  { key: 'avg_speed_mps', label: 'avg_speed_mps', value: formatFixed(summary.avg_speed_mps) },
                  {
                    key: 'total_collisions',
                    label: 'total_collisions',
                    value: formatCount(summary.total_collisions),
                  },
                  { key: 'run_duration_s', label: 'run_duration_s', value: formatFixed(summary.run_duration_s) },
                  { key: 'metric_row_count', label: 'metric_row_count', value: formatCount(summary.metric_row_count) },
                  { key: 'event_count', label: 'event_count', value: formatCount(summary.event_count) },
                ]}
              />
            </section>
          </div>

          <section className="panel panel-telemetry">
            <h2>Telemetry</h2>

            <MetricToggleRow
              metrics={EXPLORER_METRICS}
              visibility={metricVisibility}
              onToggle={toggleMetric}
            />

            {chartData.length === 0 ? (
              <StatusMessage>No metrics available for selected run.</StatusMessage>
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
              <StatusMessage>No events found for this run.</StatusMessage>
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
                      {formatFixed(event.sim_time_s)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}

      {!selectedRun && !runsLoading ? <StatusMessage>No selected run.</StatusMessage> : null}
    </main>
  )
}

export default RunExplorer
