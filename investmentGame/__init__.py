from otree.api import *
import pandas as pd
import re
import ast
import numpy as np
import json
import random
import time
import asyncio
import base64
import io
from PIL import Image
from openai import AsyncOpenAI
from otree.settings import api_key

import sharedData.assetParams as assetParams
from demographics_before import complete_slot

doc = """
Your app description
"""

ADVICE_TIMEOUT_SEC = 30      # live ChatGPT call; after this the pre-generated advice is shown (as in the FP app)
ADVICE_WAIT_MIN_SEC = 5      # FP arms: wait drawn uniformly from [MIN, MAX] seconds ...
ADVICE_TOTAL_SEC = 30        # arm 3: advice + reason coding must be done within this time, else the
                             # pre-generated pair (allocation + reasons) from the slot is shown
AI_REASONS_TIMEOUT_SEC = 30  # used inside generate_ai_reasons (copied from FP); the overall limit above applies on top

#ADVICE_SOURCE = {1: "a financial advisor", 2: "a financial advisor who could use ChatGPT", 3: "ChatGPT"}
ADVICE_SOURCE = {1: "a financial advisor", 2: "a financial advisor", 3: "ChatGPT"}
        
class C(BaseConstants):
    NAME_IN_URL = 'investmentTask'
    PLAYERS_PER_GROUP = None
    NUM_PREVRROUNDS = 10
    NUM_INVESTMENT_ROUNDS = 10
    NUM_ROUNDS_PER_CLIENT = NUM_PREVRROUNDS + NUM_INVESTMENT_ROUNDS 
    NUM_CLIENTS = 1
    NUM_ROUNDS = NUM_ROUNDS_PER_CLIENT * NUM_CLIENTS

    INVESTMENT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728']
    ADVICE_ROUNDS = [0, 5]
    PORTION_SHARES_CHANGE = 1

    UPDATE_INTERVAL = 350 # time in ms to update the chart


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    skipTask = models.BooleanField(initial=False)

    correlatedAssets = models.StringField()
     # Define comp questions
    compQ_1 = models.IntegerField(
        label = "Do your investment choices affect the price changes of the options?",
        choices = [
            [1, "Yes"],
            [2, "No"],
        ]
    )
    compQ_2 = models.IntegerField(
        label = "Are the price changes of all options independent of each other?",
        choices = [
            [1, "Yes"],
            [2, "No"],
        ]
    )

    compQ_3 = models.IntegerField(
        label = "Do all options have the same price changes?",
        choices = [
            [1, "Yes"],
            [2, "No"],
        ]
    )

    comQ1_trials = models.LongStringField(initial="[]", blank=True)
    comQ2_trials = models.LongStringField(initial="[]", blank=True)
    comQ3_trials = models.LongStringField(initial="[]", blank=True)
    
    ## Attention Check
    attention_check_done = models.BooleanField(initial=False)
    attention_check_correct = models.BooleanField(initial=False)
    attention_check = models.LongStringField(
        label = "Before starting, please provide a short description of the strategy that you would like to follow during the Investment Task.",
        initial = ""
    )

    ## Performance Predictions
    performancePrediction1 = models.FloatField(label="Suppose you invest $1,000.00 into Option 1. How much money do you expect to have in five periods? Please enter a number without a dollar sign.")
    performancePrediction2 = models.FloatField(label="Suppose you invest $1,000.00 into Option 2. How much money do you expect to have in five periods? Please enter a number without a dollar sign.")
    performancePrediction3 = models.FloatField(label="Suppose you invest $1,000.00 into Option 3. How much money do you expect to have in five periods? Please enter a number without a dollar sign.")
    performancePrediction4 = models.FloatField(label="Suppose you invest $1,000.00 into Option 4. How much money do you expect to have in five periods? Please enter a number without a dollar sign.")
    performancePrediction5 = models.FloatField(label="Suppose you invest $1,000.00 into Option 5. How much money do you expect to have in five periods? Please enter a number without a dollar sign.")

    ## Financial Advice
    portfolioAllocation = models.LongStringField(
        initial="",
        blank=False,
        label="Recommended allocation",
    )
    
    ## Post-decision justification (advice rounds only; multi-select via one BooleanField per reason)
    ## Same field names as in the FP data, so both samples can be pooled; reason_advice replaces reason_ai.
    reason_risk = models.BooleanField(initial=False, blank=True)        # own willingness to take risks
    reason_age = models.BooleanField(initial=False, blank=True)         # own age / horizon
    reason_gender = models.BooleanField(initial=False, blank=True)      # own gender
    reason_divers = models.BooleanField(initial=False, blank=True)      # diversification / hedging
    reason_payoffs = models.BooleanField(initial=False, blank=True)     # probabilities and payoffs
    reason_skew = models.BooleanField(initial=False, blank=True)        # rare large gains vs frequent small gains
    reason_prices = models.BooleanField(initial=False, blank=True)      # recent price movements
    reason_experience = models.BooleanField(initial=False, blank=True)  # own experience / intuition
    reason_advice = models.BooleanField(initial=False, blank=True)      # the advice received (arms 1-3 only)
    reason_other = models.BooleanField(initial=False, blank=True)       # other
    adviceReasonOther = models.LongStringField(initial="", blank=True)  # optional / "other" explanation

    adviceShown = models.LongStringField(initial="", blank=True)   # weights shown [Option 1..5, cash]
    adviceFactorsShown = models.LongStringField(initial="", blank=True)  # factor keys shown with the advice
    adviceReasonsChat = models.LongStringField(initial="", blank=True)   # arm 3: raw reason coding of the live advice
    adviceOrigin = models.StringField(initial="", blank=True)      # 'fp', 'live' or 'fallback'
    adviceWaitSec = models.FloatField(blank=True)                  # FP arms: drawn wait
    adviceRequestedAt = models.FloatField(initial=0)               # first click on "Show advice"
    adviceDeliveredAt = models.FloatField(initial=0)               # advice sent to the browser
    slot_kept = models.BooleanField()

    chart_image = models.LongStringField(blank=True)
    
    ## Advisee information
    wealthBOP = models.FloatField(initial=10000) # Wealth at the beginning of the period
    w1 = models.FloatField(initial=0) # Portfolio weight of the first asset
    w2 = models.FloatField(initial=0) # Portfolio weight of the second asset
    w3 = models.FloatField(initial=0) # Portfolio weight of the third asset
    w4 = models.FloatField(initial=0) # Portfolio weight of the fourth asset
    w5 = models.FloatField(initial=0) # Portfolio weight of the fifth asset
    w6 = models.FloatField(initial=100) # Portfolio weight of the risk-free asset
    
    ## AI Advice
    adviceChat = models.LongStringField(initial="", blank=True)
    adviceResponseId = models.LongStringField(initial="", blank=True)  # OpenAI response.id of the advice call
    prompt = models.LongStringField(initial="", blank=True)
    showAdviceClicked = models.IntegerField(initial=0)
    generateTime = models.FloatField(initial=0) ## Track the time it takes to generate the advice
    
    ## Measure information accessed for beliefs
    showChartClicked = models.IntegerField(initial=0)
    showDetailsClicked = models.IntegerField(initial=0)

    ## Helper variables
    isInitialize = models.BooleanField(initial=False)
    adviceGenerated = models.BooleanField()

## Define language of choices for comp questions
def compQ_1_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, "Yes"],
            [2, "No"],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, "Oui"],
            [2, "Non"],
        ]

