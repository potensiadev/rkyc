/**
 * EvidenceBackedField Component
 *
 * 근거 기반 필드 표시 컴포넌트
 * - 값과 함께 신뢰도, 출처, 발췌문을 인라인으로 표시
 * - Null-free 정책: 빈 값 시 "추정값" 또는 "정보 없음" 표시
 * - 호버 시 상세 Provenance 정보 표시
 */

import { useState } from 'react';
import { Info, ExternalLink, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';
import type { FieldProvenance, ProfileConfidence } from '@/types/profile';

interface EvidenceBackedFieldProps {
  label: string;
  value: string | number | null | undefined;
  fieldName: string;
  provenance?: FieldProvenance;
  fieldConfidence?: ProfileConfidence;
  format?: 'text' | 'currency' | 'percent' | 'number';
  fallbackLabel?: string;  // 값이 없을 때 표시할 텍스트
  isEstimate?: boolean;    // 추정값 여부
}

// 신뢰도별 색상 및 아이콘
const confidenceConfig: Record<ProfileConfidence, { bg: string; text: string; icon: typeof CheckCircle; label: string }> = {
  HIGH: { bg: 'bg-green-50', text: 'text-green-700', icon: CheckCircle, label: '검증됨' },
  MED: { bg: 'bg-yellow-50', text: 'text-yellow-700', icon: Info, label: '참고' },
  LOW: { bg: 'bg-orange-50', text: 'text-orange-700', icon: AlertTriangle, label: '추정' },
  NONE: { bg: 'bg-gray-50', text: 'text-gray-500', icon: HelpCircle, label: '미확인' },
  CACHED: { bg: 'bg-blue-50', text: 'text-blue-600', icon: Info, label: '캐시' },
  STALE: { bg: 'bg-red-50', text: 'text-red-600', icon: AlertTriangle, label: '만료' },
};

// 금액 포맷팅
function formatKRW(value: number): string {
  if (value >= 1_0000_0000_0000) return `${(value / 1_0000_0000_0000).toFixed(1)}조원`;
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(0)}억원`;
  if (value >= 1_0000) return `${(value / 1_0000).toFixed(0)}만원`;
  return `${value.toLocaleString()}원`;
}

export function EvidenceBackedField({
  label,
  value,
  fieldName,
  provenance,
  fieldConfidence,
  format = 'text',
  fallbackLabel = '정보 없음',
  isEstimate = false,
}: EvidenceBackedFieldProps) {
  const [showDetail, setShowDetail] = useState(false);

  // 값 포맷팅
  const formatValue = (val: string | number | null | undefined): string => {
    if (val === null || val === undefined || val === '') {
      return fallbackLabel;
    }

    if (typeof val === 'number') {
      switch (format) {
        case 'currency':
          return formatKRW(val);
        case 'percent':
          return `${val}%`;
        case 'number':
          return val.toLocaleString();
        default:
          return String(val);
      }
    }

    return String(val);
  };

  const displayValue = formatValue(value);
  const hasValue = value !== null && value !== undefined && value !== '';

  // 신뢰도 결정: provenance > fieldConfidence > 추정
  const confidence: ProfileConfidence =
    provenance?.confidence ||
    fieldConfidence ||
    (isEstimate ? 'LOW' : 'NONE');

  const config = confidenceConfig[confidence];
  const ConfidenceIcon = config.icon;

  return (
    <div className="group relative">
      {/* 기본 표시 */}
      <div className="flex items-start gap-2">
        <span className="w-28 text-muted-foreground shrink-0">{label}</span>
        <div className="flex items-center gap-2 flex-1">
          <span className={`font-medium ${!hasValue ? 'text-muted-foreground italic' : ''}`}>
            {displayValue}
            {isEstimate && hasValue && (
              <span className="text-xs text-orange-600 ml-1">(추정)</span>
            )}
          </span>

          {/* 신뢰도 배지 - 값이 있을 때만 */}
          {hasValue && (
            <button
              onClick={() => setShowDetail(!showDetail)}
              className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] ${config.bg} ${config.text} hover:opacity-80 transition-opacity`}
              title="근거 상세 보기"
            >
              <ConfidenceIcon className="w-3 h-3" />
              <span>{config.label}</span>
            </button>
          )}
        </div>
      </div>

      {/* 상세 Provenance 패널 */}
      {showDetail && provenance && (
        <div className="mt-2 ml-28 p-3 bg-muted/50 rounded-lg border border-border text-xs space-y-2 animate-in slide-in-from-top-2">
          {/* 발췌문 */}
          {provenance.excerpt && (
            <div>
              <span className="text-muted-foreground">근거:</span>
              <p className="mt-0.5 text-foreground italic">"{provenance.excerpt}"</p>
            </div>
          )}

          {/* 출처 URL */}
          {provenance.source_url && (
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">출처:</span>
              <a
                href={provenance.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline truncate max-w-[300px] flex items-center gap-1"
              >
                {new URL(provenance.source_url).hostname}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* 추출일 */}
          {provenance.extraction_date && (
            <div className="text-muted-foreground">
              추출일: {new Date(provenance.extraction_date).toLocaleDateString('ko-KR')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default EvidenceBackedField;
