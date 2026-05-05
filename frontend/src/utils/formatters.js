export function formatFixed(value, digits = 3) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'N/A'
  }
  return value.toFixed(digits)
}

export function formatCount(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'N/A'
  }
  return Math.round(value).toString()
}

export function formatValue(value, digits = 3) {
  if (value === null || value === undefined) {
    return 'N/A'
  }
  if (typeof value !== 'number') {
    return String(value)
  }
  return Number.isFinite(value) ? value.toFixed(digits) : 'N/A'
}

export function formatDelta(aValue, bValue, digits = 3) {
  if (typeof aValue !== 'number' || typeof bValue !== 'number') {
    return 'N/A'
  }
  const delta = bValue - aValue
  const sign = delta > 0 ? '+' : ''
  return `${sign}${delta.toFixed(digits)}`
}
