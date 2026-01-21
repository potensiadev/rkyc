import React from "react";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

export function Navbar() {
    return (
        <nav className="fixed top-0 left-0 right-0 z-50 flex justify-center py-6">
            <div className="flex h-12 items-center gap-8 rounded-full border border-white/10 bg-black/50 px-6 backdrop-blur-xl transition-all hover:bg-black/70 hover:border-white/20 hover:scale-105">
                <Link to="/" className="text-lg font-bold tracking-tighter text-white flex items-center gap-2">
                    <div className="w-3 h-3 bg-primary rounded-full shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                    RKYC
                </Link>
                <div className="h-4 w-[1px] bg-white/10" />
                <div className="flex items-center gap-6 text-sm font-medium text-muted-foreground">
                    <Link to="/features" className="hover:text-white transition-colors">Features</Link>
                    <Link to="/customers" className="hover:text-white transition-colors">Customers</Link>
                    <Link to="/dashboard" className="text-white hover:text-primary transition-colors">Sign In</Link>
                </div>
            </div>
        </nav>
    );
}
