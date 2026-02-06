import React from "react";
import { Sparkles } from "lucide-react";

interface ContextualHighlightProps {
    text: string;
    reason: string;
}

export const ContextualHighlight = ({ text, reason }: ContextualHighlightProps) => (
    <span className="relative group cursor-help inline-block decoration-rose-300/50 underline decoration-2 underline-offset-4 hover:decoration-rose-400 transition-all">
        {text}
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-900/90 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 backdrop-blur-md">
            <span className="flex items-center gap-2 mb-1 text-rose-300 font-bold">
                <Sparkles className="w-3 h-3" /> AI Insight
            </span>
            {reason}
        </span>
    </span>
);
