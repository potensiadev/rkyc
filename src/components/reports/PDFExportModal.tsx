import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Download } from "lucide-react";

interface PDFExportModalProps {
  open: boolean;
  onClose: () => void;
  fileName: string;
}

const PDFExportModal = ({ open, onClose, fileName }: PDFExportModalProps) => {
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (open) {
      setProgress(0);
      setIsComplete(false);
      
      const interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);
            setIsComplete(true);
            return 100;
          }
          return prev + 20;
        });
      }, 400);

      return () => clearInterval(interval);
    }
  }, [open]);

  const handleDownload = () => {
    // Simulate download
    const link = document.createElement('a');
    link.href = '#';
    link.download = `${fileName}.pdf`;
    // In a real implementation, this would trigger actual PDF download
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center">
            {isComplete ? "PDF 생성 완료" : "PDF 생성 중"}
          </DialogTitle>
        </DialogHeader>

        <div className="py-6">
          {!isComplete ? (
            <div className="space-y-4">
              <Progress value={progress} className="w-full" />
              <p className="text-sm text-muted-foreground text-center">
                보고서를 PDF로 변환하고 있습니다. 잠시만 기다려주세요.
              </p>
            </div>
          ) : (
            <div className="space-y-4 text-center">
              <div className="flex justify-center">
                <CheckCircle2 className="h-12 w-12 text-primary" />
              </div>
              <p className="text-sm text-muted-foreground">
                보고서 PDF가 생성되었습니다.
              </p>
              <p className="text-xs text-muted-foreground">
                {fileName}.pdf
              </p>
            </div>
          )}
        </div>

        <div className="flex justify-center gap-3">
          {isComplete && (
            <Button onClick={handleDownload} className="gap-2">
              <Download className="h-4 w-4" />
              다운로드
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            닫기
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default PDFExportModal;
