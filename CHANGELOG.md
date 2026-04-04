# Changelog

## 2026-04-02

### demographics_after — financialAdvice ranking list UX

- `demographics_after/financialAdvice.html`: Investment-strategy ranking uses bordered white rows, left grip handle (`cursor: grab`), muted helper text, and “Most important” / “Least important” labels; jQuery UI `sortable` uses `handle`, dashed placeholder, and hover shadow; ranking updates `#finAdvice_InvestmentStrategy_Ranking` on load and after each move (removed erroneous duplicate `name="ranking"` hidden input)

### demographics_after — chatbotSurvey usefulness radios

- `demographics_after/chatbotSurvey.html`: On `DOMContentLoaded`, each `input[name="genAI_usefulness"]` listens for `change` and calls `checkAllFields` so the Next button updates when usefulness is selected

### demographics_after — chatbot survey (single page)

- `demographics_after/__init__.py`: Added heard-of, per-tool usage frequency, `genai_work_q16`, conditional “why not at work” checkboxes + optional text, and work-task checkboxes; replaced `aiUsage` with `chatbotSurvey` and `error_message` validation (heard exclusivity, usage when heard, routing for q16 1/3 vs 2/4)
- `demographics_after/chatbotSurvey.html`: New template (aiLiteracy-style layout) with presentation-only JS to show/hide usage rows and why/work sections; optional `consumer_survey` intro paragraph; testing skip helper
- `demographics_after/aiUsage.html`: Removed (was duplicate demographics markup; superseded by `chatbotSurvey.html`)
- `settings.py`: `SESSION_CONFIG_DEFAULTS` includes optional `consumer_survey` (default `False`) for future copy variants

Run `otree resetdb` after pulling these model changes.

## 2026-04-10

### demographics_after — AI literacy Q10–Q12

- `demographics_after/__init__.py`: Completed `aiLit_2`–`aiLit_4` as `IntegerField` + `RadioSelectHorizontal` (same pattern as `aiLit_1`) for Q10–Q12; `aiLiteracy` `form_fields` includes all four items
- `demographics_after/aiLiteracy.html`: New page template rendering the four AI literacy fields in a single form

## 2026-04-09

### investmentGame — advice allocation table width

- `investmentGame/invPage.html`: Allocation table wrapped in a centered `max-width: 22rem` container so it does not span the full modal width

### investmentGame — advice allocation table (percentage only)

- `investmentGame/invPage.html`: Advice allocation table columns reduced to **Name** and **Share (%)** (no units / dollar columns)
- `investmentGame/__init__.py`: `create_structured_advice` aligned with JSON schema (`percentage` / optional `expected_return` only); `player.advice` stored with `json.dumps`; fixed `generate_prompt` call argument order; removed unused `prev_player` / `totalWealth` in advice branch

### investmentGame — advice table cash row label

- `investmentGame/invPage.html`: Risk-free allocation row shows **Not invested** (same wording as the main task table) instead of the model key e.g. Risk-free asset

### investmentGame — advice allocation table + live payload unwrap

- `investmentGame/invPage.html`: `#adviceAllocation` holds a Bootstrap table (name with `js_vars.investmentOptions` colors / gray for risk-free, Share %, Units, Amount); filled in `liveRecv` via `buildAdviceAllocationTable`; `liveRecv` unwraps oTree `{ id_in_group: payload }` before reading `type` (`portfolio` / `advice`)
- `investmentGame/__init__.py`: `create_structured_advice` tries `json.loads` first (API JSON string), then `ast.literal_eval` fallback

### investmentGame — Responses API structured output

- `investmentGame/__init__.py`: `generate_text` uses `text.format` with `type: json_schema` for `client.responses.create` (replacing invalid top-level `response_format`); shared `_INVESTMENT_ADVICE_JSON_SCHEMA`; returns `response.output_text` for `player.advice` / live payload

## 2026-04-02

### investmentGame — server-driven `portfolio` + `liveRecv`

