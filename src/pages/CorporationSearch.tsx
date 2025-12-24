import { MainLayout } from "@/components/layout/MainLayout";
import { Search, Building2, MoreHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface Corporation {
  id: string;
  name: string;
  businessNumber: string;
  industry: string;
  riskLevel: "low" | "medium" | "high";
  lastReviewed: string;
  signalCount: number;
}

const mockCorporations: Corporation[] = [
  {
    id: "1",
    name: "삼성전자",
    businessNumber: "124-81-00998",
    industry: "전자/반도체",
    riskLevel: "medium",
    lastReviewed: "2024-12-20",
    signalCount: 5,
  },
  {
    id: "2",
    name: "현대자동차",
    businessNumber: "101-81-15555",
    industry: "자동차",
    riskLevel: "medium",
    lastReviewed: "2024-12-19",
    signalCount: 3,
  },
  {
    id: "3",
    name: "카카오",
    businessNumber: "120-81-47521",
    industry: "IT/플랫폼",
    riskLevel: "high",
    lastReviewed: "2024-12-18",
    signalCount: 8,
  },
  {
    id: "4",
    name: "LG에너지솔루션",
    businessNumber: "110-81-12345",
    industry: "2차전지",
    riskLevel: "low",
    lastReviewed: "2024-12-22",
    signalCount: 2,
  },
  {
    id: "5",
    name: "네이버",
    businessNumber: "220-81-62517",
    industry: "IT/플랫폼",
    riskLevel: "low",
    lastReviewed: "2024-12-21",
    signalCount: 1,
  },
];

const riskLevelConfig = {
  low: { label: "낮음", className: "bg-success/10 text-success" },
  medium: { label: "보통", className: "bg-warning/10 text-warning" },
  high: { label: "높음", className: "bg-destructive/10 text-destructive" },
};

export default function CorporationSearch() {
  return (
    <MainLayout>
      <div className="max-w-6xl">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">기업 검색</h1>
          <p className="text-muted-foreground mt-1">
            기업명 또는 사업자등록번호로 기업을 검색하고 상세 정보를 조회하세요.
          </p>
        </div>

        {/* Search bar */}
        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                type="text"
                placeholder="기업명 또는 사업자등록번호를 입력하세요"
                className="pl-12 h-12 text-base"
              />
            </div>
            <Button className="h-12 px-8">검색</Button>
          </div>
        </div>

        {/* Corporation list */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="font-medium text-foreground">모니터링 기업 목록</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              전체 {mockCorporations.length}개 기업
            </p>
          </div>

          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  기업명
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  사업자등록번호
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  업종
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  관심도
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  최근 검토일
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  시그널
                </th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody>
              {mockCorporations.map((corp) => (
                <tr
                  key={corp.id}
                  className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors cursor-pointer"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
                        <Building2 className="w-4 h-4 text-primary" />
                      </div>
                      <span className="font-medium text-foreground">{corp.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {corp.businessNumber}
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {corp.industry}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`status-badge ${riskLevelConfig[corp.riskLevel].className}`}>
                      {riskLevelConfig[corp.riskLevel].label}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {corp.lastReviewed}
                  </td>
                  <td className="px-6 py-4">
                    {corp.signalCount > 0 && (
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-signal-new/10 text-signal-new text-xs font-medium">
                        {corp.signalCount}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </MainLayout>
  );
}
