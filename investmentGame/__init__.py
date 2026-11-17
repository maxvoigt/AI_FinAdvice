from otree.api import *
import pandas as pd
import re
import ast
import numpy as np
from openai import AsyncOpenAI
from otree.settings import api_key
import json
from PIL import Image
import base64
import io

import sharedData.assetParams as assetParams

class C(BaseConstants):
    NAME_IN_URL = 'investmentGame'
    PLAYERS_PER_GROUP = None
    NUM_PREVRROUNDS = 10
    NUM_INVESTMENT_ROUNDS = 10
    NUM_ROUNDS = NUM_PREVRROUNDS + NUM_INVESTMENT_ROUNDS
    INITIAL_WEALTH = 10000
    UPDATE_INTERVAL = 350 # time in ms to update the chart
    INVESTMENT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728']
    ADVICE_ROUNDS = [0, 5]
    PORTION_SHARES_CHANGE = 0.5
    PORTION_HOLDINGS_CHANGE = 1

    # Get asset parameters from global/assetParameters.csv
    # Columns: probIncrease, priceIncrease, priceDecrease (from returnSimulation.m)
    assetParameters = pd.read_csv(
        '_static/global/assetParameters.csv',
        header=None,
        names=['probIncrease', 'priceIncrease', 'priceDecrease']
    )
    # Get asset prices from global/assetPrices.csv
    assetPrices = pd.read_csv('_static/global/assetPrices.csv')
    

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Define comp questions
    compQ_1 = models.IntegerField(
        label = "Do your investment choices affect the price changes of the investment options?",
        choices = [
            [1, "Yes"],
            [2, "No"],
        ]
    )
    compQ_2 = models.IntegerField(
        label = "Are the price changes of all investment options independent of each other?",
        choices = [
            [1, "Yes"],
            [2, "No"],
        ]
    )

    compQ_3 = models.IntegerField(
        label = "Do all investment options have the same price changes?",
        choices = [
            [1, "Yes"],
            [2, "No"],
        ]
    )

    compQ_4 = models.IntegerField(
        label = "Will you have the option to receive investment advice? Please select the most correct answer.",
        choices = [
            [1, "Yes, by a financial advisor."],
            [2, "Yes, by a financial advisor who had access to a generative AI system, such as ChatGPT, when giving the advice."],
            [3, "Yes, by ChatGPT directly."],
            [4, "No."],
        ]
    )

    ## Attention Check
    attention_check_done = models.BooleanField(initial=False)
    attention_check_correct = models.BooleanField(initial=False)
    attention_check = models.LongStringField(
        label = "Before starting, please provide a short description of the strategy that you would like to follow during the Investment Task.",
        initial = ""
    )

    # Save details of the investment chocie
    changedHoldings = models.BooleanField(initial=False) # Save if user changed holdings in this round
    totalWealthBOP = models.FloatField(initial=10000) # Wealth at the beginning of the period
    w1 = models.FloatField(initial=0) # Portfolio weight of the first asset
    w2 = models.FloatField(initial=0) # Portfolio weight of the second asset
    w3 = models.FloatField(initial=0) # Portfolio weight of the third asset
    w4 = models.FloatField(initial=0) # Portfolio weight of the fourth asset
    w5 = models.FloatField(initial=0) # Portfolio weight of the fifth asset
    w6 = models.FloatField(initial=0) # Portfolio weight of the risk-free asset
    
    # Save details of the performance predictions
    performancePrediction1 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 1, on average?")
    performancePrediction2 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 2, on average?")
    performancePrediction3 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 3, on average?")
    performancePrediction4 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 4, on average?")
    performancePrediction5 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 5, on average?")
    
    # Save details of the financial advice
    advice = models.LongStringField(initial="", blank=True)
    chart_image = models.LongStringField(blank=True)

     ## Helper variables
    isInitialize = models.BooleanField(initial=False)
    correlatedAssets = models.StringField()
   

