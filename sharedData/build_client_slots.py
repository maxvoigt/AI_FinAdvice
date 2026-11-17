"""
Build the pre-generated slot table for the Client experiment.

Design (one block per FP advice record):
    Each FP advice record r (advisor, path, client cell, asset order, FP arm) defines a block.
    A block contains:
        FP_CLIENTS_PER_RECORD clients who see the FP's advice  (arm 1 = FP without AI, arm 2 = FP with AI)
        1 client with no advice                                 (arm 0, "T0 twin")
        1 client with AI advice for exactly this situation      (arm 3, "T3 twin")
    All clients in a block see the same prices, the same asset order and are in the same cell
    (gender x age x risk tolerance) as the FP's hypothetical client.

Outputs (in OUT_DIR):
    client_slots.csv   one row per client slot  -> read by the oTree app
    (AI advice for the T3 twins comes from generate_ai_advice.py -> ai_advice.csv)
    client_blocks.csv  one row per block        -> analysis only (counterfactual advice for every arm,
                                                   wealth from following each advice)

Run from the Clients folder:
    python3 sharedData/build_client_slots.py
"""
import ast
import json
import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- settings
SEED = 20261117
ADVISEES = '_static/clients/advisees.csv'

##### NOTE: NEVER USE MASTER IN LIVE DATA!
AI_SOURCE = 'master'               # 'generated' = ai_advice.csv from generate_ai_advice.py
                                       # 'master'    = old genAdvice columns of the FP master tables
AI_ADVICE = '_static/clients/ai_advice.csv'
AI_DRAW = 0                            # which draw to show if generate_ai_advice.py made several per situation
USE_ADVICE_SEEN_BY_FP = True           # T3 twin of a T2 record gets the advice that FP saw (needs aiSeen_* columns)
MASTER_TABLES = {                      # only used if AI_SOURCE == 'master'
    'field': '../FP/_static/fp/fp_master_table.csv',
    'prolific': '../FP/_static/fp/fp_master_table_Prolific.csv',
}
OUT_DIR = '_static/clients'

FP_CLIENTS_PER_RECORD = 2              # clients who see the same FP advice record
BALANCE_WITHIN_CELL = True             # replicate records so both FP arms have equal counts in every cell
ADVICE_PERIODS = {'d1': 0, 'd2': 5}    # advice decision -> period (key used in the master table)
FIRST_INVEST_INDEX = 10                # price index of period 0 (indices 0..20 = periods -10..10)
INITIAL_WEALTH = 10000
FACTORS = ['risk', 'age', 'gender', 'divers', 'payoffs', 'skew', 'prices', 'experience', 'other']  # shown factors (no 'ai'; 'other' without its text)

ARM_LABELS = {0: 'none', 1: 'fp', 2: 'fp_ai', 3: 'ai'}


# ---------------------------------------------------------------- helpers
def parse_order(x):
    """'(5, 4, 1, 2, 3)', '5,4,1,2,3' or a list -> [5, 4, 1, 2, 3] (asset type shown as Option 1..5)."""
    if isinstance(x, (list, tuple)):
        return [int(i) for i in x]
    x = str(x).strip()
    if x[0] in '([':
        return [int(i) for i in ast.literal_eval(x)]
    return [int(i) for i in x.split(',')]


def fp_weights(row, d, order):
    """FP advice: w_asset{type}_{d} -> [Option 1..5, cash] in the display order of this record."""
    w = [float(row[f'w_asset{a}_{d}']) for a in order] + [float(row[f'w_cash_{d}'])]
    return check_weights(w, f"FP {row['advisorID']} {d}")


def ai_weights(advice_json):
    """AI advice JSON (keys 'Option k' = display position k, 'Not invested') -> [Option 1..5, cash]."""
    adv = json.loads(advice_json) if isinstance(advice_json, str) else advice_json
    al = adv['allocation']
    w = [float(al[f'Option {k}']['percentage']) for k in range(1, 6)] + [float(al['Not invested']['percentage'])]
    return check_weights(w, 'AI advice'), adv.get('Justification', '')


def check_weights(w, what):
    if abs(sum(w) - 100) > 0.5 or min(w) < 0:
        raise ValueError(f'{what}: weights {w} do not sum to 100')
    return w


def fp_factors(row, d):
    return [f for f in FACTORS if row.get(f'reason_{f}_{d}') == 1]


def ai_factors(reasons_json):
    if not isinstance(reasons_json, str) or not reasons_json.strip():
        return []
    r = json.loads(reasons_json)
    return [f for f in FACTORS if r.get(f'ai_reason_{f}')]


