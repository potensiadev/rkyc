import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { getCorporationById } from "@/data/corporations";

interface ExportSettingsPanelProps {
  fileName: string;
  onFileNameChange: (name: string) => void;
  sections: {
    summary: boolean;
    companyOverview: boolean;
    valueChain: boolean;
    signalTypeSummary: boolean;
    signalTimeline: boolean;
    evidenceSummary: boolean;
    loanInsight: boolean;
    insightMemory: boolean;
    disclaimer: boolean;
  };
  onSectionChange: (section: keyof ExportSettingsPanelProps['sections'], checked: boolean) => void;
  corporationId: string;
}

const ExportSettingsPanel = ({
  fileName,
  onFileNameChange,
  sections,
  onSectionChange,
  corporationId,
}: ExportSettingsPanelProps) => {
  const corporation = getCorporationById(corporationId);
  const showLoanSection = corporation?.bankRelationship?.hasRelationship ?? false;

  const sectionLabels: { key: keyof typeof sections; label: string; conditional?: boolean }[] = [
    { key: 'summary', label: '요약' },
    { key: 'companyOverview', label: '기업 개요' },
    { key: 'valueChain', label: '가치사슬망' },
    { key: 'signalTypeSummary', label: '시그널 유형별 요약' },
    { key: 'signalTimeline', label: '시그널 타임라인' },
    { key: 'evidenceSummary', label: '주요 근거 요약' },
    { key: 'loanInsight', label: '여신 참고 관점 요약', conditional: true },
    { key: 'insightMemory', label: '과거 사례 참고' },
    { key: 'disclaimer', label: '면책 문구' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-foreground mb-4">내보내기 설정</h3>
      </div>

      {/* Paper Settings */}
      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">용지 크기</span>
          <span className="text-foreground">A4</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">방향</span>
          <span className="text-foreground">세로</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">여백</span>
          <span className="text-foreground">표준</span>
        </div>
      </div>

      <Separator />

      {/* File Name */}
      <div className="space-y-2">
        <Label htmlFor="fileName" className="text-sm text-muted-foreground">
          파일명
        </Label>
        <Input
          id="fileName"
          value={fileName}
          onChange={(e) => onFileNameChange(e.target.value)}
          className="text-sm"
        />
      </div>

      <Separator />

      {/* Section Toggles */}
      <div className="space-y-3">
        <Label className="text-sm text-muted-foreground">포함 섹션</Label>
        <div className="space-y-3">
          {sectionLabels.map(({ key, label, conditional }) => {
            // Hide loan section toggle if company doesn't have loan
            if (conditional && !showLoanSection) return null;
            
            return (
              <div key={key} className="flex items-center space-x-2">
                <Checkbox
                  id={key}
                  checked={sections[key]}
                  onCheckedChange={(checked) => onSectionChange(key, checked as boolean)}
                />
                <Label 
                  htmlFor={key} 
                  className="text-sm text-foreground cursor-pointer"
                >
                  {label}
                </Label>
              </div>
            );
          })}
        </div>
      </div>

      <div className="text-xs text-muted-foreground mt-4 p-3 bg-muted rounded">
        설정은 포함 여부 및 형식만 조정합니다. 
        우선순위나 판단을 의미하지 않습니다.
      </div>
    </div>
  );
};

export default ExportSettingsPanel;
