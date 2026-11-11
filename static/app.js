const $ = (id) => document.getElementById(id);
const PAIRS = [
  ["EURUSD=X", "EUR / USD"], ["GBPUSD=X", "GBP / USD"], ["USDJPY=X", "USD / JPY"],
  ["AUDUSD=X", "AUD / USD"], ["USDCAD=X", "USD / CAD"], ["USDCHF=X", "USD / CHF"],
  ["NZDUSD=X", "NZD / USD"], ["EURGBP=X", "EUR / GBP"], ["EURJPY=X", "EUR / JPY"],
  ["GBPJPY=X", "GBP / JPY"], ["AUDJPY=X", "AUD / JPY"], ["EURCHF=X", "EUR / CHF"],
  ["EURNZD=X", "EUR / NZD"], ["GBPCAD=X", "GBP / CAD"],
];
const state = { ticker: "EURUSD=X", timeframe: "D1", market: null, chat: [], loading: false,
  chatLoading: false, marketRequest: 0, analysisRequest: 0, backtestRequest: 0 };
const toast = $("toast");
const TV_INTERVAL = { D1: "D", H4: "240", H1: "60", M15: "15" };
const CHAT_STORAGE_KEY = "fieldnote-fx-chat-v2";
const CHAT_HISTORY_LIMIT = 40;

