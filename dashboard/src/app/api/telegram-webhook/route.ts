import { NextResponse, type NextRequest } from "next/server";

// Telegram webhook: user sends any message (e.g. a pasted @cobraalerts post)
// to Axe's existing bot, this does brief AI research + a price chart via
// OpenAI + QuickChart, and replies in the same chat. Registered once via
// https://api.telegram.org/bot<TOKEN>/setWebhook?url=<DASHBOARD_URL>/api/telegram-webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>

const TELEGRAM_API = "https://api.telegram.org";
const OPENAI_MODEL = "gpt-5-mini";

interface TelegramUpdate {
  message?: {
    chat: { id: number };
    text?: string;
  };
}

interface ResearchResult {
  ticker: string | null;
  summary: string;
  strike: number | null;
  expiration: string | null;
}

async function callOpenAI(text: string): Promise<ResearchResult> {
  const prompt = `A user sent this message (likely a trade idea or a mention of a stock/crypto ticker) to a market research bot:

"""
${text}
"""

Research it briefly using web search: identify the ticker/company if any, current price, and any relevant near-term catalyst (earnings date, news). If the message includes options details (strike price, expiration date), extract them.

Write the summary in natural, professional Spanish (2-4 sentences), analytical in tone -- never phrase anything as an instruction to buy or sell. Keep numbers/tickers/dates as-is.

Return your final answer as a single JSON code block at the very end, matching exactly:
\`\`\`json
{"ticker": "TICKER or null", "summary": "...", "strike": number or null, "expiration": "YYYY-MM-DD or null"}
\`\`\``;

  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: OPENAI_MODEL,
      tools: [{ type: "web_search" }],
      input: prompt,
    }),
  });

  if (!response.ok) {
    throw new Error(`OpenAI request failed: ${response.status} ${await response.text()}`);
  }

  const data = await response.json();
  const messageItem = (data.output ?? []).find((item: { type: string }) => item.type === "message");
  const outputText: string = messageItem?.content?.[0]?.text ?? "";

  const match = outputText.match(/```json\s*(\{[\s\S]*?\})\s*```/);
  if (!match) {
    return { ticker: null, summary: outputText.slice(0, 800) || "No se pudo generar un analisis.", strike: null, expiration: null };
  }
  const parsed = JSON.parse(match[1]);
  return {
    ticker: parsed.ticker ?? null,
    summary: parsed.summary ?? "",
    strike: parsed.strike ?? null,
    expiration: parsed.expiration ?? null,
  };
}

async function buildChartUrl(ticker: string, strike: number | null, expiration: string | null): Promise<string | null> {
  try {
    const yahooResponse = await fetch(
      `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?range=6mo&interval=1d`,
    );
    if (!yahooResponse.ok) return null;
    const yahooData = await yahooResponse.json();
    const result = yahooData?.chart?.result?.[0];
    const timestamps: number[] = result?.timestamp ?? [];
    const closes: number[] = result?.indicators?.quote?.[0]?.close ?? [];
    if (timestamps.length === 0 || closes.length === 0) return null;

    const labels = timestamps.map((ts) => new Date(ts * 1000).toISOString().slice(0, 10));
    const datasets: Record<string, unknown>[] = [
      { label: ticker, data: closes, borderColor: "#1f77b4", fill: false, pointRadius: 0 },
    ];
    if (strike) {
      datasets.push({
        label: `Strike $${strike}`,
        data: labels.map(() => strike),
        borderColor: "#d62728",
        borderDash: [6, 4],
        fill: false,
        pointRadius: 0,
      });
    }

    const chartConfig = {
      type: "line",
      data: { labels, datasets },
      options: {
        title: { display: true, text: `${ticker}${expiration ? ` - exp. ${expiration}` : ""}` },
        scales: { xAxes: [{ ticks: { maxTicksLimit: 8 } }] },
      },
    };

    const createResponse = await fetch("https://quickchart.io/chart/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chart: chartConfig, width: 800, height: 450, backgroundColor: "white" }),
    });
    if (!createResponse.ok) return null;
    const createData = await createResponse.json();
    return createData.url ?? null;
  } catch {
    return null;
  }
}

async function sendTelegramMessage(text: string): Promise<void> {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  await fetch(`${TELEGRAM_API}/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "HTML", disable_web_page_preview: true }),
  });
}

async function sendTelegramPhoto(photoUrl: string, caption: string): Promise<void> {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  await fetch(`${TELEGRAM_API}/bot${token}/sendPhoto`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, photo: photoUrl, caption }),
  });
}

export async function POST(request: NextRequest) {
  const secretHeader = request.headers.get("x-telegram-bot-api-secret-token");
  if (!secretHeader || secretHeader !== process.env.TELEGRAM_WEBHOOK_SECRET) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const update: TelegramUpdate = await request.json();
  const message = update.message;
  if (!message?.text || String(message.chat.id) !== process.env.TELEGRAM_CHAT_ID) {
    return NextResponse.json({ ok: true }); // ignore anything not from the owner's chat
  }

  try {
    const research = await callOpenAI(message.text);
    await sendTelegramMessage(`<b>Analisis</b>\n\n${research.summary}`);

    if (research.ticker) {
      const chartUrl = await buildChartUrl(research.ticker, research.strike, research.expiration);
      if (chartUrl) {
        await sendTelegramPhoto(chartUrl, research.ticker);
      }
    }
  } catch (error) {
    await sendTelegramMessage(`No pude completar el analisis: ${error instanceof Error ? error.message : "error desconocido"}`);
  }

  return NextResponse.json({ ok: true });
}
