import { useParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { 
  Signal, 
  SIGNAL_TYPE_CONFIG, 
  SIGNAL_IMPACT_CONFIG, 
  SIGNAL_STRENGTH_CONFIG 
} from "@/types/signal";
import { 
  ArrowLeft, 
  Building2, 
  Factory, 
  Globe, 
  TrendingUp, 
  TrendingDown, 
  FileText,
  Briefcase,
  Landmark,
  Calendar
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface CorporateProfile {
  id: string;
  name: string;
  businessNumber: string;
  industry: string;
  industryCode: string;
  description: string;
  hasLoanRelationship: boolean;
  loanStatus?: string;
}

interface TimelineSignal {
  id: string;
  date: string;
  signalCategory: Signal["signalCategory"];
  impact: Signal["impact"];
  impactStrength: Signal["impactStrength"];
  title: string;
}

// Mock corporate data
const mockCorporates: Record<string, CorporateProfile> = {
  "samsung": {
    id: "samsung",
    name: "삼성전자",
    businessNumber: "124-81-00998",
    industry: "반도체 및 전자부품 제조업",
    industryCode: "26110",
    description: "반도체, 디스플레이, 가전제품 및 IT 기기를 제조하는 글로벌 전자기업입니다. 메모리 반도체 및 스마트폰 분야에서 세계 선도적 위치를 차지하고 있습니다.",
    hasLoanRelationship: true,
    loanStatus: "기업 운영자금 대출 실행 중",
  },
  "skhynix": {
    id: "skhynix",
    name: "SK하이닉스",
    businessNumber: "105-81-11111",
    industry: "반도체 제조업",
    industryCode: "26110",
    description: "DRAM 및 NAND 플래시 메모리 반도체를 전문으로 제조하는 기업입니다. HBM(고대역폭 메모리) 시장에서 글로벌 1위를 차지하고 있습니다.",
    hasLoanRelationship: true,
    loanStatus: "시설자금 대출 실행 중",
  },
  "hyundai": {
    id: "hyundai",
    name: "현대자동차",
    businessNumber: "101-81-22222",
    industry: "자동차 제조업",
    industryCode: "30121",
    description: "승용차, 상용차 및 친환경 자동차를 제조하는 글로벌 자동차 기업입니다. 전기차 및 수소차 분야에서 적극적인 투자를 진행 중입니다.",
    hasLoanRelationship: false,
  },
};

// Mock timeline signals
const mockTimelineSignals: Record<string, TimelineSignal[]> = {
  "samsung": [
    {
      id: "1",
      date: "2024-12-24",
      signalCategory: "direct",
      impact: "risk",
      impactStrength: "high",
      title: "반도체 사업부 대규모 인력 구조조정 검토",
    },
    {
      id: "2",
      date: "2024-12-20",
      signalCategory: "industry",
      impact: "opportunity",
      impactStrength: "medium",
      title: "AI 반도체 수요 급증으로 메모리 시장 회복 전망",
    },
    {
      id: "3",
      date: "2024-12-15",
      signalCategory: "direct",
      impact: "neutral",
      impactStrength: "low",
      title: "신규 반도체 연구개발 센터 설립 계획 발표",
    },
    {
      id: "4",
      date: "2024-12-10",
      signalCategory: "environment",
      impact: "risk",
      impactStrength: "medium",
      title: "미중 반도체 규제 강화 조짐, 수출 영향 우려",
    },
    {
      id: "5",
      date: "2024-12-01",
      signalCategory: "direct",
      impact: "opportunity",
      impactStrength: "high",
      title: "분기 실적 시장 예상 상회, 주가 상승",
    },
    {
      id: "6",
      date: "2024-11-25",
      signalCategory: "industry",
      impact: "neutral",
      impactStrength: "low",
      title: "반도체 장비업체 설비 투자 동향 분석",
    },
    {
      id: "7",
      date: "2024-11-18",
      signalCategory: "environment",
      impact: "risk",
      impactStrength: "low",
      title: "글로벌 경기 침체 우려로 IT 수요 둔화 전망",
    },
    {
      id: "8",
      date: "2024-10-28",
      signalCategory: "direct",
      impact: "neutral",
      impactStrength: "medium",
      title: "이사회 구성 변경 공시",
    },
  ],
  "skhynix": [
    {
      id: "10",
      date: "2024-12-24",
      signalCategory: "industry",
      impact: "opportunity",
      impactStrength: "high",
      title: "AI 반도체 수요 급증, HBM 공급 부족 지속",
    },
    {
      id: "11",
      date: "2024-12-18",
      signalCategory: "direct",
      impact: "opportunity",
      impactStrength: "high",
      title: "엔비디아와 HBM 공급 계약 체결",
    },
    {
      id: "12",
      date: "2024-12-10",
      signalCategory: "direct",
      impact: "neutral",
      impactStrength: "low",
      title: "청주 공장 생산능력 확대 투자 결정",
    },
    {
      id: "13",
      date: "2024-11-28",
      signalCategory: "environment",
      impact: "risk",
      impactStrength: "medium",
      title: "미국 수출 규제 확대 가능성 보도",
    },
  ],
  "hyundai": [
    {
      id: "20",
      date: "2024-12-22",
      signalCategory: "direct",
      impact: "opportunity",
      impactStrength: "medium",
      title: "미국 전기차 공장 가동 시작",
    },
    {
      id: "21",
      date: "2024-12-15",
      signalCategory: "industry",
      impact: "neutral",
      impactStrength: "low",
      title: "자동차 산업 전기화 전환 가속",
    },
    {
      id: "22",
      date: "2024-12-05",
      signalCategory: "environment",
      impact: "risk",
      impactStrength: "medium",
      title: "글로벌 원자재 가격 상승 지속",
    },
  ],
};

function getSignalTypeIcon(category: Signal["signalCategory"]) {
  switch (category) {
    case "direct":
      return Building2;
    case "industry":
      return Factory;
    case "environment":
      return Globe;
  }
}

function getImpactIcon(impact: Signal["impact"]) {
  switch (impact) {
    case "risk":
      return TrendingDown;
    case "opportunity":
      return TrendingUp;
    case "neutral":
      return FileText;
  }
}

export default function CorporateDetailPage() {
  const { corporateId } = useParams();
  const navigate = useNavigate();

  const corporate = mockCorporates[corporateId || "samsung"] || mockCorporates["samsung"];
  const timelineSignals = mockTimelineSignals[corporateId || "samsung"] || [];

  return (
    <MainLayout>
      <div className="max-w-4xl">
        {/* Back navigation */}
        <Button 
          variant="ghost" 
          className="mb-4 -ml-2 text-muted-foreground hover:text-foreground"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          이전 페이지로 돌아가기
        </Button>

        {/* Corporate Profile Card */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <Building2 className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h1 className="text-2xl font-semibold text-foreground mb-1">
                    {corporate.name}
                  </h1>
                  <p className="text-sm text-muted-foreground">{corporate.businessNumber}</p>
                </div>
              </div>

              {/* Industry */}
              <div className="flex items-center gap-2 mb-3">
                <Briefcase className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-foreground">{corporate.industry}</span>
                <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  {corporate.industryCode}
                </span>
              </div>

              {/* Loan Relationship Status */}
              <div className="flex items-center gap-2 mb-4">
                <Landmark className="w-4 h-4 text-muted-foreground" />
                {corporate.hasLoanRelationship ? (
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">여신 거래: 있음</span>
                    {corporate.loanStatus && (
                      <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded">
                        {corporate.loanStatus}
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="text-sm text-muted-foreground">여신 거래: 없음</span>
                )}
              </div>

              {/* Description */}
              <p className="text-sm text-muted-foreground leading-relaxed">
                {corporate.description}
              </p>
            </div>
          </div>
        </div>

        {/* Signal Timeline Section */}
        <div className="bg-card rounded-lg border border-border p-6">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-info/10 flex items-center justify-center">
              <Calendar className="w-4 h-4 text-info" />
            </div>
            <h2 className="text-lg font-medium text-foreground">시그널 타임라인</h2>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
              최근 60~90일
            </span>
          </div>

          {/* Timeline */}
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-[7px] top-2 bottom-2 w-[2px] bg-border" />

            <div className="space-y-0">
              {timelineSignals.map((signal, index) => {
                const typeConfig = SIGNAL_TYPE_CONFIG[signal.signalCategory];
                const impactConfig = SIGNAL_IMPACT_CONFIG[signal.impact];
                const strengthConfig = SIGNAL_STRENGTH_CONFIG[signal.impactStrength];
                const TypeIcon = getSignalTypeIcon(signal.signalCategory);
                const ImpactIcon = getImpactIcon(signal.impact);

                return (
                  <div 
                    key={signal.id}
                    className="relative pl-8 pb-6 last:pb-0 group cursor-pointer"
                    onClick={() => navigate(`/signals/${signal.id}`)}
                  >
                    {/* Timeline dot */}
                    <div className={`absolute left-0 top-1.5 w-4 h-4 rounded-full border-2 bg-card ${impactConfig.colorClass} transition-colors`} 
                      style={{ borderColor: 'currentColor' }}
                    />

                    {/* Content card */}
                    <div className="bg-secondary/30 rounded-lg border border-border p-4 hover:border-primary/30 hover:bg-secondary/50 transition-all">
                      {/* Date */}
                      <div className="text-xs text-muted-foreground mb-2">
                        {signal.date}
                      </div>

                      {/* Badges row */}
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        {/* Signal Type */}
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${typeConfig.bgClass} ${typeConfig.colorClass}`}>
                          <TypeIcon className="w-3 h-3" />
                          {typeConfig.label}
                        </span>

                        {/* Impact */}
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${impactConfig.bgClass} ${impactConfig.colorClass}`}>
                          <ImpactIcon className="w-3 h-3" />
                          {impactConfig.label}
                        </span>

                        {/* Strength */}
                        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                          {strengthConfig.label}
                        </span>
                      </div>

                      {/* Title */}
                      <p className="text-sm text-foreground font-medium leading-relaxed group-hover:text-primary transition-colors">
                        {signal.title}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Empty state */}
          {timelineSignals.length === 0 && (
            <div className="text-center py-12">
              <Calendar className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                최근 90일간 감지된 시그널이 없습니다.
              </p>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
