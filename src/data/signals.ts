// 시그널 관련 유틸리티 함수
// 실제 시그널 데이터는 Supabase API에서 가져옵니다.

import { Signal, SignalCategory, SignalStatus, SignalImpact, Evidence } from "@/types/signal";

// 은행 거래 타입 (타입 정의만 유지)
export type BankTransactionType = "loan" | "deposit" | "fx" | "pension" | "payroll" | "card";

// 상대 시간 표시
export const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  // P1-3 Fix: Handle future dates and invalid dates gracefully
  if (isNaN(diffMs) || diffMs <= 0) return "방금 전";

  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins}분 전`;
  if (diffHours < 24) return `${diffHours}시간 전`;
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return date.toLocaleDateString('ko-KR');
};

// 날짜 포맷팅
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};

// 은행 거래 타입 레이블
export const getBankTransactionTypeLabel = (type: BankTransactionType): string => {
  const labels: Record<BankTransactionType, string> = {
    loan: "여신",
    deposit: "수신",
    fx: "외환",
    pension: "퇴직연금",
    payroll: "급여",
    card: "카드",
  };
  return labels[type];
};

// ============================================================================
// Signal Count Types and Functions
// ============================================================================

/**
 * Aggregated signal counts computed in a single pass.
 * Used for dashboard KPIs and filtering.
 */
export interface SignalCounts {
  total: number;
  new: number;
  review: number;
  resolved: number;
  todayNew: number;
  risk: number;
  opportunity: number;
  neutral: number;
  direct: number;
  industry: number;
  environment: number;
}

/**
 * Per-corporation signal counts (subset of SignalCounts).
 */
export interface CorporationSignalCounts {
  total: number;
  direct: number;
  industry: number;
  environment: number;
}

/**
 * Computes all signal counts in a single O(n) pass using reduce.
 * Avoids repeated .filter() scans which would result in O(k*n) complexity.
 *
 * @param signals - Array of Signal objects to count
 * @returns SignalCounts object with all aggregated counts
 *
 * Complexity: O(n) where n = signals.length
 * Previous: O(11*n) with 11 separate .filter() calls
 */
export const getSignalCounts = (signals: Signal[]): SignalCounts => {
  // Get today's ISO date prefix (YYYY-MM-DD) for todayNew comparison
  const todayPrefix = new Date().toISOString().slice(0, 10);

  return signals.reduce<SignalCounts>(
    (acc, signal) => {
      // Always increment total
      acc.total++;

      // Status counts (mutually exclusive: new | review | resolved)
      switch (signal.status) {
        case "new":
          acc.new++;
          break;
        case "review":
          acc.review++;
          break;
        case "resolved":
          acc.resolved++;
          break;
      }

      // todayNew: signals with status "new" detected today
      // Matches ISO date prefix (e.g., "2026-01-21")
      if (signal.status === "new" && signal.detectedAt.startsWith(todayPrefix)) {
        acc.todayNew++;
      }

      // Impact counts (mutually exclusive: risk | opportunity | neutral)
      switch (signal.impact) {
        case "risk":
          acc.risk++;
          break;
        case "opportunity":
          acc.opportunity++;
          break;
        case "neutral":
          acc.neutral++;
          break;
      }

      // Category counts (mutually exclusive: direct | industry | environment)
      switch (signal.signalCategory) {
        case "direct":
          acc.direct++;
          break;
        case "industry":
          acc.industry++;
          break;
        case "environment":
          acc.environment++;
          break;
      }

      return acc;
    },
    // Initial accumulator with all counts at zero
    {
      total: 0,
      new: 0,
      review: 0,
      resolved: 0,
      todayNew: 0,
      risk: 0,
      opportunity: 0,
      neutral: 0,
      direct: 0,
      industry: 0,
      environment: 0,
    }
  );
};

/**
 * Computes signal counts for a specific corporation in a single O(n) pass.
 * Filters by corporationId and counts categories simultaneously.
 *
 * @param signals - Array of Signal objects to filter and count
 * @param corpId - Corporation ID to filter by
 * @returns CorporationSignalCounts object with per-corp aggregated counts
 *
 * Complexity: O(n) where n = signals.length
 * Previous: O(4*m) with 4 separate .filter() calls (m = corp signals)
 *           Plus O(n) for initial corp filter = O(n + 4*m)
 */
export const getCorporationSignalCounts = (
  signals: Signal[],
  corpId: string
): CorporationSignalCounts => {
  return signals.reduce<CorporationSignalCounts>(
    (acc, signal) => {
      // Skip signals not belonging to this corporation
      if (signal.corporationId !== corpId) {
        return acc;
      }

      // Increment total for this corporation
      acc.total++;

      // Category counts (mutually exclusive: direct | industry | environment)
      switch (signal.signalCategory) {
        case "direct":
          acc.direct++;
          break;
        case "industry":
          acc.industry++;
          break;
        case "environment":
          acc.environment++;
          break;
      }

      return acc;
    },
    // Initial accumulator with all counts at zero
    {
      total: 0,
      direct: 0,
      industry: 0,
      environment: 0,
    }
  );
};

/**
 * Map type for corporationId -> CorporationSignalCounts lookup.
 */
export type SignalCountsByCorpId = Map<string, CorporationSignalCounts>;

/**
 * Default zero counts returned for corporations with no signals.
 * Defined as const to avoid repeated object allocations.
 */
const ZERO_CORP_SIGNAL_COUNTS: Readonly<CorporationSignalCounts> = {
  total: 0,
  direct: 0,
  industry: 0,
  environment: 0,
};

/**
 * Builds a precomputed map of corporationId -> CorporationSignalCounts
 * by scanning all signals once. Enables O(1) lookup per corporation.
 * Skips signals with missing corporationId.
 *
 * @param signals - Array of Signal objects to index
 * @returns Map where keys are corporationIds and values are aggregated counts
 *
 * Complexity: O(n) where n = signals.length (single pass)
 * Lookup: O(1) per corporation
 *
 * Use case: When rendering M corporations, total complexity becomes O(n + M)
 * instead of O(n * M) when calling getCorporationSignalCounts per row.
 */
export const buildSignalCountsByCorpId = (
  signals: Signal[]
): SignalCountsByCorpId => {
  const map = new Map<string, CorporationSignalCounts>();

  for (const signal of signals) {
    const corpId = signal.corporationId;

    // P1-5 Fix: Skip signals with missing corporationId
    if (!corpId) continue;

    // Get or create counts for this corporation
    let counts = map.get(corpId);
    if (!counts) {
      counts = { total: 0, direct: 0, industry: 0, environment: 0 };
      map.set(corpId, counts);
    }

    // Increment total
    counts.total++;

    // Increment category count (mutually exclusive)
    switch (signal.signalCategory) {
      case "direct":
        counts.direct++;
        break;
      case "industry":
        counts.industry++;
        break;
      case "environment":
        counts.environment++;
        break;
    }
  }

  return map;
};

/**
 * Retrieves signal counts for a corporation from a precomputed map.
 * Returns zero counts safely if the corporation has no signals.
 * Returns a defensive copy to prevent mutation of internal state.
 *
 * @param map - Precomputed SignalCountsByCorpId map
 * @param corpId - Corporation ID to look up
 * @returns Readonly CorporationSignalCounts (zero counts if not found)
 *
 * Complexity: O(1)
 */
export const getCorpSignalCountsFromMap = (
  map: SignalCountsByCorpId,
  corpId: string
): Readonly<CorporationSignalCounts> => {
  const counts = map.get(corpId);
  // P0-1 Fix: Return frozen zero counts or a copy to prevent mutation
  return counts ? { ...counts } : ZERO_CORP_SIGNAL_COUNTS;
};

/**
 * Returns signals sorted by detectedAt in descending order (newest first).
 * Creates a shallow copy before sorting to avoid mutating the input array.
 * Handles invalid dates gracefully by sorting them to the end.
 *
 * @param signals - Array of Signal objects (not mutated)
 * @returns New array sorted by detectedAt descending
 */
export const getSignalTimeline = (signals: Signal[]): Signal[] => {
  // Shallow copy via slice() to preserve immutability of input array
  return signals.slice().sort((a, b) => {
    const timeA = new Date(a.detectedAt).getTime();
    const timeB = new Date(b.detectedAt).getTime();

    // P1-4 Fix: Handle NaN (invalid dates) - sort invalid dates to end
    const validA = !isNaN(timeA);
    const validB = !isNaN(timeB);

    if (!validA && !validB) return 0;  // Both invalid: keep original order
    if (!validA) return 1;              // A invalid: sort A after B
    if (!validB) return -1;             // B invalid: sort B after A

    return timeB - timeA;               // Both valid: descending order
  });
};

// ============================================================================
// Signal Index Types and Lookup Functions
// ============================================================================

/**
 * Index structure for O(1) signal lookups.
 * Built once from signal array, used for repeated lookups.
 */
export interface SignalIndex {
  /** Map of signalId -> Signal for O(1) lookup by ID */
  byId: Map<string, Signal>;
  /** Map of corporationId -> Signal[] for O(1) lookup by corporation */
  byCorpId: Map<string, Signal[]>;
}

/** Empty array returned for corporations with no signals (avoids allocation) */
const EMPTY_SIGNAL_ARRAY: readonly Signal[] = Object.freeze([]);

/**
 * Builds indexes for O(1) signal lookups by ID and corporationId.
 * Single O(n) pass creates both indexes simultaneously.
 * Skips corporationId indexing for signals with missing corporationId.
 *
 * @param signals - Array of Signal objects to index
 * @returns SignalIndex with byId and byCorpId maps
 *
 * Complexity: O(n) build time, O(1) lookup time
 */
export const buildSignalIndex = (signals: Signal[]): SignalIndex => {
  const byId = new Map<string, Signal>();
  const byCorpId = new Map<string, Signal[]>();

  for (const signal of signals) {
    // Index by signal ID (always, if id exists)
    if (signal.id) {
      byId.set(signal.id, signal);
    }

    // P1-5 Fix: Only index by corporationId if it exists
    const corpId = signal.corporationId;
    if (corpId) {
      const corpSignals = byCorpId.get(corpId);
      if (corpSignals) {
        corpSignals.push(signal);
      } else {
        byCorpId.set(corpId, [signal]);
      }
    }
  }

  return { byId, byCorpId };
};

/**
 * Retrieves a signal by ID from precomputed index.
 *
 * @param index - Precomputed SignalIndex
 * @param signalId - Signal ID to look up
 * @returns Signal if found, undefined otherwise
 *
 * Complexity: O(1)
 * Previous (array scan): O(n)
 */
export const getSignalById = (
  index: SignalIndex,
  signalId: string
): Signal | undefined => {
  return index.byId.get(signalId);
};

/**
 * Retrieves all signals for a corporation from precomputed index.
 * Returns empty array if corporation has no signals.
 * Returns a defensive copy to prevent mutation of internal index state.
 *
 * @param index - Precomputed SignalIndex
 * @param corpId - Corporation ID to look up
 * @returns Array of signals (empty if none, shallow copy)
 *
 * Complexity: O(k) where k = signals for this corporation (typically small)
 * Previous (array filter): O(n)
 */
export const getSignalsByCorporationId = (
  index: SignalIndex,
  corpId: string
): Signal[] => {
  const signals = index.byCorpId.get(corpId);
  // P0-2 Fix: Return a copy to prevent mutation of internal index
  return signals ? [...signals] : [];
};
