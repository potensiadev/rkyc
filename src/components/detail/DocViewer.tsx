import { useRef, useState } from "react";
import { motion, useMotionTemplate, useMotionValue } from "framer-motion";
import { Lock, Eye, AlertCircle } from "lucide-react";
import { toast } from "sonner"; // Assuming sonner is installed as per App.tsx

interface DocViewerProps {
    documentText?: string;
    sensitiveData?: {
        phone: string;
        email: string;
        rrn: string; // Citizen ID or similar
    };
}

export function DocViewer({ documentText, sensitiveData }: DocViewerProps) {
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);

    function handleMouseMove(event: React.MouseEvent<HTMLDivElement>) {
        const { left, top } = event.currentTarget.getBoundingClientRect();
        mouseX.set(event.clientX - left);
        mouseY.set(event.clientY - top);
    }

    const handleCopy = (e: React.ClipboardEvent) => {
        e.preventDefault();
        toast.error("Copy Detected", {
            description: "Sensitive document content cannot be copied.",
        });
        // Trigger red flash or similar feedback here if possible, 
        // for now toast is good.
    };

    return (
        <div className="h-full flex flex-col bg-zinc-950 rounded-2xl overflow-hidden border border-zinc-800 relative">
            {/* Header */}
            <div className="h-12 bg-zinc-900 border-b border-zinc-800 flex items-center px-4 justify-between">
                <span className="text-zinc-400 text-xs font-mono flex items-center gap-2">
                    <Lock className="w-3 h-3" /> SECURE DOCUMENT VIEWER
                </span>
                <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                    <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
                </div>
            </div>

            {/* Content Area - The "Privacy Shield" */}
            <div
                className="flex-1 overflow-auto p-8 relative font-mono text-zinc-300 text-sm leading-relaxed"
                onMouseMove={handleMouseMove}
                onCopy={handleCopy}
            >
                {/* Holographic Grid Background */}
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none" />

                {/* Document Content Simulation */}
                <div className="max-w-2xl mx-auto space-y-6">
                    <div className="border-b border-zinc-700 pb-4 mb-8">
                        <h1 className="text-2xl font-bold text-zinc-100">CONFIDENTIAL REPORT</h1>
                        <p className="text-xs text-zinc-500 mt-1">ID: REF-2024-X99 • CLASS: RESTRICTED</p>
                    </div>

                    {/* Sensitive Section 1 */}
                    <PrivacyBlock
                        label="CONTACT INFO"
                        mouseX={mouseX}
                        mouseY={mouseY}
                    >
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <span className="text-zinc-500 text-xs block mb-1">PHONE</span>
                                <span className="font-bold">{sensitiveData?.phone || "010-XXXX-XXXX"}</span>
                            </div>
                            <div>
                                <span className="text-zinc-500 text-xs block mb-1">EMAIL</span>
                                <span className="font-bold">{sensitiveData?.email || "user@example.com"}</span>
                            </div>
                        </div>
                    </PrivacyBlock>

                    <p>
                        {documentText || `
               Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
               Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
             `}
                    </p>

                    <p className="opacity-80">
                        Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
                        Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
                    </p>

                    {/* Sensitive Section 2 */}
                    <PrivacyBlock
                        label="IDENTIFICATION"
                        mouseX={mouseX}
                        mouseY={mouseY}
                    >
                        <div>
                            <span className="text-zinc-500 text-xs block mb-1">RESIDENT REG. NO</span>
                            <span className="font-bold tracking-wider">{sensitiveData?.rrn || "900101-1******"}</span>
                        </div>
                    </PrivacyBlock>

                    <div className="h-32" /> {/* Spacer */}
                </div>
            </div>

            {/* Footer warning */}
            <div className="absolute bottom-4 left-0 right-0 text-center pointer-events-none">
                <span className="bg-red-950/80 text-red-400 text-[10px] px-2 py-1 rounded border border-red-900/50">
                    DO NOT DISTRIBUTE
                </span>
            </div>
        </div>
    );
}

function PrivacyBlock({ children, label, mouseX, mouseY }: any) {
    // Logic: The overlay is blurred by default.
    // The maskImage reveals the content underneath based on mouse position.

    return (
        <div className="relative group my-6 border border-zinc-800 rounded-lg p-4 bg-zinc-900/30">
            <div className="absolute -top-3 left-3 bg-zinc-950 px-2 text-xs text-zinc-500 border border-zinc-800 rounded">
                {label}
            </div>

            {/* The clean content (hidden by default, revealed by mask) */}
            <div className="relative z-0">
                {children}
            </div>

            {/* The Blur Layer (Overlay) */}
            {/* We use a motion div that tracks mouse to "erase" the blur */}
            <motion.div
                className="absolute inset-0 backdrop-blur-md bg-zinc-950/50 z-10 rounded-lg flex items-center justify-center cursor-crosshair"
                style={{
                    maskImage: useMotionTemplate`radial-gradient(circle at ${mouseX}px ${mouseY}px, transparent 0px, black 150px)`
                    // Initial logical flaw fix: standard CSS masking:
                    // black = visible, transparent = hidden.
                    // We want the BLUR layer to be HOLED out where the mouse is.
                    // So at mouse position -> Transparent (hole in blur)
                    // Outside -> Black (blur visible)
                }}
            >
                <div className="text-zinc-600 flex items-center gap-2 select-none group-hover:opacity-0 transition-opacity duration-300">
                    <Eye className="w-4 h-4" /> Hover to Reveal
                </div>
            </motion.div>
        </div>
    )
}