def _normalize_attention_text(text: str) -> str:
    """Normalize attention-check text for comparison."""
    if text is None:
        return ""
    # Lowercase, strip, collapse all whitespace to single spaces
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _levenshtein(a: str, b: str) -> int:
    """Simple Levenshtein distance implementation."""
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr_row = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = curr_row[j - 1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j - 1] + (ca != cb)
            curr_row.append(min(insert_cost, delete_cost, replace_cost))
        prev_row = curr_row
    return prev_row[-1]


def check_attention_answer(text: str, max_distance: int = 2) -> bool:
    """
    Check if the attention-check answer is sufficiently close to
    the target phrase, allowing for a small error margin.
    """
    target = "i read the explanation"
    normalized_answer = _normalize_attention_text(text)
    distance = _levenshtein(normalized_answer, target)
    return distance <= max_distance

# PAGES
class startPage(Page):
    def is_displayed(player):
        return player.round_number == 1
        
class explanations(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        tmpOrder = ast.literal_eval(player.participant.assetOrder)
        assetDictionary = assetParams.assetDictionary

        asset_rows = [
            {
                'option_num': idx+1,
                'priceIncrease': assetDictionary[i]['x_up'] * 100,
                'priceDecrease': assetDictionary[i]['x_down'] * 100,
                'probIncrease': assetDictionary[i]['p_up'] * 100,  # display as percentage
                'name': assetDictionary[i]['name'],
            }
            for idx, i in enumerate(tmpOrder)
        ]

        indexAsset = next((row['option_num'] for row in asset_rows if row['name'] == 'IndAsset'), None)
        hedgeAsset = next((row['option_num'] for row in asset_rows if row['name'] == 'Hedge'), None)

        player.correlatedAssets = str(sorted([indexAsset, hedgeAsset]))

        # Get Information for table
        return {
            'totalRounds': C.NUM_PREVRROUNDS + C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'investRounds': C.NUM_INVESTMENT_ROUNDS,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'asset_rows': asset_rows,
            'treatment': player.participant.treatment,
            'updateInterval': C.UPDATE_INTERVAL,
        }
    
    @staticmethod
    def js_vars(player):
        return {
            'treatment': player.participant.treatment,
        }

class compQuestions(Page):
    form_model = 'player'


    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def get_form_fields(player):
        if player.participant.treatment == 0:
            return ['compQ_1', 'compQ_2', 'compQ_3']
        else:
            return ['compQ_1', 'compQ_2', 'compQ_3', 'compQ_4']

    @staticmethod
    def vars_for_template(player):
        return {
            'treatment': player.participant.treatment,
            'testing': player.session.config['testing']
        }
    
    @staticmethod
    def js_vars(player):
        return {
            'treatment': player.participant.treatment,
            'testing': player.session.config['testing']
        }

class atnQuest(Page):
    @staticmethod
    def js_vars(player):
        return {
            'attention_done': player.attention_check_done,
            'attention_correct': player.attention_check_correct,
        }

    @staticmethod
    def live_method(player, answerText):
        is_correct = check_attention_answer(answerText)
        player.attention_check_done = True
        player.attention_check_correct = is_correct

        return {
            player.id_in_group: [player.attention_check_done,player.attention_check_correct ]
        }

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing']
        }


    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

