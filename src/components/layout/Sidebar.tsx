import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Inbox,
  Building2,
  Settings,
  ChevronDown,
  BarChart3,
  Factory,
  Globe,
  Newspaper,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SubMenuItem {
  id: string;
  label: string;
  icon: React.ElementType; // Kept for type compatibility but not rendered
  path: string;
}

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ElementType; // Kept for type compatibility but not rendered
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
  const [expandedItems, setExpandedItems] = useState<string[]>(["briefing"]);
  const location = useLocation();

  const toggleExpanded = (id: string, e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    setExpandedItems((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Auto-expand active group
  useEffect(() => {
    navigationItems.forEach(item => {
      if (item.subItems && item.subItems.some(sub => sub.path === location.pathname)) {
        setExpandedItems(prev => prev.includes(item.id) ? prev : [...prev, item.id]);
      }
    });
  }, [location.pathname]);

  const isItemActive = (path: string) => location.pathname === path;

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-64 bg-[#111827] text-slate-300 transition-all duration-300 ease-in-out z-50 border-r border-slate-800/50 flex flex-col shadow-2xl"
    >
      {/* Header / Logo */}
      <div className="h-20 flex items-center px-6 border-b border-slate-800/50 relative group">
        <Link to="/" className="flex items-center gap-3 overflow-hidden group px-2">
          <div className="transition-opacity duration-300 opacity-100">
            <h1 className="text-white font-bold text-2xl tracking-tight leading-none font-display">rKYC</h1>
            <p className="text-[10px] text-blue-200/70 font-medium leading-tight mt-1 whitespace-nowrap tracking-wide">really Know Your Customer</p>
          </div>
        </Link>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto py-6 px-4 space-y-8 custom-scrollbar">

        {/* Main Navigation */}
        <nav className="space-y-1">
          {navigationItems.map((item) => {
            const isActive = isItemActive(item.path);
            const hasSubItems = item.subItems && item.subItems.length > 0;
            const isExpanded = expandedItems.includes(item.id);
            const isChildActive = hasSubItems && item.subItems?.some(sub => isItemActive(sub.path));

            return (
              <div key={item.id} className="select-none">
                {/* Parent Item */}
                <div
                  className={cn(
                    "group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200",
                    (isActive || isChildActive)
                      ? "text-white bg-slate-800 font-medium"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                  )}
                  onClick={(e) => hasSubItems ? toggleExpanded(item.id, e) : null}
                >
                  {/* Link wrapper for non-subitems */}
                  {!hasSubItems ? (
                    <Link to={item.path} className="flex-1">
                      <span className="text-sm">{item.label}</span>
                    </Link>
                  ) : (
                    <>
                      <span className="text-sm flex-1">{item.label}</span>
                      <ChevronDown className={cn("w-4 h-4 transition-transform duration-200 opacity-50", isExpanded && "rotate-180")} />
                    </>
                  )}
                </div>

                {/* Submenu */}
                {hasSubItems && (
                  <div className={cn(
                    "grid transition-all duration-300 ease-in-out pl-4",
                    isExpanded ? "grid-rows-[1fr] opacity-100 mt-1" : "grid-rows-[0fr] opacity-0"
                  )}>
                    <div className="overflow-hidden border-l border-slate-700/50 space-y-1">
                      {item.subItems!.map((sub) => {
                        const isSubActive = isItemActive(sub.path);
                        return (
                          <Link
                            key={sub.id}
                            to={sub.path}
                            className={cn(
                              "block px-4 py-2 ml-1 rounded-md text-sm transition-all relative",
                              isSubActive
                                ? "text-blue-400 font-medium bg-blue-500/10"
                                : "text-slate-500 hover:text-slate-300"
                            )}
                          >
                            <span>{sub.label}</span>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800 bg-[#0F172A]">
        {bottomItems.map((item) => (
          <Link
            key={item.id}
            to={item.path}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
              isItemActive(item.path)
                ? "bg-slate-800 text-white font-medium"
                : "text-slate-400 hover:text-white hover:bg-slate-800/50"
            )}
          >
            <span className="text-sm">{item.label}</span>
          </Link>
        ))}
      </div>
    </aside>
  );
}
