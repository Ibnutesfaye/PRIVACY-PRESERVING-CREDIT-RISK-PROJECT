import http from 'k6/http'
import { check, sleep } from 'k6'
import { Counter, Trend } from 'k6/metrics'

const encryptedLatency = new Trend('encrypted_job_latency', true)
const encryptedFailures = new Counter('encrypted_job_failures')

export const options = {
  scenarios: {
    one: { executor: 'constant-vus', vus: 1, duration: '30s' },
    ten: { executor: 'constant-vus', vus: 10, startTime: '35s', duration: '30s' },
    twenty_five: { executor: 'constant-vus', vus: 25, startTime: '70s', duration: '30s' },
    fifty: { executor: 'constant-vus', vus: 50, startTime: '105s', duration: '30s' },
    one_hundred: { executor: 'constant-vus', vus: 100, startTime: '140s', duration: '30s' },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
    encrypted_job_failures: ['count==0'],
  },
}

const baseUrl = __ENV.BASE_URL
const token = __ENV.ACCESS_TOKEN
const fixture = __ENV.ENCRYPTED_FIXTURE

export default function () {
  if (!baseUrl) throw new Error('BASE_URL is required')
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const live = http.get(`${baseUrl}/api/v1/system/liveness`)
  check(live, { 'liveness 200': (response) => response.status === 200 })

  if (token) {
    const dashboard = http.get(`${baseUrl}/api/v1/admin/dashboard/overview`, { headers })
    check(dashboard, { 'dashboard authorized': (response) => response.status === 200 })
  }
  if (token && fixture) {
    const response = http.post(`${baseUrl}/api/v1/fhe/evaluate`, fixture, {
      headers: { ...headers, 'Content-Type': 'application/json' }, timeout: '180s',
    })
    encryptedLatency.add(response.timings.duration)
    if (response.status !== 200) encryptedFailures.add(1)
    check(response, { 'encrypted evaluation 200': (value) => value.status === 200 })
  }
  sleep(1)
}

