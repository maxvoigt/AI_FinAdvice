"""
Pre-generate ChatGPT advice for the AI arm (T3) of the Client experiment.

One "situation" = (source, pathID, cell, assetOrder) from advisees.csv. For every situation and every
advice period (0 and 5), the script sends exactly the prompt the live FP app sent to ChatGPT:
    - same English prompt text, model, reasoning effort, JSON schema and validation
    - options in the SAME display order the client will see (no remapping afterwards)
    - a price chart drawn like the oTree chart (x-axis from -10, observation band -10.5 to -0.5)
Then the AI codes its own advice onto the reason checkboxes (same chained call as in the FP app).

Results are appended to a cache file after every call, so the script can be stopped and re-run:
finished situations are skipped. At the end, ai_advice.csv is written for build_client_slots.py.

Usage (from the Clients folder, venv with openai installed, OPENAI_API_KEY set):
    python3 sharedData/generate_ai_advice.py --dry-run --limit 3   # build prompts + charts only, no API calls
    python3 sharedData/generate_ai_advice.py --limit 10            # small paid pilot
    python3 sharedData/generate_ai_advice.py                       # everything
"""
import argparse
import asyncio
import base64
import hashlib
import importlib.util
import io
import json
import os
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

# ---------------------------------------------------------------- settings
ADVISEES = '_static/clients/advisees.csv'
ASSET_PARAMS_FILE = '../FP/sharedData/assetParams.py'     # the calibration the FPs saw
CACHE_FILE = '_static/clients/ai_advice_cache.jsonl'
OUT_FILE = '_static/clients/ai_advice.csv'
CHART_DIR = '_static/clients/ai_charts'                     # PNGs sent to the API, for auditing

MODEL = 'gpt-5.4-mini'
ADVICE_PERIODS = [0, 5]
N_DRAWS = 1                  # independent draws per situation and period (>1 lets you measure AI randomness)
MAX_PARALLEL = 8             # simultaneous API calls
MAX_TRIES = 4                # retries per call (exponential back-off)
CALL_TIMEOUT_SEC = 180

NUM_PREVRROUNDS = 10         # price index 10 = period 0
FIRST_ROUND = -NUM_PREVRROUNDS
MAX_ROUNDS = 10
INVESTMENT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728']

spec = importlib.util.spec_from_file_location('assetParams', ASSET_PARAMS_FILE)
assetParams = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assetParams)


# ---------------------------------------------------------------- client description (= describe_client, English)
AGE_TEXT = {'Young': "between 18 and 34 years old", 'Mid': "between 35 and 54 years old", 'Old': "above 55 years old"}
RISK_TEXT = {
    'Low': "I am willing to take above average financial risks expecting to earn above-average returns",
    'Med': "I am willing to take average financial risks expecting to earn average returns",
    'High': "I am willing to take below average financial risks expecting to earn below-average returns",
}


# ---------------------------------------------------------------- chart (mirrors the Highcharts chart on invPage)
def price_max(prices_df):
    return (np.floor(prices_df.values.max() / 100) + 1.5) * 100


def render_chart(prices_df):
    x = [FIRST_ROUND + i for i in range(len(prices_df))]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100)
    ax.axvspan(FIRST_ROUND - 0.5, FIRST_ROUND + NUM_PREVRROUNDS - 0.5, color=(0.78, 0.78, 0.78, 0.3), zorder=0)
    for i, col in enumerate(prices_df.columns):
        ax.plot(x, prices_df[col].values, color=INVESTMENT_COLORS[i], marker='o', markersize=5, linewidth=1.5, label=col)
    ax.set_title('Prices of the investment options')
    ax.set_xlabel('Period')
    ax.set_ylabel('Price ($)')
    ax.set_xlim(FIRST_ROUND, MAX_ROUNDS)
    ax.set_xticks(range(FIRST_ROUND, MAX_ROUNDS + 1))
    ax.set_ylim(0, price_max(prices_df))
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=8)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def quick_compress(base64_str):
    img = Image.open(io.BytesIO(base64.b64decode(base64_str.split(',')[1])))
    img.thumbnail((512, 512))
    buf = io.BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=70)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- prompt (text copied verbatim from FP/InvestmentAdvice)
