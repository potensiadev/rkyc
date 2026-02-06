import React from "react";

interface SparklineProps {
    data: number[];
    color?: string;
    height?: number;
}

export const Sparkline = ({ data, color = "#6366f1", height = 30 }: SparklineProps) => {
    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;
    const points = data.map((d, i) => {
        const x = (i / (data.length - 1)) * 100;
        const y = 100 - ((d - min) / range) * 100;
        return `${x},${y}`;
    }).join(" ");

    return (
        <svg viewBox="0 0 100 100" width="100%" height={height} preserveAspectRatio="none" className="overflow-visible">
            <polyline
                fill="none"
                stroke={color}
                strokeWidth="3"
                points={points}
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <circle cx="100" cy={100 - ((data[data.length - 1] - min) / range) * 100} r="4" fill={color} />
        </svg>
    );
};
