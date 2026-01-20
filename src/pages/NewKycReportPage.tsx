/**
 * 신규 법인 KYC 분석 - 최종 리포트 페이지
 */

import { useParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useNewKycReport } from "@/hooks/useApi";
import {
  ArrowLeft,
  Building2,
  Users,
  FileText,
  Loader2,
  AlertCircle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  RefreshCw,
} from "lucide-react";

// 금액 포맷팅
function formatKRW(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-';
  if (value >= 1_0000_0000_0000) return `${(value / 1_0000_0000_0000).toFixed(1)}조원`;
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(0)}억원`;
  if (value >= 1_0000) return `${(value / 1_0000).toFixed(0)}만원`;
  return `${value.toLocaleString()}원`;
}

// 시그널 타입별 아이콘
function getSignalIcon(direction: string) {
  switch (direction) {
    case 'OPPORTUNITY':
      return <TrendingUp className="w-5 h-5 text-green-500" />;
    case 'RISK':
      return <TrendingDown className="w-5 h-5 text-red-500" />;
    default:
      return <Minus className="w-5 h-5 text-yellow-500" />;
  }
}

// 시그널 배경색
function getSignalBgColor(direction: string) {
  switch (direction) {
    case 'OPPORTUNITY':
      return 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800';
    case 'RISK':
      return 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800';
    default:
      return 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800';
  }
}

export default function NewKycReportPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  // 리포트 데이터 로드
  const { data: report, isLoading, error, refetch } = useNewKycReport(jobId || '');

  // 로딩 상태
  if (isLoading) {
    return (
      <MainLayout>
        <div className="max-w-4xl mx-auto text-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">리포트를 불러오는 중...</p>
        </div>
      </MainLayout>
    );
  }

  // 에러 상태
  if (error || !report) {
    return (
      <MainLayout>
        <div className="max-w-4xl mx-auto text-center py-16">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-foreground mb-2">리포트를 불러올 수 없습니다</h1>
          <p className="text-muted-foreground mb-6">
            분석이 아직 완료되지 않았거나 오류가 발생했습니다.
          </p>
          <div className="flex gap-4 justify-center">
            <Button variant="outline" onClick={() => navigate('/new-kyc')}>
              새로 분석하기
            </Button>
            <Button onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              다시 시도
            </Button>
          </div>
        </div>
      </MainLayout>
    );
  }

  // 시그널 분류
  const opportunities = report.signals?.filter(s => s.impact_direction === 'OPPORTUNITY') || [];
  const risks = report.signals?.filter(s => s.impact_direction === 'RISK') || [];
  const neutrals = report.signals?.filter(s => s.impact_direction === 'NEUTRAL') || [];

  const currentDate = new Date().toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        {/* 헤더 버튼 */}
        <div className="flex items-center justify-between mb-4">
          <Button
            variant="ghost"
            className="-ml-2 text-muted-foreground hover:text-foreground"
            onClick={() => navigate('/new-kyc')}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            새 분석하기
          </Button>
        </div>

        {/* 리포트 문서 */}
        <div className="bg-card rounded-lg border border-border p-8 space-y-8">

          {/* 리포트 헤더 */}
          <div className="text-center border-b border-border pb-6">
            <h1 className="text-xl font-bold text-foreground mb-2">
              신규 법인 KYC 분석 리포트
            </h1>
            <div className="text-lg font-semibold text-foreground mb-4">
              {report.corp_info?.corp_name || '기업명 미확인'}
            </div>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>생성일: {currentDate}</p>
              <p>분석 시스템: RKYC (Really Know Your Customer)</p>
            </div>
          </div>

          {/* 기업 개요 */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              기업 개요
            </h2>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex">
                  <span className="w-32 text-muted-foreground">기업명</span>
                  <span className="font-medium">{report.corp_info?.corp_name || '-'}</span>
                </div>
                <div className="flex">
                  <span className="w-32 text-muted-foreground">사업자등록번호</span>
                  <span>{report.corp_info?.biz_no || '-'}</span>
                </div>
                <div className="flex">
                  <span className="w-32 text-muted-foreground">법인등록번호</span>
                  <span>{report.corp_info?.corp_reg_no || '-'}</span>
                </div>
                <div className="flex">
                  <span className="w-32 text-muted-foreground">대표이사</span>
                  <span>{report.corp_info?.ceo_name || '-'}</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex">
                  <span className="w-32 text-muted-foreground">설립일</span>
                  <span>{report.corp_info?.founded_date || '-'}</span>
                </div>
                <div className="flex">
                  <span className="w-32 text-muted-foreground">업종</span>
                  <span>{report.corp_info?.industry || '-'}</span>
                </div>
                <div className="flex">
                  <span className="w-32 text-muted-foreground">자본금</span>
                  <span>{report.corp_info?.capital ? formatKRW(report.corp_info.capital) : '-'}</span>
                </div>
                <div className="flex">
                  <span className="w-32 text-muted-foreground">본점 소재지</span>
                  <span className="truncate">{report.corp_info?.address || '-'}</span>
                </div>
              </div>
            </div>

            {/* 재무 요약 */}
            {report.financial_summary && (
              <div className="mt-4 p-4 bg-muted/50 rounded-lg">
                <div className="text-xs text-muted-foreground mb-2">재무 요약 ({report.financial_summary.year}년 기준)</div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">매출액: </span>
                    <span className="font-medium">{formatKRW(report.financial_summary.revenue)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">영업이익: </span>
                    <span className="font-medium">{formatKRW(report.financial_summary.operating_profit)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">부채비율: </span>
                    <span className="font-medium">{report.financial_summary.debt_ratio}%</span>
                  </div>
                </div>
              </div>
            )}

            {/* 주요 주주 */}
            {report.shareholders && report.shareholders.length > 0 && (
              <div className="mt-4">
                <div className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  주요 주주
                </div>
                <div className="flex flex-wrap gap-2">
                  {report.shareholders.map((sh, i) => (
                    <span key={i} className="text-sm bg-muted px-3 py-1 rounded-full">
                      {sh.name} ({sh.ownership_pct}%)
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          <Separator />

          {/* 종합 평가 */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
              <FileText className="w-4 h-4" />
              종합 평가
            </h2>

            {/* 시그널 카운트 */}
            <div className="flex items-center justify-center gap-8 py-4 mb-4 bg-muted/30 rounded-lg">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{opportunities.length}</div>
                <div className="text-xs text-muted-foreground">기회 요인</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{neutrals.length}</div>
                <div className="text-xs text-muted-foreground">주의 요인</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{risks.length}</div>
                <div className="text-xs text-muted-foreground">리스크 요인</div>
              </div>
            </div>

            {/* AI 종합 의견 */}
            {report.insight && (
              <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
                <div className="text-xs text-primary font-medium mb-2">AI 종합 의견</div>
                <p className="text-sm text-foreground leading-relaxed">{report.insight}</p>
              </div>
            )}
          </section>

          <Separator />

          {/* 기회 요인 */}
          {opportunities.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-green-700 dark:text-green-400 mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                기회 요인 (OPPORTUNITY)
              </h2>

              <div className="space-y-4">
                {opportunities.map((signal, index) => (
                  <div
                    key={signal.signal_id || index}
                    className={`p-4 rounded-lg border ${getSignalBgColor('OPPORTUNITY')}`}
                  >
                    <div className="flex items-start gap-3">
                      {getSignalIcon('OPPORTUNITY')}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-foreground mb-1">{signal.title}</div>
                        <p className="text-sm text-muted-foreground mb-3">{signal.summary}</p>

                        {/* Evidence */}
                        {signal.evidences && signal.evidences.length > 0 && (
                          <div className="space-y-1">
                            {signal.evidences.map((ev, evIdx) => (
                              <div key={evIdx} className="text-xs text-muted-foreground flex items-center gap-1">
                                <FileText className="w-3 h-3" />
                                <span>출처: {ev.ref_type === 'URL' ? (
                                  <a href={ev.ref_value} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline inline-flex items-center gap-1">
                                    {ev.ref_value.slice(0, 50)}...
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                ) : ev.ref_value}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 주의 요인 */}
          {neutrals.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-yellow-700 dark:text-yellow-400 mb-4 flex items-center gap-2">
                <Minus className="w-4 h-4" />
                주의 요인 (모니터링 필요)
              </h2>

              <div className="space-y-4">
                {neutrals.map((signal, index) => (
                  <div
                    key={signal.signal_id || index}
                    className={`p-4 rounded-lg border ${getSignalBgColor('NEUTRAL')}`}
                  >
                    <div className="flex items-start gap-3">
                      {getSignalIcon('NEUTRAL')}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-foreground mb-1">{signal.title}</div>
                        <p className="text-sm text-muted-foreground mb-3">{signal.summary}</p>

                        {signal.evidences && signal.evidences.length > 0 && (
                          <div className="space-y-1">
                            {signal.evidences.map((ev, evIdx) => (
                              <div key={evIdx} className="text-xs text-muted-foreground flex items-center gap-1">
                                <FileText className="w-3 h-3" />
                                <span>출처: {ev.ref_value}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 리스크 요인 */}
          {risks.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-red-700 dark:text-red-400 mb-4 flex items-center gap-2">
                <TrendingDown className="w-4 h-4" />
                리스크 요인 (RISK)
              </h2>

              <div className="space-y-4">
                {risks.map((signal, index) => (
                  <div
                    key={signal.signal_id || index}
                    className={`p-4 rounded-lg border ${getSignalBgColor('RISK')}`}
                  >
                    <div className="flex items-start gap-3">
                      {getSignalIcon('RISK')}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-foreground mb-1">{signal.title}</div>
                        <p className="text-sm text-muted-foreground mb-3">{signal.summary}</p>

                        {signal.evidences && signal.evidences.length > 0 && (
                          <div className="space-y-1">
                            {signal.evidences.map((ev, evIdx) => (
                              <div key={evIdx} className="text-xs text-muted-foreground flex items-center gap-1">
                                <FileText className="w-3 h-3" />
                                <span>출처: {ev.ref_value}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 시그널 없음 */}
          {opportunities.length === 0 && neutrals.length === 0 && risks.length === 0 && (
            <section className="text-center py-8">
              <AlertCircle className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
                분석 결과 특별한 시그널이 발견되지 않았습니다.
              </p>
            </section>
          )}

          {/* 면책 조항 */}
          <div className="mt-8 pt-6 border-t-2 border-border">
            <div className="bg-muted p-4 rounded text-xs text-muted-foreground leading-relaxed">
              본 리포트는 AI 분석 결과이며, 최종 판단은 담당자의 검토를 거쳐야 합니다.
              모든 정보의 정확성을 보장하지 않으며, 참고 자료로만 활용하시기 바랍니다.
              자동 판단, 점수화, 예측 또는 조치를 의미하지 않습니다.
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