class attentionScreen(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

class invPage(Page):
    form_model = 'player'
    preserve_unsubmitted_inputs = True

    @staticmethod
    def get_form_fields(player):
        if player.round_number - C.NUM_PREVRROUNDS in C.ADVICE_ROUNDS:
            return ['performancePrediction1', 'performancePrediction2', 'performancePrediction3', 'performancePrediction4', 'performancePrediction5', 'chart_image']
    
    @staticmethod
    def is_displayed(player: Player):

        if not player.isInitialize:
            player.isInitialize = True
            if player.round_number == 1:
                player.totalWealthBOP = 10000 # Start with 10,000 at the beginning of the period
                player.w1 = 0
                player.w2 = 0
                player.w3 = 0
                player.w4 = 0
                player.w5 = 0
                player.w6 = 100

            else:
                #prePlayer = player.in_previous_rounds()[-1]
                player.totalWealthBOP, [player.w1, player.w2, player.w3, player.w4, player.w5, player.w6] = get_wealth_update(player)
                

        return True

    @staticmethod
    def js_vars(player):
        currentPeriod = player.round_number
        prevPeriod = currentPeriod - 1

        ### PORTFOLIO LOGIC ###

        ## Get Prices for the current and previous period
        prevPrices = inv_trade_prices(player, prevPeriod)
        currentPrices = inv_trade_prices(player, currentPeriod)

        ## Get the holdings as number of shares
        oldWealth = player.totalWealthBOP
        prevDollarHoldings, prevHoldings = get_holdings(player, oldWealth, player.w1, player.w2, player.w3, player.w4, player.w5, player.w6, prevPeriod)
        
        if currentPeriod > 1:
            prevPlayer = player.in_previous_rounds()[-1]
            oldWealth = prevPlayer.totalWealthBOP
            ## We update here with old values to get the "ground" truth at the beginning in case of page reloads
            prevDollarHoldings, prevHoldings = get_holdings(player, oldWealth, prevPlayer.w1, prevPlayer.w2, prevPlayer.w3, prevPlayer.w4, prevPlayer.w5, prevPlayer.w6, prevPeriod)
        
        ## Value holdings at the current prices
        currentDollarHoldings = [prevHoldings[i] * currentPrices[i] for i in range(len(prevHoldings))]
        currentWealth = sum(currentDollarHoldings)
        
        ## Rebalance to new allocations --> needed for nice updating if reloaded in initialPortfolio
        tmpAllocation = [player.w1, player.w2, player.w3, player.w4, player.w5, player.w6]
        newDollarHoldings = [tmpAllocation[i] * currentWealth / 100 for i in range(len(tmpAllocation))]
        newHoldings = [newDollarHoldings[i] / currentPrices[i] for i in range(len(newDollarHoldings))]

        ### DISPLAY LOGIC ###
        price_max = get_max_price(player)

        # Get all prices until before the current period for plotting --> this periods price is pushed separately
        allPrices = {
            '1': ast.literal_eval(player.participant.investmentOption1Prices)[:currentPeriod],
            '2': ast.literal_eval(player.participant.investmentOption2Prices)[:currentPeriod],
            '3': ast.literal_eval(player.participant.investmentOption3Prices)[:currentPeriod],
            '4': ast.literal_eval(player.participant.investmentOption4Prices)[:currentPeriod],
            '5': ast.literal_eval(player.participant.investmentOption5Prices)[:currentPeriod],
        }

        ## Get information about investment options including holdings
        investmentOptions = [
            dict(
                num=i + 1,
                label=f'Option {i + 1}',
                color=C.INVESTMENT_COLORS[i],
                oldPrice = prevPrices[i],
                newPrice = currentPrices[i],
                allPrices = allPrices[str(i + 1)],
                numShares = prevHoldings[i],
                #numSharesNew = newHoldings[i],
                oldValue = prevDollarHoldings[i],
                newValue = currentDollarHoldings[i],
                oldWealthShare = prevDollarHoldings[i] / currentWealth * 100,
                newWealthShare = currentDollarHoldings[i] / currentWealth * 100,
            )
            for i in range(len(C.INVESTMENT_COLORS))
        ]

        riskFreeAsset = [
            dict(
                label = "Not invested",
                color = 'gray',
                currentValue = prevDollarHoldings[-1],
                newValue = currentDollarHoldings[-1],
                oldWealthShare = currentDollarHoldings[-1] / currentWealth * 100,
                newWealthShare = currentDollarHoldings[-1] / currentWealth * 100,
            )
        ]

        ## Get the initial portfolio at EOP --> can be updated using the live method
        initialPortfolio = {
            'dollarHoldings': newDollarHoldings,
            'numShares': newHoldings,
            'allocation': [player.w1, player.w2, player.w3, player.w4, player.w5, player.w6],
        }

        ## Get characteristics of the investment options
        tmpOrder = ast.literal_eval(player.participant.assetOrder)
        assetDictionary = assetParams.assetDictionary

        assetCharacteristics = [
            {
                'option_num': idx+1,
                'priceIncrease': assetDictionary[i]['x_up'] * 100,
                'priceDecrease': assetDictionary[i]['x_down'] * 100,
                'probIncrease': assetDictionary[i]['p_up'] * 100,  # display as percentage
                'name': assetDictionary[i]['name'],
            }
            for idx, i in enumerate(tmpOrder)
        ]

        return {
            'currentPeriod': currentPeriod - C.NUM_PREVRROUNDS,
            'treatment': int(player.participant.treatment),
            'firstRound': -(C.NUM_PREVRROUNDS),
            'maxRounds': C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'price_max': price_max,
            'updateInterval': C.UPDATE_INTERVAL,
            'currentState': "Investment" if currentPeriod - C.NUM_PREVRROUNDS >= 0 else "Observation",
            'investmentOptions' : investmentOptions,
            'riskFreeAsset' : riskFreeAsset,
            'initialPortfolio': initialPortfolio,
            'id_in_group': player.id_in_group,
            'assetCharacteristics': assetCharacteristics,
            'isAdvisor': False,
            'isAdviceRound': (player.round_number-C.NUM_PREVRROUNDS) in C.ADVICE_ROUNDS,
            'beliefsBefore': player.participant.beliefsBefore,
        }

    @staticmethod
    def vars_for_template(player):
        ## Get characteristics of the investment options
        tmpOrder = player.participant.assetOrder
        tmpOrder = [int(i) for i in tmpOrder.split(',')]
        assetDictionary = assetParams.assetDictionary

        asset_rows = [
            {
                'option_num': idx+1,
                'priceIncrease': assetDictionary[i]['x_up'] * 100,
                'priceDecrease': assetDictionary[i]['x_down'] * 100,
                'probIncrease': assetDictionary[i]['p_up'] * 100,  # display as percentage
                'name': assetDictionary[i]['name'],
                'color': C.INVESTMENT_COLORS[idx],
            }
            for idx, i in enumerate(tmpOrder)
        ]

        indexAsset = next((row['option_num'] for row in asset_rows if row['name'] == 'IndAsset'), None)
        hedgeAsset = next((row['option_num'] for row in asset_rows if row['name'] == 'Hedge'), None)

        return {
            'testing': player.session.config['testing'],
            'totalRounds': C.NUM_INVESTMENT_ROUNDS ,
            'obsRounds': C.NUM_PREVRROUNDS,
            'investRounds': C.NUM_INVESTMENT_ROUNDS,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'asset_rows': asset_rows,
            'treatment': player.participant.treatment,
            'correlatedAssets': sorted([indexAsset, hedgeAsset]),
            'corrCoeff': assetParams.correlationCoefficient,
            'advicePeriod': (player.round_number-C.NUM_PREVRROUNDS) in C.ADVICE_ROUNDS,
            'currentPeriod': player.round_number - C.NUM_PREVRROUNDS,
        }

    @staticmethod
    async def live_method(player, data):
        if data['type'] == 'advice':
            if player.participant.treatment != 3: ## Only for treatment 3
                yield {
                    player.id_in_group: ""
                }
            
            chart_image = data['chart_image']
            ## Send prompt to OpenAI --> needs to be done here to have the chart image available
            player.chart_image = chart_image

            ## Generate the investment advice
            advice = ""
            if player.round_number - C.NUM_PREVRROUNDS in C.ADVICE_ROUNDS:
                tmpAge = player.participant.age
                tmpGender = player.participant.gender
                tmpRiskAversion = player.participant.riskAversion

                prices_data = {
                    f"Option {i}": getattr(player.participant, f"investmentOption{i}Prices")[:player.round_number + 1]
                    for i in range(1, 6)
                }
                tmpPrices = pd.DataFrame(prices_data)
                tmpPrices.index.name = "Year"

                prompt = generate_prompt(player, tmpAge, tmpGender, tmpRiskAversion, tmpPrices, player.chart_image)
                
                advice = await generate_text(prompt)
                player.advice = json.dumps(advice)
                
                if not player.advice:
                    advice = await generate_text(prompt)
                    player.advice = json.dumps(advice)

                ## Create structured advice for page
                retAdvice = create_structured_advice(player.advice)
                yield {
                    player.id_in_group: {
                        'type': 'advice',
                        'advice': retAdvice,
                    }
                }
        else:
            player.changedHoldings = True
            if data['type'] == 'changeShares':
                newAllocation, newNumShares, newHoldings = updatePortfolio(player, data, 'change')
            elif data['type'] == 'changeHoldings':
                newAllocation, newNumShares, newHoldings = updatePortfolio(player, data, 'change')
            elif data['type'] == 'setShares':
                newAllocation, newNumShares, newHoldings = updatePortfolio(player, data, 'set')
            elif data['type'] == 'setHoldings':
                newAllocation, newNumShares, newHoldings = updatePortfolio(player, data, 'set')

            retData = {
                'type': 'portfolio',
                'portfolio': {
                    'dollarHoldings': newHoldings,
                    'numShares': newNumShares,
                    'allocation': newAllocation,}
            }

            player.w1 = newAllocation[0]
            player.w2 = newAllocation[1]
            player.w3 = newAllocation[2]
            player.w4 = newAllocation[3]
            player.w5 = newAllocation[4]
            player.w6 = newAllocation[5]

            yield {
                player.id_in_group: retData
            }

class invResults(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'finalWealth': player.totalWealthBOP,
        }
        

page_sequence = [
    startPage,
    explanations,
    compQuestions, 
    atnQuest,
    attentionScreen,
    invPage,
    invResults
]

########## HELPER FUNCTIONS ##########
def get_max_price(player):
    listIndex = player.round_number 

    # Get asset prices for all periods
    option1Prices = ast.literal_eval(player.participant.investmentOption1Prices)
    option2Prices = ast.literal_eval(player.participant.investmentOption2Prices)
    option3Prices = ast.literal_eval(player.participant.investmentOption3Prices)
    option4Prices = ast.literal_eval(player.participant.investmentOption4Prices)
    option5Prices = ast.literal_eval(player.participant.investmentOption5Prices)

    # Get all prices for all periods to determine min and max; Forward looking
    tmp_currentPrices = (
        option1Prices[:listIndex + 1] +
        option2Prices[:listIndex + 1] +
        option3Prices[:listIndex + 1] +
        option4Prices[:listIndex + 1] +
        option5Prices[:listIndex + 1]
    )

    price_max = (np.floor(max(tmp_currentPrices) / 100) + 1.5) * 100

    return price_max

########## ADVICE PROMPTING ##########
client = AsyncOpenAI(api_key=api_key)

_INVESTMENT_ADVICE_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "situation": {"type": "string"},
        "allocation": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "Option 1": {"$ref": "#/$defs/asset"},
                "Option 2": {"$ref": "#/$defs/asset"},
                "Option 3": {"$ref": "#/$defs/asset"},
                "Option 4": {"$ref": "#/$defs/asset"},
                "Option 5": {"$ref": "#/$defs/asset"},
                "Risk-free asset": {"$ref": "#/$defs/risk_free_asset"},
            },
            "required": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4",
                "Option 5",
                "Risk-free asset",
            ],
        },
        "reason": {"type": "string"},
    },
    "required": ["situation", "allocation", "reason"],
    "$defs": {
        "asset": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "percentage": {"type": "number"},
                "expected_return": {"type": "number"},
            },
            "required": [
                "percentage",
                "expected_return",
            ],
        },
        "risk_free_asset": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "percentage": {"type": "number"},
                "expected_return": {"type": "number"},
            },
            "required": ["percentage", "expected_return"],
        },
    },
}

