"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  LineSeries,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import type { DivergenceWithPivots, PriceBar, Pivot } from "@/lib/types";

function toUnixSeconds(ts: string): UTCTimestamp {
  return Math.floor(new Date(ts).getTime() / 1000) as UTCTimestamp;
}

export function PriceRsiChart({
  bars,
  pivots,
  divergence,
}: {
  bars: PriceBar[];
  pivots: Pivot[];
  divergence: DivergenceWithPivots | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || bars.length === 0) return;

    const chart = createChart(container, {
      layout: { background: { color: "transparent" }, textColor: "#a1a1aa" },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.06)" },
        horzLines: { color: "rgba(255,255,255,0.06)" },
      },
      width: container.clientWidth,
      height: 440,
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    chartRef.current = chart;

    const priceSeries = chart.addSeries(
      CandlestickSeries,
      {
        upColor: "#16a34a",
        downColor: "#dc2626",
        borderVisible: false,
        wickUpColor: "#16a34a",
        wickDownColor: "#dc2626",
      },
      0,
    );
    priceSeries.setData(
      bars.map((b) => ({
        time: toUnixSeconds(b.ts),
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );

    const rsiSeries = chart.addSeries(LineSeries, { color: "#818cf8", lineWidth: 2 }, 1);
    rsiSeries.setData(
      bars.filter((b) => b.rsi !== null).map((b) => ({ time: toUnixSeconds(b.ts), value: b.rsi as number })),
    );
    rsiSeries.createPriceLine({
      price: 40,
      color: "#52525b",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "oversold",
    });
    rsiSeries.createPriceLine({
      price: 60,
      color: "#52525b",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "overbought",
    });

    const pane1 = chart.panes()[1];
    if (pane1) pane1.setHeight(140);

    const pivotMarkers: SeriesMarker<Time>[] = pivots.map((p) => ({
      time: toUnixSeconds(p.ts),
      position: p.kind === "high" ? "aboveBar" : "belowBar",
      color: p.kind === "high" ? "#a1a1aa" : "#a1a1aa",
      shape: p.kind === "high" ? "arrowDown" : "arrowUp",
      size: 0.6,
    }));

    if (divergence) {
      const highlight = new Set([divergence.pivot_1.id, divergence.pivot_2.id]);
      for (const marker of pivotMarkers) {
        const pivot = pivots.find((p) => toUnixSeconds(p.ts) === marker.time);
        if (pivot && highlight.has(pivot.id)) {
          marker.color = "#f97316";
          marker.size = 1.4;
        }
      }
    }
    createSeriesMarkers(priceSeries, pivotMarkers);

    if (divergence) {
      const lineSeries = chart.addSeries(LineSeries, { color: "#f97316", lineWidth: 2 }, 0);
      lineSeries.setData([
        { time: toUnixSeconds(divergence.pivot_1.ts), value: divergence.pivot_1.price_value },
        { time: toUnixSeconds(divergence.pivot_2.ts), value: divergence.pivot_2.price_value },
      ]);

      const rsiLineSeries = chart.addSeries(LineSeries, { color: "#f97316", lineWidth: 2 }, 1);
      rsiLineSeries.setData([
        { time: toUnixSeconds(divergence.pivot_1.ts), value: divergence.pivot_1.rsi_value },
        { time: toUnixSeconds(divergence.pivot_2.ts), value: divergence.pivot_2.rsi_value },
      ]);
    }

    const resizeObserver = new ResizeObserver(() => {
      if (container) chart.applyOptions({ width: container.clientWidth });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [bars, pivots, divergence]);

  return <div ref={containerRef} className="w-full rounded-lg border border-border p-2" />;
}