def compQ_2_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, "Yes"],
            [2, "No"],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, "Oui"],
            [2, "Non"],
        ]

def compQ_3_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, "Yes"],
            [2, "No"],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, "Oui"],
            [2, "Non"],
        ]

### JUSTIFICATION REASONS
## Same structure as in the FP app (adviceJustification); labels are written from the client's
## perspective, and 'reason_advice' (arms 1-3) takes the place of the FPs' 'reason_ai'.

ADVICE_SOURCE_FR = {1: "un conseiller financier", 2: "un conseiller financier", 3: "ChatGPT"}  # keep in sync with ADVICE_SOURCE

REASON_LABELS = {
    'en': {
        'reason_risk': "My willingness to take financial risks",
        'reason_age': "My age",
        'reason_gender': "My gender",
        'reason_divers': "Diversification or hedging across the options",
        'reason_payoffs': "The options' probabilities and payoffs",
        'reason_skew': "Whether an option offers rare large gains or frequent small gains",
        'reason_prices': "Recent price movements",
        'reason_experience': "My own experience or intuition",
        'reason_advice': "The advice I received from {source}",
        'reason_other': "Other",
    },
    'fr': {
        'reason_risk': "Ma tolérance au risque financier",
        'reason_age': "Mon âge / mon horizon de placement",
        'reason_gender': "Mon genre",
        'reason_divers': "La diversification ou la couverture entre les options",
        'reason_payoffs': "Les probabilités et les rendements des options",
        'reason_skew': "Le fait qu'une option offre des gains importants mais rares, ou des gains modestes mais fréquents",
        'reason_prices': "Les variations récentes des prix",
        'reason_experience': "Ma propre expérience ou mon intuition",
        'reason_advice': "Le conseil que m'a donné {source}",
        'reason_other': "Autre",
    },
}


def get_reason_fields(player):
    """Field names shown to this player: the advice reason only in the advice arms (1-3)."""
    fields = ['reason_risk', 'reason_age', 'reason_gender', 'reason_divers',
              'reason_payoffs', 'reason_skew', 'reason_prices',
              'reason_experience']
    if player.participant.treatment in (1, 2, 3):
        fields.append('reason_advice')
    return fields


CONSUMER_REASON_FIELDS = {'reason_risk', 'reason_age', 'reason_gender'}


def get_reason_options(player):
    """[{'field': ..., 'label': ...}] in a per-participant stable random order.

    Consumer-characteristic reasons are shown first (shuffled among themselves),
    then the remaining reasons (also shuffled). 'Other' is always last.
    """
    import random as _random

    lang = player.participant.lang
    labels = REASON_LABELS[lang]
    arm = player.participant.treatment
    source = (ADVICE_SOURCE_FR if lang == 'fr' else ADVICE_SOURCE).get(arm, '')

    fields = get_reason_fields(player)
    rng = _random.Random(player.participant.code)  # stable across rounds & reloads

    consumer = [f for f in fields if f in CONSUMER_REASON_FIELDS]
    rest = [f for f in fields if f not in CONSUMER_REASON_FIELDS]
    rng.shuffle(consumer)
    rng.shuffle(rest)
    fields = consumer + rest + ['reason_other']

    return [{'field': f, 'label': labels[f].format(source=source)} for f in fields]

### FACTORS SHOWN WITH THE ADVICE
## Keys as in client_slots.csv (adv_factors_*); fixed display order, identical in all advice arms.
SHOWN_FACTORS = ['risk', 'age', 'gender', 'divers', 'payoffs', 'skew', 'prices', 'experience', 'other']

FACTOR_LABELS = {
    'en': {
        'risk': "Your willingness to take financial risks",
        'age': "Your age",
        'gender': "Your gender",
        'divers': "Diversification or hedging across the options",
        'payoffs': "The options' probabilities and payoffs",
        'skew': "Whether an option offers rare large or frequent small gains",
        'prices': "Recent price movements",
        'experience': "Professional experience or intuition",
    },
    'fr': {
        'risk': "Votre tolérance au risque financier",
        'age': "Votre âge",
        'gender': "Votre genre",
        'divers': "La diversification ou la couverture entre les options",
        'payoffs': "Les probabilités et les rendements des options",
        'skew': "Le fait qu'une option offre des gains importants mais rares, ou des gains modestes mais fréquents",
        'prices': "Les variations récentes des prix",
        'experience': "L'expérience professionnelle ou l'intuition",
    },
}

## Keep in sync with ADVICE_SOURCE (arm 2 is presented as "a financial advisor")
FACTORS_HEADING = {
    'en': {1: "What the financial advisor took into account", 2: "What the financial advisor took into account",
           3: "What ChatGPT took into account"},
    'fr': {1: "Ce que le conseiller financier a pris en compte", 2: "Ce que le conseiller financier a pris en compte",
           3: "Ce que ChatGPT a pris en compte"},
}
FACTORS_INTRO = {
    'en': {1: "When giving this advice, the financial advisor indicated that they took the following factors into account:",
           2: "When giving this advice, the financial advisor indicated that they took the following factors into account:",
           3: "When giving this advice, ChatGPT indicated that it took the following factors into account:"},
    'fr': {1: "En donnant ce conseil, le conseiller financier a indiqué avoir pris en compte les facteurs suivants :",
           2: "En donnant ce conseil, le conseiller financier a indiqué avoir pris en compte les facteurs suivants :",
           3: "En donnant ce conseil, ChatGPT a indiqué avoir pris en compte les facteurs suivants :"},
}
NO_FACTORS_TEXT = {'en': "No factors were indicated.", 'fr': "Aucun facteur n'a été indiqué."}


def factor_labels(player, keys):
    """Labels of the given factor keys, in the fixed display order."""
    labels = FACTOR_LABELS[player.participant.lang]
    ## A factor without a label in FACTOR_LABELS is not shown (e.g. 'other')
    return [labels[k] for k in SHOWN_FACTORS if k in (keys or []) and k in labels]


def reason_keys(reasons):
    """AI reason coding (ai_reason_* booleans) -> factor keys."""
    if not isinstance(reasons, dict):
        return []
    return [k for k in SHOWN_FACTORS if reasons.get(f'ai_reason_{k}')]


# PAGES
class startPage(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player):
        return {
            'lang': player.participant.lang
        }


class explanations(Page):
    def is_displayed(player):
        return player.round_number == 1
    
    @staticmethod
    def vars_for_template(player):
        tmpOrder = player.participant.assetOrder
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

        correlatedAssets = sorted([indexAsset, hedgeAsset])
        player.correlatedAssets = str(correlatedAssets)

        # Options 1–5, leaving out the hedge. The hedge is correlated
        # with the index option; the other four are independent of each other.
        independentAssets = sorted(n for n in range(1, 6) if n != hedgeAsset)
        
        return {
            'testing': player.session.config['testing'],
            'exchangeRate': player.session.config['clientExchangeRate'],
            'totalRounds': C.NUM_PREVRROUNDS + C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'investRounds': C.NUM_INVESTMENT_ROUNDS,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'asset_rows': asset_rows,
            'treatment': player.participant.treatment,
            'correlatedAssets': correlatedAssets,
            'corrCoeff': assetParams.correlationCoefficient,
            'independentAssets': independentAssets,
            'adviceRounds': C.ADVICE_ROUNDS,
            'adviceHint': advice_hint_text(player),
            'lang': player.participant.lang,
            'adviceHint': advice_hint_text(player),
            'lastInvestRound': C.NUM_INVESTMENT_ROUNDS - 1,
        }

