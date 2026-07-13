import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getSupabaseClient } from "@/lib/supabase";
import type { BacktestResult } from "@/lib/types";

export const dynamic = "force-dynamic";

const ET = "America/New_York";
const PAGE_SIZE = 1000;
const TABLE_ROW_LIMIT = 200;

function formatDate(ts: string) {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "2-digit", timeZone: ET });
}

async function getAllBacktestResults(): Promise<BacktestResult[]> {
  const supabase = getSupabaseClient();
  const all: BacktestResult[] = [];
  let page = 0;

  while (true) {
    const { data, error } = await supabase
      .from("backtest_results")
      .select("*")
      .order("entry_ts", { ascending: false })
      .range(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE - 1);

    if (error) throw error;
    if (!data || data.length === 0) break;
    all.push(...(data as BacktestResult[]));
    if (data.length < PAGE_SIZE) break;
    page += 1;
  }

  return all;
}

function summarize(trades: BacktestResult[]) {
  const closed = trades.filter((t) => t.return_pct !== null);
  const wins = closed.filter((t) => (t.return_pct as number) > 0);
  const winRate = closed.length ? (wins.length / closed.length) * 100 : 0;
  const avgReturn = closed.length
    ? closed.reduce((sum, t) => sum + (t.return_pct as number), 0) / closed.length
    : 0;
  return { totalTrades: trades.length, closedTrades: closed.length, winRate, avgReturn };
}

export default async function BacktestPage() {
  const trades = await getAllBacktestResults();
  const summary = summarize(trades);
  const shown = trades.slice(0, TABLE_ROW_LIMIT);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Backtest results</h1>
        <p className="text-sm text-muted-foreground">
          No slippage/commissions modeled — real-world results will be worse. Showing the {shown.length} most
          recent of {summary.totalTrades} trades.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal text-muted-foreground">Trades</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-foreground">{summary.totalTrades}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal text-muted-foreground">Closed</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-foreground">{summary.closedTrades}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal text-muted-foreground">Win rate</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-foreground">{summary.winRate.toFixed(0)}%</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-normal text-muted-foreground">Avg return</CardTitle>
          </CardHeader>
          <CardContent
            className={`text-2xl font-semibold ${summary.avgReturn >= 0 ? "text-emerald-500" : "text-destructive"}`}
          >
            {summary.avgReturn >= 0 ? "+" : ""}
            {summary.avgReturn.toFixed(2)}%
          </CardContent>
        </Card>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticker</TableHead>
              <TableHead>Timeframe</TableHead>
              <TableHead>Session</TableHead>
              <TableHead>Direction</TableHead>
              <TableHead>Entry</TableHead>
              <TableHead>Exit</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead className="text-right">Return</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((t) => (
              <TableRow key={t.id}>
                <TableCell className="font-medium text-foreground">{t.ticker}</TableCell>
                <TableCell className="text-muted-foreground">{t.timeframe}</TableCell>
                <TableCell className="text-muted-foreground">
                  {t.session_scope === "extended" ? "incl. pre/post" : "regular"}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={t.direction === "bullish" ? "default" : "destructive"}
                    className={t.direction === "bullish" ? "bg-emerald-600 text-white" : ""}
                  >
                    {t.direction}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(t.entry_ts)}</TableCell>
                <TableCell className="text-muted-foreground">{t.exit_ts ? formatDate(t.exit_ts) : "—"}</TableCell>
                <TableCell className="text-muted-foreground">{t.exit_reason}</TableCell>
                <TableCell
                  className={`text-right font-mono ${
                    t.return_pct === null
                      ? "text-muted-foreground"
                      : t.return_pct >= 0
                        ? "text-emerald-500"
                        : "text-destructive"
                  }`}
                >
                  {t.return_pct === null ? "open" : `${t.return_pct >= 0 ? "+" : ""}${t.return_pct.toFixed(1)}%`}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
