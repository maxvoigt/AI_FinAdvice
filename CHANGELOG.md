# Changelog

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
