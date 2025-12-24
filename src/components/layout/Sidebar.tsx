import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { 
  Inbox, 
  Building2, 
  Settings, 
  Bell,
  ChevronLeft,
  ChevronRight,
  BarChart3,
  FileText
} from "lucide-react";

const navigationItems = [
  {
    id: "signals",
    label: "시그널 인박스",
    icon: Inbox,
    path: "/",
    badge: 12,
  },
  {
    id: "corporations",
    label: "기업 검색",
    icon: Building2,
    path: "/corporations",
  },
  {
    id: "reports",
    label: "보고서",
    icon: FileText,
    path: "/reports",
  },
  {
    id: "analytics",
    label: "분석 현황",
    icon: BarChart3,
    path: "/analytics",
  },
];

const bottomItems = [
  {
    id: "notifications",
    label: "알림 설정",
    icon: Bell,
    path: "/notifications",
  },
  {
    id: "settings",
    label: "설정",
    icon: Settings,
    path: "/settings",
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={`
        fixed left-0 top-0 h-screen bg-sidebar border-r border-sidebar-border
        transition-all duration-300 ease-in-out z-50
        ${collapsed ? "w-16" : "w-64"}
      `}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center h-16 px-4 border-b border-sidebar-border">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center">
                <span className="text-sidebar-primary-foreground font-bold text-sm">R</span>
              </div>
              <div>
                <h1 className="text-sidebar-foreground font-semibold text-lg tracking-tight">RKYC</h1>
                <p className="text-sidebar-foreground/50 text-[10px] -mt-0.5">고객 인텔리전스</p>
              </div>
            </div>
          )}
          {collapsed && (
            <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center mx-auto">
              <span className="text-sidebar-primary-foreground font-bold text-sm">R</span>
            </div>
          )}
        </div>

        {/* Main navigation */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navigationItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.id}
                to={item.path}
                className={`
                  nav-item
                  ${isActive ? "nav-item-active" : ""}
                  ${collapsed ? "justify-center px-2" : ""}
                `}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="w-5 h-5 shrink-0" />
                {!collapsed && (
                  <>
                    <span className="flex-1">{item.label}</span>
                    {item.badge && (
                      <span className="bg-sidebar-primary text-sidebar-primary-foreground text-xs px-2 py-0.5 rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom navigation */}
        <div className="py-4 px-2 border-t border-sidebar-border space-y-1">
          {bottomItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.id}
                to={item.path}
                className={`
                  nav-item
                  ${isActive ? "nav-item-active" : ""}
                  ${collapsed ? "justify-center px-2" : ""}
                `}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="w-5 h-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-20 w-6 h-6 bg-card border border-border rounded-full flex items-center justify-center shadow-sm hover:bg-secondary transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="w-3 h-3 text-muted-foreground" />
          ) : (
            <ChevronLeft className="w-3 h-3 text-muted-foreground" />
          )}
        </button>
      </div>
    </aside>
  );
}
