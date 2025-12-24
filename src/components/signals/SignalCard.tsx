import { 
  Building2, 
  Factory, 
  Globe, 
  FileText, 
  TrendingDown, 
  Scale, 
  Users, 
  BarChart3,
  ExternalLink, 
  Clock, 
  Info,
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { 
  Signal, 
  SignalCategory, 
  SIGNAL_TYPE_CONFIG, 
  SIGNAL_STATUS_CONFIG,
  SIGNAL_SUBTYPE_CONFIG 
} from "@/types/signal";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface SignalCardProps {
  signal: Signal;
  onViewDetail?: (signal: Signal) => void;
}

const categoryIcons = {
  direct: Building2,
  industry: Factory,
  environment: Globe,
};

const subTypeIcons = {
  news: FileText,
  financial: TrendingDown,
  regulatory: Scale,
  governance: Users,
  market: BarChart3,
  macro: Globe,
};

export function SignalCard({ signal, onViewDetail }: SignalCardProps) {
  const CategoryIcon = categoryIcons[signal.signalCategory];
  const SubTypeIcon = subTypeIcons[signal.signalSubType];
  const typeConfig = SIGNAL_TYPE_CONFIG[signal.signalCategory];
  const statusConfig = SIGNAL_STATUS_CONFIG[signal.status];
  const subTypeConfig = SIGNAL_SUBTYPE_CONFIG[signal.signalSubType];

  return (
    <article 
      className={`
        signal-card group animate-fade-in relative
        border-l-4 ${typeConfig.borderClass}
      `}
    >
      {/* Signal category indicator */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 flex-1">
          {/* Category icon with tooltip */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className={`w-11 h-11 rounded-lg ${typeConfig.bgClass} flex items-center justify-center shrink-0 cursor-help`}>
                <CategoryIcon className={`w-5 h-5 ${typeConfig.colorClass}`} />
              </div>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-xs">
              <p className="font-medium mb-1">{typeConfig.label}</p>
              <p className="text-xs text-muted-foreground">{typeConfig.description}</p>
            </TooltipContent>
          </Tooltip>

          <div className="flex-1 min-w-0">
            {/* Header with badges */}
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              {/* Signal category badge */}
              <span className={`status-badge ${typeConfig.bgClass} ${typeConfig.colorClass} font-medium`}>
                {typeConfig.label}
              </span>
              
              {/* Status badge */}
              <span className={`status-badge ${statusConfig.className}`}>
                {statusConfig.label}
              </span>
              
              {/* Sub-type indicator */}
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <SubTypeIcon className="w-3 h-3" />
                {subTypeConfig.label}
              </span>
              
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">{signal.detailCategory}</span>
            </div>

            {/* Title */}
            <h3 className="font-medium text-foreground mb-1.5 line-clamp-1">
              {signal.title}
            </h3>

            {/* Corporation info */}
            <div className="flex items-center gap-2 mb-2">
              <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-sm text-primary font-medium">{signal.corporationName}</span>
              <span className="text-xs text-muted-foreground">({signal.corporationId})</span>
              
              {/* Related corporations for industry signals */}
              {signal.signalCategory === "industry" && signal.relatedCorporations && (
                <span className="text-xs text-muted-foreground">
                  외 {signal.relatedCorporations.length}개 기업
                </span>
              )}
            </div>

            {/* Summary */}
            <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
              {signal.summary}
            </p>

            {/* Relevance note for industry/environment signals */}
            {signal.relevanceNote && signal.signalCategory !== "direct" && (
              <div className={`flex items-start gap-2 text-xs p-2 rounded-md mb-3 ${typeConfig.bgClass}`}>
                <Info className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${typeConfig.colorClass}`} />
                <span className={typeConfig.colorClass}>
                  <strong>연관성 참고:</strong> {signal.relevanceNote}
                </span>
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                {signal.detectedAt}
              </span>
              <span>출처: {signal.source}</span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => onViewDetail?.(signal)}
            className="gap-1"
          >
            상세 보기
            <ChevronRight className="w-3 h-3" />
          </Button>
          {signal.sourceUrl && (
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <a href={signal.sourceUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4" />
              </a>
            </Button>
          )}
        </div>
      </div>
    </article>
  );
}
