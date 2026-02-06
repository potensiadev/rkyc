import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

interface MainLayoutProps {
  children: ReactNode;
}

import { DynamicBackground } from "@/components/premium";

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="flex min-h-screen bg-[#F8FAFC] text-slate-900 font-sans relative selection:bg-indigo-100 selection:text-indigo-900">
      <DynamicBackground />
      <Sidebar />
      <main className="flex-1 ml-64 p-8 transition-all duration-300 ease-in-out relative z-10">
        {children}
      </main>
    </div>
  );
}
