import stat
from otree.api import *
import pandas as pd
import re
import ast

doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'investmentGame'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    NUM_PREVRROUNDS = 10
    NUM_INVESTMENT_ROUNDS = 15
    INITIAL_WEALTH = 10000

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
    currentPeriod = models.IntegerField(initial=-9)

    investmentOption1Holdings = models.StringField(initial="[]")
    investmentOption2Holdings = models.StringField(initial="[]")
    investmentOption3Holdings = models.StringField(initial="[]")
    investmentOption4Holdings = models.StringField(initial="[]")
    investmentOption5Holdings = models.StringField(initial="[]")

    beliefsPeriod1 = models.LongStringField(initial="{}")

    #returnSeries = self.participant.priceChart
   

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
class explanations(Page):

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

        return {
            'totalRounds': C.NUM_PREVRROUNDS + C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'investRounds': C.NUM_INVESTMENT_ROUNDS,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'asset_rows': asset_rows,
            'treatment': player.participant.treatment,
        }
    
    @staticmethod
    def js_vars(player):
        return {
            'treatment': player.participant.treatment,
        }

class compQuestions(Page):
    form_model = 'player'

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


class attentionScreen(Page):
    pass

class invPage(Page):
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
        tmpOption1Prices = player.participant.investmentOption1Prices
        tmpOption2Prices = player.participant.investmentOption2Prices
        tmpOption3Prices = player.participant.investmentOption3Prices
        tmpOption4Prices = player.participant.investmentOption4Prices
        tmpOption5Prices = player.participant.investmentOption5Prices

        tmp_all_prices = (
            tmpOption1Prices + tmpOption2Prices + tmpOption3Prices +
            tmpOption4Prices + tmpOption5Prices
        )
        price_min = min(tmp_all_prices)
        price_max = max(tmp_all_prices)

        print(price_min, price_max)

        return {
            'treatment': player.participant.treatment,
            'investmentOption1Prices': player.participant.investmentOption1Prices,
            'investmentOption2Prices': player.participant.investmentOption2Prices,
            'investmentOption3Prices': player.participant.investmentOption3Prices,
            'investmentOption4Prices': player.participant.investmentOption4Prices,
            'investmentOption5Prices': player.participant.investmentOption5Prices,
            'currentPeriod': player.currentPeriod,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'obsRounds': C.NUM_PREVRROUNDS,
            'investRounds': C.NUM_INVESTMENT_ROUNDS,
            'price_min': price_min,
            'price_max': price_max,
            'initialWealth': C.INITIAL_WEALTH,
        }


    @staticmethod
    def live_method(player, data):
        if data.get('type') == 'beliefs':
            player.beliefsPeriod1 = data['payload']
            return {player.id_in_group: {}}

        period   = data['period']
        holdings = data.get('holdings')   # list of 5 ints, or None for obs periods

        if holdings is not None:
            for option_num in range(1, 6):
                field        = f'investmentOption{option_num}Holdings'
                current_list = ast.literal_eval(getattr(player, field))
                current_list.append(holdings[option_num - 1])
                setattr(player, field, str(current_list))

        next_period = period + 1
        player.currentPeriod = next_period

        first_round        = -(C.NUM_PREVRROUNDS - 1)
        last_invest_period = first_round + C.NUM_PREVRROUNDS + C.NUM_INVESTMENT_ROUNDS - 1
        done = next_period > last_invest_period

        return {player.id_in_group: {'nextPeriod': next_period, 'done': done}}


page_sequence = [
    explanations,
    compQuestions, 
    atnQuest,
    attentionScreen,
    invPage,
    #invResults
]
