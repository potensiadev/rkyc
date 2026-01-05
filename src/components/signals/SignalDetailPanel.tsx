import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X,
  Building2,
  Factory,
  Globe,
  Clock,
  ExternalLink,
  FileText,
  TrendingDown,
  Scale,
  Users,
  BarChart3,
  CheckCircle2,
  MessageSquare,
  User
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { 
  Signal, 
  SignalCategory,
  SIGNAL_TYPE_CONFIG, 
  SIGNAL_STATUS_CONFIG,
  SIGNAL_SUBTYPE_CONFIG 
} from "@/types/signal";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

interface SignalDetailPanelProps {
  signal: Signal | null;
  open: boolean;
  onClose: () => void;
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

export function SignalDetailPanel({ signal, open, onClose }: SignalDetailPanelProps) {
  const [memo, setMemo] = useState("");
  const navigate = useNavigate();

  if (!signal) return null;

  const CategoryIcon = categoryIcons[signal.signalCategory];
  const SubTypeIcon = subTypeIcons[signal.signalSubType];
  const typeConfig = SIGNAL_TYPE_CONFIG[signal.signalCategory];
  const statusConfig = SIGNAL_STATUS_CONFIG[signal.status];
  const subTypeConfig = SIGNAL_SUBTYPE_CONFIG[signal.signalSubType];

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="pb-4 border-b border-border">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg ${typeConfig.bgClass} flex items-center justify-center`}>
                <CategoryIcon className={`w-5 h-5 ${typeConfig.colorClass}`} />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`status-badge ${typeConfig.bgClass} ${typeConfig.colorClass} font-medium`}>
                    {typeConfig.label}
                  </span>
                  <span className={`status-badge ${statusConfig.className}`}>
                    {statusConfig.label}
                  </span>
                </div>
                <SheetTitle className="text-left text-base">{signal.title}</SheetTitle>
              </div>
            </div>
          </div>
        </SheetHeader>

        <div className="py-6 space-y-6">
          {/* Corporation info */}
          <div className="flex items-center gap-3 p-4 bg-secondary rounded-lg">
            <Building2 className="w-5 h-5 text-primary" />
            <div>
              <p className="font-medium text-foreground">{signal.corporationName}</p>
              <p className="text-sm text-muted-foreground">{signal.corporationId}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="ml-auto"
              onClick={() => {
                onClose();
                navigate(`/corporates/${signal.corporationId}`);
              }}
            >
              기업 상세
            </Button>
          </div>

          {/* Signal type explanation */}
          <div className={`p-4 rounded-lg border-2 ${typeConfig.borderClass} ${typeConfig.bgClass}`}>
            <div className="flex items-center gap-2 mb-2">
              <CategoryIcon className={`w-4 h-4 ${typeConfig.colorClass}`} />
              <h3 className={`font-medium ${typeConfig.colorClass}`}>{typeConfig.label} 분석 방식</h3>
            </div>
            <p className="text-sm text-muted-foreground mb-3">
              {typeConfig.analysisLogic}
            </p>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">출처 유형:</p>
              <div className="flex flex-wrap gap-1.5">
                {typeConfig.evidenceSources.map((source, i) => (
                  <span key={i} className="text-xs bg-background px-2 py-1 rounded-md text-muted-foreground">
                    {source}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Summary content */}
          <div>
            <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
              <SubTypeIcon className="w-4 h-4" />
              {subTypeConfig.label} 요약
            </h3>
            <div className="p-4 bg-muted/50 rounded-lg">
              <p className="text-sm text-foreground leading-relaxed">
                {signal.summary}
              </p>
            </div>
          </div>

          {/* Relevance note for non-direct signals */}
          {signal.signalCategory !== "direct" && signal.relevanceNote && (
            <div className={`p-4 rounded-lg ${typeConfig.bgClass} border ${typeConfig.borderClass}`}>
              <h3 className={`text-sm font-medium mb-2 ${typeConfig.colorClass}`}>
                {signal.signalCategory === "industry" ? "산업 연관성 참고" : "환경 영향 참고"}
              </h3>
              <p className="text-sm text-muted-foreground">
                {signal.relevanceNote}
              </p>
              <p className="text-xs text-muted-foreground mt-2 italic">
                ※ 위 내용은 참고용으로 제공되며, 실제 영향 여부는 담당자의 판단이 필요합니다.
              </p>
            </div>
          )}

          {/* Related corporations for industry signals */}
          {signal.signalCategory === "industry" && signal.relatedCorporations && signal.relatedCorporations.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-foreground mb-2">동일 산업 관련 기업</h3>
              <div className="flex flex-wrap gap-2">
                {signal.relatedCorporations.map((corp, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 text-sm bg-secondary px-3 py-1.5 rounded-md">
                    <Building2 className="w-3 h-3 text-muted-foreground" />
                    {corp}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Source info */}
          <div className="flex items-center justify-between p-4 bg-secondary rounded-lg">
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                {signal.detectedAt}
              </span>
              <span>출처: {signal.source}</span>
            </div>
            {signal.sourceUrl && (
              <Button variant="outline" size="sm" className="gap-1.5" asChild>
                <a href={signal.sourceUrl} target="_blank" rel="noopener noreferrer">
                  원문 보기
                  <ExternalLink className="w-3 h-3" />
                </a>
              </Button>
            )}
          </div>

          {/* Memo section */}
          <div>
            <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              검토 메모
            </h3>
            <Textarea 
              placeholder="검토 내용이나 후속 조치 사항을 기록하세요..."
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              className="min-h-[100px]"
            />
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3 pt-4 border-t border-border">
            <Button className="flex-1 gap-2">
              <CheckCircle2 className="w-4 h-4" />
              검토 완료
            </Button>
            <Button variant="outline" className="flex-1 gap-2">
              <User className="w-4 h-4" />
              담당자 배정
            </Button>
          </div>

          {/* Disclaimer */}
          <p className="text-xs text-muted-foreground text-center pt-2">
            본 시그널은 참고용으로만 제공되며, 모든 판단과 결정은 담당자의 검토에 따릅니다.
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}
