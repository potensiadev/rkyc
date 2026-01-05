import { MainLayout } from "@/components/layout/MainLayout";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import {
  Radio,
  Clock,
  CheckCircle2,
  AlertCircle,
  Building2,
  Factory,
  Globe,
  ChevronRight
} from "lucide-react";

// Signal 페이지들과 동기화된 데이터 (DirectSignalPage, IndustrySignalPage, EnvironmentSignalPage 기준)
// 총 17개 시그널: Direct 6개, Industry 6개, Environment 5개
// 상태: new 8개, review 6개, resolved 3개
const kpiCards = [
  {
    id: "detected-today",
    title: "금일 감지",
    value: 8,
    icon: Radio,
  },
  {
    id: "pending-review",
    title: "검토 대기",
    value: 8,
    icon: Clock,
  },
  {
    id: "in-review",
    title: "검토 중",
    value: 6,
    icon: AlertCircle,
  },
  {
    id: "completed",
    title: "처리 완료",
    value: 3,
    icon: CheckCircle2,
  },
];

// Signal 페이지 기준 시그널 분포: Direct 6개, Industry 6개, Environment 5개
const signalTypeData = [
  {
    id: "direct",
    label: "직접 시그널",
    count: 6,
    icon: Building2,
    progressClass: "bg-blue-500",
  },
  {
    id: "industry",
    label: "산업 시그널",
    count: 6,
    icon: Factory,
    progressClass: "bg-purple-500",
  },
  {
    id: "environment",
    label: "환경 시그널",
    count: 5,
    icon: Globe,
    progressClass: "bg-emerald-500",
  },
];

// 영향도 분포 (signal 페이지 데이터 기준)
// risk: 6개, opportunity: 8개, neutral: 3개
const impactData = [
  { id: "risk", label: "위험", count: 6, dotClass: "bg-red-500" },
  { id: "opportunity", label: "기회", count: 8, dotClass: "bg-green-500" },
  { id: "reference", label: "참고", count: 3, dotClass: "bg-zinc-500" },
];

// Signal 페이지와 동기화된 최근 시그널 (corp 테이블 6개 기업)
const recentSignals = [
  {
    id: "00000001-0001-0001-0001-000000000001",
    corporateName: "엠케이전자",
    signalType: "direct",
    impact: "opportunity",
    detectedAt: "15분 전",
    title: "내부 신용등급 MED→HIGH 상향 조정",
  },
  {
    id: "00000002-0001-0001-0001-000000000002",
    corporateName: "동부건설",
    signalType: "direct",
    impact: "risk",
    detectedAt: "30분 전",
    title: "여신 노출 12억 → 18억원 증가",
  },
  {
    id: "00000018-0001-0001-0001-000000000018",
    corporateName: "엠케이전자",
    signalType: "industry",
    impact: "opportunity",
    detectedAt: "1시간 전",
    title: "반도체 업종 수출 호조, 전자부품 수요 증가",
  },
  {
    id: "00000019-0001-0001-0001-000000000019",
    corporateName: "동부건설",
    signalType: "industry",
    impact: "risk",
    detectedAt: "2시간 전",
    title: "건설업 PF 부실 우려 확대",
  },
  {
    id: "00000024-0001-0001-0001-000000000024",
    corporateName: "엠케이전자",
    signalType: "environment",
    impact: "risk",
    detectedAt: "2시간 전",
    title: "미중 반도체 규제 강화 전망",
  },
  {
    id: "00000005-0001-0001-0001-000000000005",
    corporateName: "삼성전자",
    signalType: "direct",
    impact: "risk",
    detectedAt: "3시간 전",
    title: "연체 플래그 활성화",
  },
  {
    id: "00000022-0001-0001-0001-000000000022",
    corporateName: "삼성전자",
    signalType: "industry",
    impact: "opportunity",
    detectedAt: "5시간 전",
    title: "바이오의약품 시장 성장세 지속",
  },
  {
    id: "00000028-0001-0001-0001-000000000028",
    corporateName: "휴림로봇",
    signalType: "environment",
    impact: "opportunity",
    detectedAt: "어제",
    title: "RE100 이행 로드맵 확정",
  },
];

