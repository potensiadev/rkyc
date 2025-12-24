import { useState } from "react";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileDown, Link2, X } from "lucide-react";
import ReportDocument from "./ReportDocument";
import ExportSettingsPanel from "./ExportSettingsPanel";
import PDFExportModal from "./PDFExportModal";
import ShareLinkModal from "./ShareLinkModal";

interface ReportPreviewModalProps {
  open: boolean;
  onClose: () => void;
  companyName: string;
  showLoanSection: boolean;
}

const ReportPreviewModal = ({
  open,
  onClose,
  companyName,
  showLoanSection,
}: ReportPreviewModalProps) => {
  const defaultFileName = `RKYC_기업시그널보고서_${companyName}_${new Date().toISOString().split('T')[0]}`;
  
  const [fileName, setFileName] = useState(defaultFileName);
  const [sections, setSections] = useState({
    summary: true,
    companyOverview: true,
    signalTypeSummary: true,
    signalTimeline: true,
    evidenceSummary: true,
    loanInsight: true,
    insightMemory: true,
    disclaimer: true,
  });
  const [showPDFModal, setShowPDFModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);

  const handleSectionChange = (section: keyof typeof sections, checked: boolean) => {
    setSections(prev => ({ ...prev, [section]: checked }));
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-7xl h-[90vh] p-0 gap-0">
          {/* Top Bar */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <div>
              <h2 className="text-lg font-semibold text-foreground">보고서 미리보기</h2>
              <p className="text-sm text-muted-foreground">
                PDF 내보내기 전 최종 확인용 화면입니다.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowShareModal(true)}
                className="gap-2"
              >
                <Link2 className="h-4 w-4" />
                공유 링크 생성
              </Button>
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
                <div className="p-12">
                  <ScrollArea className="h-full">
                    <ReportDocument
                      companyName={companyName}
                      showLoanSection={showLoanSection}
                      sectionsToShow={sections}
                    />
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
                showLoanSection={showLoanSection}
              />
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <PDFExportModal
        open={showPDFModal}
        onClose={() => setShowPDFModal(false)}
        fileName={fileName}
      />

      <ShareLinkModal
        open={showShareModal}
        onClose={() => setShowShareModal(false)}
        companyName={companyName}
      />
    </>
  );
};

export default ReportPreviewModal;
