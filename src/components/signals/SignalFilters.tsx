import { Filter, ChevronDown, Info, Building2, Factory, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SignalCategory, SignalStatus, SIGNAL_TYPE_CONFIG } from "@/types/signal";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FilterOption {
  id: string;
  label: string;
  count?: number;
  active?: boolean;
}

interface SignalFiltersProps {
  activeStatus: SignalStatus | "all";
  activeCategory: SignalCategory | "all";
  onStatusChange?: (status: SignalStatus | "all") => void;
  onCategoryChange?: (category: SignalCategory | "all") => void;
  counts: {
    all: number;
    new: number;
    review: number;
    resolved: number;
    direct: number;
    industry: number;
    environment: number;
  };
}

const categoryIcons = {
  direct: Building2,
  industry: Factory,
  environment: Globe,
};

export function SignalFilters({ 
  activeStatus = "all", 
  activeCategory = "all",
  onStatusChange,
  onCategoryChange,
  counts 
}: SignalFiltersProps) {
  const statusFilters: FilterOption[] = [
    { id: "all", label: "전체", count: counts.all, active: activeStatus === "all" },
    { id: "new", label: "신규", count: counts.new, active: activeStatus === "new" },
    { id: "review", label: "검토중", count: counts.review, active: activeStatus === "review" },
    { id: "resolved", label: "완료", count: counts.resolved, active: activeStatus === "resolved" },
  ];

  const categoryFilters = [
    { id: "all" as const, label: "전체 유형", count: counts.all },
    { id: "direct" as const, label: "직접 시그널", count: counts.direct },
    { id: "industry" as const, label: "산업 시그널", count: counts.industry },
    { id: "environment" as const, label: "환경 시그널", count: counts.environment },
  ];

  return (
    <div className="space-y-4 mb-6">
      {/* Signal type explanation */}
      <div className="bg-card rounded-lg border border-border p-4">
        <div className="flex items-center gap-2 mb-3">
          <Info className="w-4 h-4 text-muted-foreground" />
          <h3 className="text-sm font-medium text-foreground">시그널 유형 안내</h3>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {(Object.keys(SIGNAL_TYPE_CONFIG) as SignalCategory[]).map((category) => {
            const config = SIGNAL_TYPE_CONFIG[category];
            const Icon = categoryIcons[category];
            return (
              <Tooltip key={category}>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onCategoryChange?.(category)}
                    className={`
                      flex items-start gap-3 p-3 rounded-lg border transition-all text-left
                      ${activeCategory === category 
                        ? `${config.bgClass} ${config.borderClass} border-2` 
                        : "border-border hover:border-muted-foreground/30"
                      }
                    `}
                  >
                    <div className={`w-9 h-9 rounded-lg ${config.bgClass} flex items-center justify-center shrink-0`}>
                      <Icon className={`w-4 h-4 ${config.colorClass}`} />
                    </div>
                    <div className="min-w-0">
                      <p className={`text-sm font-medium ${config.colorClass}`}>{config.label}</p>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                        {config.description}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {counts[category]}건
                      </p>
                    </div>
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-sm">
                  <p className="font-medium mb-2">{config.label} 분석 방식</p>
                  <p className="text-xs text-muted-foreground mb-2">{config.analysisLogic}</p>
                  <p className="text-xs font-medium mb-1">주요 출처:</p>
                  <ul className="text-xs text-muted-foreground space-y-0.5">
                    {config.evidenceSources.slice(0, 3).map((source, i) => (
                      <li key={i}>• {source}</li>
                    ))}
                  </ul>
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      </div>

      {/* Status and sort filters */}
      <div className="flex items-center justify-between gap-4">
        {/* Status tabs */}
        <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
          {statusFilters.map((filter) => (
            <button
              key={filter.id}
              onClick={() => onStatusChange?.(filter.id as SignalStatus | "all")}
              className={`
                px-4 py-2 rounded-md text-sm font-medium transition-colors
                ${filter.active
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
                }
              `}
            >
              {filter.label}
              {filter.count !== undefined && (
                <span className={`ml-2 ${filter.active ? "text-primary" : "text-muted-foreground"}`}>
                  {filter.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Category dropdown and sort */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <Filter className="w-4 h-4" />
            상세 필터
            <ChevronDown className="w-3 h-3" />
          </Button>

          <div className="w-px h-6 bg-border" />

          <select 
            className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            value={activeCategory}
            onChange={(e) => onCategoryChange?.(e.target.value as SignalCategory | "all")}
          >
            {categoryFilters.map((filter) => (
              <option key={filter.id} value={filter.id}>
                {filter.label} ({filter.count})
              </option>
            ))}
          </select>

          <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
            <option value="recent">최신순</option>
            <option value="corporation">기업명순</option>
          </select>
        </div>
      </div>
    </div>
  );
}
