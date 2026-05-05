function getNumberOrNull(value) {
  return typeof value === 'number' ? value : null
}

export function normalizeRunExplorerMetrics(metrics) {
  const firstValidSimTime = metrics.find((row) => typeof row.sim_time_s === 'number')?.sim_time_s ?? 0
  return metrics
    .map((row) => {
      const simTime = getNumberOrNull(row.sim_time_s)
      return {
        sim_time_s: simTime,
        chart_time_s: simTime === null ? null : simTime - firstValidSimTime,
        speed_mps: getNumberOrNull(row.speed_mps),
        throttle: getNumberOrNull(row.throttle),
        brake: getNumberOrNull(row.brake),
        steering: getNumberOrNull(row.steering),
      }
    })
    .filter((row) => row.chart_time_s !== null)
}

export function normalizeComparisonMetrics(metrics) {
  const firstValidSimTime = metrics.find((row) => typeof row.sim_time_s === 'number')?.sim_time_s ?? 0
  return metrics
    .map((row) => {
      const simTime =
        typeof row.sim_time_s === 'number' && Number.isFinite(row.sim_time_s) ? row.sim_time_s : null
      return {
        chart_time_s: simTime === null ? null : simTime - firstValidSimTime,
        speed_mps: getNumberOrNull(row.speed_mps),
        throttle: getNumberOrNull(row.throttle),
        brake: getNumberOrNull(row.brake),
        steering: getNumberOrNull(row.steering),
      }
    })
    .filter((row) => typeof row.chart_time_s === 'number' && Number.isFinite(row.chart_time_s))
    .sort((a, b) => a.chart_time_s - b.chart_time_s)
}

export function combineChartTimeDomain(chartDataA, chartDataB) {
  const uniqueTimes = new Set()
  chartDataA.forEach((row) => uniqueTimes.add(row.chart_time_s))
  chartDataB.forEach((row) => uniqueTimes.add(row.chart_time_s))
  return [...uniqueTimes].sort((a, b) => a - b).map((value) => ({ chart_time_s: value }))
}

export function sortEventsByTimeline(events) {
  return [...events].sort((a, b) => {
    const aSim = getNumberOrNull(a.sim_time_s)
    const bSim = getNumberOrNull(b.sim_time_s)
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
}
