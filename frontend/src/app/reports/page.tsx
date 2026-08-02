"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Download, FileText, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useState } from "react";
import { cn } from "@/lib/utils";

export default function ReportsPage() {
  const [activeReport, setActiveReport] = useState<string>("monthly_sales");
  const [page, setPage] = useState(1);
  
  const { data: listData } = useQuery({
    queryKey: ["reports_list"],
    queryFn: () => fetcher<any>("/reports"),
  });
  
  const { data: rawReportPayload, isLoading, error } = useQuery({
    queryKey: ["report_data", activeReport, page],
    queryFn: () => fetcher<any>(`/reports/${activeReport}/data?page=${page}&page_size=10`),
    enabled: !!activeReport,
  });

  const reports = listData?.reports || [];
  
  // Handle both array response and paginated wrapper response
  const rows = Array.isArray(rawReportPayload) 
    ? rawReportPayload 
    : (rawReportPayload?.data || []);

  const pagination = rawReportPayload?.pagination || { 
    page: page, 
    page_size: 10, 
    total_items: rows.length, 
    total_pages: 1 
  };

  const handleExportCSV = () => {
    if (Array.isArray(rows) && rows.length > 0) {
      const headers = Object.keys(rows[0]).join(",");
      const csvRows = rows.map((r: any) =>
        Object.values(r)
          .map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`)
          .join(",")
      );
      const blob = new Blob([[headers, ...csvRows].join("\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `${activeReport}_export.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      alert("No data available to export for this report.");
    }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-outfit font-bold tracking-tight">Data Explorer & Reports</h1>
            <p className="text-muted-foreground">View and export raw analytical data tables.</p>
          </div>
          <Button 
            onClick={handleExportCSV}
            variant="outline" 
            className="gap-2 bg-card/50 backdrop-blur-md border-border/50 hover:bg-primary hover:text-primary-foreground transition-all"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="md:col-span-1 space-y-4">
            <Card className="glass-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Filter className="w-4 h-4 text-primary" />
                  Available Reports
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="flex flex-col">
                  {reports.map((report: any) => (
                    <button
                      key={report.id}
                      onClick={() => { setActiveReport(report.id); setPage(1); }}
                      className={cn(
                        "text-left px-4 py-3 text-sm transition-colors border-l-2",
                        activeReport === report.id 
                          ? "bg-primary/10 border-primary text-foreground font-medium" 
                          : "border-transparent text-muted-foreground hover:bg-white/5"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-4 h-4 text-primary" />
                        {report.name}
                      </div>
                      <p className="text-xs opacity-70 line-clamp-1 pl-6">{report.description}</p>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="md:col-span-3">
            <Card className="glass-card min-h-[500px] flex flex-col">
              <CardHeader>
                <CardTitle>{reports.find((r: any) => r.id === activeReport)?.name || "Select a report"}</CardTitle>
                <CardDescription>
                  {reports.find((r: any) => r.id === activeReport)?.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                {isLoading ? (
                  <div className="flex-1 bg-black/5 animate-pulse rounded-md border border-border/50" />
                ) : error ? (
                  <div className="flex-1 flex items-center justify-center text-destructive border border-destructive/30 rounded-lg bg-destructive/5">
                    Failed to load report data. Please check backend server.
                  </div>
                ) : rows.length > 0 ? (
                  <div className="flex-1 flex flex-col">
                    <div className="rounded-md border border-border/50 bg-black/10 flex-1 overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow className="hover:bg-transparent border-border/50">
                            {Object.keys(rows[0]).map((key) => (
                              <TableHead key={key} className="whitespace-nowrap font-semibold text-foreground py-4 px-4 bg-black/20">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</TableHead>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {rows.map((row: any, i: number) => (
                            <TableRow key={i} className="border-border/50 hover:bg-white/5 transition-colors">
                              {Object.values(row).map((val: any, j: number) => (
                                <TableCell key={j} className="whitespace-nowrap text-sm py-3 px-4">
                                  {typeof val === 'number' 
                                    ? (Object.keys(rows[0])[j].toLowerCase().includes('revenue') || Object.keys(rows[0])[j].toLowerCase().includes('value') || Object.keys(rows[0])[j].toLowerCase().includes('price') 
                                        ? `R$ ${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` 
                                        : val.toLocaleString(undefined, { maximumFractionDigits: 2 }))
                                    : val?.toString() || 'N/A'}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    
                    {/* Pagination */}
                    <div className="flex items-center justify-between pt-4 mt-auto">
                      <span className="text-xs text-muted-foreground font-mono">
                        Showing {((pagination.page - 1) * 10) + 1} to {Math.min(pagination.page * 10, pagination.total_items)} of {pagination.total_items}
                      </span>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          disabled={pagination.page === 1}
                          onClick={() => setPage(p => Math.max(1, p - 1))}
                          className="bg-card hover:bg-white/10"
                        >
                          Previous
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          disabled={pagination.page >= pagination.total_pages}
                          onClick={() => setPage(p => p + 1)}
                          className="bg-card hover:bg-white/10"
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-muted-foreground border border-dashed border-border/50 rounded-lg bg-black/5">
                    No data available for this report.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
