/**
 * RiskIndicators Component
 *
 * 조기경보 지표 및 담당자 체크리스트
 * - Profile 데이터 기반 리스크 인디케이터 자동 생성
 * - 담당자 액션 아이템 제안
 * - 조치 가능한(Actionable) 인사이트 제공
 */

import { useState } from 'react';
import {
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  Globe,
  Package,
  DollarSign,
  Users,
  Shield,
  CheckSquare,
  Square,
  ChevronDown,
  ChevronUp,
  Target,
  Zap,
} from 'lucide-react';
import type { CorpProfile, ProfileConfidence, SupplyChain, MacroFactor } from '@/types/profile';

interface RiskIndicatorsProps {
  profile: CorpProfile | null;
  industryCode?: string;
}

interface RiskIndicator {
  id: string;
  category: 'supply_chain' | 'fx_exposure' | 'market' | 'governance' | 'financial';
  severity: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  metric?: string;
  threshold?: string;
  action?: string;
}

interface ActionItem {
  id: string;
  label: string;
  completed: boolean;
  priority: 'high' | 'medium' | 'low';
}

// 카테고리별 아이콘
const categoryIcons = {
  supply_chain: Package,
  fx_exposure: DollarSign,
  market: TrendingUp,
  governance: Users,
  financial: Shield,
};

// 심각도별 색상
const severityConfig = {
  high: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', icon: AlertTriangle },
  low: { bg: 'bg-blue-50', text: 'text-blue-600', border: 'border-blue-200', icon: TrendingDown },
};

// Profile 데이터 기반 리스크 지표 생성
function generateRiskIndicators(profile: CorpProfile | null, industryCode?: string): RiskIndicator[] {
  if (!profile) return [];

  const indicators: RiskIndicator[] = [];

  // 1. 공급망 리스크
  if (profile.supply_chain) {
    const sc = profile.supply_chain;

    // 단일 조달처 위험
    if (sc.single_source_risk && sc.single_source_risk.length > 0) {
      indicators.push({
        id: 'single_source',
        category: 'supply_chain',
        severity: 'high',
        title: '단일 조달처 의존도 위험',
        description: `${sc.single_source_risk.join(', ')}에 대한 단일 조달처 의존`,
        metric: `${sc.single_source_risk.length}개 품목`,
        action: '대체 공급처 확보 여부 확인 필요',
      });
    }

    // 중국 공급망 집중
    const chinaRatio = sc.supplier_countries?.['중국'] || 0;
    if (chinaRatio >= 50) {
      indicators.push({
        id: 'china_supply',
        category: 'supply_chain',
        severity: chinaRatio >= 70 ? 'high' : 'medium',
        title: '중국 공급망 집중 리스크',
        description: '공급사의 과반이 중국에 집중되어 지정학적 리스크 노출',
        metric: `${chinaRatio}%`,
        threshold: '50% 이상',
        action: '공급망 다변화 계획 확인',
      });
    }

    // 원자재 수입 의존도
    if (sc.material_import_ratio_pct && sc.material_import_ratio_pct >= 70) {
      indicators.push({
        id: 'material_import',
        category: 'supply_chain',
        severity: 'medium',
        title: '원자재 수입 의존도 높음',
        description: '원자재의 상당 부분을 수입에 의존',
        metric: `${sc.material_import_ratio_pct}%`,
        threshold: '70% 이상',
        action: '환율 변동 및 물류 리스크 헤지 전략 검토',
      });
    }
  }

  // 2. 환노출 리스크
  if (profile.export_ratio_pct && profile.export_ratio_pct >= 30) {
    indicators.push({
      id: 'fx_exposure',
      category: 'fx_exposure',
      severity: profile.export_ratio_pct >= 50 ? 'high' : 'medium',
      title: '높은 수출 비중',
      description: '매출의 상당 부분이 수출에 의존하여 환율 변동 리스크 존재',
      metric: `${profile.export_ratio_pct}%`,
      threshold: '30% 이상',
      action: '환헤지 비율 및 전략 확인',
    });
  }

  // 국가별 노출 - 고위험 국가
  if (profile.country_exposure) {
    const highRiskCountries = ['중국', '러시아', '베트남', '인도'];
    for (const [country, ratio] of Object.entries(profile.country_exposure)) {
      if (highRiskCountries.includes(country) && Number(ratio) >= 20) {
        indicators.push({
          id: `country_${country}`,
          category: 'fx_exposure',
          severity: Number(ratio) >= 40 ? 'high' : 'medium',
          title: `${country} 노출도`,
          description: `${country}에 대한 사업 노출이 높아 지정학적/규제 리스크 존재`,
          metric: `${ratio}%`,
          action: '해당 국가 관련 규제 및 정책 변화 모니터링',
        });
      }
    }
  }

  // 3. 시장 리스크 (거시 요인)
  if (profile.macro_factors) {
    const negativeFactors = profile.macro_factors.filter(f => f.impact === 'NEGATIVE');
    if (negativeFactors.length > 0) {
      indicators.push({
        id: 'macro_negative',
        category: 'market',
        severity: negativeFactors.length >= 3 ? 'high' : 'medium',
        title: '부정적 거시 요인 존재',
        description: negativeFactors.map(f => f.factor).join(', '),
        metric: `${negativeFactors.length}개 요인`,
        action: '업황 모니터링 강화 및 대응 전략 검토',
      });
    }
  }

  // 4. 재무 리스크 (financial_history가 있는 경우)
  if (profile.financial_history && profile.financial_history.length >= 2) {
    const sorted = [...profile.financial_history].sort((a, b) => (b.year || 0) - (a.year || 0));
    const recent = sorted[0];
    const previous = sorted[1];

    if (recent?.revenue_krw && previous?.revenue_krw) {
      const revenueChange = ((recent.revenue_krw - previous.revenue_krw) / previous.revenue_krw) * 100;
      if (revenueChange <= -10) {
        indicators.push({
          id: 'revenue_decline',
          category: 'financial',
          severity: revenueChange <= -20 ? 'high' : 'medium',
          title: '매출 감소 추세',
          description: `전년 대비 매출 ${Math.abs(revenueChange).toFixed(1)}% 감소`,
          metric: `${revenueChange.toFixed(1)}%`,
          threshold: '-10% 이하',
          action: '매출 감소 원인 분석 및 사업 전망 확인',
        });
      }
    }
  }

  return indicators;
}

