import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import CorporationSearch from "./pages/CorporationSearch";
import DirectSignalPage from "./pages/DirectSignalPage";
import IndustrySignalPage from "./pages/IndustrySignalPage";
import EnvironmentSignalPage from "./pages/EnvironmentSignalPage";
import SignalDetailPage from "./pages/SignalDetailPage";
import CorporateDetailPage from "./pages/CorporateDetailPage";
import DailyBriefingPage from "./pages/DailyBriefingPage";
import AnalyticsStatusPage from "./pages/AnalyticsStatusPage";
import ReportsPage from "./pages/ReportsPage";
// 신규 법인 KYC - 비활성화
// import NewKycUploadPage from "./pages/NewKycUploadPage";
// import NewKycAnalysisPage from "./pages/NewKycAnalysisPage";
// import NewKycReportPage from "./pages/NewKycReportPage";
import SettingsPage from "./pages/SettingsPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/corporations" element={<CorporationSearch />} />
          <Route path="/briefing" element={<DailyBriefingPage />} />
          <Route path="/analytics" element={<AnalyticsStatusPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/signals/direct" element={<DirectSignalPage />} />
          <Route path="/signals/industry" element={<IndustrySignalPage />} />
          <Route path="/signals/environment" element={<EnvironmentSignalPage />} />
          <Route path="/signals/:signalId" element={<SignalDetailPage />} />
          <Route path="/corporates/:corporateId" element={<CorporateDetailPage />} />
          {/* 신규 법인 KYC - 비활성화
          <Route path="/new-kyc" element={<NewKycUploadPage />} />
          <Route path="/new-kyc/analysis/:jobId" element={<NewKycAnalysisPage />} />
          <Route path="/new-kyc/report/:jobId" element={<NewKycReportPage />} />
          */}
          <Route path="/settings" element={<SettingsPage />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