class compQuestions(Page):
    form_model = 'player'
    form_fields = ['compQ_1', 'compQ_2', 'compQ_3', 'comQ1_trials', 'comQ2_trials', 'comQ3_trials']
    preserve_unsubmitted_inputs = True

    def is_displayed(player):
        return player.round_number == 1
        
    @staticmethod
    def vars_for_template(player):
        return {
            'treatment': player.participant.treatment,
            'testing': player.session.config['testing'],
            'correlatedAssets': ast.literal_eval(player.correlatedAssets),
            'lang': player.participant.lang
        }

    @staticmethod
    def js_vars(player):
        return {
            'lang': player.participant.lang
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
    def vars_for_template(player):
        return {
            'lang': player.participant.lang
        }

def advice_hint_text(player, when='this period'):
    """One sentence describing the advice; same structure in all advice arms."""
    arm = player.participant.treatment
    if arm == 3:
        return ("ChatGPT will generate this advice for a person with the same age group, gender, and "
                "willingness to take financial risks as you, based on exactly the same price changes "
                f"as you have seen up to {when}.")
    if arm in (1, 2):
        return (f"{ADVICE_SOURCE[arm]} gave this advice for a person with the same age group, gender, "
                "and willingness to take financial risks as you, who saw exactly the same price changes "
                f"as you up to {when}.")
    return ""

def describe_client(lang, client_info):
    """Sentences and labels for one advisee.

    showAgeText fits the page ("âgée de 18 à 34 ans").
    promptAgeText fits the AI prompt ("est une femme qui a entre 18 et 34 ans").
    In English the two age phrases are the same.
    """
    is_female = client_info['gender'] == 'F'
    age = client_info['age']            # 'Young', 'Mid', or 'Old'
    risk = client_info['riskAversion']  # 'Low', 'Med', or 'High'

    if lang == 'fr':
        if is_female:
            risk_text = {
                'Low': "Je suis prête à prendre des risques financiers supérieurs à la moyenne et je m’attends à des rendements supérieurs à la moyenne.",
                'Med': "Je suis prête à prendre des risques financiers moyens et je m’attends à des rendements moyens.",
                'High': "Je suis prête à prendre des risques financiers inférieurs à la moyenne et je m’attends à des rendements inférieurs à la moyenne.",
            }[risk]
        else:
            risk_text = {
                'Low': "Je suis prêt à prendre des risques financiers supérieurs à la moyenne et je m’attends à des rendements supérieurs à la moyenne.",
                'Med': "Je suis prêt à prendre des risques financiers moyens et je m’attends à des rendements moyens.",
                'High': "Je suis prêt à prendre des risques financiers inférieurs à la moyenne et je m’attends à des rendements inférieurs à la moyenne.",
            }[risk]
        return {
            'showGender': "une femme" if is_female else "un homme",
            'pronoun': "elle" if is_female else "il",
            'frenchVerbs': "prête" if is_female else "prêt",
            'showRiskAversion': risk_text,
            'showAgeText': {'Young': "18 à 34 ans", 'Mid': "35 à 54 ans", 'Old': "plus de 55 ans"}[age],
            'promptAgeText': {
                'Young': "qui a entre 18 et 34 ans",
                'Mid': "qui a entre 35 et 54 ans",
                'Old': "qui a plus de 55 ans",
            }[age],
        }

    age_text = {
        'Young': "between 18 and 34 years old",
        'Mid': "between 35 and 54 years old",
        'Old': "above 55 years old",
    }[age]
    return {
        'showGender': "female" if is_female else "male",
        'pronoun': "she" if is_female else "he",
        'frenchVerbs': "",
        'showRiskAversion': {
            'Low': "I am willing to take above average financial risks expecting to earn above-average returns",
            'Med': "I am willing to take average financial risks expecting to earn average returns",
            'High': "I am willing to take below average financial risks expecting to earn below-average returns",
        }[risk],
        'showAgeText': age_text,
        'promptAgeText': age_text,
    }

class invPage(Page):
    form_model = 'player'
    preserve_unsubmitted_inputs = True

    @staticmethod
    def get_form_fields(player):
        if is_invest_round(player):
            fields = ['portfolioAllocation', 'showAdviceClicked', 'showChartClicked', 'showDetailsClicked']
            if is_beliefs_round(player):
                fields = ['performancePrediction1', 'performancePrediction2', 'performancePrediction3',
                          'performancePrediction4', 'performancePrediction5'] + fields
            return fields
        
        if player.session.config['testing']:
            return ['skipTask']

    @staticmethod
    def js_vars(player):
        thisClient = 1 
        thisKey = "p1" 
        currentPeriod = player.round_number # This is the index for the end of the period
        prevPeriod = currentPeriod - 1

        ### PORTFOLIO LOGIC ###

        ## Get Prices for the current and previous period
        prevPrices = inv_trade_prices(player, thisClient, prevPeriod)
        currentPrices = inv_trade_prices(player, thisClient, currentPeriod)

        ## Get the holdings as number of shares
        oldWealth = player.wealthBOP
        prevDollarHoldings, prevHoldings = get_advisee_holdings(player, oldWealth, player.w1, player.w2, player.w3, player.w4, player.w5, player.w6, prevPeriod)
        
        if currentPeriod > 1:
            prevPlayer = player.in_previous_rounds()[-1]
            oldWealth = prevPlayer.wealthBOP
            ## We update here with old values to get the "ground" truth at the beginning in case of page reloads
            prevDollarHoldings, prevHoldings = get_advisee_holdings(player, oldWealth, prevPlayer.w1, prevPlayer.w2, prevPlayer.w3, prevPlayer.w4, prevPlayer.w5, prevPlayer.w6, prevPeriod)
        
        ## Value holdings at the current prices
        currentDollarHoldings = [prevHoldings[i] * currentPrices[i] for i in range(len(prevHoldings))]
        currentWealth = sum(currentDollarHoldings)
        
        ## Rebalance to new allocations
        tmpAllocation = [player.w1, player.w2, player.w3, player.w4, player.w5, player.w6]
        newDollarHoldings = [tmpAllocation[i] * currentWealth / 100 for i in range(len(tmpAllocation))]
        newHoldings = [newDollarHoldings[i] / currentPrices[i] for i in range(len(newDollarHoldings))]

        ### DISPLAY LOGIC ###
        price_max = get_max_price(player, thisClient)

        # Get all prices until before the current period for plotting --> this periods price is pushed separately
        allPrices = {
            '1': ast.literal_eval(player.participant.investmentOption1Prices[thisKey])[:currentPeriod],
            '2': ast.literal_eval(player.participant.investmentOption2Prices[thisKey])[:currentPeriod],
            '3': ast.literal_eval(player.participant.investmentOption3Prices[thisKey])[:currentPeriod],
            '4': ast.literal_eval(player.participant.investmentOption4Prices[thisKey])[:currentPeriod],
            '5': ast.literal_eval(player.participant.investmentOption5Prices[thisKey])[:currentPeriod],
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
                numSharesNew = newHoldings[i],
                oldValue = prevDollarHoldings[i],
                newValue = currentDollarHoldings[i],
                oldWealthShare = prevDollarHoldings[i] / currentWealth * 100,
                newWealthShare = currentDollarHoldings[i] / currentWealth * 100,
            )
            for i in range(len(C.INVESTMENT_COLORS))
        ]
       
        riskFreeAsset = [
            dict(
                label = "Not invested" if player.participant.lang == 'en' else "Non investi",
                color = 'gray',
                currentValue = prevDollarHoldings[-1],
                newValue = currentDollarHoldings[-1],
                oldWealthShare = prevDollarHoldings[-1] / currentWealth * 100,
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
        tmpOrder = player.participant.assetOrder
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
            'currentState': "Investment" if is_invest_round(player) else "Observation",
            'investmentOptions' : investmentOptions,
            'riskFreeAsset' : riskFreeAsset,
            'initialPortfolio': initialPortfolio,
            'id_in_group': player.id_in_group,
            'assetCharacteristics': assetCharacteristics,
            'isAdvisor': False,
            'isAdviceRound': is_advice_round(player),
            'beliefsBefore': False,
            'beliefsMinDollar': 0,
            'beliefsMaxDollar': 10000,
            'isBeliefsRound': is_beliefs_round(player),
            'lang': player.participant.lang,
            'isInvestRound': is_invest_round(player),
            'canEdit': is_invest_round(player),
            'showAdvice': show_advice(player),
            'noFactorsText': NO_FACTORS_TEXT[player.participant.lang],
            'showHint': show_hint(player),
        }

    @staticmethod
    def vars_for_template(player):
        tmpOrder = player.participant.assetOrder
        assetDictionary = assetParams.assetDictionary
        asset_rows = [
            {
                'option_num': idx+1,
                'priceIncrease': assetDictionary[i]['x_up'] * 100,
                'priceDecrease': assetDictionary[i]['x_down'] * 100,
                'probIncrease': assetDictionary[i]['p_up'] * 100,
                'name': assetDictionary[i]['name'],
                'color': C.INVESTMENT_COLORS[idx],
            }
            for idx, i in enumerate(tmpOrder)
        ]
        indexAsset = next((row['option_num'] for row in asset_rows if row['name'] == 'IndAsset'), None)
        hedgeAsset = next((row['option_num'] for row in asset_rows if row['name'] == 'Hedge'), None)

        return {
            'testing': player.session.config['testing'],
            'totalRounds': C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'investRounds': C.NUM_INVESTMENT_ROUNDS,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'asset_rows': asset_rows,
            'treatment': player.participant.treatment,
            'correlatedAssets': sorted([indexAsset, hedgeAsset]),
            'corrCoeff': assetParams.correlationCoefficient,
            'advicePeriod': is_advice_round(player),
            'investPeriod': is_invest_round(player),
            'currentPeriod': player.round_number - C.NUM_PREVRROUNDS,
            'lang': player.participant.lang,
            'beliefsPeriod': is_beliefs_round(player),
            'showAdvice': show_advice(player),
            'adviceSource': ADVICE_SOURCE.get(player.participant.treatment, ''),
            'adviceHintText': advice_hint_text(player),
            'factorsHeading': FACTORS_HEADING[player.participant.lang].get(player.participant.treatment, ''),
            'factorsIntro': FACTORS_INTRO[player.participant.lang].get(player.participant.treatment, ''),
            'showHint': show_hint(player),
        }

    @staticmethod
    def live_method(player, data):
        msgType = data.get('type')
    
        ## Advice (all advice arms): start / poll, exactly like the FP app
        if msgType in ('advice', 'advice_poll'):
            payload = handle_advice_request(player, data.get('chart_image'))
            if payload:
                return {player.id_in_group: payload}
            return

        ## Portfolio changes: only in investment periods
        if not is_invest_round(player):
            return
        if msgType in ('changeShares', 'setShares', 'changeHoldings', 'setHoldings'):
            newAllocation, newNumShares, newHoldings = updatePortfolio(player, data, msgType)
        else:
            return

        player.portfolioAllocation = str(newAllocation)
        player.w1, player.w2, player.w3 = newAllocation[0], newAllocation[1], newAllocation[2]
        player.w4, player.w5, player.w6 = newAllocation[3], newAllocation[4], newAllocation[5]

        return {
            player.id_in_group: {
                'type': 'portfolio',
                'portfolio': {'dollarHoldings': newHoldings, 'numShares': newNumShares, 'allocation': newAllocation},
            }
        }

    @staticmethod
    def before_next_page(player, timeout_happened):
        #save_late_ai_reasons(player)  # AI reason codes that arrived late
        
        if show_advice(player):
            save_finished_advice(player, delivered=False)  # finished after the last poll -> not shown

        if player.round_number < C.NUM_ROUNDS:
            next_player = player.in_round(player.round_number + 1)
            next_player.w1 = player.w1
            next_player.w2 = player.w2
            next_player.w3 = player.w3
            next_player.w4 = player.w4
            next_player.w5 = player.w5
            next_player.w6 = player.w6
            next_player.wealthBOP = get_wealth_update(next_player)

    @staticmethod
    def app_after_this_page(player, upcoming_apps):
        if player.skipTask:
            player.participant.payoffWealth = 15000
            return upcoming_apps[0]


class investmentJustification(Page):
    form_model = 'player'
    preserve_unsubmitted_inputs = True

    @staticmethod
    def get_form_fields(player):
        return get_reason_fields(player) + ['reason_other', 'adviceReasonOther']

    @staticmethod
    def is_displayed(player):
        return is_advice_round(player)

    @staticmethod
    def js_vars(player):
        thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2
        thisKey = "p1" if thisClient == 1 else "p2"
        currentPeriod = player.round_number - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT

        ## Include the current period (invPage appends it client-side via updateChart)
        allPrices = {
            '1': ast.literal_eval(player.participant.investmentOption1Prices[thisKey])[:currentPeriod + 1],
            '2': ast.literal_eval(player.participant.investmentOption2Prices[thisKey])[:currentPeriod + 1],
            '3': ast.literal_eval(player.participant.investmentOption3Prices[thisKey])[:currentPeriod + 1],
            '4': ast.literal_eval(player.participant.investmentOption4Prices[thisKey])[:currentPeriod + 1],
            '5': ast.literal_eval(player.participant.investmentOption5Prices[thisKey])[:currentPeriod + 1],
        }

        investmentOptions = [
            dict(
                num=i + 1,
                label=f'Option {i + 1}',
                color=C.INVESTMENT_COLORS[i],
                allPrices=allPrices[str(i + 1)],
            )
            for i in range(len(C.INVESTMENT_COLORS))
        ]

        return {
            'currentPeriod': currentPeriod - C.NUM_PREVRROUNDS,
            'firstRound': -(C.NUM_PREVRROUNDS),
            'maxRounds': C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'price_max': get_max_price(player, thisClient),
            'investmentOptions': investmentOptions,
            'lang': player.participant.lang,
        }

    @staticmethod
    def vars_for_template(player):
        ## Final allocation, read-only, for reference while answering
        weights = [player.w1, player.w2, player.w3, player.w4, player.w5]
        allocation_rows = [
            {
                'label': f'Option {i + 1}',
                'color': C.INVESTMENT_COLORS[i],
                'weight': round(weights[i], 1),
            }
            for i in range(5)
        ]

        thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2
        currentPeriod = player.round_number - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT

        return {
            'testing': player.session.config['testing'],
            'allocation_rows': allocation_rows,
            'notInvested': round(player.w6, 1),
            'reason_options': get_reason_options(player),
            'lang': player.participant.lang,
            'currentPeriod': currentPeriod - C.NUM_PREVRROUNDS,
            'totalRounds': C.NUM_INVESTMENT_ROUNDS,
        }

    @staticmethod
    def error_message(player, values):
        shown_fields = get_reason_fields(player) + ['reason_other']

        ## Require at least one selection
        if not any(values.get(f) for f in shown_fields):
            if player.participant.lang == 'en':
                return "Please select at least one factor."
            else:
                return "Veuillez sélectionner au moins un facteur."

        ## If 'Other' is selected, require a short explanation
        if values.get('reason_other') and not values.get('adviceReasonOther', '').strip():
            if player.participant.lang == 'en':
                return "You selected 'Other' — please briefly describe the factor in the text box."
            else:
                return "Vous avez sélectionné «Autre» — veuillez décrire brièvement ce facteur dans la zone de texte."

    @staticmethod
    def before_next_page(player, timeout_happened):
        if show_advice(player):
            save_finished_advice(player, delivered=False)  # live advice that finished after the client left invPage

class invResults(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'finalWealth': player.wealthBOP,
            'bonus': player.wealthBOP / player.session.config['clientExchangeRate'],
            'lang': player.participant.lang,
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        if player.round_number == C.NUM_ROUNDS:
            player.participant.payoffWealth = player.wealthBOP
            player.slot_kept = complete_slot(player) 


#### PAGE SEQUENCE ####

page_sequence = [
    startPage,
    explanations,
    compQuestions, 
    atnQuest,
    attentionScreen,
    invPage,
    investmentJustification,
    invResults
]

### HELPDER FUNCTIONS ###
def is_advice_round(player):
        """
        Helper function to check if the current round is an advice round.
        Correct usage: call as invPage.is_advice_round(player)
        """
        adviceRounds = []
        for p in range(C.NUM_CLIENTS):
            for r in C.ADVICE_ROUNDS:
                adviceRounds.append(r + p * C.NUM_ROUNDS_PER_CLIENT)
        
        return (player.round_number - C.NUM_PREVRROUNDS) in adviceRounds

def is_invest_round(player):
    period = player.round_number - C.NUM_PREVRROUNDS
    return 0 <= period < C.NUM_INVESTMENT_ROUNDS   # last period: result only

def advice_otree_rounds():
    return [
        r + p * C.NUM_ROUNDS_PER_CLIENT + C.NUM_PREVRROUNDS
        for p in range(C.NUM_CLIENTS)
        for r in C.ADVICE_ROUNDS
    ]

def is_beliefs_round(player):
    selectedBeliefRound = C.ADVICE_ROUNDS[player.participant.beliefsRound - 1] + C.NUM_PREVRROUNDS
    return player.round_number == selectedBeliefRound

def show_advice(player):
    return is_advice_round(player) and player.participant.treatment in (1, 2, 3)

def show_hint(player):
    period = player.round_number - C.NUM_PREVRROUNDS
    return is_advice_round(player) or period == C.ADVICE_ROUNDS[0]

def current_advice(player):
    """Weights shown in this round: [Option 1..5, Not invested] in display order."""
    if not show_advice(player):
        return []
    period = player.round_number - C.NUM_PREVRROUNDS
    return player.participant.advice_d1 if period == C.ADVICE_ROUNDS[0] else player.participant.advice_d2


def current_factors(player):
    """Factor keys of the slot's advice for this round (FP ticks or pre-generated AI coding)."""
    if not show_advice(player):
        return []
    period = player.round_number - C.NUM_PREVRROUNDS
    return player.participant.adviceFactors_d1 if period == C.ADVICE_ROUNDS[0] else player.participant.adviceFactors_d2


def get_advisee_holdings(player, wealth, w1, w2, w3, w4, w5, w6, period):
    thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2

    prices = inv_trade_prices(player, thisClient, period)
    allocation = [w1, w2, w3, w4, w5, w6]
    dollarHoldings = [allocation[i] * wealth / 100 for i in range(len(allocation))]

    numShares = [dollarHoldings[i] / prices[i] for i in range(len(dollarHoldings))]
    return dollarHoldings, numShares


def get_wealth_update(player):
    thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2

    currentPeriod = player.round_number - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT
    prevPeriod = currentPeriod - 1

    prevPlayer = player.in_previous_rounds()[-1]

    # Last period's wealth
    lastWealth = prevPlayer.wealthBOP

    # Last period's portfolio weights
    lastWeights = [prevPlayer.w1, prevPlayer.w2, prevPlayer.w3, prevPlayer.w4, prevPlayer.w5, prevPlayer.w6]
    boughtPrices = inv_trade_prices(player, thisClient, prevPeriod)
    currentHoldings = [(lastWeights[i] / 100) * lastWealth / boughtPrices[i] for i in range(len(lastWeights))]

    currentPrices = inv_trade_prices(player, thisClient, currentPeriod)
    currentHoldings = [currentHoldings[i] * currentPrices[i] for i in range(len(currentHoldings))]

    currentWealth = sum(currentHoldings)

    return currentWealth

def get_max_price(player, thisClient):
    listIndex = player.round_number - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT # This is the index for the end of the period

    thisKey = "p1" if thisClient == 1 else "p2"
    
    # Get asset prices for all periods
    option1Prices = ast.literal_eval(player.participant.investmentOption1Prices[thisKey])
    option2Prices = ast.literal_eval(player.participant.investmentOption2Prices[thisKey])
    option3Prices = ast.literal_eval(player.participant.investmentOption3Prices[thisKey])
    option4Prices = ast.literal_eval(player.participant.investmentOption4Prices[thisKey])
    option5Prices = ast.literal_eval(player.participant.investmentOption5Prices[thisKey])

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


### FUNCTIONS FOR ATTENTION CHECK ###

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



### FUNCTIONS FOR PORTFOLIO CALCULATIONS ###

def updatePortfolio(player, data, inType):
    thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2
    currentPeriod = player.round_number - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT
    
    allocation = [player.w1, player.w2, player.w3, player.w4, player.w5, player.w6]

    totalWealth = player.wealthBOP

    dollarHoldings = [allocation[i] * totalWealth / 100 for i in range(len(allocation))]
    currentPrices = inv_trade_prices(player, thisClient, currentPeriod)

    numShares = [dollarHoldings[i] / currentPrices[i] for i in range(len(dollarHoldings))]


    newHoldings = dollarHoldings.copy()
    newNumShares = numShares.copy()

    if inType == 'changeShares':
        ## Button was used to change holdings / shares
        changedAsset = int(data['asset']) - 1
        direction = data['direction']

        targetTransfer = direction * C.PORTION_SHARES_CHANGE * totalWealth / 100
        maxBuy = dollarHoldings[-1] # Last element is risk-free asset, available cash
        maxSell = -dollarHoldings[changedAsset]

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

    elif inType == 'setShares':
        # Numerical input of target
        changedAsset = int(data['asset']) - 1
        
        targetShare = data['targetShare']
        maxValue = dollarHoldings[-1] + dollarHoldings[changedAsset]
        maxShare = maxValue / totalWealth * 100

        if targetShare > maxShare:
            targetShare = maxShare
        elif targetShare < 0:
            targetShare = 0
        
        targetHoldings = ((targetShare / 100) * totalWealth) # Dollar amoung
        targetTransfer = targetHoldings - dollarHoldings[changedAsset]
        
        newHoldings[changedAsset] = targetHoldings
        newHoldings[-1] = dollarHoldings[-1] - targetTransfer
        
        ## Update portfolio shares ( allocation )
        newShares = [newHoldings[i] / totalWealth * 100 for i in range(len(newHoldings))]
        
        ## Update number of shares
        newNumShares[changedAsset] = targetHoldings / currentPrices[changedAsset]
        newNumShares[-1] = (dollarHoldings[-1] - targetTransfer)
    
    elif inType in ('changeHoldings', 'setHoldings'):
        changedAsset = int(data['asset']) - 1
        price = currentPrices[changedAsset]
        if inType == 'changeHoldings':
            targetNumShares = numShares[changedAsset] + data['direction']  # one share per click
        else:
            targetNumShares = data['targetHoldings']
        # Cannot go below zero or buy more than the uninvested cash allows
        maxNumShares = (dollarHoldings[-1] + dollarHoldings[changedAsset]) / price
        targetNumShares = min(max(targetNumShares, 0), maxNumShares)
        targetHoldings = targetNumShares * price  # dollar amount
        targetTransfer = targetHoldings - dollarHoldings[changedAsset]
        newHoldings[changedAsset] = targetHoldings
        newHoldings[-1] = dollarHoldings[-1] - targetTransfer
        newShares = [newHoldings[i] / totalWealth * 100 for i in range(len(newHoldings))]
        newNumShares[changedAsset] = targetNumShares
        newNumShares[-1] = newHoldings[-1]

    return newShares, newNumShares, newHoldings  ## Portfolio shares, Number of shares, Dollar holdings


def inv_trade_prices(player, thisClient, period):
    """Prices for portfolio valuation; same index as updatePortfolio."""
    thisKey = "p1" if thisClient == 1 else "p2"
    return [
        float(ast.literal_eval(player.participant.investmentOption1Prices[thisKey])[period]),
        float(ast.literal_eval(player.participant.investmentOption2Prices[thisKey])[period]),
        float(ast.literal_eval(player.participant.investmentOption3Prices[thisKey])[period]),
        float(ast.literal_eval(player.participant.investmentOption4Prices[thisKey])[period]),
        float(ast.literal_eval(player.participant.investmentOption5Prices[thisKey])[period]),
        1.0,
    ]

########## ADVICE PROMPTING ##########
## Copied unchanged from FP/InvestmentAdvice/__init__.py (except: 'reason' is not sent to clients)

client = AsyncOpenAI(api_key=api_key)


AI_REASON_FIELDS = ['ai_reason_risk', 'ai_reason_age', 'ai_reason_gender', 'ai_reason_divers',
                 'ai_reason_payoffs', 'ai_reason_skew', 'ai_reason_prices',
                 'ai_reason_experience', 'ai_reason_other']


## Used in the ChatGPT reason-coding prompt: must stay word for word as in the FP app
AI_REASON_LABELS = {
    'en': {
        'ai_reason_risk': "The client's risk tolerance",
        'ai_reason_age': "The client's age / investment horizon",
        'ai_reason_gender': "The client's gender",
        'ai_reason_divers': "Diversification or hedging across the options",
        'ai_reason_payoffs': "The options' probabilities and payoffs",
        'ai_reason_skew': "Whether an option offers rare large gains or frequent small gains",
        'ai_reason_prices': "Recent price movements",
        'ai_reason_experience': "My professional experience or intuition",
        'ai_reason_other': "Other",
    },
    'fr': {
        'ai_reason_risk': "La tolérance au risque de la personne conseillée",
        'ai_reason_age': "L'âge / l'horizon de placement de la personne conseillée",
        'ai_reason_gender': "Le genre de la personne conseillée",
        'ai_reason_divers': "La diversification ou la couverture entre les options",
        'ai_reason_payoffs': "Les probabilités et les rendements des options",
        'ai_reason_skew': "Le fait qu'une option offre des gains importants mais rares, ou des gains modestes mais fréquents",
        'ai_reason_prices': "Les variations récentes des prix",
        'ai_reason_experience': "Mon expérience professionnelle ou mon intuition",
        'ai_reason_other': "Autre",
    },
}


_INVESTMENT_ADVICE_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "allocation": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "Option 1": {"$ref": "#/$defs/asset"},
                "Option 2": {"$ref": "#/$defs/asset"},
                "Option 3": {"$ref": "#/$defs/asset"},
                "Option 4": {"$ref": "#/$defs/asset"},
                "Option 5": {"$ref": "#/$defs/asset"},
                "Not invested": {"$ref": "#/$defs/not_invested"},
            },
            "required": [
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4",
                "Option 5",
                "Not invested",
            ],
        },
        "Justification": {"type": "string"},
    },
    "required": ["allocation", "Justification"],
    "$defs": {
        "asset": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "percentage": {"type": "number"},
            },
            "required": [
                "percentage",
            ],
        },
        "not_invested": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "percentage": {"type": "number"},
            },
            "required": ["percentage"],
        },
    },
}


