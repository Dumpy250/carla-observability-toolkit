async function requestJson(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

function normalizeRunsPayload(data) {
  const runList = Array.isArray(data) ? data : data?.runs
  return Array.isArray(runList) ? runList : []
}

export async function fetchRunsList() {
  const data = await requestJson('/api/runs')
  return normalizeRunsPayload(data)
}

export async function fetchRunDetails(runDirName) {
  return requestJson(`/api/runs/${encodeURIComponent(runDirName)}`)
}