def generate_prompt(order, genderText, ageText, riskAversionText, prices, chart):
    assetDictionary = assetParams.assetDictionary
    assetParameters_list = [
        {
            'Price increase (%)': assetDictionary[i]['x_up'] * 100,
            'Price decrease (%)': assetDictionary[i]['x_down'] * 100,
            'Chance of price increase (%)': assetDictionary[i]['p_up'] * 100,  # display as percentage
        }
        for _, i in enumerate(order)
    ]
    assetParameters = pd.DataFrame(assetParameters_list)
    assetParameters.index = [f'Option {i}' for i in range(1, 6)]
    assetParameters_json = assetParameters.to_dict(orient="index")

    assetPrices_json = prices.to_dict(orient="list")

    # Display positions of the index asset (1) and the hedge (5), as stored in player.correlatedAssets
    correlatedAssets = sorted([order.index(1) + 1, order.index(5) + 1])
    corrCoeff = assetParams.correlationCoefficient

    prompt = f"""
        Your advisee is { genderText } and { ageText }.
        
        In addition, when asked "Which of the following statements comes closest to describing the amount of financial risk that you are willing to take when you save or make investments?"
        your advisee answered "{ riskAversionText }".

        Your advisee has five different investment options (Option 1 to Option 5). 
        Uninvested wealth does not earn any interest.
        
        In each period, the price of each option can either increase or decrease with a known probability.
        {json.dumps(assetParameters_json, indent=2)}

        The price changes of all investment options except for Options 
        { correlatedAssets[0] } and { correlatedAssets[1] } are independent of each other. 
        Options { correlatedAssets[0] } and { correlatedAssets[1] } are 
        correlated with a correlation coefficient of { corrCoeff }, 
        which means that the
        price of Option { correlatedAssets[0] } 
        tends to decrease when the price of Option { correlatedAssets[1] } increases,
        and vice versa.

        Moreover, all price changes are independent of previous periods. 
        Before the survey, a computer has 
        randomly determined the price changes for each period according to the 
        specific probabilities of each investment option. 
        This also means that the advisee's choices do not influence how prices change.

        All this information is known to you and your advisee.

        **Recent price history:**
        {json.dumps(assetPrices_json, indent=2)}

        Your advisee has also reviewed a chart of the price history (attached), and knows 
        the properties of the investment options.

        ---

        Based on this, write a brief, personalized recommendation for your advisee. 

        - **Allocation**: For each option, specify the recommended portfolio weight in percentage of total wealth. The remaining wealth is not invested. 
        - **Justification**: Please give a short explanation for your recommendation, mentioning the reasons you used to make your recommendation.

        """

    input_data = [
        {
            "role": "system",
            "content": "You are a certified financial advisor in Canada, meeting with an advisee for investment advice."
        },
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": quick_compress(chart)},
            ]
        }
    ]
    return input_data, prompt


# ---------------------------------------------------------------- API calls (= FP app: generate_text / generate_ai_reasons)
_INVESTMENT_ADVICE_JSON_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "allocation": {
            "type": "object", "additionalProperties": False,
            "properties": {**{f"Option {k}": {"$ref": "#/$defs/asset"} for k in range(1, 6)},
                           "Not invested": {"$ref": "#/$defs/not_invested"}},
            "required": [f"Option {k}" for k in range(1, 6)] + ["Not invested"],
        },
        "Justification": {"type": "string"},
    },
    "required": ["allocation", "Justification"],
    "$defs": {
        "asset": {"type": "object", "additionalProperties": False,
                  "properties": {"percentage": {"type": "number"}}, "required": ["percentage"]},
        "not_invested": {"type": "object", "additionalProperties": False,
                         "properties": {"percentage": {"type": "number"}}, "required": ["percentage"]},
    },
}
ALLOCATION_KEYS = [f'Option {k}' for k in range(1, 6)] + ['Not invested']

AI_REASON_FIELDS = ['ai_reason_risk', 'ai_reason_age', 'ai_reason_gender', 'ai_reason_divers', 'ai_reason_payoffs',
                    'ai_reason_skew', 'ai_reason_prices', 'ai_reason_experience', 'ai_reason_other']