def follow_wealth(prices, w_d1, w_d2):
    """Wealth at the end if the client holds the advised weights, rebalanced every period
    (same rule the FPs were told): d1 weights in periods 0-4, d2 weights in periods 5-9."""
    W = INITIAL_WEALTH
    d2_index = FIRST_INVEST_INDEX + ADVICE_PERIODS['d2']
    for t in range(FIRST_INVEST_INDEX, len(prices[0]) - 1):
        w = w_d1 if t < d2_index else w_d2
        gross = sum(w[k] / 100 * prices[k][t + 1] / prices[k][t] for k in range(5)) + w[5] / 100
        W *= gross
    return round(W, 2)


# ---------------------------------------------------------------- 1. FP advice records
adv = pd.read_csv(ADVISEES)
adv['order'] = adv['assetOrder'].map(parse_order)
adv['client_arm'] = np.where(adv['treatment'] == 1, 2, 1)       # advisees: 0 = FP w/o AI, 1 = FP with AI
adv['cell'] = adv['gender'] + '-' + adv['age'] + '-' + adv['riskAversion']
adv['record_id'] = np.arange(len(adv))


# ---------------------------------------------------------------- 2. AI advice for the T3 twin
def situation_key(row):
    """Same key as in generate_ai_advice.py: source|path|cell|asset order."""
    return f"{row['source']}|{int(row['pathID'])}|{int(row['customerID'])}|{''.join(map(str, row['order']))}"


if AI_SOURCE == 'generated':
    gen = pd.read_csv(AI_ADVICE)
    gen = gen[gen['draw'] == AI_DRAW].set_index(['situation', 'period'])

    def ai_advice_for(row, period):
        try:
            rec = gen.loc[(situation_key(row), period)]
        except KeyError:
            raise KeyError(f'No generated advice for {situation_key(row)}, period {period}: '
                           f'run sharedData/generate_ai_advice.py first')
        return rec['advice'], rec['reasons'], rec['response_id'], 'generated'

else:
    masters = {}
    for src, path in MASTER_TABLES.items():
        m = pd.read_csv(path)
        m['order'] = m['assetOrder'].map(parse_order)
        masters[src] = m

    def ai_advice_for(row, period):
        """genAdvice of the master-table row with the same cell, path, order, slot and AI arm."""
        m, slot = masters[row['source']], int(row['adviseeNr'])
        hit = m[(m[f'cell_{slot}'] == row['customerID']) & (m[f'path_{slot}'] == row['pathID'])
                & (m['order'].map(tuple) == tuple(row['order'])) & (m['ai'] == row['treatment'])].iloc[0]
        return (hit[f'genAdvice_{period}_{slot}_eng'], hit[f'genAiReasons_{period}_{slot}_eng'], '',
                'pregenerated_master')


ai_cols = []
for _, row in adv.iterrows():
    out = {'record_id': row['record_id'], 'situation': situation_key(row)}
    for d, period in ADVICE_PERIODS.items():
        seen = row.get(f'aiSeen_{d}')                          # advice the T2 FP actually saw (from FP export)
        if USE_ADVICE_SEEN_BY_FP and isinstance(seen, str) and seen.strip():
            advice, reasons, rid, origin = seen, row.get(f'aiSeenReasons_{d}'), row.get(f'aiSeenResponseId_{d}', ''), 'seen_by_fp'
        else:
            advice, reasons, rid, origin = ai_advice_for(row, period)
        w, text = ai_weights(advice)                           # keys 'Option k' = display position k
        out.update({f'ai_w_{d}': json.dumps(w), f'ai_text_{d}': text,
                    f'ai_factors_{d}': json.dumps(ai_factors(reasons)),
                    f'ai_origin_{d}': origin, f'ai_response_id_{d}': rid})
    ai_cols.append(out)
adv = adv.merge(pd.DataFrame(ai_cols), on='record_id')

# ---------------------------------------------------------------- 3. prices and FP advice in display order
def record_fields(row):
    order = row['order']
    prices = [json.loads(row[f'path_asset{a}']) for a in order]   # Option k = asset type order[k-1]
    assert all(len(p) == 21 and p[0] == 100 for p in prices)
    f = {f'opt{k + 1}_prices': json.dumps(prices[k]) for k in range(5)}
    for d in ADVICE_PERIODS:
        f[f'fp_w_{d}'] = json.dumps(fp_weights(row, d, order))
        f[f'fp_factors_{d}'] = json.dumps(fp_factors(row, d))
    f['fp_follow_wealth'] = follow_wealth(prices, json.loads(f['fp_w_d1']), json.loads(f['fp_w_d2']))
    f['ai_follow_wealth'] = follow_wealth(prices, json.loads(row['ai_w_d1']), json.loads(row['ai_w_d2']))
    f['nothing_wealth'] = INITIAL_WEALTH                                       # all cash
    return pd.Series(f)

