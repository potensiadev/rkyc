import { Card } from "@/components/ui/card";
import { Check, AlertTriangle, Tag, Calendar } from "lucide-react";

interface AnalysisReportProps {
    score: number;
    corporationName: string;
    summary: string;
    history?: any[];
}

export function AnalysisReport({ score, corporationName, summary, history }: AnalysisReportProps) {
    return (
        <div className="h-full overflow-y-auto pr-2 custom-scrollbar p-6">
            {/* Header Profile */}
            <div className="bg-muted/30 rounded-xl border border-border p-6 mb-6">
                <div className="flex items-start justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <h1 className="text-2xl font-bold text-foreground">
                                {corporationName}
                            </h1>
                            <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-bold">
                                Active
                            </span>
                        </div>
                        <p className="text-muted-foreground text-sm max-w-sm leading-relaxed">
                            {summary}
                        </p>
                    </div>

                    {/* Donut Chart (Static) */}
                    <div className="relative w-24 h-24 flex items-center justify-center">
                        <svg className="w-full h-full -rotate-90">
                            <circle
                                cx="48"
                                cy="48"
                                r="40"
                                stroke="currentColor"
                                strokeWidth="8"
                                fill="transparent"
                                className="text-muted"
                            />
                            <circle
                                cx="48"
                                cy="48"
                                r="40"
                                stroke="currentColor"
                                strokeWidth="8"
                                fill="transparent"
                                className="text-primary"
                                strokeDasharray="251.2"
                                strokeDashoffset={251.2 - (251.2 * score) / 100}
                                strokeLinecap="round"
                            />
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-xl font-bold text-foreground">{score}</span>
                            <span className="text-[10px] text-muted-foreground font-bold">SCORE</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Cross Check Grid */}
            <h3 className="text-sm font-bold text-muted-foreground mb-4 uppercase tracking-wider">검증 항목 (Verification)</h3>
            <div className="grid grid-cols-2 gap-4 mb-8">
                <VerificationCard label="기업 상태" isValid={true} value="정상" />
                <VerificationCard label="세금 납부" isValid={true} value="완납" />
                <VerificationCard label="신용 등급" isValid={false} value="검토 필요" />
                <VerificationCard label="주소지 확인" isValid={true} value="일치" />
            </div>

            {/* Timeline */}
            <h3 className="text-sm font-bold text-muted-foreground mb-4 uppercase tracking-wider">히스토리 타임라인</h3>
            <div className="space-y-6 pl-4 border-l border-border ml-2">
                {[2024, 2023, 2022].map((year, i) => (
                    <div key={year} className="relative group">
                        <div className="absolute -left-[21px] top-1 w-3 h-3 rounded-full bg-background border-2 border-muted-foreground group-hover:border-primary transition-colors" />
                        <div className="bg-card border border-border p-4 rounded-lg hover:bg-muted/50 transition-colors">
                            <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-bold text-foreground">{year} 주요 이벤트</span>
                                <span className="text-xs text-green-600 font-mono">Verified</span>
                            </div>
                            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                                {year}년도 회계연도 주요 기업 공시 및 뉴스 검토 완료. 특이 위험 시그널 감지되지 않음.
                            </p>

                            {/* Tags/Satellites */}
                            <div className="flex gap-2 mt-3">
                                <span className="text-[10px] px-2 py-1 bg-muted text-muted-foreground rounded border border-border flex items-center gap-1">
                                    <Tag className="w-3 h-3" /> 감사
                                </span>
                                <span className="text-[10px] px-2 py-1 bg-muted text-muted-foreground rounded border border-border flex items-center gap-1">
                                    <Calendar className="w-3 h-3" /> 4분기
                                </span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function VerificationCard({ label, isValid, value }: { label: string, isValid: boolean, value: string }) {
    return (
        <div className="bg-card border border-border rounded-lg p-4 flex items-center justify-between hover:border-primary/50 transition-colors">
            <div>
                <p className="text-xs text-muted-foreground mb-1">{label}</p>
                <p className="font-bold text-sm text-foreground">{value}</p>
            </div>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isValid ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'}`}>
                {isValid ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            </div>
        </div>
    );
}
