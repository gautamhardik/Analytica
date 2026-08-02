"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { KPICard } from "@/components/ui/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ShoppingBag, Package, DollarSign } from "lucide-react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetcher } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export default function ProductsPage() {
  const { filters } = useAppStore();

  const queryParams = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v && v !== "all" && v !== "all_time") queryParams.append(k, v);
  });
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";

  const { data, isLoading, error } = useQuery({
    queryKey: ["products", filters],
    queryFn: () => fetcher<any>(`/products${queryString}`),
    placeholderData: keepPreviousData,
  });

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-outfit font-bold tracking-tight">Product & Seller Analytics</h1>
          <p className="text-muted-foreground">Category performance and top seller breakdown.</p>
        </div>

        {isLoading && !data ? (
          <div className="h-[400px] rounded-xl bg-card/40 animate-pulse border border-border/50" />
        ) : error ? (
          <div className="p-6 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive">
            Failed to load product data. Please check backend server.
          </div>
        ) : data ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <KPICard
                title={data.kpis.total_categories.label}
                value={data.kpis.total_categories.formatted}
                icon={<ShoppingBag className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.total_items_sold.label}
                value={data.kpis.total_items_sold.formatted}
                icon={<Package className="w-5 h-5" />}
              />
              <KPICard
                title={data.kpis.total_revenue.label}
                value={data.kpis.total_revenue.formatted}
                icon={<DollarSign className="w-5 h-5" />}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle>Top Product Categories</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-md border border-border/50 bg-black/10">
                    <Table>
                      <TableHeader>
                        <TableRow className="hover:bg-transparent border-border/50">
                          <TableHead className="w-[200px]">Category</TableHead>
                          <TableHead className="text-right">Items Sold</TableHead>
                          <TableHead className="text-right">Revenue</TableHead>
                          <TableHead className="text-right">Avg Price</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(data.top_categories ?? []).map((cat: any) => (
                          <TableRow key={cat.product_category} className="border-border/50 hover:bg-white/5 transition-colors">
                            <TableCell className="font-medium text-primary">{cat.product_category || 'N/A'}</TableCell>
                            <TableCell className="text-right">{(cat.total_items_sold ?? 0).toLocaleString()}</TableCell>
                            <TableCell className="text-right">R$ {(cat.total_revenue ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                            <TableCell className="text-right">R$ {(cat.average_item_price ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-card">
                <CardHeader>
                  <CardTitle>Top Sellers</CardTitle>
                </CardHeader>
                <CardContent>
                  {(data.top_sellers ?? []).length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground border border-dashed border-border/50 rounded-lg bg-black/5">
                      Seller data view not yet initialized in warehouse.
                    </div>
                  ) : (
                    <div className="rounded-md border border-border/50 bg-black/10">
                      <Table>
                        <TableHeader>
                          <TableRow className="hover:bg-transparent border-border/50">
                            <TableHead>Seller Location</TableHead>
                            <TableHead className="text-right">Orders Fulfilled</TableHead>
                            <TableHead className="text-right">Total Revenue</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(data.top_sellers ?? []).slice(0, 5).map((seller: any) => (
                            <TableRow key={seller.seller_id} className="border-border/50 hover:bg-white/5 transition-colors">
                              <TableCell>
                                <div className="flex flex-col">
                                  <span className="font-medium">{seller.seller_city || 'Unknown'}</span>
                                  <span className="text-xs text-muted-foreground">{seller.seller_state || 'Unknown'}</span>
                                </div>
                              </TableCell>
                            <TableCell className="text-right">{(seller.orders_fulfilled ?? 0).toLocaleString()}</TableCell>
                            <TableCell className="text-right">R$ {(seller.total_revenue_generated ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
