import { useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileDown, Link2, Eye } from "lucide-react";
import ReportDocument from "@/components/reports/ReportDocument";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import PDFExportModal from "@/components/reports/PDFExportModal";
import ShareLinkModal from "@/components/reports/ShareLinkModal";
import { CORPORATIONS, getCorporationById } from "@/data/corporations";

const ReportsPage = () => {
  const [selectedCorporationId, setSelectedCorporationId] = useState(CORPORATIONS[0].id);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showPDFModal, setShowPDFModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);

  const selectedCorporation = getCorporationById(selectedCorporationId);
  const companyName = selectedCorporation?.name ?? "기업";
  const defaultFileName = `RKYC_기업시그널보고서_${companyName}_${new Date().toISOString().split('T')[0]}`;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">보고서</h1>
          <p className="text-muted-foreground mt-1">
            RKYC 시스템이 감지한 시그널을 기반으로 기업별 참고 보고서를 생성하고 내보낼 수 있습니다.
            <br />
            <span className="text-xs">
              보고서는 기존 RKYC 데이터를 재구성하여 표시하며, 새로운 분석이나 판단을 생성하지 않습니다.
            </span>
          </p>
        </div>

        {/* Report Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">보고서 생성</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 space-y-2">
                <Label htmlFor="company" className="text-sm text-muted-foreground">
                  대상 기업 선택
                </Label>
                <Select
                  value={selectedCorporationId}
                  onValueChange={setSelectedCorporationId}
                >
                  <SelectTrigger id="company">
                    <SelectValue placeholder="기업 선택" />
                  </SelectTrigger>
                  <SelectContent>
                    {CORPORATIONS.map((corporation) => (
                      <SelectItem key={corporation.id} value={corporation.id}>
                        {corporation.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-end gap-2">
                <Button 
                  onClick={() => setShowPreviewModal(true)}
                  className="gap-2"
                >
                  <Eye className="h-4 w-4" />
                  보고서 미리보기
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => setShowPDFModal(true)}
                  className="gap-2"
                >
                  <FileDown className="h-4 w-4" />
                  PDF로 내보내기
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => setShowShareModal(true)}
                  className="gap-2"
                >
                  <Link2 className="h-4 w-4" />
                  보고서 공유 링크
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Report Preview (Inline) */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">보고서 내용</CardTitle>
            <span className="text-xs text-muted-foreground">
              아래는 기존 RKYC 데이터를 기반으로 구성된 보고서 미리보기입니다.
            </span>
          </CardHeader>
          <CardContent>
            <div className="border border-border rounded-lg bg-white p-8 max-h-[800px] overflow-auto">
              <ReportDocument corporationId={selectedCorporationId} />
            </div>
          </CardContent>
        </Card>

        {/* Disclaimer */}
        <div className="text-xs text-muted-foreground p-4 bg-muted rounded-lg">
          본 보고서는 RKYC 시스템이 감지한 시그널을 기반으로 생성된 참고 자료입니다. 
          자동 판단, 점수화, 예측 또는 조치를 의미하지 않으며, 
          최종 판단은 담당자 및 관련 조직의 책임 하에 이루어집니다.
        </div>
      </div>

      {/* Modals */}
      <ReportPreviewModal
        open={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        corporationId={selectedCorporationId}
      />

      <PDFExportModal
        open={showPDFModal}
        onClose={() => setShowPDFModal(false)}
        fileName={defaultFileName}
      />

      <ShareLinkModal
        open={showShareModal}
        onClose={() => setShowShareModal(false)}
        companyName={companyName}
      />
    </MainLayout>
  );
};

export default ReportsPage;