async function fetchWithTimeout(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

function explainNetworkError(error, action) {
  if (error?.name === "AbortError") return `La demande ${action} a dépassé le délai autorisé. Réessaie.`;
  if (!navigator.onLine) return "Tu es hors ligne. Le brouillon est conservé; réessaie quand la connexion revient.";
  if (error instanceof TypeError) return `Connexion au service interrompue pendant ${action}. Réessaie.`;
  return error?.message || `Impossible de terminer ${action}. Réessaie.`;
}

function setChatStatus(message, mode = "ready") {
  const status = $("chat-status");
  if (!status) return;
  status.textContent = message;
  status.dataset.state = mode;
}

function applyTheme(theme, persist = true) {
  const next = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  const isDark = next === "dark";
  $("theme-toggle").setAttribute("aria-pressed", String(isDark));
  $("theme-toggle").setAttribute("aria-label", isDark ? "Activer le mode clair" : "Activer le mode sombre");
  $("theme-icon").textContent = isDark ? "☼" : "◐";
  $("theme-label").textContent = isDark ? "Mode clair" : "Mode sombre";
  if (persist) {
    try { sessionStorage.setItem("fieldnote-fx-theme", next); } catch { /* Private browsing can disable storage. */ }
  }
}

function renderTradingViewChart() {
  const requestId = (renderTradingViewChart.requestId || 0) + 1;
  renderTradingViewChart.requestId = requestId;
  const mount = $("tradingview-chart");
  const frame = $("chart-wrap");
  if (!mount || !frame) return;
  frame.classList.remove("tv-ready", "tv-error");
  mount.replaceChildren();
  $("tv-source-status").textContent = "Chargement du flux TradingView…";

  const container = document.createElement("div");
  container.className = "tradingview-widget-container";
  const widget = document.createElement("div");
  widget.className = "tradingview-widget-container__widget";
  const attribution = document.createElement("div");
  attribution.className = "tradingview-widget-copyright";
  const link = document.createElement("a");
  link.href = `https://www.tradingview.com/symbols/OANDA-${state.ticker.replace("=X", "")}/`;
  link.target = "_blank";
  link.rel = "noopener nofollow";
  link.textContent = "Ouvrir ce graphique sur TradingView";
  attribution.append(link, document.createTextNode(" · données forex via OANDA"));

  const script = document.createElement("script");
  script.type = "text/javascript";
  script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
  script.async = true;
  script.textContent = JSON.stringify({
    allow_symbol_change: false,
    calendar: false,
    details: false,
    hide_side_toolbar: true,
    hide_top_toolbar: false,
    hide_legend: false,
    hide_volume: true,
    hotlist: false,
    interval: TV_INTERVAL[state.timeframe] || "D",
    locale: "fr",
    save_image: false,
    style: "1",
    symbol: `OANDA:${state.ticker.replace("=X", "")}`,
    theme: "dark",
    timezone: "Etc/UTC",
    backgroundColor: "#172a22",
    gridColor: "rgba(182, 205, 188, 0.10)",
    withdateranges: true,
    // Keep the two stable overlays in TradingView; ADX is calculated locally
    // and shown with the other validated FX indicators above the chart.
    studies: ["STD;RSI", "STD;MACD"],
    autosize: true,
  });
  script.addEventListener("load", () => {
    if (renderTradingViewChart.requestId === requestId) {
      frame.classList.add("tv-ready");
      $("tv-source-status").textContent = "Graphique et études en direct · TradingView / OANDA";
    }
  }, { once: true });
  script.addEventListener("error", () => {
    if (renderTradingViewChart.requestId !== requestId) return;
    frame.classList.add("tv-error");
    $("tv-source-status").textContent = "Secours local · cours Yahoo Finance";
    notify("TradingView est momentanément indisponible. Le graphique local reste affiché.");
  }, { once: true });

  container.append(widget, attribution, script);
  mount.append(container);
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(notify.timer);
  notify.timer = window.setTimeout(() => toast.classList.remove("visible"), 4600);
}

function formatPrice(value, ticker = state.ticker) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const decimals = ticker.includes("JPY") ? 3 : 5;
  return new Intl.NumberFormat("fr-FR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
}

function displayValue(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? "—" : Number(value).toLocaleString("fr-FR", { maximumFractionDigits: digits });
}

function valueTone(value, neutral = false) {
  if (neutral || value == null) return "";
  return Number(value) > 0 ? "positive" : Number(value) < 0 ? "negative" : "";
}

function sma(values, period) {
  return values.map((_, index) => index + 1 < period ? null : values.slice(index + 1 - period, index + 1).reduce((a, b) => a + b, 0) / period);
}

function ema(values, period) {
  const result = Array(values.length).fill(null);
  if (values.length < period) return result;
  let current = values.slice(0, period).reduce((a, b) => a + b, 0) / period;
  result[period - 1] = current;
  const multiplier = 2 / (period + 1);
  for (let i = period; i < values.length; i += 1) {
    current = values[i] * multiplier + current * (1 - multiplier);
    result[i] = current;
  }
  return result;
}

function drawChart(market) {
  const bars = market.bars.slice(-120);
  const closes = bars.map((bar) => bar.close);
  const highs = bars.map((bar) => bar.high);
  const lows = bars.map((bar) => bar.low);
  const middle = sma(closes, 20);
  const variance = closes.map((_, index) => {
    if (index < 19) return null;
    const sample = closes.slice(index - 19, index + 1);
    const mean = middle[index];
    return Math.sqrt(sample.reduce((sum, value) => sum + (value - mean) ** 2, 0) / 20);
  });
  const upper = middle.map((value, index) => value == null ? null : value + 2 * variance[index]);
  const lower = middle.map((value, index) => value == null ? null : value - 2 * variance[index]);
  const moving = ema(closes, 21);
  const all = [...highs, ...lows, ...upper, ...lower, ...moving].filter(Number.isFinite);
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min || market.pip_size;
  const width = 840;
  const height = 280;
  const point = (value, index) => `${(index / (closes.length - 1) * width).toFixed(1)},${(height - (value - min) / range * (height - 20) - 10).toFixed(1)}`;
  const path = (values) => values.map((value, index) => value == null ? null : `${index ? "L" : "M"}${point(value, index)}`).filter(Boolean).join(" ");
  const makeArea = () => {
    const indices = upper.map((value, index) => value == null || lower[index] == null ? null : index).filter((index) => index != null);
    if (!indices.length) return "";
    return `${upper.slice(indices[0], indices.at(-1) + 1).map((value, offset) => ` ${offset ? "L" : "M"}${point(value, indices[0] + offset)}`).join("")}${lower.slice(indices[0], indices.at(-1) + 1).reverse().map((value, offset) => ` L${point(value, indices.at(-1) - offset)}`).join("")} Z`;
  };
  $("chart-line").setAttribute("d", path(closes));
  $("chart-ema").setAttribute("d", path(moving));
  $("chart-bb-upper").setAttribute("d", path(upper));
  $("chart-bb-lower").setAttribute("d", path(lower));
  $("chart-bb-area").setAttribute("d", makeArea());
  const candles = $("candle-layer");
  const fragment = document.createDocumentFragment();
  const step = width / Math.max(1, bars.length - 1);
  const bodyWidth = Math.min(5, Math.max(2.4, step * 0.62));
  bars.forEach((bar, index) => {
    const x = index * step;
    const rising = bar.close >= bar.open;
    const wick = document.createElementNS("http://www.w3.org/2000/svg", "line");
    wick.setAttribute("x1", x.toFixed(1));
    wick.setAttribute("x2", x.toFixed(1));
    wick.setAttribute("y1", point(bar.high, index).split(",")[1]);
    wick.setAttribute("y2", point(bar.low, index).split(",")[1]);
    wick.setAttribute("class", `candle-wick ${rising ? "candle-up" : "candle-down"}`);
    const body = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const openY = Number(point(bar.open, index).split(",")[1]);
    const closeY = Number(point(bar.close, index).split(",")[1]);
    body.setAttribute("x", (x - bodyWidth / 2).toFixed(1));
    body.setAttribute("y", Math.min(openY, closeY).toFixed(1));
    body.setAttribute("width", bodyWidth.toFixed(1));
    body.setAttribute("height", Math.max(1.4, Math.abs(closeY - openY)).toFixed(1));
    body.setAttribute("class", `candle-body ${rising ? "candle-up" : "candle-down"}`);
    fragment.append(wick, body);
  });
  candles.replaceChildren(fragment);
  const x = width;
  const y = height - ((closes.at(-1) - min) / range) * (height - 20) - 10;
  $("chart-last").setAttribute("cx", x);
  $("chart-last").setAttribute("cy", y);
  $("chart-price-label").textContent = formatPrice(closes.at(-1));
  $("chart-axis").innerHTML = `<span>${bars[0].date}</span><span>${market.source}</span><span>${bars.at(-1).date}</span>`;
}

const GROUPS = {
  "trend-indicators": [
    ["SMA · 20", "sma20", 5], ["SMA · 50", "sma50", 5], ["SMA · 200", "sma200", 5],
    ["EMA · 9", "ema9", 5], ["EMA · 21", "ema21", 5], ["EMA · 50", "ema50", 5],
    ["ADX · 14", "adx14"], ["DI positif · 14", "plus_di14"], ["DI négatif · 14", "minus_di14"],
    ["Ichimoku · Tenkan", "ichimoku_tenkan", 5], ["Ichimoku · Kijun", "ichimoku_kijun", 5],
  ],
  "momentum-indicators": [
    ["RSI · 14", "rsi14"], ["MACD · ligne", "macd", 5], ["MACD · signal", "macd_signal", 5],
    ["MACD · histogramme", "macd_histogram", 5], ["Stochastique · %K", "stochastic_k"],
    ["Stochastique · %D", "stochastic_d"], ["CCI · 20", "cci20"], ["Williams %R · 14", "williams_r14"],
  ],
  "volatility-indicators": [
    ["ATR · 14", "atr14", 5], ["ATR · pips", "atr_pips", 1], ["Bollinger · supérieure", "bollinger_upper", 5],
    ["Bollinger · moyenne", "bollinger_middle", 5], ["Bollinger · inférieure", "bollinger_lower", 5],
    ["Volatilité réalisée · 20", "realized_volatility20", 2],
  ],
  "levels-indicators": [
    ["Pivot journalier", "pivot", 5], ["Résistance · R1", "pivot_r1", 5], ["Résistance · R2", "pivot_r2", 5],
    ["Support · S1", "pivot_s1", 5], ["Support · S2", "pivot_s2", 5], ["Fibonacci · 23,6 %", "fib_236", 5],
    ["Fibonacci · 38,2 %", "fib_382", 5], ["Fibonacci · 50 %", "fib_500", 5],
    ["Fibonacci · 61,8 %", "fib_618", 5], ["Fibonacci · 78,6 %", "fib_786", 5],
    ["OBV · proxy de volume", "obv", 0],
  ],
};

function renderIndicators(indicators) {
  for (const [id, items] of Object.entries(GROUPS)) {
    $(id).innerHTML = items.map(([label, key, precision]) => {
      const value = indicators[key];
      const tone = ["macd_histogram", "cci20", "williams_r14"].includes(key) ? valueTone(value) : "";
      return `<div class="indicator-cell"><span class="indicator-name">${label}</span><span class="indicator-value ${tone}">${displayValue(value, precision ?? 2)}</span></div>`;
    }).join("");
  }
  $("quick-rsi").textContent = displayValue(indicators.rsi14, 1);
  $("quick-rsi-note").textContent = indicators.rsi14 == null ? "indisponible" : indicators.rsi14 >= 70 ? "zone haute · à contextualiser" : indicators.rsi14 <= 30 ? "zone basse · à contextualiser" : "indice de momentum";
  $("quick-atr").textContent = indicators.atr_pips == null ? "—" : `${displayValue(indicators.atr_pips, 1)} pips`;
  $("quick-adx").textContent = displayValue(indicators.adx14, 1);
  $("quick-macd").textContent = displayValue(indicators.macd_histogram, 5);
  $("quick-macd").className = valueTone(indicators.macd_histogram);
  $("volume-note").textContent = indicators.volume_note;
}

function renderMarket(market) {
  state.market = market;
  const activeRow = document.querySelector(`.pair-row[data-pair="${CSS.escape(market.ticker)}"] small`);
  if (activeRow) activeRow.textContent = formatPrice(market.price, market.ticker);
  $("pair-symbol").textContent = market.ticker;
  $("pair-title").innerHTML = `${market.pair.split(" / ")[0]} <span>/</span> ${market.pair.split(" / ")[1]}`;
  $("quote-date").textContent = `${market.timeframe} · ${market.as_of}`;
  $("price-value").textContent = formatPrice(market.price);
  const change = `${market.change_pips > 0 ? "+" : ""}${displayValue(market.change_pips, 1)} pips`;
  $("price-change").textContent = `${change} sur la dernière bougie`;
  $("price-change").className = `price-change ${valueTone(market.change_pips)}`;
  $("data-status").textContent = `Cartes et analyse : instantané Yahoo · ${market.as_of}`;
  $("chat-pair-context").textContent = `${market.pair} · ${market.timeframe}`;
  renderIndicators(market.indicators);
  drawChart(market);
}

function renderAgentTeam(team = {}) {
  const technical = team.technical;
  const technicalNode = document.querySelector('[data-agent="technical"]');
  if (technical) {
    const labels = { bullish: "Biais haussier", bearish: "Biais baissier", mixed: "Signaux mixtes" };
    const summary = document.createElement("strong");
    summary.textContent = `${labels[technical.bias] || "Lecture indisponible"} · score ${technical.score > 0 ? "+" : ""}${technical.score}`;
    const details = document.createElement("span");
    details.textContent = (technical.evidence || []).map((item) => item.reason).join(" ") || "Données techniques insuffisantes.";
    technicalNode.replaceChildren(summary, details);
  }
  const risk = team.risk;
  const riskNode = document.querySelector('[data-agent="risk"]');
  if (risk) {
    const summary = document.createElement("strong");
    summary.textContent = risk.atr_percent_of_price == null
      ? "ATR indisponible"
      : `ATR = ${displayValue(risk.atr_percent_of_price, 3)} % du prix`;
    const details = document.createElement("span");
    details.textContent = (risk.market_flags || []).slice(0, 2).join(" ");
    riskNode.replaceChildren(summary, details);
  }
  const sentimentNode = document.querySelector('[data-agent="sentiment"]');
  if (sentimentNode) {
    const labels = { bullish: "Ton haussier", bearish: "Ton baissier", mixed: "Ton partagé", unclear: "Ton indéterminé" };
    const summary = document.createElement("strong");
    summary.textContent = labels[team.sentiment?.sentiment] || "Analyse indisponible";
    const details = document.createElement("span");
    details.textContent = team.sentiment?.summary || team.sentiment?.reason || "Aucun sentiment calculé.";
    sentimentNode.replaceChildren(summary, details);
  }
  const headlineLinks = document.querySelector('[data-agent="headlines"]');
  if (headlineLinks) {
    headlineLinks.replaceChildren();
    for (const item of (team.news?.headlines || []).slice(0, 3)) {
      try {
        const url = new URL(item.url);
        if (url.protocol !== "https:") continue;
        const link = document.createElement("a");
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = `${item.publisher} · ${item.title}`;
        headlineLinks.append(link);
      } catch { /* Skip a malformed provider URL. */ }
    }
  }
  const macro = document.querySelector('[data-agent="macro"]');
  if (macro) {
    const rows = team.macro?.observations || [];
    const summary = rows.map((row) => row.value_percent == null
      ? `${row.currency} · donnée absente`
      : `${row.currency} ${displayValue(row.value_percent, 2)} % · ${row.observed_at}${row.status === "stale" ? " · ancienne" : ""}`);
    macro.textContent = summary.length ? summary.join("; ") : team.macro?.reason || "Séries indisponibles.";
  }
}

function renderAnalysis(analysis, agentTeam) {
  $("market-view").textContent = analysis.market_view || "—";
  $("bull-case").textContent = analysis.bull_case || "—";
  $("bear-case").textContent = analysis.bear_case || "—";
  $("risk-check").textContent = analysis.risk_check || "—";
  $("decision-title").textContent = analysis.decision || "Hold";
  $("decision-copy").textContent = `Confiance de formulation : ${analysis.confidence}% · ${analysis.model}. Ce score n’est pas une probabilité de réussite.`;
  $("confidence-value").textContent = `${analysis.confidence}%`;
  $("confidence-bar").style.width = `${analysis.confidence}%`;
  $("model-label").textContent = `${analysis.model} · ${state.timeframe}`;
  renderAgentTeam(agentTeam);
}

function renderBacktest(payload) {
  const result = payload.result;
  const metrics = result.out_of_sample;
  const baseline = result.buy_and_hold_baseline;
  $("backtest-source").textContent = `${payload.pair} · ${result.timeframe} · ${payload.as_of}`;
  $("backtest-summary").textContent = `${result.strategy} · ${result.split.test_bars} bougies de test sur ${result.split.method}. Spread simulé : ${displayValue(result.spread_assumption_pips, 1)} pips.`;
  $("bt-return").textContent = `${displayValue(metrics.total_return_pct, 2)} %`;
  $("bt-return").className = valueTone(metrics.total_return_pct);
  $("bt-drawdown").textContent = `${displayValue(metrics.max_drawdown_pct, 2)} %`;
  $("bt-sharpe").textContent = displayValue(metrics.annualized_sharpe, 2);
  $("bt-trades").textContent = String(result.trades);
  $("bt-baseline").textContent = `${displayValue(baseline.total_return_pct, 2)} %`;
  $("backtest-caveat").textContent = result.caveats.join(" ");
  $("backtest-result").hidden = false;
}

async function runBacktest() {
  const requestId = ++state.backtestRequest;
  const button = $("backtest-button");
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Calcul…";
  $("backtest-result").hidden = true;
  try {
    const response = await fetchWithTimeout("/api/backtest", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: state.ticker, timeframe: state.timeframe, fast_period: 10, slow_period: 30, spread_pips: 1.0 }),
    }, 30000);
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "Le backtest n’a pas abouti.");
    if (requestId !== state.backtestRequest || result.ticker !== state.ticker || result.result.timeframe !== state.timeframe) return;
    renderBacktest(result);
  } catch (error) {
    if (requestId === state.backtestRequest) notify(explainNetworkError(error, "le backtest"));
  } finally {
    if (requestId === state.backtestRequest) {
      button.disabled = false;
      button.textContent = label;
    }
  }
}

