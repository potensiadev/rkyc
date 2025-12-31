import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Sparkles, Puzzle, Clock, Filter } from "lucide-react";
import { cn } from "@/lib/utils";

interface SpotlightSearchProps {
  onSearch: (query: string, mode: "keyword" | "semantic") => void;
}

export function SpotlightSearch({ onSearch }: SpotlightSearchProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"keyword" | "semantic">("semantic");

  // Simple heuristic to switch modes based on input
  useEffect(() => {
    // If it looks like SQL or structured keyword (e.g. comma separated), it's keyword
    // Otherwise it's semantic/natural language
    if (query.includes(",") || query.includes("=")) {
      setMode("keyword");
    } else {
      setMode("semantic");
    }
  }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query, mode);
  };

  return (
    <div className="relative w-full flex justify-center z-50 mb-8">
      {/* Backdrop Dimming */}
      <AnimatePresence>
        {isFocused && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            onClick={() => setIsFocused(false)}
          />
        )}
      </AnimatePresence>

      <motion.div
        layout
        className={cn(
          "relative z-50 flex flex-col items-center",
          isFocused ? "w-full max-w-4xl" : "w-full max-w-2xl"
        )}
      >
        <motion.form
          layout
          onSubmit={handleSubmit}
          className={cn(
            "w-full rounded-2xl overflow-hidden border transition-all duration-300",
            isFocused
              ? "bg-background border-primary/50 shadow-[0_0_50px_-10px_rgba(124,58,237,0.2)]"
              : "bg-background/40 backdrop-blur-md border-white/20 hover:bg-background/60"
          )}
        >
          <div className="relative flex items-center h-16 px-6 gap-4">
            <motion.div
              layout
              className={cn(
                "flex items-center justify-center w-8 h-8 rounded-lg",
                mode === "semantic" ? "bg-purple-500/10" : "bg-blue-500/10"
              )}
            >
              {mode === "semantic" ? (
                <Sparkles className="w-5 h-5 text-purple-500" />
              ) : (
                <Puzzle className="w-5 h-5 text-blue-500" />
              )}
            </motion.div>

            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setIsFocused(true)}
              placeholder={isFocused 
                ? "조건(SQL)이나 문맥(Vector)으로 인재를 찾아보세요..." 
                : "Ask AI..."}
              className="flex-1 bg-transparent border-none outline-none text-lg placeholder:text-muted-foreground/50"
            />

            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground border px-2 py-1 rounded-md">
                {mode === "semantic" ? "Vector Mode" : "Exact Mode"}
              </span>
              <button
                type="submit"
                className="p-2 rounded-full bg-primary/10 hover:bg-primary/20 text-primary transition-colors"
              >
                <Search className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Expanded Filter Area */}
          <AnimatePresence>
            {isFocused && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t border-border/50 bg-muted/30"
              >
                <div className="p-4 grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="flex items-center gap-2 text-sm font-semibold text-muted-foreground mb-3">
                      <Clock className="w-4 h-4" /> 최근 검색어
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {["Java Backend", "판교 3년차", "재무 리스크"].map((tag) => (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => setQuery(tag)}
                          className="px-3 py-1.5 text-sm rounded-full bg-background border border-border hover:border-primary/50 transition-colors"
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4 className="flex items-center gap-2 text-sm font-semibold text-muted-foreground mb-3">
                      <Filter className="w-4 h-4" /> 추천 필터
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {["High Risk", "Opportunity", "Top Tier"].map((tag) => (
                        <button
                          key={tag}
                          type="button"
                          className="px-3 py-1.5 text-sm rounded-full bg-accent/50 border border-transparent hover:bg-accent transition-colors"
                        >
                          {tag}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.form>
      </motion.div>
    </div>
  );
}
