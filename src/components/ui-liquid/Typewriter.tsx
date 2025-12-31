import { motion, useInView } from "framer-motion";
import { useRef } from "react";

interface TypewriterProps {
    text: string;
    speed?: number;
    className?: string;
    delay?: number;
}

export function Typewriter({ text, speed = 0.02, className, delay = 0 }: TypewriterProps) {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true });

    const characters = Array.from(text);

    return (
        <span ref={ref} className={className}>
            {characters.map((char, index) => (
                <motion.span
                    key={index}
                    initial={{ opacity: 0 }}
                    animate={isInView ? { opacity: 1 } : {}}
                    transition={{ duration: 0.1, delay: delay + index * speed }}
                >
                    {char}
                </motion.span>
            ))}
        </span>
    );
}