- `investmentGame/__init__.py`: Added `inv_trade_prices`, `inv_portfolio_payload`, `inv_initial_portfolio_payload`; `invPage.js_vars` exposes `initialPortfolio` and `id_in_group`; `live_method` includes `portfolio` in the payload after `updatePortfolio`
- `investmentGame/invPage.html`: Global `liveRecv` dispatches to `window.invModuleApplyLivePayload` (default no-op until React mounts)
- `_static/js/invModule.js`: “New” column values (`lineValues`, `shares`, cash, totals) from `useState(livePortfolio)` seeded by `js_vars.initialPortfolio`; holdings state synced from server on each live response; removed client-side `portfolio` object construction

### investmentGame — no duplicate `liveSend` for debounced share / holdings

- `_static/js/invModule.js`: `lastLiveSentShareRef` / `lastLiveSentHoldingsRef` skip repeat sends (`NUMERIC_LIVE_SEND_EPS`); cleared on share/holdings `onFocus`; **blur** only flushes when a debounced timer was still pending; holdings flush mirrors shares (parsed `v` dedup + `sendHoldingsLive` only, no local `setHoldings` in flush)

### investmentGame — debounced holdings input + `setHoldings` live

- `_static/js/invModule.js`: Holdings typed field uses the same debounce / draft-string / blur-flush pattern as portfolio share; `flushSetHoldingsInput` matches `flushSetSharesInput`; `sendHoldingsLive` → `liveSend` (`setHoldings`); server clamps (Python)
- `investmentGame/__init__.py`: `live_method` handles `setHoldings`; `updatePortfolio` `set` branch clamps target holdings to budget (aligned with JS) and adjusts `riskFree`

### investmentGame — debounced portfolio-share input

- `_static/js/invModule.js`: Portfolio share `%` field uses debounce (400 ms) before `setShares` / `liveSend`; draft string state while focused; blur flushes only if a debounced send was still pending; Enter blurs the field (`LIVE_NUMERIC_INPUT_DEBOUNCE_MS` shared with holdings)

## 2026-04-04

### investmentGame — `invModule` exact holdings, 2dp display

- `_static/js/invModule.js`: Holdings stored as full-precision floats; `withClampedHolding` / `holdingsAfterTargetShare` use float caps (no integer rounding); new `HoldingsQtyInput` shows `formatNumber2` when blurred and raw `String(quantity)` while focused; line values still computed exactly, `formatNumber2` only in the UI; ± uses `HOLDINGS_NUDGE` (0.01); removed incorrect share→holdings formula and `console.log`

### investmentGame — `invModule` React state refactor

- `_static/js/invModule.js`: Portfolio “New” columns driven by `useState(holdings)` + `useMemo` for line values, shares, cash, and totals; pure helpers `withClampedHolding` / `holdingsAfterTargetShare` enforce budget `js_vars.newTotalValue`; `useEffect` syncs holdings into oTree `forminputs`; removed imperative `updateNewValues` / `stepHolding` / DOM hacks and the large HTML comment block

## 2026-04-03

### investmentGame — `invModule` parse money with commas

- `_static/js/invModule.js`: Added `parseMoneyFromInput`; `updateNewValues` reads `#riskFreeNewValue` with `.value` and parses values like `10,000.00` correctly

### investmentGame — Risk-free cash as formatted, editable text

- `_static/js/invModule.js`: “Not invested” **New** value column uses `type="text"` with `formatNumber2` on blur, raw numeric string on focus; `syncRiskFreeRowFromCash` updates option `newS` inputs, `#riskFreeNewShare`, and `#totalNewVal` / `#totalNewShare` from cash + holdings; `stepHolding` / `stepShare` call sync after updates

## 2026-04-01

### investmentGame — `invModule` stable input width

