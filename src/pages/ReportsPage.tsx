import { useState, useRef } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileDown, Link2, Eye, Printer } from "lucide-react";
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
  const reportRef = useRef<HTMLDivElement>(null);

  const selectedCorporation = getCorporationById(selectedCorporationId);
  const companyName = selectedCorporation?.name ?? "기업";
  const defaultFileName = `RKYC_기업시그널보고서_${companyName}_${new Date().toISOString().split('T')[0]}`;

  return (
    <MainLayout>
      <div className="space-y-6 max-w-5xl mx-auto">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">보고서 관리</h1>
          <p className="text-muted-foreground mt-2">
            기업별 시그널 분석 보고서를 조회하고 PDF로 내보내거나 공유할 수 있습니다.
          </p>
        </div>

        {/* Report Controls */}
        <Card>
          <CardHeader>
            <CardTitle>보고서 생성 옵션</CardTitle>
            <CardDescription>
              보고서를 생성할 대상 기업을 선택하세요.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              {/* Select component for corporation */}
              <div className="flex-1 space-y-2 w-full">
                <Label htmlFor="company">대상 기업 선택</Label>
                <Select value={selectedCorporationId} onValueChange={setSelectedCorporationId}>
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

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowPreviewModal(true)}>
                  <Eye className="w-4 h-4 mr-2" />
                  미리보기
                </Button>
                <Button variant="default" onClick={() => setShowPDFModal(true)}>
                  <FileDown className="w-4 h-4 mr-2" />
                  PDF 다운로드
                </Button>
                <Button variant="secondary" onClick={() => setShowShareModal(true)}>
                  <Link2 className="w-4 h-4 mr-2" />
                  링크 공유
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Report Preview Area */}
        <div className="border rounded-lg bg-background shadow-sm overflow-hidden">
          <div className="bg-muted px-4 py-2 border-b flex justify-between items-center">
            <span className="text-sm font-medium text-muted-foreground">미리보기: {defaultFileName}.pdf</span>
            <Button variant="ghost" size="sm" disabled>
              <Printer className="w-4 h-4 mr-2" /> 인쇄
            </Button>
          </div>
          <div className="h-[600px] overflow-auto bg-white p-8">
            <div ref={reportRef}>
              <ReportDocument corporationId={selectedCorporationId} />
            </div>
          </div>
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
        contentRef={reportRef}
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
