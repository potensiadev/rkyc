
import React from 'react';
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetDescription,
} from "@/components/ui/sheet";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Download, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface DrillDownSheetProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    data: any;
    type?: 'table' | 'key-value' | 'custom';
    columns?: { key: string; label: string; format?: (val: any) => React.ReactNode }[];
}

export function DrillDownSheet({
    isOpen,
    onClose,
    title,
    subtitle,
    data,
    type = 'table',
    columns,
}: DrillDownSheetProps) {

    const renderContent = () => {
        if (!data) return <div className="p-4 text-center text-slate-500">No data available</div>;

        // Auto-detect type if not explicit
        const isTable = Array.isArray(data);
        const isKeyValue = !Array.isArray(data) && typeof data === 'object' && data !== null;

        if (isTable) {
            if (data.length === 0) return <div className="p-4 text-center text-slate-500">No records found</div>;

            // Auto-detect columns if not provided
            const cols = columns || Object.keys(data[0]).map(key => ({
                key,
                label: key.replace(/_/g, ' ').toUpperCase(),
                format: (val: any) => typeof val === 'object' ? JSON.stringify(val) : String(val)
            }));

            return (
                <div className="border rounded-md">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                {cols.map((col) => (
                                    <TableHead key={col.key} className="whitespace-nowrap bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider h-9">
                                        {col.label}
                                    </TableHead>
                                ))}
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {data.map((row, i) => (
                                <TableRow key={i}>
                                    {cols.map((col) => (
                                        <TableCell key={col.key} className="py-2.5 text-xs font-mono text-slate-600">
                                            {col.format ? col.format(row[col.key]) : row[col.key]}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            );
        }

        if (isKeyValue) {
            return (
                <div className="space-y-4">
                    {Object.entries(data).map(([key, value]) => (
                        <div key={key} className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0">
                            <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                                {key.replace(/_/g, ' ')}
                            </span>
                            <span className="text-sm font-bold text-slate-800 font-mono">
                                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                        </div>
                    ))}
                </div>
            );
        }

        return (
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 font-mono text-xs whitespace-pre-wrap">
                {JSON.stringify(data, null, 2)}
            </div>
        );
    };

    return (
        <Sheet open={isOpen} onOpenChange={onClose}>
            <SheetContent className="w-[400px] sm:w-[540px] flex flex-col h-full p-0 gap-0">
                <SheetHeader className="p-6 border-b border-slate-100 bg-white z-10">
                    <SheetTitle className="text-lg font-bold text-slate-900">{title}</SheetTitle>
                    {subtitle && <SheetDescription className="text-xs text-slate-500">{subtitle}</SheetDescription>}
                </SheetHeader>

                <ScrollArea className="flex-1 bg-white p-6">
                    {renderContent()}
                </ScrollArea>

                <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={onClose} className="text-xs">
                        닫기 (Close)
                    </Button>
                    <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-xs gap-1.5 font-bold">
                        <Download className="w-3.5 h-3.5" />
                        Excel 다운로드
                    </Button>
                </div>
            </SheetContent>
        </Sheet>
    );
}
