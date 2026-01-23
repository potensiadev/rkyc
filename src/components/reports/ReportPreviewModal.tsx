import { useState, useRef, lazy, Suspense } from "react";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileDown, Loader2, X } from "lucide-react";
import ExportSettingsPanel from "./ExportSettingsPanel";
import PDFExportModal from "./PDFExportModal";
import { useCorporation } from "@/hooks/useApi";

// Lazy load ReportDocument for better initial load
const ReportDocument = lazy(() => import("./ReportDocument"));

// Fallback component while ReportDocument loads
const ReportLoadingFallback = () => (
  <div className="flex flex-col items-center justify-center py-20 space-y-4">
    <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
    <p className="text-sm text-muted-foreground">보고서 컴포넌트 로딩 중...</p>
  </div>
);

interface ReportPreviewModalProps {
  open: boolean;
  onClose: () => void;
  corporationId: string;
}

const ReportPreviewModal = ({
  open,
  onClose,
  corporationId,
}: ReportPreviewModalProps) => {
  const { data: corporation } = useCorporation(corporationId);
  const companyName = corporation?.name ?? "기업";
  const reportRef = useRef<HTMLDivElement>(null);

  const defaultFileName = `RKYC_기업시그널보고서_${companyName}_${new Date().toISOString().split('T')[0]}`;

  const [fileName, setFileName] = useState(defaultFileName);
  const [sections, setSections] = useState({
    summary: true,
    companyOverview: true,
    valueChain: false,
    signalTypeSummary: true,
    signalTimeline: true,
    evidenceSummary: true,
    loanInsight: true,
    insightMemory: false,
    disclaimer: true,
  });
  const [showPDFModal, setShowPDFModal] = useState(false);

  const handleSectionChange = (section: keyof typeof sections, checked: boolean) => {
    setSections(prev => ({ ...prev, [section]: checked }));
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[90vh] p-0 gap-0" hideCloseButton>
          {/* Top Bar */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <div>
              <h2 className="text-lg font-semibold text-foreground">보고서 미리보기</h2>
              <p className="text-sm text-muted-foreground">
                PDF 내보내기 전 최종 확인용 화면입니다. 기존 RKYC 데이터를 기반으로 구성됩니다.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => setShowPDFModal(true)}
                className="gap-2"
              >
                <FileDown className="h-4 w-4" />
                PDF로 내보내기
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex flex-1 overflow-hidden">
            {/* Left: PDF Preview */}
            <div className="flex-1 bg-muted/50 p-8 overflow-auto">
              <div className="max-w-[210mm] mx-auto bg-white shadow-lg rounded-sm">
                {/* p-8 instead of p-12 for better A4 fit, data-report-content for PDF capture */}
                <div className="p-8" style={{ maxWidth: '680px', margin: '0 auto' }} ref={reportRef} data-report-content>
                  <ScrollArea className="h-full">
                    <Suspense fallback={<ReportLoadingFallback />}>
                      <ReportDocument
                        corporationId={corporationId}
                        sectionsToShow={sections}
                      />
                    </Suspense>
                  </ScrollArea>
                </div>
              </div>
            </div>

            {/* Right: Export Settings */}
            <div className="w-72 border-l border-border p-6 overflow-auto bg-background">
              <ExportSettingsPanel
                fileName={fileName}
                onFileNameChange={setFileName}
                sections={sections}
                onSectionChange={handleSectionChange}
                corporationId={corporationId}
              />
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <PDFExportModal
        open={showPDFModal}
        onClose={() => setShowPDFModal(false)}
        fileName={fileName}
        contentRef={reportRef}
      />
    </>
  );
};

export default ReportPreviewModal;
