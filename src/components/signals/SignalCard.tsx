import { Building2, ExternalLink, Clock, AlertCircle, TrendingDown, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

export type SignalType = "news" | "financial" | "regulatory" | "industry";
export type SignalStatus = "new" | "review" | "resolved";

interface SignalCardProps {
  id: string;
  corporationName: string;
  corporationId: string;
  signalType: SignalType;
  status: SignalStatus;
  title: string;
  summary: string;
  source: string;
  detectedAt: string;
  category: string;
}

const signalTypeConfig = {
  news: { icon: FileText, label: "언론 보도" },
  financial: { icon: TrendingDown, label: "재무 변동" },
  regulatory: { icon: AlertCircle, label: "규제/법률" },
  industry: { icon: Building2, label: "산업 동향" },
};

const statusConfig = {
  new: { label: "신규", className: "status-new" },
  review: { label: "검토중", className: "status-review" },
  resolved: { label: "완료", className: "status-resolved" },
};

export function SignalCard({
  corporationName,
  corporationId,
  signalType,
  status,
  title,
  summary,
  source,
  detectedAt,
  category,
}: SignalCardProps) {
  const TypeIcon = signalTypeConfig[signalType].icon;
  const typeLabel = signalTypeConfig[signalType].label;
  const statusInfo = statusConfig[status];

  return (
    <article className="signal-card group animate-fade-in">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 flex-1">
          {/* Signal type icon */}
          <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center shrink-0">
            <TypeIcon className="w-5 h-5 text-primary" />
          </div>

          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-1">
              <span className={`status-badge ${statusInfo.className}`}>
                {statusInfo.label}
              </span>
              <span className="text-xs text-muted-foreground">{typeLabel}</span>
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">{category}</span>
            </div>

            {/* Title */}
            <h3 className="font-medium text-foreground mb-1 line-clamp-1">
              {title}
            </h3>

            {/* Corporation info */}
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-sm text-primary font-medium">{corporationName}</span>
              <span className="text-xs text-muted-foreground">({corporationId})</span>
            </div>

            {/* Summary */}
            <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
              {summary}
            </p>

            {/* Footer */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {detectedAt}
              </span>
              <span>출처: {source}</span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="outline" size="sm">
            상세 보기
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <ExternalLink className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </article>
  );
}
