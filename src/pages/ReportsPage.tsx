import { useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileDown, Link2, Eye, Search } from "lucide-react";
import ReportDocument from "@/components/reports/ReportDocument";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import PDFExportModal from "@/components/reports/PDFExportModal";
import ShareLinkModal from "@/components/reports/ShareLinkModal";
import { ScrollArea } from "@/components/ui/scroll-area";

const mockCompanies = [
  { id: "1", name: "삼성전자", hasLoan: true },
  { id: "2", name: "SK하이닉스", hasLoan: true },
  { id: "3", name: "현대자동차", hasLoan: false },
  { id: "4", name: "LG에너지솔루션", hasLoan: true },
  { id: "5", name: "카카오", hasLoan: false },
];

const ReportsPage = () => {
  const [selectedCompany, setSelectedCompany] = useState(mockCompanies[0]);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showPDFModal, setShowPDFModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);

  const defaultFileName = `RKYC_기업시그널보고서_${selectedCompany.name}_${new Date().toISOString().split('T')[0]}`;

  const handleCompanyChange = (companyId: string) => {
    const company = mockCompanies.find(c => c.id === companyId);
    if (company) {
      setSelectedCompany(company);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">보고서</h1>
          <p className="text-muted-foreground mt-1">
            RKYC 시스템이 감지한 시그널을 기반으로 기업별 참고 보고서를 생성하고 내보낼 수 있습니다.
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
                  value={selectedCompany.id}
                  onValueChange={handleCompanyChange}
                >
                  <SelectTrigger id="company">
                    <SelectValue placeholder="기업 선택" />
                  </SelectTrigger>
                  <SelectContent>
                    {mockCompanies.map((company) => (
                      <SelectItem key={company.id} value={company.id}>
                        {company.name}
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
              아래는 현재 선택된 기업의 보고서 미리보기입니다.
            </span>
          </CardHeader>
          <CardContent>
            <div className="border border-border rounded-lg bg-white p-8 max-h-[800px] overflow-auto">
              <ReportDocument
                companyName={selectedCompany.name}
                showLoanSection={selectedCompany.hasLoan}
              />
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
        companyName={selectedCompany.name}
        showLoanSection={selectedCompany.hasLoan}
      />

      <PDFExportModal
        open={showPDFModal}
        onClose={() => setShowPDFModal(false)}
        fileName={defaultFileName}
      />

      <ShareLinkModal
        open={showShareModal}
        onClose={() => setShowShareModal(false)}
        companyName={selectedCompany.name}
      />
    </MainLayout>
  );
};

export default ReportsPage;
