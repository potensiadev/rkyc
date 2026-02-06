import React from "react";

interface TagProps {
    children: React.ReactNode;
    className?: string;
    onClick?: () => void;
}

export const Tag = ({ children, className = "", onClick }: TagProps) => (
    <span
        onClick={onClick}
        className={`
            inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-medium text-slate-600 
            bg-slate-50 border border-slate-100 hover:bg-white hover:border-indigo-100 hover:text-indigo-600 hover:shadow-sm transition-all cursor-default
            ${className}
        `}
    >
        {children}
    </span>
);
