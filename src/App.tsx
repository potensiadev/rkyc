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
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