async def generate_text(prompt):

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
        max_output_tokens=4000,
        reasoning={"effort": "medium"},
        text={
            "format": {
                "type": "json_schema",
                "name": "investment_advice",
                "schema": _INVESTMENT_ADVICE_JSON_SCHEMA,
            }
        },
    )
    
    return json.loads(response.output_text)

def generate_prompt(player, age, gender, riskAversion, prices, chart):
    ageRanges = [[18,34], [35,50], [51,100]]
    useRange = ageRanges[0] if age < 35 else ageRanges[1] if age < 51 else ageRanges[2]
    minAge = useRange[0]
    maxAge = useRange[1]

    genderChoices = {
        1: 'male',
        2: 'female',
        3: 'prefer to self-describe',
        4: 'prefer not to say',
    }
    useGender = genderChoices[gender]

    riskAversionQuestion = "Which of the following statements comes closest to describing the amount of financial risk that you are willing to take when you save or make investments?"
    riskAversionChoices = {
        1: 'I am willing to take substantial financial risks expecting to earn substantial returns.',
        2: 'I am willing to take above average financial risks expecting to earn above-average returns.',
        3: 'I am willing to take average financial risks expecting to earn average returns.',
        4: 'I am willing to take below average financial risks expecting to earn below-average returns.',
        5: 'I am not willing to take any risk, knowing I will earn a small but certain return.',
    }

    useRiskAversion = riskAversionChoices[riskAversion]

    assetParameters = C.assetParameters.copy()

    # Format the dataframe: rows = Options 1-5; columns ordered as instructed
    assetParameters = assetParameters[['priceIncrease', 'priceDecrease', 'probIncrease']]

    # Rename columns to be more descriptive for the prompt
    assetParameters.columns = ['Price Increase', 'Price Decrease', 'Prob. Price Increase']

    # Add Option 5 as a perfectly negatively correlated copy of Option 1
    option5 = assetParameters.iloc[0].copy()
    assetParameters.loc[4] = option5.values  # Option 5 is row index 4 (Python 0-based)
    assetParameters.index = [f'Option {i}' for i in range(1, 6)]
    assetParameters_json = assetParameters.to_dict(orient="index")

    assetPrices_json = prices.to_dict(orient="list")

    prompt = f"""
    You are a financial advisor certified in Canada, meeting with a client for investment advice.

    **Client profile:**
    - Age range: {minAge}–{maxAge} years old
    - Gender: {useGender}
    - Risk tolerance: "{useRiskAversion}"

    **Available investment options:**
    Each option has a price that either increases or decreases each period with a known probability.
    {json.dumps(assetParameters_json, indent=2)}

    Any uninvested wealth earns 0% in a risk-free account.

    **Recent price history:**
    {json.dumps(assetPrices_json, indent=2)}

    Your client has also reviewed a chart of the price history (attached), and knows 
    the properties of the investment options.

    ---

    Based on this, write a brief, personalized investment recommendation for this client. 

    - **situation**: Start the advice by briefly summarizing the situation, mentioning client or asset characteristics as you wish. Keep the description short and concise.
    - **allocation**: For each option (1–5) and the risk-free asset, specify the recommended portfolio weight (%) and your expected average return for that option.
    - **reason**: Please give a short explanation for the advice.
    """

    input_data = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": prompt
                },
                {
                    "type": "input_image",
                    "image_url": quick_compress(chart)  # base64 string with data:image/png;base64,...
                }
            ]
        }
    ]

    return input_data