export default function AnalyticsStatusPage() {
  const navigate = useNavigate();
  const totalSignalTypes = signalTypeData.reduce((sum, item) => sum + item.count, 0);

  return (
    <MainLayout>
      <div className="max-w-6xl space-y-6 text-foreground">
        {/* Page Header */}
        <div className="mb-2">
          <h1 className="text-2xl font-semibold">
            분석 현황
          </h1>
          <p className="text-muted-foreground mt-1">
            RKYC 시스템이 감지·분석 중인 시그널 현황을 한눈에 확인할 수 있습니다.
            <br />
            모든 정보는 참고 및 검토용으로 제공됩니다.
          </p>
        </div>

        {/* KPI Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpiCards.map((card, idx) => (
            <Card key={card.id}>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{card.title}</p>
                  <div className="text-2xl font-bold mt-1">
                    {card.value}
                  </div>
                </div>
                <div className="text-muted-foreground/50">
                  <card.icon className="w-8 h-8" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Signal Distribution */}
          <Card className="lg:col-span-1">
            <CardContent className="p-6">
              <h3 className="font-semibold mb-4">시그널 유형 분포</h3>
              <div className="space-y-4">
                {signalTypeData.map((item) => {
                  const percentage = Math.round((item.count / totalSignalTypes) * 100);
                  return (
                    <div key={item.id}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="flex items-center gap-2">
                          <item.icon className="w-3 h-3 text-muted-foreground" /> {item.label}
                        </span>
                        <span className="text-muted-foreground">{percentage}%</span>
                      </div>
                      <div className="h-2 bg-secondary rounded-full overflow-hidden">
                        <div
                          className={`h-full ${item.progressClass}`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              <div className="mt-8">
                <h3 className="font-semibold mb-4">영향도 평가</h3>
                <div className="space-y-2">
                  {impactData.map((item) => (
                    <div key={item.id} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${item.dotClass}`} />
                        <span className="text-sm">{item.label}</span>
                      </div>
                      <span className="font-semibold">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Signals List */}
          <Card className="lg:col-span-2">
            <CardContent className="p-0">
              <div className="px-6 py-4 border-b border-border flex justify-between items-center">
                <h3 className="font-semibold">최근 감지된 시그널</h3>
                <span className="text-xs text-muted-foreground">실시간 업데이트 중</span>
              </div>

              <div className="divide-y divide-border">
                {recentSignals.map((signal) => (
                  <div
                    key={signal.id}
                    className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/signals/${signal.id}`)}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        signal.signalType === 'direct' ? 'bg-blue-500/10 text-blue-500' :
                        signal.signalType === 'industry' ? 'bg-purple-500/10 text-purple-500' :
                        'bg-emerald-500/10 text-emerald-500'
                      }`}>
                        {signal.signalType === 'direct' ? <Building2 className="w-5 h-5" /> :
                         signal.signalType === 'industry' ? <Factory className="w-5 h-5" /> :
                         <Globe className="w-5 h-5" />}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{signal.title}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-muted-foreground">{signal.corporateName}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${signal.signalType === 'direct' ? 'border-blue-500/30 text-blue-500' :
                              signal.signalType === 'industry' ? 'border-purple-500/30 text-purple-500' :
                                'border-emerald-500/30 text-emerald-500'
                            }`}>
                            {signal.signalType === 'direct' ? '직접' : signal.signalType === 'industry' ? '산업' : '환경'}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className={`px-2 py-1 rounded text-xs font-medium ${signal.impact === 'risk' ? 'bg-red-500/10 text-red-500' :
                          signal.impact === 'opportunity' ? 'bg-green-500/10 text-green-500' :
                            'bg-zinc-500/10 text-zinc-500'
                        }`}>
                        {signal.impact === 'risk' ? '위험' : signal.impact === 'opportunity' ? '기회' : '참고'}
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">{signal.detectedAt}</p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