adv = pd.concat([adv, adv.apply(record_fields, axis=1)], axis=1)

# ---------------------------------------------------------------- 4. blocks (balanced across FP arms within cell)
rng = np.random.default_rng(SEED)
blocks = []
for cell, g in adv.groupby('cell'):
    target = g['client_arm'].value_counts().max() if BALANCE_WITHIN_CELL else None
    for arm, ga in g.groupby('client_arm'):
        ids = list(ga['record_id'])
        if target and len(ids) < target:                    # replicate random records of the smaller arm
            ids += list(rng.choice(ids, size=target - len(ids), replace=False if target - len(ids) <= len(ids) else True))
        blocks += [{'record_id': i, 'cell': cell} for i in ids]
blocks = pd.DataFrame(blocks)
blocks['replica'] = blocks.groupby('record_id').cumcount()
blocks['block_id'] = blocks['record_id'].astype(str) + '_' + blocks['replica'].astype(str)
blocks['block_rank'] = blocks.groupby('cell')['block_id'].transform(lambda s: rng.permutation(len(s)))
blocks = blocks.merge(adv, on=['record_id', 'cell'])

# ---------------------------------------------------------------- 5. slots (random arm order within block)
PAGE_COLS = ['gender', 'age', 'riskAversion', 'source', 'pathID', 'assetOrder'] + [f'opt{k}_prices' for k in range(1, 6)]
slots = []
for _, b in blocks.iterrows():
    arms = [b['client_arm']] * FP_CLIENTS_PER_RECORD + [0, 3]
    for pos, arm in enumerate(rng.permutation(arms)):
        s = {'slot_id': f"{b['block_id']}_{pos}", 'block_id': b['block_id'], 'record_id': b['record_id'],
             'cell': b['cell'], 'arm': int(arm), 'arm_label': ARM_LABELS[int(arm)],
             'perm_rank': int(b['block_rank']) * len(arms) + pos,      # fill order within cell
             'assetOrder': json.dumps(b['order'])}
        s.update({c: b[c] for c in PAGE_COLS if c != 'assetOrder'})
        for d in ADVICE_PERIODS:                                       # advice actually shown to this slot
            if arm in (1, 2):
                s[f'adv_w_{d}'], s[f'adv_factors_{d}'] = b[f'fp_w_{d}'], b[f'fp_factors_{d}']
            elif arm == 3:
                s[f'adv_w_{d}'], s[f'adv_factors_{d}'] = b[f'ai_w_{d}'], b[f'ai_factors_{d}']
            else:
                s[f'adv_w_{d}'], s[f'adv_factors_{d}'] = '', ''
        s.update({'status': 'free', 'participant_code': '', 'reserved_at': ''})
        slots.append(s)
slots = pd.DataFrame(slots).sort_values(['cell', 'perm_rank']).reset_index(drop=True)

# ---------------------------------------------------------------- 6. write + checks
os.makedirs(OUT_DIR, exist_ok=True)
slots.to_csv(os.path.join(OUT_DIR, 'client_slots.csv'), index=False)
block_cols = ['block_id', 'record_id', 'replica', 'cell', 'client_arm', 'source', 'pathID', 'advisorID', 'adviseeNr',
              'situation', 'lang', 'assetOrder', 'adviceOpened_d1', 'adviceOpened_d2',
              'adviceLive_d1', 'adviceLive_d2', 'fp_w_d1', 'fp_w_d2', 'fp_factors_d1', 'fp_factors_d2',
              'ai_w_d1', 'ai_w_d2', 'ai_factors_d1', 'ai_factors_d2', 'ai_origin_d1', 'ai_origin_d2', 'ai_response_id_d1', 'ai_response_id_d2',
              'ai_text_d1', 'ai_text_d2', 'fp_follow_wealth', 'ai_follow_wealth', 'nothing_wealth']
blocks[block_cols].to_csv(os.path.join(OUT_DIR, 'client_blocks.csv'), index=False)

print(f'records: {len(adv)}   blocks: {len(blocks)}   slots: {len(slots)}')
print('slots per arm:', slots['arm_label'].value_counts().to_dict())
tab = slots.pivot_table(index='cell', columns='arm_label', values='slot_id', aggfunc='count')
print(tab.to_string())
assert (tab.nunique(axis=1) == 1).all() or not BALANCE_WITHIN_CELL, 'arms not balanced within cell'
print('AI advice origin:', adv['ai_origin_d1'].value_counts().to_dict())
print('mean wealth if advice followed:  FP', round(adv['fp_follow_wealth'].mean()),
      '  AI', round(adv['ai_follow_wealth'].mean()))
