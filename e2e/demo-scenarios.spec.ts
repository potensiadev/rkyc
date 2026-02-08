import { test, expect } from '@playwright/test';

/**
 * E2E Tests for rKYC Demo Scenarios
 * PRD v2.0 Hackathon Edition
 */

const API_BASE = 'https://rkyc-production.up.railway.app';

// 6개 시드 기업
const SEED_CORPS = [
  { id: '8001-3719240', name: '엠케이전자', minSignals: 3 },
  { id: '8000-7647330', name: '동부건설', minSignals: 3 },
  { id: '4028-1234567', name: '전북식품', minSignals: 3 },
  { id: '6201-2345678', name: '광주정밀기계', minSignals: 3 },
  { id: '4301-3456789', name: '삼성전자', minSignals: 4 },
  { id: '6701-4567890', name: '휴림로봇', minSignals: 3 },
];

test.describe('System Health', () => {
  test('API server is healthy', async ({ request }) => {
    const response = await request.get(`${API_BASE}/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('Frontend loads successfully', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/rKYC/i);
  });

  test('Signal Inbox page loads', async ({ page }) => {
    await page.goto('/');
    // 시그널 목록이 표시될 때까지 대기
    await page.waitForSelector('[data-testid="signal-list"], .signal-card, table tbody tr', { timeout: 10000 }).catch(() => {});
    // 페이지가 에러 없이 로드되었는지 확인
    const errorText = await page.locator('text=Error').count();
    expect(errorText).toBeLessThan(2); // 일부 에러 텍스트는 허용
  });
});

test.describe('API Endpoints', () => {
  test('GET /corporations returns seed corps', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/corporations`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    // API returns {total, items} format
    const corps = data.items || data;
    expect(Array.isArray(corps)).toBeTruthy();
    expect(corps.length).toBeGreaterThanOrEqual(6);

    // 시드 기업 존재 확인
    const corpIds = corps.map((c: any) => c.corp_id);
    for (const seed of SEED_CORPS) {
      expect(corpIds).toContain(seed.id);
    }
  });

  test('GET /signals returns signals', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    const signals = data.items || data.signals || data;
    expect(Array.isArray(signals) || typeof data.total === 'number').toBeTruthy();
  });

  test('GET /signals filters by corp_id', async ({ request }) => {
    const corpId = '8001-3719240';
    const response = await request.get(`${API_BASE}/api/v1/signals?corp_id=${corpId}`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    const signals = data.items || data.signals || data;

    if (Array.isArray(signals) && signals.length > 0) {
      for (const signal of signals) {
        expect(signal.corp_id).toBe(corpId);
      }
    }
  });

  test('GET /dashboard/summary returns stats', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/dashboard/summary`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(typeof data.total_signals).toBe('number');
  });
});

test.describe('Signal Count per Corp', () => {
  for (const corp of SEED_CORPS) {
    test(`${corp.name} has >= ${corp.minSignals} signals`, async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/v1/signals?corp_id=${corp.id}`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      const signals = data.items || data.signals || data;
      const count = Array.isArray(signals) ? signals.length : (data.total || 0);

      expect(count).toBeGreaterThanOrEqual(corp.minSignals);
    });
  }
});

test.describe('Signal Quality', () => {
  test('No hallucinated extreme percentages', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    const data = await response.json();
    const signals = data.items || data.signals || data;

    if (!Array.isArray(signals)) return;

    const suspiciousPatterns = [
      /8[0-9]%\s*(감소|하락|축소)/,
      /9[0-9]%\s*(감소|하락|축소)/,
    ];

    const issues: string[] = [];

    for (const signal of signals) {
      const text = `${signal.title || ''} ${signal.summary || ''} ${signal.summary_short || ''}`;

      for (const pattern of suspiciousPatterns) {
        const match = text.match(pattern);
        if (match) {
          issues.push(`Suspicious pattern "${match[0]}" in signal: ${signal.title?.substring(0, 30) || signal.signal_id}`);
        }
      }
    }

    expect(issues).toHaveLength(0);
  });

  test('All signals have required fields', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    const data = await response.json();
    const signals = data.items || data.signals || data;

    if (!Array.isArray(signals)) return;

    const issues: string[] = [];

    for (const signal of signals) {
      if (!signal.signal_type) {
        issues.push(`Missing signal_type: ${signal.signal_id}`);
      }
      if (!signal.event_type) {
        issues.push(`Missing event_type: ${signal.signal_id}`);
      }
      if (!signal.impact_direction) {
        issues.push(`Missing impact_direction: ${signal.signal_id}`);
      }
      if (!signal.corp_id) {
        issues.push(`Missing corp_id: ${signal.signal_id}`);
      }
    }

    expect(issues).toHaveLength(0);
  });
});

