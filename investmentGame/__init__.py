import stat
from otree.api import *
import pandas as pd
import re
import ast
import numpy as np
from openai import OpenAI
from otree.settings import api_key
import json


doc = """
Your app description
"""

client = OpenAI(api_key=api_key)

def generate_text(prompt):
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
        max_output_tokens=3000,
        reasoning={"effort": "low"}, # ensure some reasoning is done
        #temperature=0,  # reduces randomness
    )
    return response.output_text

def generate_prompt(player, wealth, age, gender, riskAversion, prices, chart):
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
    You are a financial advisor certified in Canada, giving advice to a real human—your client—as part of this research study.
    You are given the following information:
    - The current investable wealth of your client is ${wealth}.
    - Your client is between ${minAge} and ${maxAge} years old.
    - Your client's gender is ${useGender}.
    - Your client was asked the following question: '{riskAversionQuestion}' The client's answer was ${useRiskAversion}.

    Your client has the following investment options, which are known in an identical way to your client:
    {json.dumps(assetParameters_json, indent=2)}.
    Any wealth not invested in the investment options is invested in a risk-free asset with a return of 0%.

    The price development of the investment options is as follows:
    {json.dumps(assetPrices_json, indent=2)}.

    Your client has seen a chart of the investment options (provided separately).

    Generate a short personalized investment advice for your client. The advice should contain 
    the client's target allocation to each investment option as well as in cash.
    The allocation should be in dollar and percentage, as well as the number of units for the investment options. 
    The number of units should be based on the current price of the investment options.
    The advice should be in a format that is easy to understand and follow, and can contain 
    a justification if it is useful. Start the advice by briefly summarizing the 
    situation. Do not include any other text than the advice, and do not include any text that hints at follow-up questions.

    Ensure that the advice looks nice when displayed in HTML, 
    that is, include HTML tags to allow for a nice rendering.
    Do not use headings or tables. 
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
                    "image_url": chart  # base64 string with data:image/png;base64,...
                }
            ]
        }
    ]

    return input_data

class C(BaseConstants):
    NAME_IN_URL = 'investmentGame'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 25
    NUM_PREVRROUNDS = 10
    NUM_INVESTMENT_ROUNDS = 15
    INITIAL_WEALTH = 10000
    UPDATE_INTERVAL = 350 # time in ms to update the chart
    INVESTMENT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728']
    ADVICE_ROUNDS = [1, 5, 10]

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