def quick_compress(base64_str):
    img = Image.open(io.BytesIO(base64.b64decode(base64_str.split(",")[1])))
    img.thumbnail((512, 512))

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=70)

    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def _advice_allocation_row_payload(row):
    """Normalize one allocation entry for the page (percentage required; expected_return optional)."""
    if not isinstance(row, dict):
        return {'percentage': 0}
    out = {'percentage': row['percentage']}
    if 'expected_return' in row:
        out['expected_return'] = row['expected_return']
    return out


def create_structured_advice(advice):
    if isinstance(advice, dict):
        tmpAdvice = advice
    else:
        try:
            tmpAdvice = json.loads(advice)
        except json.JSONDecodeError:
            tmpAdvice = ast.literal_eval(advice)
    retAdvice = {}
    retAdvice['situation'] = tmpAdvice['situation']
    alloc = tmpAdvice['allocation']
    retAdvice['allocation'] = {
        'Option 1': _advice_allocation_row_payload(alloc['Option 1']),
        'Option 2': _advice_allocation_row_payload(alloc['Option 2']),
        'Option 3': _advice_allocation_row_payload(alloc['Option 3']),
        'Option 4': _advice_allocation_row_payload(alloc['Option 4']),
        'Option 5': _advice_allocation_row_payload(alloc['Option 5']),
        'Risk-free asset': _advice_allocation_row_payload(alloc['Risk-free asset']),
    }
    retAdvice['reason'] = tmpAdvice['reason']
    return retAdvice