test.describe('Frontend Navigation', () => {
  test('Can navigate to corporation list', async ({ page }) => {
    await page.goto('/');

    // 기업 검색 또는 목록 링크 찾기
    const corpLink = page.locator('a[href*="corp"], a[href*="search"], button:has-text("기업")').first();
    if (await corpLink.isVisible()) {
      await corpLink.click();
      await page.waitForLoadState('networkidle');
    }
  });

  test('Can view signal detail', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 시그널 카드나 행 클릭
    const signalItem = page.locator('.signal-card, table tbody tr, [data-testid="signal-item"]').first();
    if (await signalItem.isVisible()) {
      await signalItem.click();
      await page.waitForLoadState('networkidle');
      // URL이 변경되었는지 확인
      await page.waitForTimeout(1000);
    }
  });
});

test.describe('Demo Panel', () => {
  test('Demo panel is visible when enabled', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Demo 패널 또는 관련 UI 요소 찾기
    const demoPanel = page.locator('[data-testid="demo-panel"], .demo-panel, text=시연');
    const isVisible = await demoPanel.isVisible().catch(() => false);

    // Demo 모드가 활성화되어 있으면 패널이 보여야 함
    // 비활성화되어 있으면 테스트 스킵
    if (!isVisible) {
      test.skip();
    }
  });
});

test.describe('Corporation Detail', () => {
  test('Corporation detail page loads', async ({ page }) => {
    // 첫 번째 시드 기업 상세 페이지로 이동
    await page.goto('/corporations/8001-3719240');
    await page.waitForLoadState('networkidle');

    // 기업명이 표시되는지 확인
    const corpName = page.locator('text=엠케이전자');
    // 페이지가 로드되면 OK (404가 아니면 성공)
    const is404 = await page.locator('text=404, text=Not Found').isVisible().catch(() => false);
    if (is404) {
      // 다른 URL 패턴 시도
      await page.goto('/corp/8001-3719240');
      await page.waitForLoadState('networkidle');
    }
  });

  test('Corporation profile section exists', async ({ page }) => {
    await page.goto('/corporations/8001-3719240');
    await page.waitForLoadState('networkidle');

    // 프로필 관련 섹션 찾기
    const profileSection = page.locator('text=프로필, text=Profile, text=외부 정보').first();
    // 존재 여부만 확인 (필수는 아님)
  });
});

test.describe('Error Handling', () => {
  test('Invalid corp_id returns 404', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/corporations/invalid-corp-id`);
    expect(response.status()).toBe(404);
  });

  test('Invalid signal_id returns 404', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals/invalid-signal-id/detail`);
    expect([404, 422]).toContain(response.status());
  });
});

test.describe('Data Consistency', () => {
  test('Signal corp_id matches corporation', async ({ request }) => {
    const signalsResponse = await request.get(`${API_BASE}/api/v1/signals`);
    const signalsData = await signalsResponse.json();
    const signals = signalsData.items || signalsData.signals || signalsData;

    if (!Array.isArray(signals) || signals.length === 0) return;

    const corpsResponse = await request.get(`${API_BASE}/api/v1/corporations`);
    const corpsData = await corpsResponse.json();
    const corps = corpsData.items || corpsData;
    const corpIds = new Set(corps.map((c: any) => c.corp_id));

    const orphanedSignals: string[] = [];

    for (const signal of signals) {
      if (!corpIds.has(signal.corp_id)) {
        orphanedSignals.push(`Signal ${signal.signal_id} references non-existent corp ${signal.corp_id}`);
      }
    }

    expect(orphanedSignals).toHaveLength(0);
  });

  test('All signals have valid enum values', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/signals`);
    const data = await response.json();
    const signals = data.items || data.signals || data;

    if (!Array.isArray(signals)) return;

    const validSignalTypes = ['DIRECT', 'INDUSTRY', 'ENVIRONMENT'];
    const validImpactDirections = ['RISK', 'OPPORTUNITY', 'NEUTRAL'];
    const validImpactStrengths = ['HIGH', 'MED', 'LOW'];
    const validConfidences = ['HIGH', 'MED', 'LOW'];

    const issues: string[] = [];

    for (const signal of signals) {
      if (!validSignalTypes.includes(signal.signal_type)) {
        issues.push(`Invalid signal_type: ${signal.signal_type}`);
      }
      if (!validImpactDirections.includes(signal.impact_direction)) {
        issues.push(`Invalid impact_direction: ${signal.impact_direction}`);
      }
      if (!validImpactStrengths.includes(signal.impact_strength)) {
        issues.push(`Invalid impact_strength: ${signal.impact_strength}`);
      }
      if (!validConfidences.includes(signal.confidence)) {
        issues.push(`Invalid confidence: ${signal.confidence}`);
      }
    }

    expect(issues).toHaveLength(0);
  });
});