async function checkService() {
  try {
    const response = await fetchWithTimeout("/api/health", {}, 8000);
    const health = await response.json();
    $("server-label").textContent = health.provider_configured ? "Desk IA prêt" : "Clé API à configurer";
    document.querySelector(".server-state").classList.toggle("ready", health.provider_configured);
    if (health.provider_configured) setChatStatus("IA prête · Groq", "ready");
    else setChatStatus("IA non configurée", "error");
  } catch (error) {
    $("server-label").textContent = "Service indisponible";
    setChatStatus(explainNetworkError(error, "la connexion"), "error");
  }
}

function setActivePair() {
  document.querySelectorAll(".pair-row").forEach((row) => row.classList.toggle("active", row.dataset.pair === state.ticker));
}

async function loadMarket() {
  const requestId = ++state.marketRequest;
  state.timeframe = $("timeframe").value;
  $("quote-date").textContent = "Récupération des cotations…";
  $("market-summary").setAttribute("aria-busy", "true");
  $("market-summary").classList.add("is-loading");
  $("chart-line").classList.add("loading-state");
  try {
    const response = await fetchWithTimeout(`/api/market/${encodeURIComponent(state.ticker)}?timeframe=${encodeURIComponent(state.timeframe)}`, {}, 30000);
    const market = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(market.detail || "Cours momentanément indisponibles.");
    if (requestId !== state.marketRequest) return;
    renderMarket(market);
    $("model-label").textContent = "Indicateurs calculés · lecture IA en attente";
  } catch (error) {
    if (requestId !== state.marketRequest) return;
    $("quote-date").textContent = "Cotation indisponible";
    $("price-value").textContent = "—";
    $("price-change").textContent = explainNetworkError(error, "la récupération des cours");
    $("model-label").textContent = "Données indisponibles";
    renderIndicators({ volume_note: "Les indicateurs réapparaîtront dès que les cotations seront de nouveau accessibles." });
    notify(explainNetworkError(error, "la récupération des cours"));
  } finally {
    if (requestId === state.marketRequest) {
      $("market-summary").removeAttribute("aria-busy");
      $("market-summary").classList.remove("is-loading");
      $("chart-line").classList.remove("loading-state");
    }
  }
}

