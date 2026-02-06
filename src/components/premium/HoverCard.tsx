import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface HoverCardProps {
    trigger: React.ReactNode;
    content: React.ReactNode;
}

export const HoverCard = ({ trigger, content }: HoverCardProps) => {
    const [isOpen, setIsOpen] = useState(false);
    return (
        <div
            className="relative flex items-center group/card"
            onMouseEnter={() => setIsOpen(true)}
            onMouseLeave={() => setIsOpen(false)}
        >
            {trigger}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                        className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-64 bg-white/95 backdrop-blur-xl rounded-xl shadow-xl border border-slate-200/60 p-4"
                    >
                        {content}
                        <div className="absolute bottom-[-6px] left-1/2 -translate-x-1/2 w-3 h-3 bg-white rotate-45 border-r border-b border-slate-200/60" />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};
