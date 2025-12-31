import { motion } from "framer-motion";
import { ReactNode } from "react";

interface GravityGridProps {
    children: ReactNode;
    className?: string; // Allow passing class names for grid columns config
}

export function GravityGrid({ children, className }: GravityGridProps) {
    return (
        <motion.div
            className={className || "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"}
            initial="hidden"
            animate="visible"
            variants={{
                hidden: { opacity: 0 },
                visible: {
                    opacity: 1,
                    transition: {
                        staggerChildren: 0.1
                    }
                }
            }}
        >
            {children}
        </motion.div>
    );
}
