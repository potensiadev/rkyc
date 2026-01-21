import React from "react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { Shield, Zap, Globe, Activity, LineChart, Lock } from "lucide-react"; // Note: Lucide icons generic import

export function BentoGrid() {
    const features = [
        {
            title: "Real-time Detection",
            description: "Analyze thousands of news sources per second.",
            header: <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-primary/20 to-violet-500/20 items-center justify-center group-hover:scale-105 transition-transform"><Zap className="w-10 h-10 text-primary" /></div>,
            className: "md:col-span-2",
            icon: <Zap className="h-4 w-4 text-neutral-500" />,
        },
        {
            title: "Global Coverage",
            description: "Monitoring markets across 50+ countries.",
            header: <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 items-center justify-center group-hover:scale-105 transition-transform"><Activity className="w-10 h-10 text-emerald-500" /></div>,
            className: "md:col-span-1",
            icon: <Activity className="h-4 w-4 text-neutral-500" />,
        },
        {
            title: "Institutional Security",
            description: "Bank-grade encryption and data protection.",
            header: <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 items-center justify-center group-hover:scale-105 transition-transform"><Shield className="w-10 h-10 text-orange-500" /></div>,
            className: "md:col-span-1",
            icon: <Shield className="h-4 w-4 text-neutral-500" />,
        },
        {
            title: "Deep Analytics",
            description: "Turn noise into actionable signals with AI.",
            header: <div className="flex flex-1 w-full h-full min-h-[6rem] rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 items-center justify-center group-hover:scale-105 transition-transform"><LineChart className="w-10 h-10 text-blue-500" /></div>,
            className: "md:col-span-2",
            icon: <LineChart className="h-4 w-4 text-neutral-500" />,
        },
    ];

    return (
        <div className="py-20 bg-background relative z-10">
            <div className="max-w-7xl mx-auto px-4 md:px-8">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="mb-12 text-center"
                >
                    <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl mb-4">Under the Hood</h2>
                    <p className="text-muted-foreground text-lg">Built for the most demanding financial environments.</p>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
                    {features.map((item, i) => (
                        <BentoGridItem
                            key={i}
                            title={item.title}
                            description={item.description}
                            header={item.header}
                            className={item.className}
                            icon={item.icon}
                            index={i}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}

const BentoGridItem = ({
    className,
    title,
    description,
    header,
    icon,
    index,
}: {
    className?: string;
    title?: string | React.ReactNode;
    description?: string | React.ReactNode;
    header?: React.ReactNode;
    icon?: React.ReactNode;
    index: number;
}) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className={cn(
                "row-span-1 rounded-xl group/bento hover:shadow-xl transition duration-200 shadow-input dark:shadow-none p-4 dark:bg-black dark:border-white/[0.2] bg-white border border-transparent justify-between flex flex-col space-y-4",
                "border border-white/10 bg-white/5 backdrop-blur-sm", // Custom glass overrides
                className
            )}
        >
            {header}
            <div className="group-hover/bento:translate-x-2 transition duration-200">
                {icon}
                <div className="font-sans font-bold text-neutral-600 dark:text-neutral-200 mb-2 mt-2">
                    {title}
                </div>
                <div className="font-sans font-normal text-neutral-600 text-xs dark:text-neutral-300">
                    {description}
                </div>
            </div>
        </motion.div>
    );
};
