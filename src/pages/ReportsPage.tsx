import { useState, useRef } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileDown, Eye, Printer, Loader2, FileText } from "lucide-react";
import ReportDocument from "@/components/reports/ReportDocument";
import ReportPreviewModal from "@/components/reports/ReportPreviewModal";
import PDFExportModal from "@/components/reports/PDFExportModal";
import { useCorporations, useCorporation } from "@/hooks/useApi";
import {
  DynamicBackground,
  GlassCard
} from "@/components/premium";
import { motion } from "framer-motion";

const ReportsPage = () => {
  const { data: corporations = [], isLoading } = useCorporations();
  const [selectedCorporationId, setSelectedCorporationId] = useState<string>("");
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showPDFModal, setShowPDFModal] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);

  // Set default selection when corporations load
  if (!selectedCorporationId && corporations.length > 0) {
    setSelectedCorporationId(corporations[0].id);
  }

  const { data: selectedCorporation } = useCorporation(selectedCorporationId);
  const companyName = selectedCorporation?.name ?? "기업";
  const defaultFileName = `RKYC_기업시그널보고서_${companyName}_${new Date().toISOString().split('T')[0]}`;

  return (
    <MainLayout>
      <DynamicBackground />
      <div className="space-y-6 max-w-5xl mx-auto pb-20 relative z-10 p-6">
        {/* Page Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4 mb-2"
        >
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 backdrop-blur-sm">
            <FileText className="w-6 h-6 text-indigo-500" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Report Management</h1>
            <p className="text-slate-500 font-medium mt-1">
              Generate, preview, and export comprehensive signal analysis reports.
            </p>
          </div>
        </motion.div>

        {/* Report Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <GlassCard className="p-6">
            <div className="flex flex-col gap-1 mb-6">
              <h3 className="text-lg font-semibold text-slate-900">Report Generator</h3>
              <p className="text-sm text-slate-500">Select a corporation to generate a detailed compliance and risk signal report.</p>
            </div>

            {isLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row gap-5 items-end">
                {/* Select component for corporation */}
                <div className="flex-1 space-y-2 w-full">
                  <Label htmlFor="company" className="text-sm font-medium text-slate-700 ml-1">Select Corporation</Label>
                  <Select value={selectedCorporationId} onValueChange={setSelectedCorporationId}>
                    <SelectTrigger id="company" className="h-11 bg-white/50 backdrop-blur-sm border-slate-200 focus:ring-indigo-500">
                      <SelectValue placeholder="Select a corporation..." />
                    </SelectTrigger>
                    <SelectContent>
                      {corporations.map((corporation) => (
                        <SelectItem key={corporation.id} value={corporation.id}>
                          {corporation.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 w-full sm:w-auto">
                  <Button variant="outline" className="h-11 px-5 border-slate-200 hover:bg-slate-50 gap-2 flex-1 sm:flex-none" onClick={() => setShowPreviewModal(true)} disabled={!selectedCorporationId}>
                    <Eye className="w-4 h-4" />
                    Preview
                  </Button>
                  <Button variant="default" className="h-11 px-5 bg-indigo-600 hover:bg-indigo-700 gap-2 flex-1 sm:flex-none shadow-md shadow-indigo-200" onClick={() => setShowPDFModal(true)} disabled={!selectedCorporationId}>
                    <FileDown className="w-4 h-4" />
                    Export PDF
                  </Button>
                </div>
              </div>
            )}
          </GlassCard>
        </motion.div>

        {/* Report Preview Area */}
        {selectedCorporationId && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="border border-slate-200 rounded-xl bg-white shadow-sm overflow-hidden ring-1 ring-slate-100"
          >
            <div className="bg-slate-50/80 backdrop-blur px-5 py-3 border-b border-slate-200 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <span className="text-sm font-medium text-slate-600">Preview: {defaultFileName}.pdf</span>
              </div>
              <Button variant="ghost" size="sm" disabled className="text-slate-400">
                <Printer className="w-4 h-4 mr-2" /> Print
              </Button>
            </div>
            <div className="h-[600px] overflow-auto bg-slate-100/50 p-8 custom-scrollbar">
              <div className="bg-white shadow-lg mx-auto max-w-4xl min-h-[800px] p-10" ref={reportRef}>
                <ReportDocument corporationId={selectedCorporationId} />
              </div>
            </div>
          </motion.div>
        )}

      </div>

      {/* Modals */}
      {selectedCorporationId && (
        <>
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
        </>
      )}
    </MainLayout>
  );
};

export default ReportsPage;
