import { Filter, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FilterOption {
  id: string;
  label: string;
  count?: number;
  active?: boolean;
}

const statusFilters: FilterOption[] = [
  { id: "all", label: "전체", count: 45, active: true },
  { id: "new", label: "신규", count: 12 },
  { id: "review", label: "검토중", count: 18 },
  { id: "resolved", label: "완료", count: 15 },
];

const typeFilters: FilterOption[] = [
  { id: "all", label: "전체 유형" },
  { id: "news", label: "언론 보도" },
  { id: "financial", label: "재무 변동" },
  { id: "regulatory", label: "규제/법률" },
  { id: "industry", label: "산업 동향" },
];

export function SignalFilters() {
  return (
    <div className="flex items-center justify-between gap-4 mb-6">
      {/* Status tabs */}
      <div className="flex items-center gap-1 bg-secondary rounded-lg p-1">
        {statusFilters.map((filter) => (
          <button
            key={filter.id}
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

      {/* Type and additional filters */}
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" className="gap-2">
          <Filter className="w-4 h-4" />
          필터
          <ChevronDown className="w-3 h-3" />
        </Button>

        <div className="w-px h-6 bg-border" />

        <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
          {typeFilters.map((filter) => (
            <option key={filter.id} value={filter.id}>
              {filter.label}
            </option>
          ))}
        </select>

        <select className="text-sm border border-input rounded-md px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-ring">
          <option value="recent">최신순</option>
          <option value="corporation">기업명순</option>
          <option value="priority">중요도순</option>
        </select>
      </div>
    </div>
  );
}