########## PORTFOLIO LOGIC ##########

def updatePortfolio(player, data, inType):
    currentPeriod = player.round_number
    allocation = [player.w1, player.w2, player.w3, player.w4, player.w5, player.w6]

    totalWealth = player.totalWealthBOP

    dollarHoldings = [allocation[i] * totalWealth / 100 for i in range(len(allocation))]
    currentPrices = inv_trade_prices(player, currentPeriod)

    numShares = [dollarHoldings[i] / currentPrices[i] for i in range(len(dollarHoldings))]


    newHoldings = dollarHoldings.copy()
    newNumShares = numShares.copy()
    
    if inType == 'change':
        ## Button was used to change holdings / shares
        changedAsset = int(data['asset']) - 1
        direction = data['direction']

        if data['type'] == 'changeHoldings':
            maxBuy = dollarHoldings[-1] / currentPrices[changedAsset] # Number of shares that can be bought
            maxSell = -numShares[changedAsset] # Number of shares that can be sold

            delta = direction * C.PORTION_HOLDINGS_CHANGE
            
            if direction > 0:
                delta = min(delta, maxBuy)
            else:
                delta = max(delta, maxSell)

            # Delta is in shares
            dollarTransfer = delta * currentPrices[changedAsset]

            ## Update dollar holdings
            tmpNewHoldings = dollarHoldings[changedAsset] + dollarTransfer

            newHoldings[changedAsset] = tmpNewHoldings
            newHoldings[-1] = dollarHoldings[-1] - dollarTransfer

            ## Update portfolio shares ( allocation )
            newShares = [newHoldings[i] / totalWealth * 100 for i in range(len(newHoldings))]

            ## Update number of shares
            newNumShares[changedAsset] = tmpNewHoldings / currentPrices[changedAsset]
            newNumShares[-1] = (dollarHoldings[-1] - dollarTransfer)

        else:
            targetTransfer = direction * C.PORTION_SHARES_CHANGE * totalWealth / 100
            maxBuy = dollarHoldings[-1] # Last element is risk-free asset, available cash
            maxSell = -dollarHoldings[changedAsset] * currentPrices[changedAsset]

            transfer = targetTransfer
            if direction > 0:
                transfer = min(transfer, maxBuy)
            else:
                transfer = max(transfer, maxSell)
            
            ## Update dollar holdings
            tmpNewHoldings = dollarHoldings[changedAsset] + transfer

            newHoldings[changedAsset] = tmpNewHoldings
            newHoldings[-1] = dollarHoldings[-1] - transfer

            ## Update portfolio shares ( allocation )
            newShares = [newHoldings[i] / totalWealth * 100 for i in range(len(newHoldings))]
            
            ## Update number of shares
            newNumShares[changedAsset] = tmpNewHoldings / currentPrices[changedAsset]
            newNumShares[-1] = (dollarHoldings[-1] - transfer)
    elif inType == 'set':
        # Numerical input of target
        changedAsset = int(data['asset']) - 1

        if data['type'] == 'setShares':
            targetShare = data['targetShare']
            maxValue = dollarHoldings[-1] + dollarHoldings[changedAsset]
            maxShare = maxValue / totalWealth * 100

            if targetShare > maxShare:
                targetShare = maxShare
            elif targetShare < 0:
                targetShare = 0
            
            targetHoldings = ((targetShare / 100) * totalWealth) # Dollar amoung
            targetTransfer = targetHoldings - dollarHoldings[changedAsset]
            
            ## Update dollar holdings
            newHoldings[changedAsset] = targetHoldings
            newHoldings[-1] = dollarHoldings[-1] - targetTransfer
            
            ## Update portfolio shares ( allocation )
            newShares = [newHoldings[i] / totalWealth * 100 for i in range(len(newHoldings))]
            
            ## Update number of shares
            newNumShares[changedAsset] = targetHoldings / currentPrices[changedAsset]
            newNumShares[-1] = (dollarHoldings[-1] - targetTransfer)
        
        elif data['type'] == 'setHoldings':
            targetHoldings = data['targetHoldings']

            maxValue = dollarHoldings[-1] + dollarHoldings[changedAsset]
            maxHoldings = maxValue / currentPrices[changedAsset]

            if targetHoldings > maxHoldings:
                targetHoldings = maxHoldings
            elif targetHoldings < 0:
                targetHoldings = 0

            targetTransfer = targetHoldings * currentPrices[changedAsset] - dollarHoldings[changedAsset]

            ## Update dollar holdings
            newHoldings[changedAsset] = targetHoldings * currentPrices[changedAsset]
            newHoldings[-1] = dollarHoldings[-1] - targetTransfer

            ## Update portfolio shares ( allocation )
            newShares = [newHoldings[i] / totalWealth * 100 for i in range(len(newHoldings))]

            ## Update number of shares
            newNumShares[changedAsset] = targetHoldings
            newNumShares[-1] = (dollarHoldings[-1] - targetTransfer)
            
    return newShares, newNumShares, newHoldings  ## Portfolio shares, Number of shares, Dollar holdings

