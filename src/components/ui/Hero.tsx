import React from "react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

export function Hero() {
    return (
        <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background pt-20">
            {/* Background Gradients & Spotlights */}
            <div className="absolute inset-0 w-full h-full bg-background bg-grid-white/[0.02] -z-10" />
            <div className="absolute top-0 left-1/2 w-full -translate-x-1/2 h-[500px] bg-primary/20 blur-[120px] rounded-full opacity-50 -z-10" />

            {/* Spotlight Animation */}
            <div className="pointer-events-none absolute -top-40 left-0 right-0 mx-auto h-[500px] w-full max-w-7xl bg-gradient-to-r from-transparent via-primary/30 to-transparent blur-3xl opacity-20 animate-spotlight" />

            <div className="container relative z-10 px-4 md:px-6 text-center">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    className="inline-flex items-center rounded-full border border-white/5 bg-white/5 px-3 py-1 text-sm text-white/80 backdrop-blur-xl mb-8"
                >
                    <span className="flex h-2 w-2 rounded-full bg-signal-new mr-2 animate-pulse" />
                    RKYC 2.0 is now live
                </motion.div>

                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                    className="mx-auto max-w-5xl text-5xl font-bold tracking-tighter sm:text-7xl md:text-8xl bg-clip-text text-transparent bg-gradient-to-b from-white to-white/40"
                >
                    Risk Detection, <br />
                    <span className="text-white">Reinvented.</span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.4 }}
                    className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl"
                >
                    The AI-powered sentry for global finance. Detect risks in real-time with
                    institutional-grade precision and speed.
                </motion.p>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.5 }}
                    className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
                >
                    <a
                        href="/dashboard"
                        className="group relative inline-flex h-12 items-center justify-center rounded-full bg-white px-8 font-medium text-black transition-transform hover:scale-105 active:scale-95"
                    >
                        Start Analyzing <ChevronRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                        <div className="absolute inset-0 -z-10 rounded-full bg-white/50 blur-lg opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                    <button className="inline-flex h-12 items-center justify-center rounded-full border border-white/10 bg-white/5 px-8 font-medium text-white backdrop-blur-sm transition-colors hover:bg-white/10">
                        View Documentation
                    </button>
                </motion.div>
            </div>

            {/* Decorative Bottom Fade */}
            <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent z-10" />
        </div>
    );
}
