import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getSupabaseClient } from "@/lib/supabase";
import type { DivergenceWithPivots } from "@/lib/types";

export const dynamic = "force-dynamic";

const ET = "America/New_York";

function formatDate(ts: string) {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: ET });
}

async function getActiveDivergences(): Promise<DivergenceWithPivots[]> {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase
    .from("divergences")
    .select(
      `*,
      pivot_1:pivots!divergences_pivot_1_id_fkey(*),
      pivot_2:pivots!divergences_pivot_2_id_fkey(*)`,
    )
    .eq("status", "active")
    .order("detected_at", { ascending: false });

  if (error) throw error;
  return data as unknown as DivergenceWithPivots[];
}

export default async function DivergenceTablePage() {
  const divergences = await getActiveDivergences();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Active divergences</h1>
        <p className="text-sm text-muted-foreground">{divergences.length} signals</p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticker</TableHead>
              <TableHead>Timeframe</TableHead>
              <TableHead>Session</TableHead>
              <TableHead>Direction</TableHead>
              <TableHead>Strength</TableHead>
              <TableHead>Pivot 1</TableHead>
              <TableHead>Pivot 2</TableHead>
              <TableHead className="text-right">Price at signal</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {divergences.map((d) => (
              <TableRow key={d.id}>
                <TableCell>
                  <Link href={`/symbol/${d.ticker}`} className="font-medium text-foreground hover:underline">
                    {d.ticker}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{d.timeframe}</TableCell>
                <TableCell className="text-muted-foreground">
                  {d.session_scope === "extended" ? "incl. pre/post" : "regular"}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={d.direction === "bullish" ? "default" : "destructive"}
                    className={d.direction === "bullish" ? "bg-emerald-600 text-white" : ""}
                  >
                    {d.direction}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={d.strength === "strong" ? "default" : "secondary"}>{d.strength}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(d.pivot_1.ts)}</TableCell>
                <TableCell className="text-muted-foreground">{formatDate(d.pivot_2.ts)}</TableCell>
                <TableCell className="text-right font-mono text-foreground">
                  {d.price_at_signal.toFixed(2)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