AI_REASON_LABELS = {
    'ai_reason_risk': "The client's risk tolerance",
    'ai_reason_age': "The client's age / investment horizon",
    'ai_reason_gender': "The client's gender",
    'ai_reason_divers': "Diversification or hedging across the options",
    'ai_reason_payoffs': "The options' probabilities and payoffs",
    'ai_reason_skew': "Whether an option offers rare large gains or frequent small gains",
    'ai_reason_prices': "Recent price movements",
    'ai_reason_experience': "My professional experience or intuition",
    'ai_reason_other': "Other",
}
_AI_REASONS_JSON_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {**{f: {"type": "boolean"} for f in AI_REASON_FIELDS}, "other_text": {"type": "string"}},
    "required": AI_REASON_FIELDS + ["other_text"],
}


def validate_advice(advice):
    allocation, justification = advice.get('allocation'), advice.get('Justification')
    if not isinstance(allocation, dict) or set(allocation) != set(ALLOCATION_KEYS):
        raise ValueError('Advice has missing or unexpected allocation entries.')
    if not isinstance(justification, str) or not justification.strip():
        raise ValueError('Advice must contain a justification.')
    pct = [allocation[k].get('percentage') for k in ALLOCATION_KEYS]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or v > 100 for v in pct):
        raise ValueError('Percentages must be numbers between 0 and 100.')
    if abs(sum(pct) - 100) > 0.01:
        raise ValueError('Allocation percentages must total 100.')
    return advice


def reasons_prompt(allocation, justification, chained):
    factor_lines = "\n".join(f"- {f}: {AI_REASON_LABELS[f]}" for f in AI_REASON_FIELDS)
    intro = ("Now code the recommendation you just wrote. Do not revise it." if chained else
             "Here is an already-written investment recommendation. Do not change it.")
    return f"""{intro}

**Allocation:**
{json.dumps(allocation, indent=2, ensure_ascii=False)}

**Justification:**
{justification}

Which of the following factors drove THIS recommendation? Select all that apply.

{factor_lines}

Instructions:
- Do not revise the allocation or the justification.
- At least one factor must be true.
- If Other (ai_reason_other) is true, put a brief phrase in other_text. Otherwise leave other_text empty.
"""


async def call_advice(client, input_data):
    response = await client.responses.create(
        model=MODEL, input=input_data, max_output_tokens=6000, reasoning={"effort": "medium"},
        text={"format": {"type": "json_schema", "name": "investment_advice", "schema": _INVESTMENT_ADVICE_JSON_SCHEMA}},
    )
    return validate_advice(json.loads(response.output_text)), response.id


async def call_reasons(client, advice, previous_response_id):
    chained = bool(previous_response_id)
    text = reasons_prompt(advice['allocation'], advice['Justification'], chained)
    prompt = ([{"role": "user", "content": text}] if chained else
              [{"role": "system", "content": "You are coding an already-written investment recommendation onto a fixed "
                                             "set of factors. Do not revise the recommendation."},
               {"role": "user", "content": text}])
    kwargs = dict(model=MODEL, input=prompt, max_output_tokens=800, reasoning={"effort": "low"},
                  text={"format": {"type": "json_schema", "name": "ai_reasons", "schema": _AI_REASONS_JSON_SCHEMA}})
    if previous_response_id:
        kwargs['previous_response_id'] = previous_response_id
    response = await client.responses.create(**kwargs)
    return json.loads(response.output_text)


async def with_retries(fn, *args):
    for attempt in range(MAX_TRIES):
        try:
            return await asyncio.wait_for(fn(*args), timeout=CALL_TIMEOUT_SEC)
        except Exception as e:
            if attempt == MAX_TRIES - 1:
                raise
            await asyncio.sleep(2 ** attempt * 5)
            print(f'   retry {attempt + 1} after: {type(e).__name__}: {str(e)[:120]}')


# ---------------------------------------------------------------- situations
def parse_order(x):
    x = str(x).strip()
    return [int(i) for i in x.strip('()[]').split(',')]


def situation_key(source, path, cell, order):
    return f"{source}|{int(path)}|{int(cell)}|{''.join(map(str, order))}"


