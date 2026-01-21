import React from "react";
import { Navbar } from "@/components/ui/Navbar";
import { Hero } from "@/components/ui/Hero";
import { BentoGrid } from "@/components/ui/BentoGrid";
import { LiveSignalTicker } from "@/components/landing/LiveSignalTicker";

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-black text-white antialiased selection:bg-primary/20 selection:text-white">
            <Navbar />
            <Hero />
            <LiveSignalTicker />
            <BentoGrid />

            {/* Footer Mock */}
            <footer className="py-12 border-t border-white/10 bg-black text-center text-white/40 text-sm">
                <p>© 2026 RKYC Intelligence. Built for Wall Street.</p>
            </footer>
        </div>
    );
}
