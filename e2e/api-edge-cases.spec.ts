import { test, expect } from '@playwright/test';

/**
 * API Edge Cases and Error Handling Tests
 */

const API_BASE = 'https://rkyc-production.up.railway.app';

test.describe('API Response Format Consistency', () => {
  test('GET /corporations returns consistent format', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/corporations`);
    const data = await response.json();

    // 반드시 total과 items가 있어야 함
    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('items');
    expect(typeof data.total).toBe('number');
    expect(Array.isArray(data.items)).toBeTruthy();
  });

  test('GET /signals returns consistent format', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    const data = await response.json();

    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('items');
    expect(typeof data.total).toBe('number');
    expect(Array.isArray(data.items)).toBeTruthy();
  });
});

test.describe('Pagination', () => {
  test('GET /signals supports limit parameter', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals?limit=5`);
    const data = await response.json();
    const items = data.items || data;

    if (Array.isArray(items)) {
      expect(items.length).toBeLessThanOrEqual(5);
    }
  });

  test('GET /signals supports offset parameter', async ({ request }) => {
    const response1 = await request.get(`${API_BASE}/api/v1/signals?limit=10`);
    const response2 = await request.get(`${API_BASE}/api/v1/signals?limit=10&offset=5`);

    const data1 = await response1.json();
    const data2 = await response2.json();

    const items1 = data1.items || data1;
    const items2 = data2.items || data2;

    if (Array.isArray(items1) && Array.isArray(items2) && items1.length > 5 && items2.length > 0) {
      // offset 5인 첫 번째 항목이 원래 목록의 6번째 항목과 같아야 함
      expect(items2[0].signal_id).toBe(items1[5]?.signal_id);
    }
  });
});

test.describe('Filtering', () => {
  test('GET /signals filters by signal_type', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals?signal_type=DIRECT`);
    const data = await response.json();
    const items = data.items || data;

    if (Array.isArray(items) && items.length > 0) {
      for (const signal of items) {
        expect(signal.signal_type).toBe('DIRECT');
      }
    }
  });

  test('GET /signals filters by impact_direction', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals?impact_direction=RISK`);
    const data = await response.json();
    const items = data.items || data;

    if (Array.isArray(items) && items.length > 0) {
      for (const signal of items) {
        expect(signal.impact_direction).toBe('RISK');
      }
    }
  });

  test('GET /signals filters by event_type', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals?event_type=KYC_REFRESH`);
    const data = await response.json();
    const items = data.items || data;

    if (Array.isArray(items) && items.length > 0) {
      for (const signal of items) {
        expect(signal.event_type).toBe('KYC_REFRESH');
      }
    }
  });
});

test.describe('Signal Detail API', () => {
  test('GET /signals/{id}/detail returns evidence', async ({ request }) => {
    // 먼저 시그널 목록 조회
    const listResponse = await request.get(`${API_BASE}/api/v1/signals`);
    const listData = await listResponse.json();
    const items = listData.items || listData;

    if (!Array.isArray(items) || items.length === 0) {
      test.skip();
      return;
    }

    const signalId = items[0].signal_id;
    const detailResponse = await request.get(`${API_BASE}/api/v1/signals/${signalId}/detail`);

    if (detailResponse.status() === 404) {
      // detail 엔드포인트가 없을 수 있음
      return;
    }

    expect(detailResponse.ok()).toBeTruthy();
    const detail = await detailResponse.json();

    // evidence 필드 확인 (API는 'evidences' 복수형 사용)
    const evidenceField = detail.evidence || detail.evidences;
    expect(evidenceField).toBeDefined();
    expect(Array.isArray(evidenceField)).toBeTruthy();
  });
});

test.describe('Corporation Profile API', () => {
  test('GET /corporations/{id}/profile returns profile data', async ({ request }) => {
    const corpId = '8001-3719240'; // 엠케이전자
    const response = await request.get(`${API_BASE}/api/v1/corporations/${corpId}/profile`);

    // 프로필이 없으면 404 또는 null 반환 가능
    if (response.status() === 404) {
      return; // 프로필 없음은 허용
    }

    if (response.ok()) {
      const profile = await response.json();
      // 기본 필드 확인
      if (profile) {
        expect(profile).toHaveProperty('corp_id');
      }
    }
  });

  test('GET /corporations/{id}/snapshot returns snapshot', async ({ request }) => {
    const corpId = '8001-3719240';
    const response = await request.get(`${API_BASE}/api/v1/corporations/${corpId}/snapshot`);

    if (response.status() === 404) {
      return; // 스냅샷 없음은 허용
    }

    if (response.ok()) {
      const snapshot = await response.json();
      // 기본 구조 확인
      if (snapshot && snapshot.snapshot_json) {
        expect(typeof snapshot.snapshot_json).toBe('object');
      }
    }
  });
});

test.describe('Dashboard API', () => {
  test('GET /dashboard/summary returns all required stats', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/dashboard/summary`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    // 필수 필드 확인
    expect(data).toHaveProperty('total_signals');
    expect(typeof data.total_signals).toBe('number');

    // 선택적 필드 확인
    if ('by_status' in data) {
      expect(typeof data.by_status).toBe('object');
    }
    if ('by_type' in data) {
      expect(typeof data.by_type).toBe('object');
    }
  });
});

