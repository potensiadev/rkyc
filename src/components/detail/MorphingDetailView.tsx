import { ReactNode } from "react";
import { motion } from "framer-motion";
import { Download, Share2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface MorphingDetailViewProps {
    children: ReactNode; // Expects 2 children usually: Left and Right panes
    onBack: () => void;
}

export function MorphingDetailView({ children, onBack }: MorphingDetailViewProps) {
    return (
        <div className="min-h-screen bg-zinc-950 text-foreground flex flex-col relative overflow-hidden">
            {/* Background Ambient Layers */}
            <div className="absolute top-[-20%] right-[-10%] w-[500px] h-[500px] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />
            <div className="absolute bottom-[-20%] left-[-10%] w-[400px] h-[400px] bg-blue-500/10 blur-[100px] rounded-full pointer-events-none" />

            <div className="flex-1 p-6 h-screen max-h-screen grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
                {children}
            </div>


        </div>
    );
}

function DockButton({ icon: Icon, label, highlight }: { icon: any, label: string, highlight?: boolean }) {
    return (
        <motion.button
            whileHover={{ scale: 1.2, y: -5 }}
            whileTap={{ scale: 0.9 }}
            className={`
         relative w-12 h-12 rounded-xl flex items-center justify-center transition-colors
         ${highlight ? 'bg-primary/20 text-primary hover:bg-primary/30' : 'hover:bg-muted text-muted-foreground hover:text-foreground'}
       `}
            title={label}
        >
            <Icon className="w-5 h-5" />
        </motion.button>
    )
}
