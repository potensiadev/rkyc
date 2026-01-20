import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Inbox,
  Building2,
  Settings,
  Bell,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  BarChart3,
  FileText,
  Factory,
  Globe,
  Newspaper,
  UserPlus,
} from "lucide-react";

interface SubMenuItem {
  id: string;
  label: string;
  icon: React.ElementType;
  path: string;
}

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ElementType;
  path: string;
  badge?: number;
  subItems?: SubMenuItem[];
}

const navigationItems: NavigationItem[] = [
  {
    id: "briefing",
    label: "일일 브리핑",
    icon: Newspaper,
    path: "/briefing",
    subItems: [
      {
        id: "direct-signals",
        label: "직접 시그널",
        icon: Building2,
        path: "/signals/direct",
      },
      {
        id: "industry-signals",
        label: "산업 시그널",
        icon: Factory,
        path: "/signals/industry",
      },
      {
        id: "environment-signals",
        label: "환경 시그널",
        icon: Globe,
        path: "/signals/environment",
      },
    ],
  },
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
    id: "analytics",
    label: "분석 현황",
    icon: BarChart3,
    path: "/analytics",
  },
  {
    id: "new-kyc",
    label: "신규 법인 PRE-KYC",
    icon: UserPlus,
    path: "/new-kyc",
  },
];

const bottomItems: NavigationItem[] = [
  {
    id: "settings",
    label: "설정",
    icon: Settings,
    path: "/settings",
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [expandedItems, setExpandedItems] = useState<string[]>(["briefing"]);
  const location = useLocation();

  const toggleExpanded = (id: string) => {
    setExpandedItems((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  const isItemActive = (path: string) => location.pathname === path;
  const isParentActive = (item: NavigationItem) => {
    if (isItemActive(item.path)) return true;
    if (item.subItems) {
      return item.subItems.some((sub) => isItemActive(sub.path));
    }
    return false;
  };

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
        <Link to="/" className="flex items-center h-16 px-4 border-b border-sidebar-border hover:bg-sidebar-accent/50 transition-colors">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center">
                <span className="text-sidebar-primary-foreground font-bold text-sm">R</span>
              </div>
              <div>
                <h1 className="text-sidebar-foreground font-semibold text-lg tracking-tight">rKYC</h1>
                <p className="text-sidebar-foreground/50 text-[10px] -mt-0.5">really Know Your Customer</p>
              </div>
            </div>
          )}
          {collapsed && (
            <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center mx-auto">
              <span className="text-sidebar-primary-foreground font-bold text-sm">R</span>
            </div>
          )}
        </Link>

        {/* Main navigation */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {navigationItems.map((item) => {
            const isActive = isParentActive(item);
            const isExpanded = expandedItems.includes(item.id);
            const hasSubItems = item.subItems && item.subItems.length > 0;

            return (
              <div key={item.id}>
                {/* Parent item */}
                <div className="flex items-center">
                  <Link
                    to={item.path}
                    className={`
                      nav-item flex-1
                      ${isActive && !hasSubItems ? "nav-item-active" : ""}
                      ${isActive && hasSubItems ? "text-sidebar-foreground font-medium" : ""}
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
                  {!collapsed && hasSubItems && (
                    <button
                      onClick={() => toggleExpanded(item.id)}
                      className="p-1.5 rounded-md hover:bg-sidebar-accent text-sidebar-foreground/70 hover:text-sidebar-foreground transition-colors"
                    >
                      <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                    </button>
                  )}
                </div>

                {/* Sub items */}
                {!collapsed && hasSubItems && isExpanded && (
                  <div className="mt-1 ml-4 pl-4 border-l border-sidebar-border space-y-1">
                    {item.subItems!.map((subItem) => {
                      const isSubActive = isItemActive(subItem.path);
                      return (
                        <Link
                          key={subItem.id}
                          to={subItem.path}
                          className={`
                            flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors
                            ${isSubActive
                              ? "bg-sidebar-accent text-sidebar-foreground font-medium"
                              : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                            }
                          `}
                        >
                          <subItem.icon className="w-4 h-4 shrink-0" />
                          <span>{subItem.label}</span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
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
