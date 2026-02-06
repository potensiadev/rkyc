import React from "react";

interface StatusBadgeProps {
    children: React.ReactNode;
    variant?: "success" | "warning" | "danger" | "neutral" | "brand";
    className?: string;
}

export const StatusBadge = ({ children, variant = "neutral", className = "" }: StatusBadgeProps) => {
    const styles = {
        success: { dot: "bg-emerald-500", text: "text-slate-700", bg: "bg-emerald-50/50" },
        warning: { dot: "bg-amber-500", text: "text-slate-700", bg: "bg-amber-50/50" },
        danger: { dot: "bg-rose-500", text: "text-slate-700", bg: "bg-rose-50/50" },
        neutral: { dot: "bg-slate-400", text: "text-slate-600", bg: "bg-slate-100/50" },
        brand: { dot: "bg-indigo-500", text: "text-slate-700", bg: "bg-indigo-50/50" },
    };
    const style = styles[variant] || styles.neutral;
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium ${style.bg} ${style.text} ${className}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse`} />
            {children}
        </span>
    );
};