async function runAnalysis() {
  if (state.loading) return;
  const ticker = state.ticker;
  const timeframe = state.timeframe;
  const requestId = ++state.analysisRequest;
  state.loading = true;
  const button = $("analyze-button");
  button.disabled = true;
  button.querySelector("span:first-child").textContent = "Lecture…";
  $("analysis-grid").classList.add("loading");
  $("model-label").textContent = "Analyse de la structure, du momentum et du risque…";
  try {
    const response = await fetchWithTimeout("/api/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker, timeframe, question: "" }),
    }, 150000);
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "L’analyse n’a pas abouti.");
    if (requestId !== state.analysisRequest || ticker !== state.ticker || timeframe !== $("timeframe").value) {
      notify("L’analyse est terminée pour l’ancienne sélection; relance-la pour la paire affichée.");
      return;
    }
    renderMarket(result.market);
    renderAnalysis(result.analysis, result.agent_team);
  } catch (error) {
    if (requestId !== state.analysisRequest) return;
    $("model-label").textContent = "Analyse non terminée";
    notify(explainNetworkError(error, "l’analyse IA"));
  } finally {
    if (requestId === state.analysisRequest) {
      state.loading = false;
      button.disabled = false;
      button.querySelector("span:first-child").textContent = "Lire le marché";
      $("analysis-grid").classList.remove("loading");
    }
  }
}

