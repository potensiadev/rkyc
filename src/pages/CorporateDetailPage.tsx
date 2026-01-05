import { useParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { getCorporationById, CORPORATIONS } from "@/data/corporations";
import {
  getSignalsByCorporationId,
  getIntegratedTimeline,
  getAllEvidencesForCorporation,
  getCorporationSignalCounts,
  formatDate,
  getBankTransactionTypeLabel,
} from "@/data/signals";
import { getInsightMemoryByCorporationId } from "@/data/insightMemory";
import { getValueChainByCorpId } from "@/data/valueChain";
import { SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG } from "@/types/signal";
import {
  ArrowLeft,
  Building2,
  Factory,
  Globe,
  TrendingUp,
  TrendingDown,
  Minus,
  FileText,
  Landmark,
  Users,
  Banknote,
  Calendar,
  FileDown,
  Link2,
  Loader2,
  ArrowRight,
  Network,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useState } from "react";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import { useCorporation, useSignals, useCorporationSnapshot } from "@/hooks/useApi";

export default function CorporateDetailPage() {
  const { corporateId } = useParams();
  const navigate = useNavigate();
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  // API 훅 사용
  const { data: apiCorporation, isLoading: isLoadingCorp } = useCorporation(corporateId || "");
  const { data: apiSignals, isLoading: isLoadingSignals } = useSignals({ corp_id: corporateId });
  const { data: snapshot, isLoading: isLoadingSnapshot } = useCorporationSnapshot(corporateId || "");

  // Mock 데이터 fallback (API에 없는 상세 정보용)
  const mockCorporation = getCorporationById(corporateId || "1");

  // 로딩 상태
  if (isLoadingCorp) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-primary mr-2" />
          <span className="text-muted-foreground">기업 정보를 불러오는 중...</span>
        </div>
      </MainLayout>
    );
  }

  // API 데이터 우선, 없으면 Mock 사용
  const corporation = apiCorporation || mockCorporation;

  if (!corporation) {
    return (
      <MainLayout>
        <div className="text-center py-16">
          <p className="text-muted-foreground">기업 정보를 찾을 수 없습니다.</p>
          <Button variant="outline" onClick={() => navigate(-1)} className="mt-4">
            돌아가기
          </Button>
        </div>
      </MainLayout>
    );
  }

  // API 시그널 카운트 또는 Mock 카운트
  const signalCounts = apiSignals ? {
    direct: apiSignals.filter(s => s.signalCategory === 'direct').length,
    industry: apiSignals.filter(s => s.signalCategory === 'industry').length,
    environment: apiSignals.filter(s => s.signalCategory === 'environment').length,
  } : getCorporationSignalCounts(corporation.id);

  // Mock 데이터 (상세 정보용)
  const integratedTimeline = getIntegratedTimeline(corporation.id);
  const evidences = getAllEvidencesForCorporation(corporation.id);
  const insightMemory = getInsightMemoryByCorporationId(corporation.id);
  const valueChain = getValueChainByCorpId(corporation.id);

  const currentDate = new Date().toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  return (
    <MainLayout>
      <div className="max-w-4xl mx-auto">
        {/* Back & Actions */}
        <div className="flex items-center justify-between mb-4">
          <Button 
            variant="ghost" 
            className="-ml-2 text-muted-foreground hover:text-foreground"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            이전 페이지
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-2">
              <Link2 className="w-4 h-4" />
              공유 링크
            </Button>
            <Button size="sm" className="gap-2" onClick={() => setShowPreviewModal(true)}>
              <FileDown className="w-4 h-4" />
              PDF 내보내기
            </Button>
          </div>
        </div>

        {/* Report Document Style */}
        <div className="bg-card rounded-lg border border-border p-8 space-y-8">
          
          {/* Report Header */}
          <div className="text-center border-b border-border pb-6">
            <h1 className="text-xl font-bold text-foreground mb-2">
              RKYC 기업 시그널 분석 보고서 (참고용)
            </h1>
            <div className="text-lg font-semibold text-foreground mb-4">{corporation.name}</div>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>보고서 생성일: {currentDate}</p>
              <p>생성 시스템: RKYC (Really Know Your Customer Intelligence)</p>
            </div>
            <div className="mt-4 inline-block px-3 py-1.5 bg-muted rounded text-xs text-muted-foreground">
              본 보고서는 참고 및 검토용 자료입니다.
            </div>
          </div>

          {/* Executive Summary */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border">
              요약 (Executive Summary)
            </h2>
            <div className="text-sm text-muted-foreground space-y-2 leading-relaxed">
              <p>
                <strong className="text-foreground">{corporation.name}</strong>은(는) {corporation.industry} 분야에서 
                {corporation.mainBusiness}을(를) 영위하는 기업입니다. 
                본사는 {corporation.headquarters}에 소재하며, 임직원 {corporation.employeeCount}명 규모입니다.
              </p>
              {corporation.bankRelationship.hasRelationship && (
                <p>
                  당행과는 여신 {corporation.bankRelationship.loanBalance}, 수신 {corporation.bankRelationship.depositBalance} 규모의 
                  거래 관계를 유지하고 있습니다.
                  {corporation.bankRelationship.fxTransactions && ` 외환 거래 규모는 ${corporation.bankRelationship.fxTransactions}입니다.`}
                </p>
              )}
              <p>
                최근 직접 시그널 {signalCounts.direct}건, 산업 시그널 {signalCounts.industry}건, 
                환경 시그널 {signalCounts.environment}건이 감지되었습니다.
              </p>
              <p>아래 내용은 담당자의 검토를 위해 정리된 참고 자료입니다.</p>
            </div>
          </section>

          <Separator />

          {/* Company Profile */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              기업 개요
            </h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex"><span className="w-28 text-muted-foreground">기업명</span><span>{corporation.name}</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">사업자등록번호</span><span>{corporation.businessNumber}</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">업종</span><span>{corporation.industry}</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">업종코드</span><span>{corporation.industryCode}</span></div>
              </div>
              <div className="space-y-2">
                <div className="flex"><span className="w-28 text-muted-foreground">대표이사</span><span>{corporation.ceo}</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">임직원 수</span><span>{corporation.employeeCount}명</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">설립연도</span><span>{corporation.foundedYear}년</span></div>
                <div className="flex"><span className="w-28 text-muted-foreground">본사 소재지</span><span>{corporation.headquarters}</span></div>
              </div>
            </div>
            
            {/* Key Executives */}
            <div className="mt-4">
              <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                <Users className="w-3.5 h-3.5" /> 주요 경영진 (Key Man)
              </h3>
              <div className="flex flex-wrap gap-2">
                {corporation.executives.filter(e => e.isKeyMan).map((exec, i) => (
                  <span key={i} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                    {exec.name} ({exec.position})
                  </span>
                ))}
              </div>
            </div>
          </section>

          <Separator />

          {/* Value Chain */}
          {valueChain && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
                <Network className="w-4 h-4" />
                가치사슬망
              </h2>

              {/* 산업 개요 */}
              <div className="mb-4">
                <h3 className="text-sm font-medium text-foreground mb-2">산업 구조 및 비즈니스 모델</h3>
                <div className="text-xs text-muted-foreground leading-relaxed whitespace-pre-line bg-muted/30 p-3 rounded">
                  {valueChain.industryOverview}
                </div>
                <div className="mt-2 text-xs">
                  <span className="text-muted-foreground">비즈니스 모델: </span>
                  <span className="text-foreground font-medium">{valueChain.businessModel}</span>
                </div>
              </div>

              {/* 공급-당사-수요 플로우 */}
              <div className="mb-4">
                <h3 className="text-sm font-medium text-foreground mb-2">공급망 구조</h3>
                <div className="flex items-stretch gap-2 text-xs">
                  {/* 공급 측 */}
                  <div className="flex-1 border border-border rounded p-2 bg-blue-50/50">
                    <div className="font-medium text-blue-800 mb-1.5 text-center text-[10px]">공급 (Upstream)</div>
                    <div className="space-y-0.5">
                      {valueChain.suppliers.slice(0, 4).map((supplier, idx) => (
                        <div key={idx} className="flex justify-between text-muted-foreground text-[10px]">
                          <span className="truncate">{supplier.name}</span>
                          <span className="text-blue-600 shrink-0 ml-1">{supplier.share}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center">
                    <ArrowRight className="w-3 h-3 text-muted-foreground" />
                  </div>
                  <div className="w-16 border-2 border-primary rounded p-2 bg-primary/5 flex flex-col justify-center items-center">
                    <div className="font-semibold text-primary text-[10px] text-center">당사</div>
                  </div>
                  <div className="flex items-center">
                    <ArrowRight className="w-3 h-3 text-muted-foreground" />
                  </div>
                  {/* 수요 측 */}
                  <div className="flex-1 border border-border rounded p-2 bg-green-50/50">
                    <div className="font-medium text-green-800 mb-1.5 text-center text-[10px]">수요 (Downstream)</div>
                    <div className="space-y-0.5">
                      {valueChain.customers.map((customer, idx) => (
                        <div key={idx} className="flex justify-between text-muted-foreground text-[10px]">
                          <span className="truncate">{customer.name}</span>
                          <span className="text-green-600 shrink-0 ml-1">{customer.share}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* 경쟁 현황 */}
              <div className="mb-4">
                <h3 className="text-sm font-medium text-foreground mb-2">경쟁 현황 (Top Players)</h3>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-1.5 font-medium text-muted-foreground">기업명</th>
                      <th className="text-right py-1.5 font-medium text-muted-foreground">점유율</th>
                      <th className="text-right py-1.5 font-medium text-muted-foreground">매출</th>
                      <th className="text-left py-1.5 pl-2 font-medium text-muted-foreground">비고</th>
                    </tr>
                  </thead>
                  <tbody>
                    {valueChain.competitors.map((competitor, idx) => (
                      <tr
                        key={idx}
                        className={`border-b border-border/50 ${competitor.note?.includes("당사") ? "bg-primary/5 font-medium" : ""}`}
                      >
                        <td className="py-1.5 text-foreground">{competitor.name}</td>
                        <td className="py-1.5 text-right text-foreground">{competitor.marketShare}</td>
                        <td className="py-1.5 text-right text-muted-foreground">{competitor.revenue}</td>
                        <td className="py-1.5 pl-2 text-muted-foreground">{competitor.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 매크로 환경 요인 */}
              <div className="mb-2">
                <h3 className="text-sm font-medium text-foreground mb-2">매크로 환경 요인</h3>
                <div className="space-y-1.5">
                  {valueChain.macroFactors.map((factor, idx) => (
                    <div
                      key={idx}
                      className={`flex items-start gap-2 text-xs p-2 rounded ${
                        factor.impact === "positive"
                          ? "text-green-700 bg-green-50"
                          : factor.impact === "negative"
                          ? "text-red-700 bg-red-50"
                          : "text-gray-700 bg-gray-50"
                      }`}
                    >
                      <span className="shrink-0 mt-0.5">
                        {factor.impact === "positive" ? (
                          <TrendingUp className="w-3 h-3" />
                        ) : factor.impact === "negative" ? (
                          <TrendingDown className="w-3 h-3" />
                        ) : (
                          <Minus className="w-3 h-3" />
                        )}
                      </span>
                      <div>
                        <span className="font-medium">[{factor.category}]</span>{" "}
                        <span>{factor.description}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <p className="text-[10px] text-muted-foreground italic">
                위 가치사슬망 정보는 산업 분석 참고용이며, 실제 거래 관계와 다를 수 있습니다.
              </p>
            </section>
          )}

          <Separator />

          {/* Bank Relationship - Snapshot API 데이터 사용 */}
          {(snapshot?.snapshot_json?.credit?.has_loan || corporation.bankRelationship.hasRelationship) && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
                <Landmark className="w-4 h-4" />
                당행 거래 현황
              </h2>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="bg-muted/50 rounded p-3">
                  <div className="text-muted-foreground text-xs mb-1">수신 잔액</div>
                  <div className="font-medium">{corporation.bankRelationship.depositBalance || "-"}</div>
                </div>
                <div className="bg-muted/50 rounded p-3">
                  <div className="text-muted-foreground text-xs mb-1">여신 잔액</div>
                  <div className="font-medium">
                    {snapshot?.snapshot_json?.credit?.loan_summary?.total_exposure_krw
                      ? `${(snapshot.snapshot_json.credit.loan_summary.total_exposure_krw / 100000000).toFixed(0)}억원`
                      : corporation.bankRelationship.loanBalance || "-"}
                  </div>
                </div>
                <div className="bg-muted/50 rounded p-3">
                  <div className="text-muted-foreground text-xs mb-1">외환 거래</div>
                  <div className="font-medium">{corporation.bankRelationship.fxTransactions || "-"}</div>
                </div>
              </div>
              {/* 담보 정보 (Snapshot API) */}
              {snapshot?.snapshot_json?.collateral?.has_collateral && (
                <div className="mt-3 p-3 bg-muted/30 rounded">
                  <div className="text-xs text-muted-foreground mb-2">담보 현황</div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="font-medium">
                      {snapshot.snapshot_json.collateral.total_collateral_value_krw
                        ? `${(snapshot.snapshot_json.collateral.total_collateral_value_krw / 100000000).toFixed(0)}억원`
                        : "-"}
                    </span>
                    <div className="flex gap-1">
                      {snapshot.snapshot_json.collateral.collateral_types?.map((type, i) => (
                        <span key={i} className="text-xs bg-muted px-2 py-0.5 rounded">{type}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
              {/* KYC 상태 (Snapshot API) */}
              {snapshot?.snapshot_json?.corp?.kyc_status && (
                <div className="mt-3 p-3 bg-muted/30 rounded">
                  <div className="text-xs text-muted-foreground mb-2">KYC 상태</div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      snapshot.snapshot_json.corp.kyc_status.is_kyc_completed
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {snapshot.snapshot_json.corp.kyc_status.is_kyc_completed ? 'KYC 완료' : 'KYC 미완료'}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'HIGH'
                        ? 'bg-red-100 text-red-700'
                        : snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'MED'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-green-100 text-green-700'
                    }`}>
                      내부등급: {snapshot.snapshot_json.corp.kyc_status.internal_risk_grade}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      최종 갱신: {snapshot.snapshot_json.corp.kyc_status.last_kyc_updated}
                    </span>
                  </div>
                </div>
              )}
              <div className="flex gap-2 mt-3">
                {corporation.bankRelationship.retirementPension && (
                  <span className="text-xs bg-muted px-2 py-1 rounded">퇴직연금</span>
                )}
                {corporation.bankRelationship.payrollService && (
                  <span className="text-xs bg-muted px-2 py-1 rounded">급여이체</span>
                )}
                {corporation.bankRelationship.corporateCard && (
                  <span className="text-xs bg-muted px-2 py-1 rounded">법인카드</span>
                )}
                {snapshot?.snapshot_json?.credit?.loan_summary?.overdue_flag && (
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">연체 발생</span>
                )}
              </div>
            </section>
          )}

          <Separator />

          {/* Financial Overview */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
              <Banknote className="w-4 h-4" />
              재무 개요 (3개년)
            </h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 text-muted-foreground font-medium">연도</th>
                  <th className="text-right py-2 text-muted-foreground font-medium">매출액</th>
                  <th className="text-right py-2 text-muted-foreground font-medium">영업이익</th>
                  <th className="text-right py-2 text-muted-foreground font-medium">순이익</th>
                  <th className="text-right py-2 text-muted-foreground font-medium">자본</th>
                </tr>
              </thead>
              <tbody>
                {corporation.financialSnapshots.map((fs) => (
                  <tr key={fs.year} className="border-b border-border/50">
                    <td className="py-2">{fs.year}</td>
                    <td className="text-right py-2">{fs.revenue}</td>
                    <td className="text-right py-2">{fs.operatingProfit}</td>
                    <td className="text-right py-2">{fs.netProfit}</td>
                    <td className="text-right py-2">{fs.equity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <Separator />

          {/* Shareholders */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border">
              주주 구성
            </h2>
            <div className="space-y-2 text-sm">
              {corporation.shareholders.map((sh, i) => (
                <div key={i} className="flex justify-between">
                  <span>{sh.name} <span className="text-muted-foreground">({sh.type})</span></span>
                  <span className="font-medium">{sh.ownership}</span>
                </div>
              ))}
            </div>
          </section>

          <Separator />

          {/* Integrated Timeline */}
          <section>
            <h2 className="text-base font-semibold text-foreground mb-3 pb-2 border-b border-border flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              통합 타임라인 (시그널 + 거래)
            </h2>
            <div className="space-y-3">
              {integratedTimeline.slice(0, 10).map((item) => (
                <div key={item.id} className="flex items-start gap-3 text-sm border-b border-border/50 pb-3 last:border-0">
                  <span className="w-24 text-muted-foreground shrink-0">{item.date}</span>
                  {item.type === "signal" ? (
                    <>
                      <span className={`w-14 shrink-0 text-xs px-1.5 py-0.5 rounded ${SIGNAL_TYPE_CONFIG[item.category as keyof typeof SIGNAL_TYPE_CONFIG]?.bgClass} ${SIGNAL_TYPE_CONFIG[item.category as keyof typeof SIGNAL_TYPE_CONFIG]?.colorClass}`}>
                        {item.category === "direct" ? "직접" : item.category === "industry" ? "산업" : "환경"}
                      </span>
                      <span className="flex-1">{item.title}</span>
                      {item.impact && (
                        <span className={`text-xs ${SIGNAL_IMPACT_CONFIG[item.impact].colorClass}`}>
                          {SIGNAL_IMPACT_CONFIG[item.impact].label}
                        </span>
                      )}
                    </>
                  ) : (
                    <>
                      <span className="w-14 shrink-0 text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                        {getBankTransactionTypeLabel(item.bankTransactionType!)}
                      </span>
                      <span className="flex-1">{item.title}</span>
                    </>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Disclaimer */}
          <div className="mt-8 pt-6 border-t-2 border-border">
            <div className="bg-muted p-4 rounded text-xs text-muted-foreground leading-relaxed">
              본 보고서는 RKYC 시스템이 감지한 시그널을 기반으로 생성된 참고 자료입니다. 
              자동 판단, 점수화, 예측 또는 조치를 의미하지 않으며, 
              최종 판단은 담당자 및 관련 조직의 책임 하에 이루어집니다.
            </div>
          </div>
        </div>
      </div>

      <ReportPreviewModal
        open={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        corporationId={corporation.id}
      />
    </MainLayout>
  );
}
