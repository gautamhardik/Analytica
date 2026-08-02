"use client";

import { useState } from "react";
import { Sidebar } from "./sidebar";
import { TopNav } from "./topnav";
import { GlobalFilterBar } from "./global-filter-bar";
import { PageTransition } from "./page-transition";
import { CommandPalette } from "../ui/command-palette";
import { AnimatePresence, motion } from "framer-motion";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Global Command Palette */}
      <CommandPalette />

      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Mobile Slide-Over Drawer */}
      <AnimatePresence>
        {mobileNavOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileNavOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 w-72 bg-card border-r border-border z-50 md:hidden shadow-2xl"
            >
              <Sidebar 
                isMobile={true} 
                onItemClick={() => setMobileNavOpen(false)} 
                onCloseMobile={() => setMobileNavOpen(false)} 
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <TopNav onToggleMobileSidebar={() => setMobileNavOpen(prev => !prev)} />
        <GlobalFilterBar />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8">
          <div className="max-w-7xl mx-auto h-full">
            <AnimatePresence mode="wait">
              <PageTransition>
                {children}
              </PageTransition>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}
