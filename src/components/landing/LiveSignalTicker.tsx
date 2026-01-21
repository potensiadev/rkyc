import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, TrendingUp, ShieldAlert } from "lucide-react";

const SIGNALS = [
    { id: 1, type: "risk", message: "Supply chain disruption detected in Southeast Asia", source: "Global Trade News", time: "2s ago" },
    { id: 2, type: "opportunity", message: "Semiconductor yield rates improving at TSMC", source: "TechCrunch", time: "5s ago" },
    { id: 3, type: "warning", message: "Regulatory change proposed for EU AI Act", source: "Reuters", time: "12s ago" },
    { id: 4, type: "risk", message: "Unusual trading volume for manufacturing sector", source: "Bloomberg Terminal", time: "15s ago" },
    { id: 5, type: "opportunity", message: "New lithium deposit verification complete", source: "Mining Weekly", time: "22s ago" },
];

export function LiveSignalTicker() {
    const [signals, setSignals] = useState(SIGNALS);

    // Simulate incoming live data
    useEffect(() => {
        const interval = setInterval(() => {
            setSignals((prev) => {
                const first = prev[0];
                const rest = prev.slice(1);
                return [...rest, { ...first, id: Date.now(), time: "Just now" }];
            });
        }, 4000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="w-full bg-black/60 backdrop-blur-md border-y border-white/5 py-4 overflow-hidden relative">
            <div className="max-w-7xl mx-auto px-4 flex items-center gap-4">
                <div className="flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-wider min-w-max">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                    </span>
                    Live Intelligence
                </div>

                <div className="flex-1 overflow-hidden relative h-8">
                    <AnimatePresence mode="popLayout">
                        <motion.div
                            key={signals[0].id}
                            initial={{ y: 20, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: -20, opacity: 0 }}
                            className="flex items-center gap-3 text-sm text-white/80 absolute top-1 left-0"
                        >
                            {signals[0].type === 'risk' ? <ShieldAlert className="w-4 h-4 text-red-500" /> :
                                signals[0].type === 'opportunity' ? <TrendingUp className="w-4 h-4 text-emerald-500" /> :
                                    <AlertCircle className="w-4 h-4 text-yellow-500" />}
                            <span className="font-medium">{signals[0].message}</span>
                            <span className="text-white/40 text-xs border-l border-white/10 pl-3">{signals[0].source}</span>
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