def build_tasks():
    adv = pd.read_csv(ADVISEES)
    tasks, seen = [], set()
    for _, r in adv.iterrows():
        order = parse_order(r['assetOrder'])
        skey = situation_key(r['source'], r['pathID'], r['customerID'], order)
        if skey in seen:
            continue
        seen.add(skey)
        series = [json.loads(r[f'path_asset{a}']) for a in order]          # Option k = asset type order[k-1]
        for period in ADVICE_PERIODS:
            upto = NUM_PREVRROUNDS + period + 1                             # prices of periods -10 .. period
            prices = pd.DataFrame({f'Option {k + 1}': series[k][:upto] for k in range(5)})
            prices.index.name = "Year"
            for draw in range(N_DRAWS):
                tasks.append(dict(
                    key=f'{skey}|{period}|{draw}', situation=skey, source=r['source'], pathID=int(r['pathID']),
                    customerID=int(r['customerID']), gender=r['gender'], age=r['age'], riskAversion=r['riskAversion'],
                    assetOrder=json.dumps(order), period=period, draw=draw, order=order, prices=prices))
    return tasks


def prepare(task):
    chart = render_chart(task['prices'])
    gender = 'female' if task['gender'] == 'F' else 'male'
    input_data, prompt = generate_prompt(task['order'], gender, AGE_TEXT[task['age']],
                                         RISK_TEXT[task['riskAversion']], task['prices'], chart)
    return chart, input_data, prompt


# ---------------------------------------------------------------- main
def load_cache():
    done = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            for line in f:
                rec = json.loads(line)
                done[rec['key']] = rec
    return done


async def run(tasks):
    from openai import AsyncOpenAI                       # only needed for real runs
    client = AsyncOpenAI(api_key=os.environ['OPENAI_API_KEY'])
    sem = asyncio.Semaphore(MAX_PARALLEL)
    lock = asyncio.Lock()
    n_done = 0

    async def one(task):
        nonlocal n_done
        async with sem:
            _, input_data, prompt = prepare(task)
            t0 = time.time()
            try:
                advice, response_id = await with_retries(call_advice, client, input_data)
                try:
                    reasons = await with_retries(call_reasons, client, advice, response_id)
                except Exception:
                    reasons = await with_retries(call_reasons, client, advice, None)
            except Exception as e:
                print(f"FAILED {task['key']}: {type(e).__name__}: {str(e)[:200]}  (will retry on next run)")
                return
            rec = {k: task[k] for k in ['key', 'situation', 'source', 'pathID', 'customerID', 'gender', 'age',
                                        'riskAversion', 'assetOrder', 'period', 'draw']}
            rec.update(advice=json.dumps(advice), reasons=json.dumps(reasons), response_id=response_id,
                       model=MODEL, seconds=round(time.time() - t0, 1),
                       prompt_sha1=hashlib.sha1(prompt.encode()).hexdigest(),
                       created_at=time.strftime('%Y-%m-%d %H:%M:%S'))
            async with lock:
                with open(CACHE_FILE, 'a') as f:
                    f.write(json.dumps(rec) + '\n')
                n_done += 1
                print(f'{n_done}/{len(tasks)}  {task["key"]}  ({rec["seconds"]}s)')

    await asyncio.gather(*(one(t) for t in tasks))


def write_output():
    done = load_cache()
    out = pd.DataFrame(done.values()).sort_values(['situation', 'period', 'draw'])
    out.to_csv(OUT_FILE, index=False)
    print(f'Wrote {OUT_FILE}: {len(out)} advice rows for {out["situation"].nunique()} situations')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='build prompts and charts only, no API calls')
    ap.add_argument('--limit', type=int, default=None, help='only the first N open tasks')
    args = ap.parse_args()

    tasks = build_tasks()
    done = load_cache()
    open_tasks = [t for t in tasks if t['key'] not in done][:args.limit]
    print(f'{len(tasks)} tasks in total, {len(done)} already in cache, {len(open_tasks)} to run now')

    if args.dry_run:
        os.makedirs(CHART_DIR, exist_ok=True)
        for t in open_tasks:
            chart, _, prompt = prepare(t)
            name = t['key'].replace('|', '_')
            with open(os.path.join(CHART_DIR, name + '.png'), 'wb') as f:
                f.write(base64.b64decode(chart.split(',')[1]))
            with open(os.path.join(CHART_DIR, name + '.txt'), 'w') as f:
                f.write(prompt)
        print(f'Dry run: wrote {len(open_tasks)} charts and prompts to {CHART_DIR}')
    else:
        asyncio.run(run(open_tasks))
        write_output()
