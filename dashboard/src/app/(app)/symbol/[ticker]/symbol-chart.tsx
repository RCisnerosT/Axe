"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import type { DivergenceWithPivots, PriceBar, Pivot, DisplayTimeframe } from "@/lib/types";
import { PriceRsiChart } from "./price-rsi-chart";

const TIMEFRAMES: DisplayTimeframe[] = ["4h", "1d"];

export function SymbolChart({
  dataByTimeframe,
}: {
  ticker: string;
  dataByTimeframe: Record<
    DisplayTimeframe,
    { bars: PriceBar[]; pivots: Pivot[]; divergence: DivergenceWithPivots | null }
  >;
}) {
  return (
    <Tabs defaultValue="4h">
      <TabsList>
        {TIMEFRAMES.map((tf) => (
          <TabsTrigger key={tf} value={tf}>
            {tf}
          </TabsTrigger>
        ))}
      </TabsList>
      {TIMEFRAMES.map((tf) => {
        const { bars, pivots, divergence } = dataByTimeframe[tf];
        return (
          <TabsContent key={tf} value={tf} className="space-y-3">
            {divergence && (
              <div className="flex items-center gap-2 text-sm">
                <Badge
                  className={divergence.direction === "bullish" ? "bg-emerald-600 text-white" : ""}
                  variant={divergence.direction === "bullish" ? "default" : "destructive"}
                >
                  {divergence.direction}
                </Badge>
                <Badge variant={divergence.strength === "strong" ? "default" : "secondary"}>
                  {divergence.strength}
                </Badge>
                <span className="text-muted-foreground">
                  {new Date(divergence.pivot_1.ts).toLocaleDateString("en-US", { month: "short", day: "2-digit" })} →{" "}
                  {new Date(divergence.pivot_2.ts).toLocaleDateString("en-US", { month: "short", day: "2-digit" })}
                </span>
              </div>
            )}
            {bars.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data for this timeframe yet.</p>
            ) : (
              <PriceRsiChart bars={bars} pivots={pivots} divergence={divergence} />
            )}
          </TabsContent>
        );
      })}
    </Tabs>
  );
}
