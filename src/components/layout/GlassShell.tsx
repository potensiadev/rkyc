import { ReactNode, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
    Inbox,
    Building2,
    Settings,
    Bell,
    BarChart3,
    Factory,
    Globe,
    Newspaper,
    Menu,
    X,
    ChevronRight
} from "lucide-react";
import { cn } from "@/lib/utils";
import { TopBar } from "./TopBar";

interface GlassShellProps {
    children: ReactNode;
}

const navItems = [
    { id: "briefing", label: "브리핑", icon: Newspaper, path: "/briefing" },
    { id: "signals", label: "시그널", icon: Inbox, path: "/", badge: 12 },
    { id: "corporations", label: "데이터베이스", icon: Building2, path: "/corporations" },
    { id: "analytics", label: "분석", icon: BarChart3, path: "/analytics" },
];

const bottomItems: typeof navItems = [
    // 알림, 설정 페이지는 미노출 처리
];

export function GlassShell({ children }: GlassShellProps) {
    const [isHovered, setIsHovered] = useState(false);
    const location = useLocation();

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-foreground font-sans selection:bg-primary/30 relative overflow-hidden">
            {/* 1. Global Ambient Background */}
            <div className="fixed inset-0 z-0 pointer-events-none">
                <motion.div
                    animate={{
                        x: [0, 100, 0],
                        y: [0, 50, 0],
                        opacity: [0.3, 0.5, 0.3],
                    }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                    className="absolute top-0 left-0 w-[800px] h-[800px] bg-purple-500/10 rounded-full blur-[120px]"
                />
                <motion.div
                    animate={{
                        x: [0, -100, 0],
                        y: [0, -50, 0],
                        opacity: [0.2, 0.4, 0.2],
                    }}
                    transition={{ duration: 25, repeat: Infinity, ease: "linear", delay: 2 }}
                    className="absolute bottom-0 right-0 w-[600px] h-[600px] bg-blue-500/10 rounded-full blur-[120px]"
                />
            </div>

            {/* 2. Glass Rail (Sidebar) */}
            <motion.aside
                initial={false}
                animate={{ width: isHovered ? 240 : 80 }}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
                className={cn(
                    "fixed left-4 top-4 bottom-4 z-50",
                    "bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl",
                    "flex flex-col py-6 overflow-hidden shadow-2xl transition-all duration-500"
                )}
            >
                {/* Logo Area */}
                <Link to="/" className="flex items-center justify-center h-12 mb-8 relative hover:opacity-80 transition-opacity">
                    <AnimatePresence>
                        {!isHovered && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.5 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.5 }}
                                className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shrink-0"
                            >
                                <span className="font-bold text-white">R</span>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <AnimatePresence>
                        {isHovered && (
                            <motion.div
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                className="absolute left-5 whitespace-nowrap"
                            >
                                <span className="font-bold text-lg tracking-tight text-white">rKYC</span>
                                <span className="text-[10px] text-zinc-400 block -mt-1">Know Your Customer</span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </Link>

                {/* Navigation Items */}
                <nav className="flex-1 flex flex-col gap-2 px-3">
                    {navItems.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <RailItem
                                key={item.id}
                                item={item}
                                isActive={isActive}
                                isExpanded={isHovered}
                            />
                        );
                    })}
                </nav>

                {/* Bottom Actions */}
                <div className="mt-auto flex flex-col gap-2 px-3 pt-6 border-t border-white/10">
                    {bottomItems.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <RailItem
                                key={item.id}
                                item={item}
                                isActive={isActive}
                                isExpanded={isHovered}
                            />
                        );
                    })}
                </div>
            </motion.aside>

            {/* 3. Main Content Area */}
            <motion.div
                className={cn(
                    "relative z-10 min-h-screen",
                    "pr-6 py-6"
                )}
                animate={{
                    paddingLeft: isHovered ? "260px" : "100px"
                }}
                transition={{ duration: 0.5, ease: "easeInOut" }} // Match sidebar animation duration
            >
                {/* Top Bar (now integrated seamlessly) */}
                <div className="mb-6 flex items-center justify-between">
                    {/* Breadcrumbs or Title could go here */}
                    <div />
                    <div className="flex items-center gap-4">
                        <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
                            <Bell className="w-4 h-4" />
                        </div>
                        <div className="flex items-center gap-2 pr-4">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-zinc-700 to-zinc-600 border border-white/10" />
                            <span className="text-sm font-medium text-zinc-300">Admin User</span>
                        </div>
                    </div>
                </div>

                {/* Page Content */}
                <motion.main
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    {children}
                </motion.main>
            </motion.div>
        </div >
    );
}

function RailItem({ item, isActive, isExpanded }: any) {
    return (
        <Link to={item.path} className="relative group">
            <div
                className={cn(
                    "flex items-center h-12 rounded-2xl transition-all duration-300",
                    isActive
                        ? "bg-primary text-white shadow-[0_0_20px_rgba(124,58,237,0.4)]"
                        : "text-zinc-400 hover:text-white hover:bg-white/10"
                )}
            >
                {/* Icon Container */}
                <div className="w-[54px] h-12 flex items-center justify-center shrink-0">
                    <item.icon className={cn("w-5 h-5", isActive && "animate-pulse")} />
                </div>

                {/* Label */}
                <AnimatePresence>
                    {isExpanded && (
                        <motion.div
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: "auto" }}
                            exit={{ opacity: 0, width: 0 }}
                            className="whitespace-nowrap overflow-hidden"
                        >
                            <span className="font-medium text-sm pr-4">{item.label}</span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Floating tooltip if collapsed (optional / hidden for simplicity in this version) */}
            </div>
        </Link>
    );
}