class invPage(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if player.round_number - C.NUM_PREVRROUNDS in C.ADVICE_ROUNDS:
            return ['investmentOption1Holdings', 'investmentOption2Holdings', 'investmentOption3Holdings', 'investmentOption4Holdings', 'investmentOption5Holdings', 'chart_image', 'performancePrediction1', 'performancePrediction2', 'performancePrediction3', 'performancePrediction4', 'performancePrediction5']
        else:
            return ['investmentOption1Holdings', 'investmentOption2Holdings', 'investmentOption3Holdings', 'investmentOption4Holdings', 'investmentOption5Holdings', 'chart_image']

    # TEST
    '''
    @staticmethod
    def is_displayed(player):
        player.currentPeriod = -9
        print(player.currentPeriod)
        return True
    '''

    @staticmethod
    def js_vars(player):
        # Get asset prices for all periods
        option1Prices = player.participant.investmentOption1Prices
        option2Prices = player.participant.investmentOption2Prices
        option3Prices = player.participant.investmentOption3Prices
        option4Prices = player.participant.investmentOption4Prices
        option5Prices = player.participant.investmentOption5Prices

        # Get all prices for all periods to determine min and max
        tmp_currentPrices = (
            option1Prices[:player.round_number] +
            option2Prices[:player.round_number] +
            option3Prices[:player.round_number] +
            option4Prices[:player.round_number] +
            option5Prices[:player.round_number]
        )

        price_max = (np.floor(max(tmp_currentPrices) / 100) + 1) * 100

        # Prepare thisPrices and prevPrices as dictionaries
        thisPrices = {
            '1': option1Prices[player.round_number - 1],
            '2': option2Prices[player.round_number - 1],
            '3': option3Prices[player.round_number - 1],
            '4': option4Prices[player.round_number - 1],
            '5': option5Prices[player.round_number - 1],
        }

        # Default values for prevPrices set to np.nan
        prevPrices = {
            '1': np.nan,
            '2': np.nan,
            '3': np.nan,
            '4': np.nan,
            '5': np.nan,
        }

        if player.round_number > 1:
            prevPrices = {
                '1': option1Prices[:player.round_number - 1],
                '2': option2Prices[:player.round_number - 1],
                '3': option3Prices[:player.round_number - 1],
                '4': option4Prices[:player.round_number - 1],
                '5': option5Prices[:player.round_number - 1],
            }

        oldHoldings = {
            '1': 0,
            '2': 0,
            '3': 0,
            '4': 0,
            '5': 0,
        }

        totalWealth = player.totalWealth

        if player.round_number > 1:
            prev_player = player.in_previous_rounds()[-1]
            oldHoldings = {
                '1': prev_player.investmentOption1Holdings,
                '2': prev_player.investmentOption2Holdings,
                '3': prev_player.investmentOption3Holdings,
                '4': prev_player.investmentOption4Holdings,
                '5': prev_player.investmentOption5Holdings,
            }
            totalWealth = prev_player.totalWealth
        
        currentValues = {}
        for i in range(1, 6):
            # Use string keys as in oldHoldings, thisPrices
            opt = str(i)
            currentValues[opt] = thisPrices[opt] * oldHoldings[opt]

        totalCurrentValue = sum(currentValues.values())

        currentShares = {}
        for i in range(1, 6):
            opt = str(i)
            currentShares[opt] = "—" if totalCurrentValue == 0 else f"{round(currentValues[opt] / totalCurrentValue * 100, 2):.2f}%"

        return {
            'currentPeriod': player.round_number - C.NUM_PREVRROUNDS,
            'treatment': player.participant.treatment,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'maxRounds': C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'prevPrices': prevPrices,
            'thisPrices': thisPrices,
            'currentValues': currentValues, # Note: Old holdings at new price
            'totalCurrentValue': totalCurrentValue,
            'currentShares': currentShares,
            'totalCurrentShares': "—" if totalCurrentValue == 0 else "100.00%",
            'totalWealth': totalWealth,
            'price_max': price_max,
            'investmentColors': C.INVESTMENT_COLORS,
            'roundType': "Investment" if player.round_number > C.NUM_PREVRROUNDS else "Observation",
            'updateInterval': C.UPDATE_INTERVAL,
            'oldHoldings': oldHoldings,
            'adviceRounds': C.ADVICE_ROUNDS,
        }

    @staticmethod
    def vars_for_template(player):
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
        
        lastPrices = {
            '1': player.participant.investmentOption1Prices[:player.round_number][0] if player.round_number == 1 else player.participant.investmentOption1Prices[:player.round_number][-2],
            '2': player.participant.investmentOption2Prices[:player.round_number][0] if player.round_number == 1 else player.participant.investmentOption2Prices[:player.round_number][-2],
            '3': player.participant.investmentOption3Prices[:player.round_number][0] if player.round_number == 1 else player.participant.investmentOption3Prices[:player.round_number][-2],
            '4': player.participant.investmentOption4Prices[:player.round_number][0] if player.round_number == 1 else player.participant.investmentOption4Prices[:player.round_number][-2],
            '5': player.participant.investmentOption5Prices[:player.round_number][0] if player.round_number == 1 else player.participant.investmentOption5Prices[:player.round_number][-2],
        }

        totalValue = 0
        for i in range(len(C.INVESTMENT_COLORS)):
            totalValue += oldHoldings[str(i + 1)] * lastPrices[str(i + 1)]

        # Build option metadata so the template doesn't need to index lists
        options = [
            dict(
                num=i + 1,
                label=f'Alternative {i + 1}',
                color=C.INVESTMENT_COLORS[i],
                lastPrices = round(lastPrices[str(i + 1)], 2),
                oldHoldings=oldHoldings[str(i + 1)],
                currentValue = lastPrices[str(i + 1)] * oldHoldings[str(i + 1)],
                currentShare = "—" if totalValue == 0 else f"{round(lastPrices[str(i + 1)] * oldHoldings[str(i + 1)] / totalValue * 100, 2)}%",
            )
            for i in range(len(C.INVESTMENT_COLORS))
        ]

        newWealth = totalValue + riskFreeHoldings

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
            'options': options,
            'totalValue': totalValue,
            'totalShare': "—" if totalValue == 0 else "100.00%",
            'totalWealth': newWealth,
            'adviceRounds': C.ADVICE_ROUNDS,
            'asset_rows': asset_rows,
        }
    
    @staticmethod
    def live_method(player, chart_image):
        if player.participant.treatment != 3:
            return {
                player.id_in_group: ""
            }

        ## Send prompt to OpenAI --> needs to be done here to have the chart image available
        player.chart_image = chart_image

        ## Generate the investment advice
        advice = ""
        if player.round_number - C.NUM_PREVRROUNDS in C.ADVICE_ROUNDS:
            tmpAge = player.participant.age
            tmpGender = player.participant.gender
            tmpRiskAversion = player.participant.riskAversion

            prev_player = player.in_previous_rounds()[-1]
            totalWealth = prev_player.totalWealth

            prices_data = {
                f"Option {i}": getattr(player.participant, f"investmentOption{i}Prices")[:player.round_number + 1]
                for i in range(1, 6)
            }
            tmpPrices = pd.DataFrame(prices_data)
            tmpPrices.index.name = "Year"


            prompt = generate_prompt(player, totalWealth, tmpAge, tmpGender, tmpRiskAversion, tmpPrices, player.chart_image)
            #print(prompt)
            
            #advice = generate_text(prompt)
            #player.advice = advice
            
            if not player.advice:
                advice = generate_text(prompt)
                player.advice = advice
            
            return {
                player.id_in_group: player.advice}
        

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
