/**
 * EvidenceMap Component
 *
 * 근거-주장 연결 시각화 컴포넌트
 * - 필드별 출처 매핑을 시각적으로 표시
 * - 감사 가능성(Auditability) 향상
 * - 월가 수준 IB/신용분석 레포트 스타일
 */

import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  ExternalLink,
  CheckCircle,
  AlertTriangle,
  Info,
  HelpCircle,
  FileText,
  Link2,
  Globe,
} from 'lucide-react';
import type { FieldProvenance, ProfileConfidence } from '@/types/profile';
import { Button } from '@/components/ui/button';

interface EvidenceMapProps {
  fieldProvenance: Record<string, FieldProvenance>;
  fieldConfidences: Record<string, ProfileConfidence>;
  sourceUrls: string[];
  consensusMetadata?: {
    perplexity_success: boolean;
    gemini_success: boolean;
    claude_success: boolean;
    total_fields: number;
    matched_fields: number;
    discrepancy_fields: number;
    fallback_layer: number;
  };
}

// 필드명 한글 매핑
const fieldNameMap: Record<string, string> = {
  business_summary: '사업 개요',
  revenue_krw: '연간 매출',
  export_ratio_pct: '수출 비중',
  ceo_name: '대표이사',
  employee_count: '임직원 수',
  founded_year: '설립 연도',
  headquarters: '본사 소재지',
  industry_overview: '업종 개요',
  business_model: '비즈니스 모델',
  country_exposure: '국가별 노출',
  key_materials: '주요 원자재',
  key_customers: '주요 고객사',
  overseas_operations: '해외 사업',
  supply_chain: '공급망',
  shareholders: '주요 주주',
  competitors: '경쟁사',
  macro_factors: '거시 요인',
};

// 신뢰도 설정
const confidenceConfig: Record<ProfileConfidence, { bg: string; text: string; border: string; icon: typeof CheckCircle }> = {
  HIGH: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle },
  MED: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', icon: Info },
  LOW: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', icon: AlertTriangle },
  NONE: { bg: 'bg-gray-50', text: 'text-gray-500', border: 'border-gray-200', icon: HelpCircle },
  CACHED: { bg: 'bg-blue-50', text: 'text-blue-600', border: 'border-blue-200', icon: Info },
  STALE: { bg: 'bg-red-50', text: 'text-red-600', border: 'border-red-200', icon: AlertTriangle },
};

