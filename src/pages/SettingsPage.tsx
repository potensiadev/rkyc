import { MainLayout } from "@/components/layout/MainLayout";
import { DemoPanel } from "@/components/demo/DemoPanel";
import { SchedulerPanel } from "@/components/demo/SchedulerPanel";
import { Badge } from "@/components/ui/badge";
import { Activity, Settings as SettingsIcon, Database } from "lucide-react";
import {
    DynamicBackground,
    GlassCard,
    StatusBadge
} from "@/components/premium";
import { motion } from "framer-motion";

export default function SettingsPage() {
    const enableScheduler = import.meta.env.VITE_ENABLE_SCHEDULER === 'true';
    const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';
    const apiUrl = import.meta.env.VITE_API_URL;

    return (
        <MainLayout>
            <DynamicBackground />
            <div className="max-w-4xl mx-auto space-y-8 pb-20 relative z-10 px-6">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-center gap-4 pt-6 mb-2"
                >
                    <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center border border-slate-200">
                        <SettingsIcon className="w-6 h-6 text-slate-700" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">System Settings</h1>
                        <p className="text-slate-500 font-medium mt-1">Configure system behavior and manage demo environments.</p>
                    </div>
                </motion.div>

                {/* System Features */}
                <section className="space-y-6">

                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 }}
                        className="flex items-center gap-2 mb-4"
                    >
                        <Activity className="w-5 h-5 text-indigo-500" />
                        <h2 className="text-lg font-bold text-slate-800">Feature Control</h2>
                    </motion.div>

                    <div className="grid gap-8">
                        {/* Scheduler Panel (Env Controlled) */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">Automated Scheduler</h3>
                                <StatusBadge variant={enableScheduler ? "success" : "neutral"}>
                                    {enableScheduler ? "Active" : "Disabled (Env)"}
                                </StatusBadge>
                            </div>

                            {enableScheduler ? (
                                <div className="bg-white/50 backdrop-blur-sm rounded-xl border border-slate-200 shadow-sm p-1">
                                    <SchedulerPanel />
                                </div>
                            ) : (
                                <GlassCard className="bg-slate-50/50 border-dashed border-slate-300 p-8 text-center flex flex-col items-center justify-center gap-2">
                                    <h4 className="text-slate-900 font-semibold">Scheduler Disabled</h4>
                                    <p className="text-slate-500 text-sm max-w-md">The scheduler feature is disabled by the environment variable (VITE_ENABLE_SCHEDULER). Please check your configuration.</p>
                                </GlassCard>
                            )}
                        </motion.div>

                        {/* Demo Mode Panel */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.3 }}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider">Demo Environment</h3>
                                <StatusBadge variant={demoMode ? "brand" : "neutral"}>
                                    {demoMode ? "Demo Mode Active" : "Production Mode"}
                                </StatusBadge>
                            </div>

                            {demoMode ? (
                                <div className="bg-gradient-to-br from-indigo-50/50 to-purple-50/50 backdrop-blur-sm rounded-xl border border-indigo-100 shadow-sm p-1">
                                    <DemoPanel />
                                </div>
                            ) : (
                                <GlassCard className="bg-slate-50/50 border-dashed border-slate-300 p-8 text-center flex flex-col items-center justify-center gap-2">
                                    <h4 className="text-slate-900 font-semibold">Production Mode</h4>
                                    <p className="text-slate-500 text-sm max-w-md">Demo controls are hidden in production mode.</p>
                                </GlassCard>
                            )}
                        </motion.div>
                    </div>
                </section>

                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="pt-10 border-t border-slate-200 mt-10"
                >
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                        <Database className="w-3 h-3" />
                        <span>API Endpoint: {apiUrl}</span>
                    </div>
                </motion.div>
            </div>
        </MainLayout>
    );
}
