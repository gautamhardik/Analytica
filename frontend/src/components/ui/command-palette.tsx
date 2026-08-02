"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Map, FileText, LineChart, ShoppingBag, LayoutDashboard, Users, User, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

const commands = [
  { name: "Executive Workspace", href: "/", icon: LayoutDashboard, category: "Workspaces" },
  { name: "Revenue Workspace", href: "/sales", icon: LineChart, category: "Workspaces" },
  { name: "Customer Workspace", href: "/customers", icon: Users, category: "Workspaces" },
  { name: "Product Workspace", href: "/products", icon: ShoppingBag, category: "Workspaces" },
  { name: "Geography Workspace", href: "/geography", icon: Map, category: "Workspaces" },
  { name: "Reports Workspace", href: "/reports", icon: FileText, category: "Workspaces" },
  { name: "Switch to Executive Role", action: "role:executive", icon: User, category: "Actions" },
  { name: "Switch to Sales Manager Role", action: "role:sales_manager", icon: User, category: "Actions" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  if (!open) return null;

  const filteredCommands = query === "" 
    ? commands 
    : commands.filter(c => c.name.toLowerCase().includes(query.toLowerCase()) || c.category.toLowerCase().includes(query.toLowerCase()));

  const handleSelect = (cmd: typeof commands[0]) => {
    if (cmd.href) {
      router.push(cmd.href);
    } else if (cmd.action) {
      // Simulate action - in a real app this would call setRole from store
      console.log("Action selected:", cmd.action);
    }
    setOpen(false);
    setQuery("");
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[15vh]"
        onClick={() => setOpen(false)}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          className="w-full max-w-lg bg-card border border-border shadow-2xl rounded-xl overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center px-4 py-3 border-b border-border/50 gap-3">
            <Search className="w-5 h-5 text-muted-foreground" />
            <input
              autoFocus
              className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground placeholder:font-light"
              placeholder="Type a command or search..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button className="text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground font-mono" onClick={() => setOpen(false)}>
              ESC
            </button>
          </div>
          <div className="max-h-[300px] overflow-y-auto p-2">
            {filteredCommands.length === 0 ? (
              <p className="p-4 text-sm text-center text-muted-foreground">No results found.</p>
            ) : (
              <div className="space-y-1">
                {Array.from(new Set(filteredCommands.map(c => c.category))).map(category => (
                  <div key={category}>
                    <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider mt-2">
                      {category}
                    </div>
                    {filteredCommands.filter(c => c.category === category).map((cmd, i) => {
                      const Icon = cmd.icon;
                      return (
                        <button
                          key={i}
                          onClick={() => handleSelect(cmd)}
                          className="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-lg text-left hover:bg-primary hover:text-primary-foreground transition-colors group"
                        >
                          <Icon className="w-4 h-4 text-muted-foreground group-hover:text-primary-foreground" />
                          <span>{cmd.name}</span>
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