export function EvidenceMap({
  fieldProvenance,
  fieldConfidences,
  sourceUrls,
  consensusMetadata,
}: EvidenceMapProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // 신뢰도별 필드 그룹화
  const fieldsByConfidence = Object.entries(fieldProvenance).reduce(
    (acc, [field, prov]) => {
      const confidence = prov.confidence || 'NONE';
      if (!acc[confidence]) acc[confidence] = [];
      acc[confidence].push({ field, provenance: prov });
      return acc;
    },
    {} as Record<ProfileConfidence, { field: string; provenance: FieldProvenance }[]>
  );

  // 통계 계산
  const totalFields = Object.keys(fieldProvenance).length;
  const highConfidenceCount = (fieldsByConfidence['HIGH'] || []).length;
  const medConfidenceCount = (fieldsByConfidence['MED'] || []).length;
  const lowConfidenceCount = (fieldsByConfidence['LOW'] || []).length;

  // 출처 도메인 추출
  const domains = sourceUrls.map((url) => {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  });
  const uniqueDomains = [...new Set(domains)];

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* 헤더 - 항상 표시 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <FileText className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">근거 맵 (Evidence Map)</span>
          {/* 신뢰도 요약 배지 */}
          <div className="flex items-center gap-1.5">
            {highConfidenceCount > 0 && (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                검증 {highConfidenceCount}
              </span>
            )}
            {medConfidenceCount > 0 && (
              <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
                참고 {medConfidenceCount}
              </span>
            )}
            {lowConfidenceCount > 0 && (
              <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">
                추정 {lowConfidenceCount}
              </span>
            )}
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* 상세 패널 */}
      {isExpanded && (
        <div className="p-4 space-y-4 animate-in slide-in-from-top-2">
          {/* Consensus 메타데이터 */}
          {consensusMetadata && (
            <div className="p-3 bg-blue-50/50 rounded-lg border border-blue-100">
              <div className="text-xs font-medium text-blue-800 mb-2">Multi-Agent Consensus</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="flex items-center gap-1">
                  {consensusMetadata.perplexity_success ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-3 h-3 text-red-500" />
                  )}
                  <span className={consensusMetadata.perplexity_success ? 'text-green-700' : 'text-red-600'}>
                    Perplexity
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {consensusMetadata.gemini_success ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-3 h-3 text-red-500" />
                  )}
                  <span className={consensusMetadata.gemini_success ? 'text-green-700' : 'text-red-600'}>
                    Gemini
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {consensusMetadata.claude_success ? (
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-3 h-3 text-red-500" />
                  )}
                  <span className={consensusMetadata.claude_success ? 'text-green-700' : 'text-red-600'}>
                    Claude
                  </span>
                </div>
              </div>
              <div className="mt-2 flex items-center gap-4 text-[10px] text-blue-600">
                <span>전체 {consensusMetadata.total_fields}개 필드</span>
                <span>일치 {consensusMetadata.matched_fields}개</span>
                {consensusMetadata.discrepancy_fields > 0 && (
                  <span className="text-orange-600">불일치 {consensusMetadata.discrepancy_fields}개</span>
                )}
                {consensusMetadata.fallback_layer > 1 && (
                  <span className="text-gray-500">Fallback Layer {consensusMetadata.fallback_layer}</span>
                )}
              </div>
            </div>
          )}

          {/* 출처 도메인 */}
          <div>
            <div className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <Globe className="w-3 h-3" />
              출처 ({uniqueDomains.length}개 도메인)
            </div>
            <div className="flex flex-wrap gap-1.5">
              {uniqueDomains.slice(0, 8).map((domain, i) => (
                <span key={i} className="text-xs bg-muted px-2 py-1 rounded flex items-center gap-1">
                  <Link2 className="w-3 h-3" />
                  {domain}
                </span>
              ))}
              {uniqueDomains.length > 8 && (
                <span className="text-xs text-muted-foreground">+{uniqueDomains.length - 8}개</span>
              )}
            </div>
          </div>

          {/* 필드별 근거 테이블 */}
          <div>
            <div className="text-xs font-medium text-muted-foreground mb-2">필드별 근거</div>
            <div className="border border-border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left px-3 py-2 font-medium">필드</th>
                    <th className="text-left px-3 py-2 font-medium">신뢰도</th>
                    <th className="text-left px-3 py-2 font-medium">출처</th>
                    <th className="text-left px-3 py-2 font-medium">근거 발췌</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(fieldProvenance).map(([field, prov]) => {
                    const confidence = prov.confidence || 'NONE';
                    const config = confidenceConfig[confidence];
                    const Icon = config.icon;
                    const displayName = fieldNameMap[field] || field;

                    return (
                      <tr key={field} className="border-t border-border hover:bg-muted/20">
                        <td className="px-3 py-2 font-medium">{displayName}</td>
                        <td className="px-3 py-2">
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${config.bg} ${config.text}`}>
                            <Icon className="w-3 h-3" />
                            {confidence}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          {prov.source_url ? (
                            <a
                              href={prov.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline flex items-center gap-1 max-w-[150px] truncate"
                            >
                              {new URL(prov.source_url).hostname}
                              <ExternalLink className="w-3 h-3 shrink-0" />
                            </a>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground max-w-[200px] truncate">
                          {prov.excerpt || '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 범례 */}
          <div className="flex items-center gap-4 text-[10px] text-muted-foreground pt-2 border-t border-border">
            <span className="flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-green-600" /> HIGH: 공시/IR 자료
            </span>
            <span className="flex items-center gap-1">
              <Info className="w-3 h-3 text-yellow-600" /> MED: 뉴스/기사
            </span>
            <span className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3 text-orange-600" /> LOW: AI 추정
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default EvidenceMap;