// 담당자 체크리스트 생성
function generateActionItems(indicators: RiskIndicator[]): ActionItem[] {
  const items: ActionItem[] = [];

  // 기본 체크리스트
  items.push(
    { id: 'kyc_review', label: 'KYC 정보 최신성 확인', completed: false, priority: 'high' },
    { id: 'financial_verify', label: '최근 재무제표 검토', completed: false, priority: 'high' },
  );

  // 리스크 지표 기반 체크리스트
  if (indicators.some(i => i.category === 'supply_chain')) {
    items.push({ id: 'supply_chain_check', label: '공급망 리스크 대응 현황 확인', completed: false, priority: 'high' });
  }

  if (indicators.some(i => i.category === 'fx_exposure')) {
    items.push({ id: 'fx_hedge_check', label: '환헤지 전략 검토', completed: false, priority: 'medium' });
  }

  if (indicators.some(i => i.severity === 'high')) {
    items.push({ id: 'escalation', label: '고위험 지표 상급자 보고', completed: false, priority: 'high' });
  }

  items.push(
    { id: 'collateral_review', label: '담보 가치 적정성 검토', completed: false, priority: 'medium' },
    { id: 'covenant_check', label: '약정 조건 준수 여부 확인', completed: false, priority: 'medium' },
  );

  return items;
}

export function RiskIndicators({ profile, industryCode }: RiskIndicatorsProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [checklist, setChecklist] = useState<ActionItem[]>([]);

  // 리스크 지표 생성
  const indicators = generateRiskIndicators(profile, industryCode);

  // 체크리스트 초기화 (한 번만)
  useState(() => {
    setChecklist(generateActionItems(indicators));
  });

  // 체크 토글
  const toggleCheck = (id: string) => {
    setChecklist(prev =>
      prev.map(item => (item.id === id ? { ...item, completed: !item.completed } : item))
    );
  };

  if (!profile) return null;

  const highSeverityCount = indicators.filter(i => i.severity === 'high').length;
  const mediumSeverityCount = indicators.filter(i => i.severity === 'medium').length;

  return (
    <div className="space-y-4">
      {/* 조기경보 지표 */}
      <div className="border border-border rounded-lg overflow-hidden">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <Zap className="w-4 h-4 text-amber-500" />
            <span className="text-sm font-medium">조기경보 지표</span>
            {/* 요약 배지 */}
            <div className="flex items-center gap-1.5">
              {highSeverityCount > 0 && (
                <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  고위험 {highSeverityCount}
                </span>
              )}
              {mediumSeverityCount > 0 && (
                <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
                  주의 {mediumSeverityCount}
                </span>
              )}
              {indicators.length === 0 && (
                <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                  정상
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

        {isExpanded && (
          <div className="p-4 space-y-3">
            {indicators.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4">
                현재 감지된 조기경보 지표가 없습니다.
              </div>
            ) : (
              indicators.map((indicator) => {
                const config = severityConfig[indicator.severity];
                const CategoryIcon = categoryIcons[indicator.category];

                return (
                  <div
                    key={indicator.id}
                    className={`p-3 rounded-lg border ${config.border} ${config.bg}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-1.5 rounded ${config.bg}`}>
                        <CategoryIcon className={`w-4 h-4 ${config.text}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-medium ${config.text}`}>
                            {indicator.title}
                          </span>
                          {indicator.metric && (
                            <span className={`text-xs px-1.5 py-0.5 rounded ${config.bg} ${config.text} font-mono`}>
                              {indicator.metric}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {indicator.description}
                        </p>
                        {indicator.action && (
                          <p className="text-xs mt-1.5 flex items-center gap-1">
                            <Target className="w-3 h-3 text-muted-foreground" />
                            <span className="font-medium">조치:</span>
                            <span className="text-muted-foreground">{indicator.action}</span>
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* 담당자 체크리스트 */}
      <div className="border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <CheckSquare className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">담당자 체크리스트</span>
          <span className="text-xs text-muted-foreground">
            ({checklist.filter(c => c.completed).length}/{checklist.length} 완료)
          </span>
        </div>
        <div className="space-y-2">
          {checklist.map((item) => (
            <label
              key={item.id}
              className="flex items-center gap-3 p-2 rounded hover:bg-muted/50 cursor-pointer group"
            >
              <button
                onClick={() => toggleCheck(item.id)}
                className="shrink-0"
              >
                {item.completed ? (
                  <CheckSquare className="w-4 h-4 text-green-600" />
                ) : (
                  <Square className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                )}
              </button>
              <span className={`text-sm ${item.completed ? 'text-muted-foreground line-through' : ''}`}>
                {item.label}
              </span>
              {item.priority === 'high' && !item.completed && (
                <span className="text-[10px] bg-red-100 text-red-700 px-1 py-0.5 rounded">필수</span>
              )}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

export default RiskIndicators;
