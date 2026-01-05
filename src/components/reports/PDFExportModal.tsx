import { useState, useEffect, useCallback, RefObject } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Download, Loader2 } from "lucide-react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

interface PDFExportModalProps {
  open: boolean;
  onClose: () => void;
  fileName: string;
  contentRef: RefObject<HTMLDivElement>;
}

const PDFExportModal = ({ open, onClose, fileName, contentRef }: PDFExportModalProps) => {
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const generatePDF = useCallback(async () => {
    setError(null);

    if (!contentRef || !contentRef.current) {
      console.error("Content ref is not available");
      setError("보고서 콘텐츠를 찾을 수 없습니다. 다시 시도해주세요.");
      setProgress(100);
      setIsComplete(true);
      return;
    }

    try {
      setProgress(20);

      // Wait for fonts to load
      await document.fonts.ready;

      setProgress(40);

      const element = contentRef.current;

      // Capture the element
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: "#ffffff",
        width: element.scrollWidth,
        height: element.scrollHeight,
        windowWidth: element.scrollWidth,
        windowHeight: element.scrollHeight,
      });

      setProgress(60);

      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4",
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;

      // Calculate scale to fit width with margins
      const margin = 10;
      const scale = (pdfWidth - margin * 2) / imgWidth;
      const scaledWidth = imgWidth * scale;
      const scaledHeight = imgHeight * scale;

      // Calculate number of pages needed
      const pageContentHeight = pdfHeight - margin * 2;
      const totalPages = Math.ceil(scaledHeight / pageContentHeight);

      setProgress(70);

      for (let page = 0; page < totalPages; page++) {
        if (page > 0) {
          pdf.addPage();
        }

        // Calculate source area for this page
        const sourceY = (page * pageContentHeight) / scale;
        const sourceHeight = Math.min(pageContentHeight / scale, imgHeight - sourceY);

        // Create a temporary canvas for this page
        const pageCanvas = document.createElement("canvas");
        pageCanvas.width = imgWidth;
        pageCanvas.height = Math.ceil(sourceHeight);
        const ctx = pageCanvas.getContext("2d");

        if (ctx) {
          ctx.fillStyle = "#ffffff";
          ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);
          ctx.drawImage(
            canvas,
            0, sourceY,
            imgWidth, sourceHeight,
            0, 0,
            imgWidth, sourceHeight
          );

          const pageImgData = pageCanvas.toDataURL("image/png");
          pdf.addImage(
            pageImgData,
            "PNG",
            margin,
            margin,
            scaledWidth,
            sourceHeight * scale
          );
        }
      }

      setProgress(90);

      // Generate blob for download
      const blob = pdf.output("blob");
      setPdfBlob(blob);

      setProgress(100);
      setIsComplete(true);
    } catch (err) {
      console.error("PDF generation failed:", err);
      setError("PDF 생성 중 오류가 발생했습니다. 다시 시도해주세요.");
      setProgress(100);
      setIsComplete(true);
    }
  }, [contentRef]);

  useEffect(() => {
    if (open) {
      setProgress(0);
      setIsComplete(false);
      setPdfBlob(null);
      setError(null);

      // Start PDF generation after a short delay to ensure ref is ready
      const timer = setTimeout(() => {
        generatePDF();
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [open, generatePDF]);

  const handleDownload = async () => {
    if (!pdfBlob) {
      return;
    }

    setIsDownloading(true);

    // Create download link
    const url = URL.createObjectURL(pdfBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${fileName}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setIsDownloading(false);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-center">
            {!isComplete ? "PDF 생성 중" : error ? "PDF 생성 실패" : "PDF 생성 완료"}
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
          ) : error ? (
            <div className="space-y-4 text-center">
              <div className="flex justify-center">
                <div className="h-12 w-12 rounded-full bg-red-100 flex items-center justify-center">
                  <span className="text-red-600 text-xl">!</span>
                </div>
              </div>
              <p className="text-sm text-red-600">
                {error}
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
          {isComplete && !error && (
            <Button onClick={handleDownload} className="gap-2" disabled={isDownloading || !pdfBlob}>
              {isDownloading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
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
