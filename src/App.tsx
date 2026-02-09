import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ErrorBoundary } from "@/components/ErrorBoundary";
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
import SettingsPage from "./pages/SettingsPage";
import DesignShowcasePage from "./pages/DesignShowcasePage";
import NotFound from "./pages/NotFound";
import LandingPage from "./pages/LandingPage";

import BankingDataDemoPage from "./pages/BankingDataDemoPage";

const queryClient = new QueryClient();

const App = () => (
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/landing" element={<LandingPage />} />
            <Route path="/banking-demo" element={<BankingDataDemoPage />} />
            <Route path="/" element={<Index />} />
            <Route path="/corporations" element={<CorporationSearch />} />
            <Route path="/briefing" element={<DailyBriefingPage />} />
            <Route path="/analytics" element={<AnalyticsStatusPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/signals/direct" element={<DirectSignalPage />} />
            <Route path="/signals/industry" element={<IndustrySignalPage />} />
            <Route path="/signals/environment" element={<EnvironmentSignalPage />} />
            <Route path="/signals/:signalId" element={<SignalDetailPage />} />
            <Route path="/corporations/:corpId" element={<CorporateDetailPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/design-showcase" element={<DesignShowcasePage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

export default App;
