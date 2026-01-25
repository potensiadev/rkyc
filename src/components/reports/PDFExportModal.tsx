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
      setProgress(10);

      // Wait for fonts to load completely
      await document.fonts.ready;

      // Additional delay for font rendering
      await new Promise(resolve => setTimeout(resolve, 300));

      setProgress(20);

      const element = contentRef.current;

      // A4 dimensions in mm: 210 x 297
      // With 15mm margins: content area = 180 x 267mm
      // At 96 DPI: 180mm = ~680px
      const A4_WIDTH_MM = 210;
      const A4_HEIGHT_MM = 297;
      const MARGIN_MM = 15;
      const CONTENT_WIDTH_MM = A4_WIDTH_MM - (MARGIN_MM * 2);
      const CONTENT_HEIGHT_MM = A4_HEIGHT_MM - (MARGIN_MM * 2);

      // Pixel dimensions (at 96 DPI, 1mm ≈ 3.78px)
      const MM_TO_PX = 3.78;
      const CONTENT_WIDTH_PX = Math.floor(CONTENT_WIDTH_MM * MM_TO_PX);

      setProgress(30);

      // Clone and prepare element for capture
      const clonedElement = element.cloneNode(true) as HTMLElement;
      clonedElement.style.width = `${CONTENT_WIDTH_PX}px`;
      clonedElement.style.maxWidth = `${CONTENT_WIDTH_PX}px`;
      clonedElement.style.position = 'absolute';
      clonedElement.style.left = '-9999px';
      clonedElement.style.top = '0';
      clonedElement.style.backgroundColor = '#ffffff';
      clonedElement.style.padding = '0';
      clonedElement.style.margin = '0';

      // Apply PDF-optimized styles to cloned element
      const styleElement = document.createElement('style');
      styleElement.textContent = `
        * {
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          text-rendering: optimizeLegibility;
        }
        .line-clamp-1, .line-clamp-2, .line-clamp-3 {
          display: block !important;
          -webkit-line-clamp: unset !important;
          overflow: visible !important;
          text-overflow: clip !important;
          white-space: normal !important;
        }
        .truncate {
          overflow: visible !important;
          text-overflow: clip !important;
          white-space: normal !important;
          word-break: break-word !important;
        }
      `;
      clonedElement.prepend(styleElement);

      document.body.appendChild(clonedElement);

      // Wait for layout
      await new Promise(resolve => setTimeout(resolve, 100));

      setProgress(40);

      // Capture with improved settings
      const canvas = await html2canvas(clonedElement, {
        scale: 2, // Higher scale for better quality
        useCORS: true,
        logging: false,
        backgroundColor: "#ffffff",
        width: CONTENT_WIDTH_PX,
        height: clonedElement.scrollHeight,
        windowWidth: CONTENT_WIDTH_PX,
        windowHeight: clonedElement.scrollHeight,
        imageTimeout: 15000,
        // Improve text rendering
        onclone: (clonedDoc, clonedEl) => {
          // Force font family on all text elements
          const textElements = clonedEl.querySelectorAll('*');
          textElements.forEach((el) => {
            if (el instanceof HTMLElement) {
              const computedStyle = window.getComputedStyle(el);
              // Preserve existing font but ensure fallback
              el.style.fontFamily = `${computedStyle.fontFamily}, "Malgun Gothic", "맑은 고딕", sans-serif`;
            }
          });
        },
      });

      // Remove cloned element
      document.body.removeChild(clonedElement);

      setProgress(60);

      // Create PDF
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4",
        compress: true,
      });

      const imgWidth = canvas.width;
      const imgHeight = canvas.height;

      // Calculate dimensions for PDF
      const pdfContentWidth = CONTENT_WIDTH_MM;
      const scale = pdfContentWidth / (imgWidth / 2); // Divide by 2 because canvas scale is 2
      const scaledHeight = (imgHeight / 2) * scale;

      // Calculate number of pages
      const totalPages = Math.ceil(scaledHeight / CONTENT_HEIGHT_MM);

      setProgress(70);

      // Source height per page in canvas pixels (accounting for scale)
      const sourceHeightPerPage = (CONTENT_HEIGHT_MM / scale) * 2;

      for (let page = 0; page < totalPages; page++) {
        if (page > 0) {
          pdf.addPage();
        }

        // Calculate source area for this page
        const sourceY = page * sourceHeightPerPage;
        const remainingHeight = imgHeight - sourceY;
        const sourceHeight = Math.min(sourceHeightPerPage, remainingHeight);

        if (sourceHeight <= 0) continue;

        // Create a temporary canvas for this page
        const pageCanvas = document.createElement("canvas");
        pageCanvas.width = imgWidth;
        pageCanvas.height = Math.ceil(sourceHeight);
        const ctx = pageCanvas.getContext("2d");

        if (ctx) {
          // White background
          ctx.fillStyle = "#ffffff";
          ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height);

          // Draw portion of the main canvas
          ctx.drawImage(
            canvas,
            0, sourceY,           // Source x, y
            imgWidth, sourceHeight, // Source width, height
            0, 0,                   // Dest x, y
            imgWidth, sourceHeight  // Dest width, height
          );

          const pageImgData = pageCanvas.toDataURL("image/png", 1.0);

          // Calculate actual height for this page content
          const actualPageHeight = (sourceHeight / 2) * scale;

          pdf.addImage(
            pageImgData,
            "PNG",
            MARGIN_MM,
            MARGIN_MM,
            pdfContentWidth,
            actualPageHeight,
            undefined,
            'FAST'
          );
        }

        setProgress(70 + Math.floor((page / totalPages) * 20));
      }

      setProgress(95);

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