- `_templates/global/Page.html`: Scoped `.inv-module` rules — `table-layout: fixed`, fixed-width `.inv-input-group-wrap`, `!important` flex/width on `.inv-input-fixed`, hide `type=number` spinners
- `_static/js/invModule.js`: `inv-module` / `inv-module-table` / `inv-input-group-wrap` / `inv-input-fixed`; drop redundant flex from inline style

### investmentGame — `invModule` unified rows + `invPage` investment globals

- `_static/js/invModule.js`: Single `tbody` path for all options; holdings/share input groups always rendered; `disabled={!(pageStatus === 'New' && phase === 'Investment')}`; fixed React handlers/ids/names (`newS`, `ShareAdj`, `stepHolding`/`stepShare`); 100px-wide inputs; totals use `totalCurVal` / `totalNewVal` / `totalNewShare`
- `investmentGame/invPage.html`: Removed blanket jQuery `disabled=false` on investment rounds so React controls gating; added `highlightChangedCells`, `thisPrices`, and `totalWealth` for `updateNewValues` / `updateHoldingsFromShare`

### investmentGame — Chart series indexing on `invPage`

- `investmentGame/invPage.html`: `oldPrices` / `prevPrices` / `newPrices` are 0-based arrays from `investmentOptions.map`; chart init and `updateChart` now use `allPrices[s - 1]` and `newPrices[i]` so Alternative 5 (and all series) map to the correct data

### investmentGame — `InvModuleApp` wrapper + `invPage` root

- `_static/js/invModule.js`: Added `InvModuleApp` with `useState`/`useEffect`; registers `window.invModuleSetPageStatus` for non-React code; moved new-price highlight to `useEffect` and fixed `newPrice` cell ids / jQuery class toggles
- `investmentGame/invPage.html`: Single `createRoot` + `render(<InvModuleApp />)`; `updateAll` calls `invModuleSetPageStatus('New')` instead of re-creating a root

### investmentGame — `invModule` number formatting

- `_static/js/invModule.js`: Added `formatNumber2` using `toLocaleString('en-US', …)` so dollar/holding cells show thousands separators and two decimals; non-numeric placeholders (`-`, `—`) pass through

### investmentGame — `invModule` tbody JSX fix

- `_static/js/invModule.js`: Wrapped `"Old"` / non-`"Old"` table bodies in fragments; second branch maps `investmentOptions` like the first; added risk-free row with nine columns; `riskFreeAsset` read from `js_vars.riskFreeAsset[0]`; guard numeric formatting when `newPrice` / `newValue` are `"-"`

## 2026-03-30

### investmentGame — New portfolio share controls on `invPage`

- `investmentGame/__init__.py`: Each `options` row includes `currentShareNum`; `js_vars` adds `currentShareNums` for client sync after period updates
- `investmentGame/invPage.html`: Replaced static new-share cells with ± steppers and numeric share input; `updateHoldingsFromShare` / `stepShare` adjust holdings (other lines fixed) within total wealth; `updateNewValues` refreshes share fields and supports `skipHighlight` for init

## 2026-03-18

### welcome — Add Participation Rules Modal

- `welcome/welcomePage.html`: Added "View participation rules" button below the consent paragraph; added Bootstrap modal (`#participationRulesModal`) with an empty body for the rules text, a scrollable dialog, and a Close button

## 2026-03-06

### investmentGame — Gate "Okay" Button on Modal Completion + Persist Beliefs

- `investmentGame/__init__.py`: Added `beliefsPeriod1 = models.LongStringField(initial="{}")` to `Player`; extended `invPage.live_method` to handle `data['type'] == 'beliefs'` — stores the JSON payload string in `player.beliefsPeriod1` and returns early
- `investmentGame/invPage.html`: Added `disabled` attribute to `startInvestingModalOkBtn` and removed `data-bs-dismiss="modal"`; added `checkModalComplete()` function that enables the button only when all 5 return inputs and 5 risk selects are non-empty; attached `input`/`change` listeners to all 10 fields inside the `currentPeriod == 1` init block; added click handler that serialises beliefs to JSON, sends via `liveSend({type: 'beliefs', payload: ...})`, then manually hides the modal