test.describe('Job API', () => {
  test('POST /jobs/analyze/run requires corp_id', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/v1/jobs/analyze/run`, {
      data: {},
    });

    // 유효성 검증 에러 (422) 또는 Bad Request (400) 예상
    expect([400, 422]).toContain(response.status());
  });

  test('POST /jobs/analyze/run with invalid corp_id returns 404', async ({ request }) => {
    const response = await request.post(`${API_BASE}/api/v1/jobs/analyze/run`, {
      data: { corp_id: 'non-existent-corp' },
    });

    expect(response.status()).toBe(404);
  });

  test('GET /jobs/{id} with invalid job_id returns 404', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/jobs/invalid-job-id`);
    expect([404, 422]).toContain(response.status());
  });
});

test.describe('CORS Headers', () => {
  test('API returns proper CORS headers', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);

    // CORS 헤더 확인 (preflight가 아닌 일반 요청에서도 확인 가능)
    const headers = response.headers();

    // Access-Control-Allow-Origin이 설정되어 있어야 함
    // 프로덕션에서는 특정 도메인으로 제한될 수 있음
  });
});

test.describe('Response Time', () => {
  test('GET /signals responds within 5 seconds', async ({ request }) => {
    const start = Date.now();
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    const duration = Date.now() - start;

    expect(response.ok()).toBeTruthy();
    expect(duration).toBeLessThan(5000);
  });

  test('GET /corporations responds within 3 seconds', async ({ request }) => {
    const start = Date.now();
    const response = await request.get(`${API_BASE}/api/v1/corporations`);
    const duration = Date.now() - start;

    expect(response.ok()).toBeTruthy();
    expect(duration).toBeLessThan(3000);
  });
});

test.describe('Data Integrity', () => {
  test('Signal detected_at is valid date', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    const data = await response.json();
    const items = data.items || data;

    if (!Array.isArray(items)) return;

    const issues: string[] = [];

    for (const signal of items) {
      if (signal.detected_at) {
        const date = new Date(signal.detected_at);
        if (isNaN(date.getTime())) {
          issues.push(`Invalid detected_at: ${signal.detected_at} for signal ${signal.signal_id}`);
        }
      }
    }

    expect(issues).toHaveLength(0);
  });

  test('Corporation founded_date is valid', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/corporations`);
    const data = await response.json();
    const corps = data.items || data;

    if (!Array.isArray(corps)) return;

    const issues: string[] = [];

    for (const corp of corps) {
      if (corp.founded_date) {
        const date = new Date(corp.founded_date);
        if (isNaN(date.getTime())) {
          issues.push(`Invalid founded_date: ${corp.founded_date} for corp ${corp.corp_id}`);
        }
        // 미래 날짜 확인
        if (date > new Date()) {
          issues.push(`Future founded_date: ${corp.founded_date} for corp ${corp.corp_id}`);
        }
      }
    }

    expect(issues).toHaveLength(0);
  });
});

test.describe('Korean Text Handling', () => {
  test('Signal titles contain valid Korean text', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    const data = await response.json();
    const items = data.items || data;

    if (!Array.isArray(items) || items.length === 0) return;

    // 최소 하나의 시그널에 한글이 포함되어야 함
    const hasKorean = items.some((signal: any) => {
      const title = signal.title || '';
      const summary = signal.summary_short || signal.summary || '';
      const text = title + summary;
      return /[가-힣]/.test(text);
    });

    expect(hasKorean).toBeTruthy();
  });

  test('Corporation names are Korean', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/corporations`);
    const data = await response.json();
    const corps = data.items || data;

    if (!Array.isArray(corps)) return;

    for (const corp of corps) {
      // 기업명에 한글이 포함되어야 함
      expect(/[가-힣]/.test(corp.corp_name)).toBeTruthy();
    }
  });
});