function persistChat() {
  try { sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(state.chat.slice(-CHAT_HISTORY_LIMIT))); }
  catch { setChatStatus("Historique limité à cet onglet", "warning"); }
}

function scrollChatToLatest() {
  const log = $("chat-messages");
  log.scrollTop = log.scrollHeight;
}

function appendMessage(role, content, options = {}) {
  const message = document.createElement("article");
  message.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}${options.error ? " message-error" : ""}`;
  message.dataset.messageId = options.id || "";
  const author = document.createElement("span");
  author.className = "message-author";
  author.textContent = role === "user" ? "TOI" : "FIELDNOTE · FX";
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  message.append(author);
  if (options.context) {
    const context = document.createElement("span");
    context.className = "message-context";
    context.textContent = options.context;
    message.append(context);
  }
  message.append(paragraph);
  if (Array.isArray(options.sources) && options.sources.length) {
    const sources = document.createElement("nav");
    sources.className = "message-sources";
    sources.setAttribute("aria-label", "Sources pédagogiques citées");
    for (const source of options.sources.slice(0, 5)) {
      try {
        const url = new URL(source.url);
        if (url.protocol !== "https:") continue;
        const link = document.createElement("a");
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = source.title;
        sources.append(link);
      } catch { /* Skip malformed persisted or provider URLs. */ }
    }
    if (sources.childElementCount) message.append(sources);
  }
  if (options.requestId) {
    const reference = document.createElement("small");
    reference.className = "message-reference";
    reference.textContent = `Référence : ${options.requestId}`;
    message.append(reference);
  }
  if (options.retryId) {
    const retry = document.createElement("button");
    retry.className = "retry-message";
    retry.type = "button";
    retry.textContent = "Réessayer";
    retry.setAttribute("aria-label", "Réessayer l’envoi de ce message");
    retry.addEventListener("click", () => sendChat(content, {
      retryId: options.retryId, errorNode: message,
      ticker: options.ticker, timeframe: options.timeframe, context: options.context,
    }));
    message.append(retry);
  }
  $("chat-messages").append(message);
  while ($("chat-messages").children.length > CHAT_HISTORY_LIMIT + 4) {
    $("chat-messages").firstElementChild.remove();
  }
  scrollChatToLatest();
  return message;
}

function showTyping() {
  const indicator = document.createElement("div");
  indicator.className = "chat-message assistant-message typing-indicator";
  indicator.setAttribute("role", "status");
  indicator.setAttribute("aria-label", "Fieldnote rédige une réponse");
  indicator.innerHTML = '<span class="message-author">FIELDNOTE · FX</span><span class="typing-label">Analyse en cours</span><span class="typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>';
  $("chat-messages").append(indicator);
  $("chat-messages").setAttribute("aria-busy", "true");
  scrollChatToLatest();
  return indicator;
}

function restoreChat() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY) || "[]");
    if (!Array.isArray(saved)) return;
    state.chat = saved.filter((message) => message && ["user", "assistant"].includes(message.role)
      && typeof message.content === "string" && message.content.length <= 6000)
      .map((message) => ({ ...message, sources: Array.isArray(message.sources) ? message.sources.slice(0, 5)
        .filter((source) => source && typeof source.title === "string" && typeof source.url === "string"
          && source.url.startsWith("https://")) : [] }))
      .slice(-CHAT_HISTORY_LIMIT);
  } catch {
    state.chat = [];
  }
  if (!state.chat.length) return;
  $("chat-messages").replaceChildren();
  state.chat.forEach((message) => appendMessage(message.role, message.content, { id: message.id, context: message.context, sources: message.sources }));
  const last = state.chat.at(-1);
  if (last.role === "user") {
    appendMessage("assistant", "La dernière réponse n’a pas été reçue. Tu peux réessayer.", {
      error: true, retryId: last.id, ticker: last.ticker, timeframe: last.timeframe, context: last.context,
    });
    setChatStatus("Réponse interrompue · réessayer", "warning");
  } else {
    setChatStatus("Conversation restaurée pour cet onglet", "ready");
  }
}

function resetChat() {
  if (state.chatLoading) return;
  if (state.chat.length && !window.confirm("Démarrer une nouvelle conversation et effacer l’historique de cet onglet ?")) return;
  state.chat = [];
  try { sessionStorage.removeItem(CHAT_STORAGE_KEY); } catch { /* Session storage is optional. */ }
  $("chat-messages").replaceChildren();
  appendMessage("assistant", "Je peux expliquer les indicateurs affichés et leurs limites. Les cotations sont récupérées à la demande. Par quoi veux-tu commencer?");
  setChatStatus("Nouvelle conversation", "ready");
  $("chat-input").focus();
}

async function sendChat(text, options = {}) {
  if (state.chatLoading) return;
  const content = String(text || "").trim();
  if (!content || content.length > 1200) return;
  const restoreFocus = [$("chat-input"), $("chat-send")].includes(document.activeElement)
    || Boolean(options.fromSuggestion);
  const context = options.context || `${PAIRS.find(([ticker]) => ticker === state.ticker)?.[1] || state.ticker} · ${state.timeframe}`;
  let history;
  if (options.retryId) {
    const index = state.chat.findIndex((message) => message.id === options.retryId);
    if (index < 0) {
      setChatStatus("Ce message a quitté l’historique actif. Pose-le à nouveau.", "warning");
      return;
    }
    history = state.chat.slice(0, index + 1);
    options.errorNode?.remove();
  } else {
    const userMessage = {
      id: crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      role: "user", content, ticker: state.ticker, timeframe: state.timeframe, context,
    };
    state.chat.push(userMessage);
    state.chat = state.chat.slice(-CHAT_HISTORY_LIMIT);
    persistChat();
    appendMessage("user", content, { id: userMessage.id, context });
    history = state.chat;
    $("chat-input").value = "";
  }

  state.chatLoading = true;
  $("chat-send").disabled = true;
  $("chat-input").setAttribute("aria-disabled", "true");
  setChatStatus("Fieldnote prépare une réponse…", "loading");
  const typing = showTyping();
  const started = performance.now();
  try {
    if (!navigator.onLine) throw new Error("Tu es hors ligne. Ton message est conservé; réessaie quand la connexion revient.");
    const response = await fetchWithTimeout("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker: options.ticker || state.ticker,
        timeframe: options.timeframe || state.timeframe,
        messages: history.slice(-12).map(({ role, content: messageContent }) => ({ role, content: messageContent })),
      }),
    }, 100000);
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(result.detail || "Fieldnote n’a pas pu répondre.");
      error.requestId = result.request_id || response.headers.get("X-Request-ID");
      error.retryAfter = response.headers.get("Retry-After");
      throw error;
    }
    if (typeof result.answer !== "string" || result.answer.trim().length < 8) {
      throw new Error("La réponse reçue était vide. Réessaie avec une question plus précise.");
    }
    typing.remove();
    const assistantMessage = {
      id: crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      role: "assistant", content: result.answer.trim(), context,
      sources: Array.isArray(result.sources) ? result.sources.slice(0, 5) : [],
    };
    state.chat.push(assistantMessage);
    state.chat = state.chat.slice(-CHAT_HISTORY_LIMIT);
    persistChat();
    appendMessage("assistant", assistantMessage.content, { id: assistantMessage.id, context, sources: assistantMessage.sources });
    const seconds = ((performance.now() - started) / 1000).toFixed(1).replace(".", ",");
    setChatStatus(`Réponse reçue · ${seconds} s`, "ready");
  } catch (error) {
    typing.remove();
    const message = explainNetworkError(error, "la réponse de l’assistant");
    appendMessage("assistant", message, {
      error: true, retryId: options.retryId || state.chat.at(-1)?.id,
      ticker: options.ticker || state.ticker, timeframe: options.timeframe || state.timeframe,
      context, requestId: error.requestId,
    });
    setChatStatus(error.retryAfter ? `Limite atteinte · réessayer dans ${error.retryAfter} s` : "Connexion interrompue · réessayer", "error");
  } finally {
    state.chatLoading = false;
    $("chat-messages").setAttribute("aria-busy", "false");
    $("chat-send").disabled = false;
    $("chat-input").removeAttribute("aria-disabled");
    if (restoreFocus && [document.body, $("chat-input"), $("chat-send")].includes(document.activeElement)) $("chat-input").focus();
  }
}

document.querySelectorAll(".pair-row").forEach((row) => row.addEventListener("click", () => {
  state.ticker = row.dataset.pair;
  setActivePair();
  $("backtest-result").hidden = true;
  state.backtestRequest += 1;
  renderTradingViewChart();
  loadMarket();
}));
$("timeframe").addEventListener("change", () => {
  state.timeframe = $("timeframe").value;
  $("backtest-result").hidden = true;
  state.backtestRequest += 1;
  renderTradingViewChart();
  loadMarket();
});
$("analyze-button").addEventListener("click", runAnalysis);
$("backtest-button").addEventListener("click", runBacktest);
$("chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  sendChat($("chat-input").value);
});
$("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChat($("chat-input").value);
  }
});
document.querySelectorAll(".suggestion-chip").forEach((button) => button.addEventListener("click", () => sendChat(button.dataset.question, { fromSuggestion: true })));
$("theme-toggle").addEventListener("click", () => {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});
$("chat-reset").addEventListener("click", resetChat);
window.addEventListener("offline", () => {
  $("server-label").textContent = "Hors ligne";
  document.querySelector(".server-state").classList.remove("ready");
  setChatStatus("Hors ligne · ton historique de session est conservé", "error");
});
window.addEventListener("online", () => {
  $("server-label").textContent = "Reconnexion…";
  setChatStatus("Reconnexion au service…", "loading");
  checkService();
});
try { applyTheme(sessionStorage.getItem("fieldnote-fx-theme") || "light", false); }
catch { applyTheme("light", false); }
restoreChat();
checkService();
setActivePair();
renderTradingViewChart();
loadMarket();