ALLOCATION_KEYS = [
    'Option 1', 'Option 2', 'Option 3',
    'Option 4', 'Option 5', 'Not invested',
]


def validate_advice(advice):
    if not isinstance(advice, dict):
        raise ValueError('Advice must be an object.')

    allocation = advice.get('allocation')
    justification = advice.get('Justification')
    if not isinstance(allocation, dict) or set(allocation) != set(ALLOCATION_KEYS):
        raise ValueError('Advice has missing or unexpected allocation entries.')
    if not isinstance(justification, str) or not justification.strip():
        raise ValueError('Advice must contain a justification.')

    percentages = []
    for key in ALLOCATION_KEYS:
        row = allocation[key]
        value = row.get('percentage') if isinstance(row, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{key} must have a numeric percentage.')
        if not np.isfinite(value) or value < 0 or value > 100:
            raise ValueError(f'{key} must be between 0 and 100.')
        percentages.append(value)

    if abs(sum(percentages) - 100) > 0.01:
        raise ValueError('Allocation percentages must total 100.')

    return advice


_AI_REASONS_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **{field: {"type": "boolean"} for field in AI_REASON_FIELDS},
        "other_text": {"type": "string"},
    },
    "required": AI_REASON_FIELDS + ["other_text"],
}


def _ai_reasons_coding_prompt(allocation, justification, lang, chained=False):
    labels = AI_REASON_LABELS[lang]
    factor_lines = "\n".join(f"- {field}: {labels[field]}" for field in AI_REASON_FIELDS)
    allocation_json = json.dumps(allocation, indent=2, ensure_ascii=False)

    if lang == 'fr':
        intro = (
            "Codez maintenant la recommandation que vous venez d'écrire. Ne la modifiez pas."
            if chained else
            "Voici une recommandation d'investissement déjà rédigée. Ne la modifiez pas."
        )
        return f"""{intro}

**Allocation:**
{allocation_json}

**Justification:**
{justification}

Parmi les facteurs suivants, lesquels ont motivé CETTE recommandation? Cochez tous ceux qui s'appliquent.

{factor_lines}

Consignes:
- Ne révisez pas l'allocation ni la justification.
- Au moins un facteur doit être vrai.
- Si «Autre» (ai_reason_other) est vrai, mettez une courte phrase dans other_text. Sinon, laissez other_text vide.
"""

    intro = (
        "Now code the recommendation you just wrote. Do not revise it."
        if chained else
        "Here is an already-written investment recommendation. Do not change it."
    )
    return f"""{intro}

**Allocation:**
{allocation_json}

**Justification:**
{justification}

Which of the following factors drove THIS recommendation? Select all that apply.

{factor_lines}

Instructions:
- Do not revise the allocation or the justification.
- At least one factor must be true.
- If Other (ai_reason_other) is true, put a brief phrase in other_text. Otherwise leave other_text empty.
"""


