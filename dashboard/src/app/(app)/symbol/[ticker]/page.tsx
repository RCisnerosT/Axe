import { notFound } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase";
import type { DivergenceWithPivots, PriceBar, Pivot, Timeframe } from "@/lib/types";
import { SymbolChart } from "./symbol-chart";

export const dynamic = "force-dynamic";

const TIMEFRAMES: Timeframe[] = ["1h", "4h", "1d"];

export default async function SymbolPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const supabase = getSupabaseClient();

  const { data: symbol } = await supabase.from("symbols").select("*").eq("ticker", ticker).maybeSingle();
  if (!symbol) notFound();

  const dataByTimeframe: Record<
    Timeframe,
    { bars: PriceBar[]; pivots: Pivot[]; divergence: DivergenceWithPivots | null }
  > = {
    "1h": { bars: [], pivots: [], divergence: null },
    "4h": { bars: [], pivots: [], divergence: null },
    "1d": { bars: [], pivots: [], divergence: null },
  };

  for (const timeframe of TIMEFRAMES) {
    const [{ data: bars }, { data: pivots }, { data: divergences }] = await Promise.all([
      supabase
        .from("price_bars")
        .select("*")
        .eq("ticker", ticker)
        .eq("timeframe", timeframe)
        .order("ts", { ascending: true }),
      supabase
        .from("pivots")
        .select("*")
        .eq("ticker", ticker)
        .eq("timeframe", timeframe)
        .eq("session_scope", "regular")
        .order("ts", { ascending: true }),
      supabase
        .from("divergences")
        .select(
          `*,
          pivot_1:pivots!divergences_pivot_1_id_fkey(*),
          pivot_2:pivots!divergences_pivot_2_id_fkey(*)`,
        )
        .eq("ticker", ticker)
        .eq("timeframe", timeframe)
        .eq("session_scope", "regular")
        .eq("status", "active")
        .order("detected_at", { ascending: false })
        .limit(1),
    ]);

    dataByTimeframe[timeframe] = {
      bars: (bars ?? []) as PriceBar[],
      pivots: (pivots ?? []) as Pivot[],
      divergence: (divergences?.[0] as unknown as DivergenceWithPivots) ?? null,
    };
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">
          {symbol.ticker} <span className="font-normal text-muted-foreground">{symbol.name}</span>
        </h1>
      </div>
      <SymbolChart ticker={ticker} dataByTimeframe={dataByTimeframe} />
    </div>
  );
}
