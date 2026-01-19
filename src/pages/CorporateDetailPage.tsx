import { useParams, useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
// Mock data imports removed
import {
  formatDate,
  getBankTransactionTypeLabel,
} from "@/data/signals";
import { SIGNAL_TYPE_CONFIG, SIGNAL_IMPACT_CONFIG } from "@/types/signal";
import {
  ArrowLeft,
  Building2,
  Landmark,
  Users,
  Link2,
  Loader2,
  FileDown,
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
  const { data: corporation, isLoading: isLoadingCorp } = useCorporation(corporateId || "");
  const { data: apiSignals, isLoading: isLoadingSignals } = useSignals({ corp_id: corporateId });
  const { data: snapshot, isLoading: isLoadingSnapshot } = useCorporationSnapshot(corporateId || "");

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

  // API 시그널 카운트
  const signalCounts = apiSignals ? {
    direct: apiSignals.filter(s => s.signalCategory === 'direct').length,
    industry: apiSignals.filter(s => s.signalCategory === 'industry').length,
    environment: apiSignals.filter(s => s.signalCategory === 'environment').length,
  } : { direct: 0, industry: 0, environment: 0 };

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
                사업을 영위하는 기업입니다.
                {corporation.headquarters ? `본사는 ${corporation.headquarters}에 소재하고 있습니다.` : ''}
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
                {/* Mock data fields removed unless populated by API */}
                {corporation.headquarters && <div className="flex"><span className="w-28 text-muted-foreground">본사 소재지</span><span>{corporation.headquarters}</span></div>}
              </div>
            </div>
          </section>

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
                    <span className={`px-2 py-0.5 rounded text-xs ${snapshot.snapshot_json.corp.kyc_status.is_kyc_completed
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                      }`}>
                      {snapshot.snapshot_json.corp.kyc_status.is_kyc_completed ? 'KYC 완료' : 'KYC 미완료'}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs ${snapshot.snapshot_json.corp.kyc_status.internal_risk_grade === 'HIGH'
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
