import { Bell, Search, User } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function TopBar() {
  return (
    <header className="h-16 border-b border-border bg-card px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-4 flex-1 max-w-md">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="기업명, 사업자등록번호로 검색..."
            className="pl-10 bg-secondary border-0 focus-visible:ring-1 focus-visible:ring-primary/30"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="w-5 h-5 text-muted-foreground" />
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-signal-new text-primary-foreground text-[10px] rounded-full flex items-center justify-center">
            3
          </span>
        </Button>

        <div className="w-px h-6 bg-border mx-2" />

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-medium text-foreground">김경민 과장</p>
            <p className="text-xs text-muted-foreground">리스크관리부</p>
          </div>
          <Button variant="ghost" size="icon" className="rounded-full bg-secondary">
            <User className="w-5 h-5 text-muted-foreground" />
          </Button>
        </div>
      </div>
    </header>
  );
}