async def generate_text(prompt):

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt,
        max_output_tokens=6000, # Seems to work well based on trials
        reasoning={"effort": "medium"},
        text={
            "format": {
                "type": "json_schema",
                "name": "investment_advice",
                "schema": _INVESTMENT_ADVICE_JSON_SCHEMA,
            }
        },
    )
    
    return validate_advice(json.loads(response.output_text)), response.id


async def generate_ai_reasons(allocation, justification, lang, previous_response_id=None):
    """Map an already-written recommendation onto the reason checkboxes.

    Separate from generate_text so the participant-facing advice is uncontaminated.
    If previous_response_id is set, this is a follow-up turn on that advice call.
    Timeout is AI_REASONS_TIMEOUT_SEC and is independent of ADVICE_TIMEOUT_SEC.
    """
    chained = bool(previous_response_id)
    prompt_text = _ai_reasons_coding_prompt(
        allocation, justification, lang, chained=chained
    )

    if chained:
        prompt = [{"role": "user", "content": prompt_text}]
    else:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are coding an already-written investment recommendation onto a fixed "
                    "set of factors. Do not revise the recommendation."
                    if lang != 'fr'
                    else
                    "Vous codez une recommandation d'investissement déjà rédigée selon un ensemble "
                    "fixe de facteurs. Ne révisez pas la recommandation."
                ),
            },
            {
                "role": "user",
                "content": prompt_text,
            },
        ]

    async def _call():
        kwargs = dict(
            model="gpt-5.4-mini",
            input=prompt,
            max_output_tokens=800,
            reasoning={"effort": "low"},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "ai_reasons",
                    "schema": _AI_REASONS_JSON_SCHEMA,
                }
            },
        )
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        response = await client.responses.create(**kwargs)
        return json.loads(response.output_text)

    return await asyncio.wait_for(_call(), timeout=AI_REASONS_TIMEOUT_SEC)


