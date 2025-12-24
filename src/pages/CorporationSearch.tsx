import { MainLayout } from "@/components/layout/MainLayout";
import { Search, Building2, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

interface Corporation {
  id: string;
  name: string;
  industry: string;
  recentSignalCount: number;
  recentSignalTypes: ("direct" | "industry" | "environment")[];
  lastReviewed: string;
}

const mockCorporations: Corporation[] = [
  {
    id: "1",
    name: "삼성전자",
    industry: "전자/반도체",
    recentSignalCount: 5,
    recentSignalTypes: ["direct", "industry"],
    lastReviewed: "2024-12-20",
  },
  {
    id: "2",
    name: "현대자동차",
    industry: "자동차",
    recentSignalCount: 3,
    recentSignalTypes: ["industry", "environment"],
    lastReviewed: "2024-12-19",
  },
  {
    id: "3",
    name: "카카오",
    industry: "IT/플랫폼",
    recentSignalCount: 8,
    recentSignalTypes: ["direct", "industry", "environment"],
    lastReviewed: "2024-12-18",
  },
  {
    id: "4",
    name: "LG에너지솔루션",
    industry: "2차전지",
    recentSignalCount: 2,
    recentSignalTypes: ["industry"],
    lastReviewed: "2024-12-22",
  },
  {
    id: "5",
    name: "네이버",
    industry: "IT/플랫폼",
    recentSignalCount: 1,
    recentSignalTypes: ["environment"],
    lastReviewed: "2024-12-21",
  },
];

const signalTypeConfig = {
  direct: { label: "직접", className: "bg-primary/10 text-primary" },
  industry: { label: "산업", className: "bg-accent text-accent-foreground" },
  environment: { label: "환경", className: "bg-muted text-muted-foreground" },
};

export default function CorporationSearch() {
  const navigate = useNavigate();

  const handleCorporationClick = (corporateId: string) => {
    navigate(`/corporates/${corporateId}`);
  };

  return (
    <MainLayout>
      <div className="max-w-6xl">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">기업 검색</h1>
          <p className="text-muted-foreground mt-1">
            기업명 또는 사업자등록번호로 기업을 검색하여,
            <br />
            해당 기업에 대해 AI가 감지한 시그널과 분석 맥락을 확인할 수 있습니다.
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

        {/* Corporation list - analysis oriented */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="font-medium text-foreground">분석 대상 기업 목록</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              시그널이 감지된 기업 {mockCorporations.length}개 (참고용)
            </p>
          </div>

          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  기업명
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  업종
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  최근 감지 시그널 수
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  최근 시그널 유형
                </th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  최근 검토일
                </th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody>
              {mockCorporations.map((corp) => (
                <tr
                  key={corp.id}
                  onClick={() => handleCorporationClick(corp.id)}
                  className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors cursor-pointer group"
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
                    {corp.industry}
                  </td>
                  <td className="px-6 py-4">
                    {corp.recentSignalCount > 0 && (
                      <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 rounded-full bg-signal-new/10 text-signal-new text-xs font-medium">
                        {corp.recentSignalCount}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5">
                      {corp.recentSignalTypes.map((type) => (
                        <span
                          key={type}
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${signalTypeConfig[type].className}`}
                        >
                          {signalTypeConfig[type].label}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {corp.lastReviewed}
                  </td>
                  <td className="px-6 py-4">
                    <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Reference note */}
        <p className="text-xs text-muted-foreground mt-4 text-center">
          본 목록은 시그널 감지 현황을 요약한 참고 자료이며, 기업 클릭 시 상세 분석 맥락을 확인할 수 있습니다.
        </p>
      </div>
    </MainLayout>
  );
}