### investmentGame — Compact Combined Table in `startInvestingModal`

- `investmentGame/invPage.html`: Replaced two separate card/table blocks (expected return + perceived risk) in `startInvestingModal` with a single 3-column table (Option | Expected return % | Perceived risk 1–7); updated modal title to "Period X — Before You Start"; preserved all input/select IDs

### investmentGame — Gain/Loss Column on `invPage` Portfolio Table

- `investmentGame/invPage.html`: Added "Gain / Loss ($)" column header to the portfolio table; added `<span id="gl{n}">` cells per asset row and `<span id="totalGL">` in tfoot; added `costBasis` JS state array; updated `buttonClick()` to record cost basis on holdings commit; updated `updateTableForPeriod()` to compute and render per-asset and total gain/loss with green/red coloring

### investmentGame — Portfolio Management Logic for `invPage`

**`investmentGame/__init__.py`**
- Added `C.INITIAL_WEALTH = 10000` to constants
- Added `'initialWealth': C.INITIAL_WEALTH` to `invPage.js_vars`
- Replaced `invPage.live_method`: now accepts a `{period, holdings}` dict instead of a bare integer; appends each holding value to the 5 `investmentOption{N}Holdings` JSON string fields when `holdings` is not `None`; computes `done = next_period > last_invest_period` and returns `{nextPeriod, done}` to the client

**`investmentGame/invPage.html`** — full rewrite
- Layout: full-width Highcharts price chart card on top; portfolio table card (flex-grow) + side panel card (280 px fixed) below
- Portfolio table: 5 rows (colored option badge, Current Price, Holdings, Portfolio Value, New Holdings input, New Value) + dark Total footer; inputs are disabled during observation periods
- Side panel: period heading with Observation/Investment badge, description text, wealth summary (Total Wealth / Invested / Cash Remaining + progress bar), budget-exceeded alert, action button
- JS state: `holdings`, `cash`, `currentPrices`, `totalWealth` tracked client-side across periods
- `updateTableForPeriod(period)` — recomputes total wealth (`cash + Σ holdings·prices`) on every period change
- `updateNewValues()` — fires on every input event; updates New Value cells, Invested/Cash Remaining, progress bar; disables button and shows alert when over budget
- `buttonClick()` — for investment periods validates budget, commits `holdings`/`cash`, sends `{period, holdings: [...]}` via `liveSend`; for observation periods sends `{period, holdings: null}`
- `liveRecv(data)` — submits oTree form when `data.done`; otherwise advances period and re-enables button
- Highcharts plotBand shades observation phase (−9.5 → 0.5) with "Observation" label

## 2026-03-19

### demographics — Restore income-choice after errors

- `demographics_before/demographicsPage.html`: Render the real `income_choice` field (hidden) and sync it with the UI checkbox, so the selection survives oTree validation errors/reloads

- `demographics_before/demographicsPage.html`: Update JS syncing logic to treat `income_choice` as a BooleanField (checked => prefer not to say)
- `demographics_before/__init__.py`: Fix `error_message()` validation logic for boolean `income_choice` and handle `0` as a valid bracket value

## 2026-03-23

### investmentGame — Capture Highcharts SVG without exporting module

- `investmentGame/invPage.html`: Removed the CDN `exporting.js` dependency (403) and updated `captureChart()` to serialize the SVG from the DOM instead of calling `chart.getSVG()`
- `investmentGame/invPage.html`: Render the copied chart image in the beliefs modal as a smaller preview (`max-width: 70%`) while keeping aspect ratio
- `investmentGame/invPage.html`: Refactored the beliefs modal layout with clearer introductory text, prediction fields first, and a collapsed "Show price chart (optional)" section so the chart is explicitly optional
- `investmentGame/invPage.html`: Added collapse event handlers so the chart toggle button text switches between "Show price chart" and "Hide price chart"
