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
import { combineChartTimeDomain, normalizeComparisonMetrics } from '../utils/chartData.js'
import { formatDelta, formatValue } from '../utils/formatters.js'

const COMPARISON_FIELDS = [
  { key: 'max_speed_mps', label: 'max_speed_mps', digits: 3 },
  { key: 'avg_speed_mps', label: 'avg_speed_mps', digits: 3 },
  { key: 'total_collisions', label: 'total_collisions', digits: 0 },
  { key: 'run_duration_s', label: 'run_duration_s', digits: 3 },
  { key: 'metric_row_count', label: 'metric_row_count', digits: 0 },
  { key: 'event_count', label: 'event_count', digits: 0 },
]

const CONTROL_INPUT_METRICS = [
  { key: 'throttle', label: 'Throttle' },
  { key: 'brake', label: 'Brake' },
  { key: 'steering', label: 'Steering' },
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
        const normalizedRuns = await fetchRunsList()
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
        const data = await fetchRunDetails(runA)
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
        const data = await fetchRunDetails(runB)
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
  const chartDataA = normalizeComparisonMetrics(metricsA)
  const chartDataB = normalizeComparisonMetrics(metricsB)
  const combinedTimeDomainData = combineChartTimeDomain(chartDataA, chartDataB)

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
          <RunSelector
            id="run-a-select"
            label="Run A"
            value={runA}
            onChange={setRunA}
            disabled={runsLoading || runs.length === 0}
            runs={runs}
            optionKeyPrefix="a-"
          />
          <RunSelector
            id="run-b-select"
            label="Run B"
            value={runB}
            onChange={setRunB}
            disabled={runsLoading || runs.length === 0}
            runs={runs}
            optionKeyPrefix="b-"
          />
        </div>
      </section>

      {runsLoading ? <StatusMessage>Loading runs...</StatusMessage> : null}
      {runsError ? <StatusMessage error>Error loading runs: {runsError}</StatusMessage> : null}
      {!runsLoading && !runsError && runs.length === 0 ? <StatusMessage>No runs available.</StatusMessage> : null}

      {detailsLoadingA ? <StatusMessage>Loading Run A...</StatusMessage> : null}
      {detailsLoadingB ? <StatusMessage>Loading Run B...</StatusMessage> : null}
      {detailsErrorA ? <StatusMessage error>Error loading Run A: {detailsErrorA}</StatusMessage> : null}
      {detailsErrorB ? <StatusMessage error>Error loading Run B: {detailsErrorB}</StatusMessage> : null}

      <div className="panel-grid">
        <section className="panel">
          <h2>Run A Summary</h2>
          <KeyValueGrid
            entries={[
              { key: 'a-run_dir_name', label: 'run_dir_name', value: runA || 'N/A' },
              { key: 'a-run_id', label: 'run_id', value: metadataA.run_id ?? 'N/A' },
              { key: 'a-status', label: 'status', value: metadataA.status ?? 'N/A' },
              ...COMPARISON_FIELDS.map((field) => ({
                key: `a-${field.key}`,
                label: field.label,
                value: formatValue(summaryA[field.key], field.digits),
              })),
            ]}
          />
        </section>

        <section className="panel">
          <h2>Run B Summary</h2>
          <KeyValueGrid
            entries={[
              { key: 'b-run_dir_name', label: 'run_dir_name', value: runB || 'N/A' },
              { key: 'b-run_id', label: 'run_id', value: metadataB.run_id ?? 'N/A' },
              { key: 'b-status', label: 'status', value: metadataB.status ?? 'N/A' },
              ...COMPARISON_FIELDS.map((field) => ({
                key: `b-${field.key}`,
                label: field.label,
                value: formatValue(summaryB[field.key], field.digits),
              })),
            ]}
          />
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
          <StatusMessage>Load both runs to view telemetry comparison.</StatusMessage>
        ) : !hasChartData ? (
          <StatusMessage>
            One or both selected runs have no metrics. Select runs with telemetry data.
          </StatusMessage>
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
        <MetricToggleRow
          metrics={CONTROL_INPUT_METRICS}
          visibility={metricVisibility}
          onToggle={toggleMetric}
        />

        {!chartReady ? (
          <StatusMessage>Load both runs to view telemetry comparison.</StatusMessage>
        ) : !hasChartData ? (
          <StatusMessage>
            One or both selected runs have no metrics. Select runs with telemetry data.
          </StatusMessage>
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
