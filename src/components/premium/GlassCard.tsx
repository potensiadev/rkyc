import React from "react";

interface GlassCardProps {
    children: React.ReactNode;
    className?: string;
    id?: string;
    onClick?: () => void;
}

export const GlassCard = ({ children, className = "", id = "", onClick }: GlassCardProps) => (
    <div
        id={id}
        onClick={onClick}
        className={`
            relative rounded-3xl bg-white/70 backdrop-blur-xl border border-white/50 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] 
            transition-all duration-300 hover:shadow-[0_8px_30px_-8px_rgba(0,0,0,0.08)] hover:bg-white/90
            ${className}
        `}
    >
        {children}
    </div>
);
