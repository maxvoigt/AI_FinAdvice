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


class C(BaseConstants):
    NAME_IN_URL = 'investmentGame'
    PLAYERS_PER_GROUP = None
    NUM_PREVRROUNDS = 10
    NUM_INVESTMENT_ROUNDS = 10
    NUM_ROUNDS = NUM_PREVRROUNDS + NUM_INVESTMENT_ROUNDS
    INITIAL_WEALTH = 10000
    UPDATE_INTERVAL = 350 # time in ms to update the chart
    INVESTMENT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728']
    ADVICE_ROUNDS = [1, 5]
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
    investmentOption1Holdings = models.FloatField(initial=0, blank=True)
    investmentOption2Holdings = models.FloatField(initial=0, blank=True)
    investmentOption3Holdings = models.FloatField(initial=0, blank=True)
    investmentOption4Holdings = models.FloatField(initial=0, blank=True)
    investmentOption5Holdings = models.FloatField(initial=0, blank=True)
    totalWealth = models.FloatField(initial=10000)
    riskFreeHoldings = models.FloatField(initial=0)
    
    # Save details of the performance predictions
    performancePrediction1 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 1, on average?")
    performancePrediction2 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 2, on average?")
    performancePrediction3 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 3, on average?")
    performancePrediction4 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 4, on average?")
    performancePrediction5 = models.FloatField(label="What return (price change in %) do you expect for Investment Option 5, on average?")
    
    # Save details of the financial advice
    advice = models.LongStringField(initial="", blank=True)
    chart_image = models.LongStringField(blank=True)
   

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
        # Convert DataFrame to list of dicts for template (oTree templates cannot use pandas .loc)
        df = C.assetParameters
        asset_rows = [
            {
                'option_num': i + 1,
                'priceIncrease': float(df.iloc[i]['priceIncrease']) * 100,
                'priceDecrease': float(df.iloc[i]['priceDecrease']) * 100,
                'probIncrease': float(df.iloc[i]['probIncrease']) * 100,  # display as percentage
            }
            for i in range(len(df))
        ]

        # Add Investment Option 5 --> Perfectly negatively correlated with Investment Option 1
        asset_rows.append({
            'option_num': 5,
            'priceIncrease': float(df.iloc[0]['priceIncrease']) * 100,
            'priceDecrease': float(df.iloc[0]['priceDecrease']) * 100,
            'probIncrease': float(df.iloc[0]['probIncrease']) * 100,
        })

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
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.riskFreeHoldings = player.totalWealth


