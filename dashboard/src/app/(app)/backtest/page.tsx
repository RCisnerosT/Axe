import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MOCK_TRADES, mockSummary } from "./mock-data";

export default function BacktestPage() {
  const summary = mockSummary(MOCK_TRADES);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Backtest results</h1>
        <p className="text-sm text-muted-foreground">
          Mock data — scanner/backtest.py hasn&apos;t been built yet. No slippage/commissions modeled once real.
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
            {summary.avgReturn.toFixed(1)}%
          </CardContent>
        </Card>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticker</TableHead>
              <TableHead>Timeframe</TableHead>
              <TableHead>Direction</TableHead>
              <TableHead>Entry</TableHead>
              <TableHead>Exit</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead className="text-right">Return</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {MOCK_TRADES.map((t, i) => (
              <TableRow key={i}>
                <TableCell className="font-medium text-foreground">{t.ticker}</TableCell>
                <TableCell className="text-muted-foreground">{t.timeframe}</TableCell>
                <TableCell>
                  <Badge
                    variant={t.direction === "bullish" ? "default" : "destructive"}
                    className={t.direction === "bullish" ? "bg-emerald-600 text-white" : ""}
                  >
                    {t.direction}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{t.entryDate}</TableCell>
                <TableCell className="text-muted-foreground">{t.exitDate ?? "—"}</TableCell>
                <TableCell className="text-muted-foreground">{t.exitReason}</TableCell>
                <TableCell
                  className={`text-right font-mono ${
                    t.returnPct === null ? "text-muted-foreground" : t.returnPct >= 0 ? "text-emerald-500" : "text-destructive"
                  }`}
                >
                  {t.returnPct === null ? "open" : `${t.returnPct >= 0 ? "+" : ""}${t.returnPct.toFixed(1)}%`}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
