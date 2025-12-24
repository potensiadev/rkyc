import { MainLayout } from "@/components/layout/MainLayout";
import { Search, Building2, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { getAllCorporations } from "@/data/corporations";
import { getCorporationSignalCounts } from "@/data/signals";

const signalTypeConfig = {
  direct: { label: "직접", className: "bg-primary/10 text-primary" },
  industry: { label: "산업", className: "bg-accent text-accent-foreground" },
  environment: { label: "환경", className: "bg-muted text-muted-foreground" },
};

export default function CorporationSearch() {
  const navigate = useNavigate();
  const corporations = getAllCorporations();

  // Click company -> go directly to report
  const handleCorporationClick = (corporateId: string) => {
    navigate(`/corporates/${corporateId}`);
  };

  return (
    <MainLayout>
      <div className="max-w-6xl">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">기업 검색</h1>
          <p className="text-muted-foreground mt-1">
            기업명 또는 사업자등록번호로 기업을 검색하여 보고서를 확인할 수 있습니다.
          </p>
        </div>

        <div className="bg-card rounded-lg border border-border p-6 mb-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input type="text" placeholder="기업명 또는 사업자등록번호를 입력하세요" className="pl-12 h-12 text-base" />
            </div>
            <Button className="h-12 px-8">검색</Button>
          </div>
        </div>

        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="font-medium text-foreground">분석 대상 기업 목록</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              시그널이 감지된 기업 {corporations.length}개
            </p>
          </div>

          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">기업명</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">업종</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">최근 시그널</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">시그널 유형</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">여신 잔액</th>
                <th className="w-12"></th>
              </tr>
            </thead>
            <tbody>
              {corporations.map((corp) => {
                const signalCounts = getCorporationSignalCounts(corp.id);
                return (
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
                        <span className="font-medium text-foreground group-hover:text-primary">{corp.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">{corp.industry}</td>
                    <td className="px-6 py-4">
                      {signalCounts.total > 0 && (
                        <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 rounded-full bg-signal-new/10 text-signal-new text-xs font-medium">
                          {signalCounts.total}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        {corp.recentSignalTypes.map((type) => (
                          <span key={type} className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${signalTypeConfig[type].className}`}>
                            {signalTypeConfig[type].label}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">
                      {corp.bankRelationship.loanBalance || "-"}
                    </td>
                    <td className="px-6 py-4">
                      <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-muted-foreground mt-4 text-center">
          기업 클릭 시 해당 기업의 시그널 분석 보고서를 확인할 수 있습니다.
        </p>
      </div>
    </MainLayout>
  );
}