def _parse_stored_advice(advice):
    if isinstance(advice, dict):
        return advice
    try:
        return json.loads(advice)
    except json.JSONDecodeError:
        return ast.literal_eval(advice)


def generate_prompt(player, ageText, genderText, riskAversionText, prices, chart):
    tmpOrder = player.participant.assetOrder
    assetDictionary = assetParams.assetDictionary

    # Prepare assetParameters as a list of dicts, then convert to DataFrame and format columns as needed for prompt
    if player.participant.lang == 'en':
        assetParameters_list = [
            {
                'Price increase (%)': assetDictionary[i]['x_up'] * 100,
                'Price decrease (%)': assetDictionary[i]['x_down'] * 100,
                'Chance of price increase (%)': assetDictionary[i]['p_up'] * 100,  # display as percentage
            }
            for _, i in enumerate(tmpOrder)
        ]
    elif player.participant.lang == 'fr':
        assetParameters_list = [
            {
                'Augmentation du prix (%)': assetDictionary[i]['x_up'] * 100,
                'Diminution du prix (%)': assetDictionary[i]['x_down'] * 100,
                'Probabilité d\'augmentation du prix (%)': assetDictionary[i]['p_up'] * 100,  # display as percentage
            }
            for _, i in enumerate(tmpOrder)
        ]
    
    assetParameters = pd.DataFrame(assetParameters_list)
    assetParameters.index = [f'Option {i}' for i in range(1, 6)]
    assetParameters_json = assetParameters.to_dict(orient="index")

    assetPrices_json = prices.to_dict(orient="list")

    firstPlayer = player.in_previous_rounds()[0]
    correlatedAssets = ast.literal_eval(firstPlayer.correlatedAssets)
    corrCoeff = assetParams.correlationCoefficient

    #### English prompt ####
    if player.participant.lang == 'en':

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

    #### French prompt ####
    elif player.participant.lang == 'fr':
        prompt = f"""
        La personne conseillée est { genderText } { ageText }.
        
        De plus, lorsqu’on lui a posé la question «Lequel des énoncés suivants décrit le mieux le niveau de risque financier que vous êtes prêt(e) à prendre lorsque vous épargnez ou faites des placements?»,
        la personne conseillée a répondu: «{ riskAversionText }».

        La personne conseillée dispose de cinq options d’investissement différentes (de l’option 1 à l’option 5). 
        Le patrimoine non investi ne rapporte aucun intérêt.
        
        À chaque période, le prix de chaque option peut augmenter ou diminuer selon une probabilité connue.
        {json.dumps(assetParameters_json, indent=2)}

        Les variations de prix de toutes les options d’investissement, à l’exception de l’option 
        { correlatedAssets[0] } et { correlatedAssets[1] }, sont indépendantes les unes des autres. 
        Les options { correlatedAssets[0] } et { correlatedAssets[1] } sont 
        corrélées avec un coefficient de corrélation de { corrCoeff }, 
        ce qui signifie que le prix de l’option { correlatedAssets[0] } 
        a tendance à diminuer lorsque le prix de l’option { correlatedAssets[1] } augmente,
        et inversement.

        De plus, toutes les variations de prix sont indépendantes des périodes précédentes. 
        Avant l’expérience, un ordinateur a déterminé aléatoirement les variations de prix pour chaque période, selon les probabilités propres à chaque option d’investissement. 
        Cela signifie également que les choix de la personne conseillée n’influencent pas l’évolution des prix.

        Toutes ces informations sont connues de vous et de la personne conseillée.

        **Historique récent des prix:**
        {json.dumps(assetPrices_json, indent=2)}

        La personne conseillée a également consulté un graphique de l’historique des prix (ci-joint) et connaît 
        les caractéristiques des options d’investissement.

        ---

        Sur cette base, rédigez une brève recommandation personnalisée pour la personne conseillée. 

        - **Allocation**: Pour chaque option, indiquez la pondération que vous recommandez en pourcentage de la richesse totale. La richesse restante n’est pas investie.
        - **Justification**: Donnez une brève explication de votre recommandation, mentionnant les raisons que vous avez utilisées pour faire votre recommandation.

        Répondez en français.
        """

        input_data = [
            {
                "role": "system",
                "content": "Vous êtes un conseiller financier certifié au Canada et vous rencontrez une personne conseillée pour lui donner des conseils en investissement."
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": quick_compress(chart)},
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
    """Participant-facing payload: allocation + justification only (never AI reason codes)."""
    tmpAdvice = _parse_stored_advice(advice)
    alloc = tmpAdvice['allocation']
    retAdvice = {
        'allocation': {
            'Option 1': _advice_allocation_row_payload(alloc['Option 1']),
            'Option 2': _advice_allocation_row_payload(alloc['Option 2']),
            'Option 3': _advice_allocation_row_payload(alloc['Option 3']),
            'Option 4': _advice_allocation_row_payload(alloc['Option 4']),
            'Option 5': _advice_allocation_row_payload(alloc['Option 5']),
            'Not invested': _advice_allocation_row_payload(alloc['Not invested']),
        },
        'reason': '',   # clients see the allocation (and factors) only; full text stays in player.adviceChat
    }
    return retAdvice


########## ADVICE DELIVERY (arms 1-3) ##########
## Live advice being generated in the background (arm 3), as in the FP app.
## Key: (participant code, round number). Only plain Python data, never oTree objects.
ADVICE_CACHE = {}
_ADVICE_TASKS = set()


def weights_to_advice(w):
    """[Option 1..5, cash] -> the same dict format as ChatGPT's advice."""
    allocation = {f'Option {k}': {'percentage': w[k - 1]} for k in range(1, 6)}
    allocation['Not invested'] = {'percentage': w[5]}
    return {'allocation': allocation, 'Justification': ''}


def advice_weights(advice):
    al = advice['allocation']
    return [al[f'Option {k}']['percentage'] for k in range(1, 6)] + [al['Not invested']['percentage']]


def draw_wait_seconds():
    return random.uniform(ADVICE_WAIT_MIN_SEC, ADVICE_TIMEOUT_SEC)


def advice_payload(player, advice, factor_keys):
    """What the browser receives: allocation + factor labels; same format in all advice arms."""
    structured = create_structured_advice(advice)
    structured['factors'] = factor_labels(player, factor_keys)
    return {'type': 'advice', 'advice': structured}


def handle_advice_request(player, chart_image):
    """Answers the browser's 'advice' and 'advice_poll' messages for all advice arms."""
    if not show_advice(player):
        return None
    if player.adviceRequestedAt == 0:
        player.adviceRequestedAt = time.time()
    if player.participant.treatment == 3:
        return handle_ai_request(player, chart_image)
    return handle_fp_request(player)


def handle_fp_request(player):
    """Arms 1 and 2: the FP's advice after a random wait. The wait is drawn once and timed on the
    server, so reloading the page does not restart it."""
    if player.field_maybe_none('adviceWaitSec') is None:
        player.adviceWaitSec = draw_wait_seconds()
    if time.time() < player.adviceRequestedAt + player.adviceWaitSec:
        return {'type': 'advice_pending'}
    if not player.adviceShown:
        player.adviceShown = json.dumps(current_advice(player))
        player.adviceFactorsShown = json.dumps(current_factors(player))
        player.adviceOrigin = 'fp'
        player.adviceDeliveredAt = time.time()
    return advice_payload(player, weights_to_advice(current_advice(player)), current_factors(player))


def handle_ai_request(player, chart_image):
    """Arm 3: live ChatGPT call in the background, exactly as in the FP app."""
    key = (player.participant.code, player.round_number)
    save_finished_advice(player)
    if not player.adviceChat and key not in ADVICE_CACHE:
        if chart_image:
            player.chart_image = chart_image
        start_advice_job(player, key)
        save_finished_advice(player)
    if player.adviceChat:
        return advice_payload(player, player.adviceChat, json.loads(player.adviceFactorsShown or '[]'))
    return {'type': 'advice_pending'}


def build_advice_prompt(player):
    """Same prompt as in the FP app. The 'advisee' is the client's cell, i.e. the same profile
    the FPs advised."""
    currentPeriod = player.round_number                       # one client: index of the end of the period
    gender, age, risk = player.participant.cell.split('-')
    text = describe_client(player.participant.lang, {'gender': gender, 'age': age, 'riskAversion': risk})
    prices_data = {
        f'Option {k}': ast.literal_eval(getattr(player.participant, f'investmentOption{k}Prices')['p1'])[:currentPeriod + 1]
        for k in range(1, 6)
    }
    tmpPrices = pd.DataFrame(prices_data)
    tmpPrices.index.name = "Year"
    return generate_prompt(player, text['promptAgeText'], text['showGender'], text['showRiskAversion'],
                           tmpPrices, player.chart_image)


async def _code_reasons(advice, response_id, lang, deadline):
    """Reason coding of the live advice, as in the FP app: chained on the advice call first, then
    unchained. Must finish before the deadline."""
    attempts = [response_id, None] if response_id else [None]
    for previous_response_id in attempts:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            return await asyncio.wait_for(
                generate_ai_reasons(advice['allocation'], advice['Justification'], lang,
                                    previous_response_id=previous_response_id),
                timeout=remaining,
            )
        except Exception:
            continue
    raise TimeoutError('reason coding not finished in time')


async def _advice_job(key, prompt, fallback_advice, fallback_keys, lang):
    """Runs in the background. Talks to OpenAI only. NEVER touches the oTree database.
    Live advice is only used together with its own reason coding; if either part fails or the
    total time exceeds ADVICE_TOTAL_SEC, the pre-generated pair from the slot is shown instead."""
    entry = ADVICE_CACHE[key]
    start_time = time.time()
    deadline = start_time + ADVICE_TOTAL_SEC
    try:
        advice, response_id = await asyncio.wait_for(
            generate_text(prompt), timeout=min(ADVICE_TIMEOUT_SEC, ADVICE_TOTAL_SEC))
        reasons = await _code_reasons(advice, response_id, lang, deadline)
        keys, generated = reason_keys(reasons), True
    except Exception:
        advice, response_id, reasons, keys, generated = fallback_advice, "", None, fallback_keys, False
    entry.update(advice=advice, response_id=response_id or "", generated=generated, reasons=reasons,
                 factor_keys=keys, elapsed=time.time() - start_time, status='done')


def start_advice_job(player, key):
    """Prepares everything that needs the database, then starts the background task.
    Fallback = the pre-generated AI advice and its reasons stored in this client's slot."""
    fallback_advice = weights_to_advice(current_advice(player))
    fallback_keys = current_factors(player)
    try:
        prompt = build_advice_prompt(player)
    except Exception:
        prompt = None                                          # e.g. no chart image yet
    ADVICE_CACHE[key] = {'status': 'running', 'prompt': str(prompt) if prompt is not None else ""}
    if prompt is None:
        ADVICE_CACHE[key].update(status='done', advice=fallback_advice, response_id="", generated=False,
                                 reasons=None, factor_keys=fallback_keys, elapsed=0.0)
        return
    task = asyncio.get_running_loop().create_task(
        _advice_job(key, prompt, fallback_advice, fallback_keys, player.participant.lang))
    _ADVICE_TASKS.add(task)
    task.add_done_callback(_ADVICE_TASKS.discard)


def save_finished_advice(player, delivered=True):
    """Copies finished live advice from ADVICE_CACHE into the database. Only call from oTree code
    that holds the global lock (live method or before_next_page).

    delivered=True:  called from the live method, which sends the advice to the browser right after.
    delivered=False: called from before_next_page; the client had already left the page, so the
                     advice is stored for the record but NOT marked as shown."""
    key = (player.participant.code, player.round_number)
    entry = ADVICE_CACHE.get(key)
    if entry is None or entry['status'] != 'done':
        return
    if not player.adviceChat:
        player.adviceGenerated = entry['generated']
        player.adviceChat = json.dumps(entry['advice'])
        player.adviceResponseId = entry['response_id']
        player.generateTime = entry['elapsed']
        player.prompt = entry['prompt']
        player.adviceReasonsChat = json.dumps(entry['reasons']) if entry.get('reasons') else ""
        player.adviceOrigin = 'live' if entry['generated'] else 'fallback'
        if delivered:
            player.adviceShown = json.dumps(advice_weights(entry['advice']))
            player.adviceFactorsShown = json.dumps(entry.get('factor_keys') or [])
            player.adviceDeliveredAt = time.time()
        else:
            player.adviceOrigin += '_not_shown'
    ADVICE_CACHE.pop(key, None)