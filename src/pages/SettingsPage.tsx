import { MainLayout } from "@/components/layout/MainLayout";
import { DemoPanel } from "@/components/demo/DemoPanel";
import { SchedulerPanel } from "@/components/demo/SchedulerPanel";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Settings as SettingsIcon, Database } from "lucide-react";

export default function SettingsPage() {
    const enableScheduler = import.meta.env.VITE_ENABLE_SCHEDULER === 'true';
    const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';
    const apiUrl = import.meta.env.VITE_API_URL;

    return (
        <MainLayout>
            <div className="max-w-4xl space-y-8">
                {/* Header */}
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <SettingsIcon className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-semibold text-foreground">설정 (Settings)</h1>
                            <p className="text-muted-foreground text-sm">시스템 환경 설정 및 기능 제어</p>
                        </div>
                    </div>
                </div>

                {/* System Features */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2">
                        <Activity className="w-5 h-5 text-primary" />
                        <h2 className="text-lg font-semibold">시스템 기능 제어</h2>
                    </div>

                    <div className="grid gap-6">
                        {/* Scheduler Panel (Env Controlled) */}
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="text-sm font-medium text-muted-foreground">실시간 자동 탐지 (Scheduler)</h3>
                                <Badge variant={enableScheduler ? "default" : "secondary"}>
                                    {enableScheduler ? "Enabled" : "Disabled (Env)"}
                                </Badge>
                            </div>

                            {enableScheduler ? (
                                <SchedulerPanel />
                            ) : (
                                <Card className="bg-muted/30 border-dashed">
                                    <CardHeader>
                                        <CardTitle className="text-base text-muted-foreground">기능 비활성화됨</CardTitle>
                                        <CardDescription>
                                            Vercel 환경 변수 (VITE_ENABLE_SCHEDULER)가 false로 설정되어 있어 스케줄러 제어 패널을 사용할 수 없습니다.
                                        </CardDescription>
                                    </CardHeader>
                                </Card>
                            )}
                        </div>

                        {/* Demo Mode Panel */}
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="text-sm font-medium text-muted-foreground">데모 모드 (Demo Mode)</h3>
                                <Badge variant={demoMode ? "outline" : "secondary"} className={demoMode ? "text-blue-500 border-blue-200 bg-blue-50" : ""}>
                                    {demoMode ? "Demo Active" : "Production"}
                                </Badge>
                            </div>

                            {demoMode ? (
                                <DemoPanel />
                            ) : (
                                <Card className="bg-muted/30 border-dashed">
                                    <CardHeader>
                                        <CardTitle className="text-base text-muted-foreground">데모 모드 비활성화</CardTitle>
                                        <CardDescription>
                                            현재 프로덕션 모드로 동작 중입니다. 데모 제어 기능이 숨겨집니다.
                                        </CardDescription>
                                    </CardHeader>
                                </Card>
                            )}
                        </div>
                    </div>
                </section>

                {/* Environment Info */}
                <section className="space-y-4 pt-4 border-t">
                    <div className="flex items-center gap-2">
                        <Database className="w-5 h-5 text-muted-foreground" />
                        <h2 className="text-lg font-semibold">환경 변수 정보</h2>
                    </div>

                    <Card>
                        <CardContent className="pt-6">
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="p-3 bg-muted/50 rounded-lg">
                                        <span className="text-xs text-muted-foreground block mb-1">VITE_ENABLE_SCHEDULER</span>
                                        <code className="text-sm font-mono font-medium">{String(enableScheduler)}</code>
                                    </div>
                                    <div className="p-3 bg-muted/50 rounded-lg">
                                        <span className="text-xs text-muted-foreground block mb-1">VITE_DEMO_MODE</span>
                                        <code className="text-sm font-mono font-medium">{String(demoMode)}</code>
                                    </div>
                                    <div className="p-3 bg-muted/50 rounded-lg md:col-span-2">
                                        <span className="text-xs text-muted-foreground block mb-1">VITE_API_URL</span>
                                        <code className="text-sm font-mono text-muted-foreground break-all">{apiUrl || '(Not Set)'}</code>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </section>
            </div>
        </MainLayout>
    );
}