def get_wealth_update(player):
    currentPeriod = player.round_number
    prevPeriod = currentPeriod - 1

    prevPlayer = player.in_previous_rounds()[-1]

    # Last period's wealth
    lastWealth = prevPlayer.totalWealthBOP

    # Last period's portfolio weights
    lastWeights = [prevPlayer.w1, prevPlayer.w2, prevPlayer.w3, prevPlayer.w4, prevPlayer.w5, prevPlayer.w6]
    boughtPrices = inv_trade_prices(player, prevPeriod)
    currentNumShares = [(lastWeights[i] / 100) * lastWealth / boughtPrices[i] for i in range(len(lastWeights))]

    currentPrices = inv_trade_prices(player, currentPeriod)
    currentDollarHoldings = [currentNumShares[i] * currentPrices[i] for i in range(len(currentNumShares))]

    currentWealth = sum(currentDollarHoldings)

    currentPortfolioShares = [currentDollarHoldings[i] / currentWealth * 100 for i in range(len(currentNumShares))]

    return currentWealth, currentPortfolioShares

def inv_trade_prices(player, period):
    """Prices for portfolio valuation; same index as updatePortfolio."""
    return [
        float(ast.literal_eval(player.participant.investmentOption1Prices)[period]),
        float(ast.literal_eval(player.participant.investmentOption2Prices)[period]),
        float(ast.literal_eval(player.participant.investmentOption3Prices)[period]),
        float(ast.literal_eval(player.participant.investmentOption4Prices)[period]),
        float(ast.literal_eval(player.participant.investmentOption5Prices)[period]),
        1.0,
    ]

def get_holdings(player, wealth, w1, w2, w3, w4, w5, w6, period):
    prices = inv_trade_prices(player, period)
    allocation = [w1, w2, w3, w4, w5, w6]
    
    dollarHoldings = [allocation[i] * wealth / 100 for i in range(len(allocation))]
    numShares = [dollarHoldings[i] / prices[i] for i in range(len(dollarHoldings))]

    return dollarHoldings, numShares