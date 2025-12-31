import { motion, useMotionTemplate, useMotionValue } from "framer-motion";
import { InputHTMLAttributes, useState } from "react";
import { cn } from "@/lib/utils";

interface GlowInputProps extends InputHTMLAttributes<HTMLInputElement> {
    icon?: React.ElementType;
}

export function GlowInput({ className, icon: Icon, ...props }: GlowInputProps) {
    const [isFocused, setIsFocused] = useState(false);
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);

    function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
        const { left, top } = currentTarget.getBoundingClientRect();
        mouseX.set(clientX - left);
        mouseY.set(clientY - top);
    }

    return (
        <div
            className="relative group rounded-xl p-[1px]"
            onMouseMove={handleMouseMove}
        >
            {/* Glow Layer */}
            <motion.div
                className="pointer-events-none absolute -inset-px rounded-xl opacity-0 transition duration-300 group-hover:opacity-100"
                style={{
                    background: useMotionTemplate`
            radial-gradient(
              650px circle at ${mouseX}px ${mouseY}px,
              rgba(124, 58, 237, 0.4),
              transparent 40%
            )
          `,
                }}
            />

            {/* Focus Border */}
            <div
                className={cn(
                    "absolute inset-0 rounded-xl transition-all duration-300",
                    isFocused ? "bg-primary/50 blur-sm" : "opacity-0"
                )}
            />

            <div className="relative flex items-center bg-zinc-950 rounded-xl border border-white/10 overflow-hidden">
                {Icon && (
                    <div className="pl-4 text-zinc-500">
                        <Icon className="w-5 h-5" />
                    </div>
                )}
                <input
                    className={cn(
                        "w-full bg-transparent px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none",
                        className
                    )}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    {...props}
                />
            </div>
        </div>
    );
}