class invPage(Page):
    form_model = 'player'
    preserve_unsubmitted_inputs = True

    @staticmethod
    def get_form_fields(player):
        if player.round_number - C.NUM_PREVRROUNDS in C.ADVICE_ROUNDS:
            return ['performancePrediction1', 'performancePrediction2', 'performancePrediction3', 'performancePrediction4', 'performancePrediction5', 'chart_image']
    
    def is_displayed(player):
        ## Initialize holdings if user did not change them in this round
        if not player.changedHoldings and player.round_number > 1:
            prev_player = player.in_previous_rounds()[-1]
            player.investmentOption1Holdings = prev_player.investmentOption1Holdings
            player.investmentOption2Holdings = prev_player.investmentOption2Holdings
            player.investmentOption3Holdings = prev_player.investmentOption3Holdings
            player.investmentOption4Holdings = prev_player.investmentOption4Holdings
            player.investmentOption5Holdings = prev_player.investmentOption5Holdings
            player.riskFreeHoldings = prev_player.riskFreeHoldings
        return True


    @staticmethod
    def js_vars(player):
        thisIndex = player.round_number - 1;
        # Get asset prices for all periods
        option1Prices = player.participant.investmentOption1Prices
        option2Prices = player.participant.investmentOption2Prices
        option3Prices = player.participant.investmentOption3Prices
        option4Prices = player.participant.investmentOption4Prices
        option5Prices = player.participant.investmentOption5Prices

        # Get all prices for all periods to determine min and max
        tmp_currentPrices = (
            option1Prices[:player.round_number + 1] +
            option2Prices[:player.round_number + 1] +
            option3Prices[:player.round_number + 1] +
            option4Prices[:player.round_number + 1] +
            option5Prices[:player.round_number + 1]
        )

        prices_by_investmentOption = {
            '1': option1Prices[:player.round_number],
            '2': option2Prices[:player.round_number],
            '3': option3Prices[:player.round_number],
            '4': option4Prices[:player.round_number],
            '5': option5Prices[:player.round_number],
        }

        price_max = (np.floor(max(tmp_currentPrices) / 100) + 1) * 100

        # Get holdings
        oldHoldings = {
            '1': 0,
            '2': 0,
            '3': 0,
            '4': 0,
            '5': 0,
        }

        riskFreeHoldings = player.riskFreeHoldings

        if player.round_number > 1:
            prev_player = player.in_previous_rounds()[-1]
            oldHoldings = {
                '1': prev_player.investmentOption1Holdings,
                '2': prev_player.investmentOption2Holdings,
                '3': prev_player.investmentOption3Holdings,
                '4': prev_player.investmentOption4Holdings,
                '5': prev_player.investmentOption5Holdings,
            }

            riskFreeHoldings = prev_player.riskFreeHoldings

        ## Calculate current total value
        totalCurrentValue = 0
        for i in range(len(C.INVESTMENT_COLORS)):
            totalCurrentValue += locals()[f'option{i+1}Prices'][player.round_number-1] * oldHoldings[str(i + 1)]

        totalCurrentValue = totalCurrentValue + riskFreeHoldings

        newTotalValue = 0
        for i in range(len(C.INVESTMENT_COLORS)):
            newTotalValue += locals()[f'option{i+1}Prices'][player.round_number] * oldHoldings[str(i + 1)]

        newTotalValue = newTotalValue + riskFreeHoldings

        ## Get information about investment options
        investmentOptions = [
            dict(
                num=i + 1,
                label=f'Alternative {i + 1}',
                color=C.INVESTMENT_COLORS[i],
                oldPrice = prices_by_investmentOption[str(i + 1)][thisIndex-1],
                newPrice = prices_by_investmentOption[str(i + 1)][thisIndex] if thisIndex > 0 else "-",
                prevPrices = prices_by_investmentOption[str(i + 1)][:thisIndex] if thisIndex > 0 else "-",
                numShares = oldHoldings[str(i + 1)],
                currentValue = prices_by_investmentOption[str(i + 1)][thisIndex-1] * oldHoldings[str(i + 1)],
                newValue = prices_by_investmentOption[str(i + 1)][thisIndex] * oldHoldings[str(i + 1)] if thisIndex > 0 else "-",
                oldWealthShare = "—" if totalCurrentValue == 0 else round(prices_by_investmentOption[str(i + 1)][thisIndex-1] * oldHoldings[str(i + 1)] / totalCurrentValue * 100, 2),
                newWealthShare = (
                    "—"
                    if newTotalValue == 0
                    else (
                        round(prices_by_investmentOption[str(i + 1)][thisIndex] * oldHoldings[str(i + 1)] / newTotalValue * 100, 2)
                        if thisIndex > 0
                        else round(prices_by_investmentOption[str(i + 1)][thisIndex-1] * oldHoldings[str(i + 1)] / newTotalValue * 100, 2)
                    )
                ),
            )
            for i in range(len(C.INVESTMENT_COLORS))
        ]
       
        riskFreeAsset = [
            dict(
                label = "Not invested",
                color = 'gray',
                currentValue = riskFreeHoldings,
                newValue = riskFreeHoldings,
                oldWealthShare = "—" if totalCurrentValue == 0 else round(riskFreeHoldings / totalCurrentValue * 100, 2),
                newWealthShare = "—" if newTotalValue == 0 else round(riskFreeHoldings / newTotalValue * 100, 2),
            )
        ]

        ## Get characteristics of the investment options
        df = C.assetParameters
        assetCharacteristics = [
            {
                'option_num': i + 1,
                'priceIncrease': float(df.iloc[i]['priceIncrease']) * 100,
                'priceDecrease': float(df.iloc[i]['priceDecrease']) * 100,
                'probIncrease': float(df.iloc[i]['probIncrease']) * 100,  # display as percentage
                'color': C.INVESTMENT_COLORS[i],
            }
            for i in range(len(df))
        ]

        # Add Investment Option 5 --> Perfectly negatively correlated with Investment Option 1
        assetCharacteristics.append({
            'option_num': 5,
            'priceIncrease': float(df.iloc[0]['priceIncrease']) * 100,
            'priceDecrease': float(df.iloc[0]['priceDecrease']) * 100,
            'probIncrease': float(df.iloc[0]['probIncrease']) * 100,
            'color': C.INVESTMENT_COLORS[-1],
        })
        
        return {
            'currentPeriod': player.round_number - C.NUM_PREVRROUNDS,
            'treatment': player.participant.treatment,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'maxRounds': C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'price_max': price_max,
            'roundType': "Investment" if player.round_number > C.NUM_PREVRROUNDS else "Observation",
            'updateInterval': C.UPDATE_INTERVAL,
            #'oldHoldings': oldHoldings,
            'adviceRounds': C.ADVICE_ROUNDS,
            'currentState': "Investment" if player.round_number > C.NUM_PREVRROUNDS else "Observation",
            'investmentOptions' : investmentOptions,
            'riskFreeAsset' : riskFreeAsset,
            'initialPortfolio': inv_initial_portfolio_payload(player),
            'id_in_group': player.id_in_group,
            'assetCharacteristics': assetCharacteristics,
        }

    @staticmethod
    def vars_for_template(player):
        ## Get characteristics of the investment options
        df = C.assetParameters
        asset_rows = [
            {
                'option_num': i + 1,
                'priceIncrease': float(df.iloc[i]['priceIncrease']) * 100,
                'priceDecrease': float(df.iloc[i]['priceDecrease']) * 100,
                'probIncrease': float(df.iloc[i]['probIncrease']) * 100,  # display as percentage
                'color': C.INVESTMENT_COLORS[i],
            }
            for i in range(len(df))
        ]

        # Add Investment Option 5 --> Perfectly negatively correlated with Investment Option 1
        asset_rows.append({
            'option_num': 5,
            'priceIncrease': float(df.iloc[0]['priceIncrease']) * 100,
            'priceDecrease': float(df.iloc[0]['priceDecrease']) * 100,
            'probIncrease': float(df.iloc[0]['probIncrease']) * 100,
            'color': C.INVESTMENT_COLORS[-1],
        })

        return {
            'treatment': player.participant.treatment,
            'currentPeriod': player.round_number - C.NUM_PREVRROUNDS,
            'totalRounds': C.NUM_INVESTMENT_ROUNDS,
            'adviceRounds': C.ADVICE_ROUNDS,
            'testing': player.session.config['testing'],
            'asset_rows': asset_rows,
            'advicePeriod': player.round_number - C.NUM_PREVRROUNDS in C.ADVICE_ROUNDS,
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
                print('here')
                yield {
                    player.id_in_group: {
                        'type': 'advice',
                        'advice': retAdvice,
                    }
                }
        else:
            player.changedHoldings = True
            if data['type'] == 'changeShares':
                newHoldings, newShares = updatePortfolio(player, data, 'change')
            elif data['type'] == 'changeHoldings':
                newHoldings, newShares = updatePortfolio(player, data, 'change')
            elif data['type'] == 'setShares':
                newHoldings, newShares = updatePortfolio(player, data, 'set')
            elif data['type'] == 'setHoldings':
                newHoldings, newShares = updatePortfolio(player, data, 'set')

            retData = {
                'type': 'portfolio',
                'newHoldings': newHoldings,
                'newShares': newShares,
                'portfolio': inv_portfolio_payload(player, newHoldings, newShares),
            }

            player.investmentOption1Holdings = newHoldings['1']
            player.investmentOption2Holdings = newHoldings['2']
            player.investmentOption3Holdings = newHoldings['3']
            player.investmentOption4Holdings = newHoldings['4']
            player.investmentOption5Holdings = newHoldings['5']
            player.riskFreeHoldings = newHoldings['riskFree']

            yield {
                player.id_in_group: retData
            }

    @staticmethod
    def before_next_page(player, timeout_happened):
        currentWealth = player.totalWealth
        if player.round_number > 1:
            prev_player = player.in_previous_rounds()[-1]
            currentWealth = prev_player.totalWealth

        ## Costs for the investment positions
        costBasis = {
            '1': player.investmentOption1Holdings * player.participant.investmentOption1Prices[player.round_number - 1],
            '2': player.investmentOption2Holdings * player.participant.investmentOption2Prices[player.round_number - 1],
            '3': player.investmentOption3Holdings * player.participant.investmentOption3Prices[player.round_number - 1],
            '4': player.investmentOption4Holdings * player.participant.investmentOption4Prices[player.round_number - 1],
            '5': player.investmentOption5Holdings * player.participant.investmentOption5Prices[player.round_number - 1],
        }
        totalCostBasis = sum(costBasis.values())

        riskFreeHoldings = currentWealth - totalCostBasis

        ## Update the total wealth
        newPortfolioValue = {
            '1': player.investmentOption1Holdings * player.participant.investmentOption1Prices[player.round_number],
            '2': player.investmentOption2Holdings * player.participant.investmentOption2Prices[player.round_number],
            '3': player.investmentOption3Holdings * player.participant.investmentOption3Prices[player.round_number],
            '4': player.investmentOption4Holdings * player.participant.investmentOption4Prices[player.round_number],
            '5': player.investmentOption5Holdings * player.participant.investmentOption5Prices[player.round_number],
        }

        totalNewPortfolioValue = sum(newPortfolioValue.values())

        newTotalWealth = totalNewPortfolioValue + riskFreeHoldings

        ## Update the total wealth
        player.totalWealth = newTotalWealth
        player.riskFreeHoldings = riskFreeHoldings

        return {
            'totalWealth': newTotalWealth,
        }


page_sequence = [
    startPage,
    explanations,
    compQuestions, 
    atnQuest,
    attentionScreen,
    invPage,
    #invResults
]


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

    - **situation**: Start the advice by briefly summarizing the situation, mentioning client or asset characteristics as you wish. Keep the situation short and concise.
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
    currentHoldings = {
        '1': player.investmentOption1Holdings,
        '2': player.investmentOption2Holdings,
        '3': player.investmentOption3Holdings,
        '4': player.investmentOption4Holdings,
        '5': player.investmentOption5Holdings,
        'riskFree': player.riskFreeHoldings,
    }

    currentPrices = {
        '1': player.participant.investmentOption1Prices[player.round_number-1],
        '2': player.participant.investmentOption2Prices[player.round_number-1],
        '3': player.participant.investmentOption3Prices[player.round_number-1],
        '4': player.participant.investmentOption4Prices[player.round_number-1],
        '5': player.participant.investmentOption5Prices[player.round_number-1],
        'riskFree': 1,
    }

    totalWealth = 0

    for key, value in currentPrices.items():
        totalWealth += value * currentHoldings[key]

    currentShares = {}
    for key, value in currentHoldings.items():
        currentShares[key] = (value * currentPrices[key]) / totalWealth * 100
    
    newShares = currentShares.copy()
    newHoldings = currentHoldings.copy()
    
    if inType == 'change':
        ## Button was used to change holdings / shares
        changedAsset = data['asset']
        direction = data['direction']


        if data['type'] == 'changeHoldings':
            maxBuy = currentHoldings['riskFree'] / currentPrices[str(changedAsset)]
            maxSell = -currentHoldings[str(changedAsset)]

            delta = direction * C.PORTION_HOLDINGS_CHANGE
            
            if direction > 0:
                delta = min(delta, maxBuy)
            else:
                delta = max(delta, maxSell)

            tmpNewHoldings = max(0, newHoldings[str(changedAsset)] + delta)

            newHoldings[str(changedAsset)] = tmpNewHoldings

            # Update risk-free asset
            newHoldings['riskFree'] = currentHoldings['riskFree'] - delta * currentPrices[str(changedAsset)]

            # Update shares
            for key, value in newHoldings.items():
                newShares[key] = (value * currentPrices[key]) / totalWealth * 100
        else:
            targetTransfer = direction * C.PORTION_SHARES_CHANGE * totalWealth / 100
            maxBuy = currentHoldings['riskFree']
            maxSell = -currentHoldings[str(changedAsset)] * currentPrices[str(changedAsset)]

            transfer = targetTransfer
            if direction > 0:
                transfer = min(transfer, maxBuy)
            else:
                transfer = max(transfer, maxSell)
            
            holdingsChange = transfer / currentPrices[str(changedAsset)]
            newHoldings[str(changedAsset)] = max(0, newHoldings[str(changedAsset)] + holdingsChange)
            newHoldings['riskFree'] = max(0, newHoldings['riskFree'] - transfer)

            # Update shares
            for key, value in newHoldings.items():
                newShares[key] = (value * currentPrices[key]) / totalWealth * 100
    elif inType == 'set':
        # Numerical input of target
        changedAsset = data['asset']

        if data['type'] == 'setShares':
            targetShare = data['targetShare']
            maxValue = currentHoldings['riskFree'] + currentHoldings[str(changedAsset)] * currentPrices[str(changedAsset)]
            maxShare = maxValue / totalWealth * 100

            if targetShare > maxShare:
                targetShare = maxShare
            elif targetShare < 0:
                targetShare = 0
            
            targetHoldings = ((targetShare / 100) * totalWealth) / currentPrices[str(changedAsset)]
            targetTransfer = targetHoldings * currentPrices[str(changedAsset)] - currentHoldings[str(changedAsset)] * currentPrices[str(changedAsset)]

            newHoldings[str(changedAsset)] = targetHoldings
            newHoldings['riskFree'] = currentHoldings['riskFree'] - targetTransfer
            
            # Update shares
            for key, value in newHoldings.items():
                newShares[key] = (value * currentPrices[key]) / totalWealth * 100
        elif data['type'] == 'setHoldings':
            targetHoldings = data['targetHoldings']
            maxValue = currentHoldings['riskFree'] + currentHoldings[str(changedAsset)] * currentPrices[str(changedAsset)]
            maxHoldings = maxValue / currentPrices[str(changedAsset)]

            if targetHoldings > maxHoldings:
                targetHoldings = maxHoldings
            elif targetHoldings < 0:
                targetHoldings = 0
                
            targetTransfer = targetHoldings * currentPrices[str(changedAsset)] - currentHoldings[str(changedAsset)] * currentPrices[str(changedAsset)]
            newHoldings[str(changedAsset)] = targetHoldings
            newHoldings['riskFree'] = currentHoldings['riskFree'] - targetTransfer
            
            # Update shares
            for key, value in newHoldings.items():
                newShares[key] = (value * currentPrices[key]) / totalWealth * 100

    return newHoldings, newShares


def inv_trade_prices(player):
    """Prices for portfolio valuation; same index as updatePortfolio."""
    idx = player.round_number - 1
    return {
        '1': float(player.participant.investmentOption1Prices[idx]),
        '2': float(player.participant.investmentOption2Prices[idx]),
        '3': float(player.participant.investmentOption3Prices[idx]),
        '4': float(player.participant.investmentOption4Prices[idx]),
        '5': float(player.participant.investmentOption5Prices[idx]),
        'riskFree': 1.0,
    }


def inv_portfolio_payload(player, new_holdings, new_shares):
    """
    JSON-serializable display bundle for the React table (New column).
    new_holdings / new_shares use keys '1'..'5' and 'riskFree'.
    """
    prices = inv_trade_prices(player)
    line_values = [
        float(new_holdings[str(i)] * prices[str(i)])
        for i in range(1, 6)
    ]
    sum_risky = float(sum(line_values))
    cash = float(new_holdings['riskFree'])
    total_wealth = float(sum_risky + cash)
    return {
        'holdings': [float(new_holdings[str(i)]) for i in range(1, 6)],
        'lineValues': line_values,
        'shares': [float(new_shares[str(i)]) for i in range(1, 6)],
        'cash': cash,
        'cashShare': float(new_shares['riskFree']),
        'sumRisky': sum_risky,
        'totalWealth': total_wealth,
    }


def inv_initial_portfolio_payload(player):
    """Current player holdings mark-to-market at trade prices (matches page load before live edits)."""
    h = {
        '1': float(player.investmentOption1Holdings),
        '2': float(player.investmentOption2Holdings),
        '3': float(player.investmentOption3Holdings),
        '4': float(player.investmentOption4Holdings),
        '5': float(player.investmentOption5Holdings),
        'riskFree': float(player.riskFreeHoldings),
    }
    prices = inv_trade_prices(player)
    total_wealth = sum(prices[k] * h[k] for k in h)
    if total_wealth <= 0:
        s = {k: 0.0 for k in h}
    else:
        s = {k: (h[k] * prices[k]) / total_wealth * 100.0 for k in h}
    return inv_portfolio_payload(player, h, s)