import http from 'k6/http'
import { check, sleep } from 'k6'

export const options = {
  insecureSkipTLSVerify: true,
  scenarios: {
    single_user: { executor: 'constant-vus', vus: 1, duration: '30s' },
    ten_users: { executor: 'constant-vus', vus: 10, startTime: '35s', duration: '30s' },
    fifty_users: { executor: 'constant-vus', vus: 50, startTime: '70s', duration: '30s' },
  },
  thresholds: { http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<1000'] },
}

const baseUrl = __ENV.BASE_URL || 'https://127.0.0.1:8443'

export default function () {
  const response = http.get(`${baseUrl}/api/v1/system/liveness`)
  check(response, { 'liveness is 200': (value) => value.status === 200 })
  sleep(1)
}
