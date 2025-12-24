import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Copy, Check } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ShareLinkModalProps {
  open: boolean;
  onClose: () => void;
  companyName: string;
}

const ShareLinkModal = ({ open, onClose, companyName }: ShareLinkModalProps) => {
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  const shareLink = `https://rkyc.internal.bank/reports/${encodeURIComponent(companyName)}/view?token=abc123xyz`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      toast({
        title: "링크가 복사되었습니다",
        description: "클립보드에 공유 링크가 복사되었습니다.",
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast({
        title: "복사 실패",
        description: "링크 복사에 실패했습니다. 수동으로 복사해주세요.",
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>공유 링크</DialogTitle>
        </DialogHeader>

        <div className="py-4 space-y-4">
          <div className="flex gap-2">
            <Input
              value={shareLink}
              readOnly
              className="text-sm bg-muted"
            />
            <Button 
              variant="outline" 
              size="icon"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="h-4 w-4 text-primary" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            기본 만료: 7일
          </p>

          <div className="text-xs text-muted-foreground p-3 bg-muted rounded">
            이 링크는 내부 직원만 접근할 수 있으며, 
            보고서 내용은 참고용으로만 제공됩니다.
          </div>
        </div>

        <div className="flex justify-end">
          <Button variant="outline" onClick={onClose}>
            닫기
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ShareLinkModal;
