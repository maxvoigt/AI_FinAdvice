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


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'investmentAdvice'
    PLAYERS_PER_GROUP = None
    NUM_PREVRROUNDS = 10
    NUM_INVESTMENT_ROUNDS = 10
    NUM_ROUNDS_PER_CLIENT = NUM_PREVRROUNDS + NUM_INVESTMENT_ROUNDS 
    NUM_CLIENTS = 2
    NUM_ROUNDS = NUM_ROUNDS_PER_CLIENT * NUM_CLIENTS

    INVESTMENT_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728']
    ADVICE_ROUNDS = [0, 5]
    PORTION_SHARES_CHANGE = 0.5
    PORTION_HOLDINGS_CHANGE = 1

    UPDATE_INTERVAL = 350 # time in ms to update the chart


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    correlatedAssets = models.StringField()
     # Define comp questions
    compQ_1 = models.IntegerField(
        label = "Do the investment choices of your advisees affect the price changes of the options?",
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

    compQ_4 = models.IntegerField(
        label = "Does your advice affect your bonus? Please select the most correct answer.",
        choices = [
            [1, "Yes, my advice affects whether I am eligible for a bonus or not."],
            [2, "Yes, my advice affects the size of my bonus."],
            [3, "Yes, my advice affects both whether I am eligible for a bonus or not, and the size of my bonus."],
            [4, "No, my advice does not affect my bonus."],
        ]
    )

    comQ1_trials = models.LongStringField(initial="[]", blank=True)
    comQ2_trials = models.LongStringField(initial="[]", blank=True)
    comQ3_trials = models.LongStringField(initial="[]", blank=True)
    comQ4_trials = models.LongStringField(initial="[]", blank=True)

    ## Attention Check
    attention_check_done = models.BooleanField(initial=False)
    attention_check_correct = models.BooleanField(initial=False)
    attention_check = models.LongStringField(
        label = "Before starting, please provide a short description of the strategy that you would like to follow during the Investment Task.",
        initial = ""
    )

    ## Performance Predictions
    performancePrediction1 = models.FloatField(label="Suppose you invest $1,000.00 into Option 1. How much money do you expect to have in five periods?")
    performancePrediction2 = models.FloatField(label="Suppose you invest $1,000.00 into Option 2. How much money do you expect to have in five periods?")
    performancePrediction3 = models.FloatField(label="Suppose you invest $1,000.00 into Option 3. How much money do you expect to have in five periods?")
    performancePrediction4 = models.FloatField(label="Suppose you invest $1,000.00 into Option 4. How much money do you expect to have in five periods?")
    performancePrediction5 = models.FloatField(label="Suppose you invest $1,000.00 into Option 5. How much money do you expect to have in five periods?")

    ## Financial Advice
    adviceSituation = models.LongStringField(
        initial="",
        blank=False,
        label="Situation summary",
    )
    adviceAllocation = models.LongStringField(
        initial="",
        blank=False,
        label="Recommended allocation (text)",
    )
    adviceReason = models.LongStringField(
        initial="",
        blank=False,
        label="Reasoning",
    )

    chart_image = models.LongStringField(blank=True)
    
    ## Advisee information
    adviseeWealthBOP = models.FloatField(initial=10000) # Wealth at the beginning of the period
    w1 = models.FloatField(initial=0) # Portfolio weight of the first asset
    w2 = models.FloatField(initial=0) # Portfolio weight of the second asset
    w3 = models.FloatField(initial=0) # Portfolio weight of the third asset
    w4 = models.FloatField(initial=0) # Portfolio weight of the fourth asset
    w5 = models.FloatField(initial=0) # Portfolio weight of the fifth asset
    w6 = models.FloatField(initial=0) # Portfolio weight of the risk-free asset
    
    ## AI Advice
    adviceChat = models.LongStringField(initial="", blank=True)
    prompt = models.LongStringField(initial="", blank=True)
    showAdviceClicked = models.IntegerField(initial=0)
    
    ## Helper variables
    isInitialize = models.BooleanField(initial=False)
    

# PAGES
class startPage(Page):
    def is_displayed(player):
        return player.round_number == 1


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

        player.correlatedAssets = str(sorted([indexAsset, hedgeAsset]))

        return {
            'testing': player.session.config['testing'],
            'exchangeRate': player.session.config['advisorExchangeRate'],
            'totalRounds': C.NUM_PREVRROUNDS + C.NUM_INVESTMENT_ROUNDS,
            'obsRounds': C.NUM_PREVRROUNDS,
            'investRounds': C.NUM_INVESTMENT_ROUNDS,
            'firstRound': -(C.NUM_PREVRROUNDS - 1),
            'asset_rows': asset_rows,
            'treatment': player.participant.treatment,
            'correlatedAssets': sorted([indexAsset, hedgeAsset]),
            'corrCoeff': assetParams.correlationCoefficient,
            'adviceRounds': C.ADVICE_ROUNDS,
        }

class compQuestions(Page):
    form_model = 'player'
    form_fields = ['compQ_1', 'compQ_2', 'compQ_3', 'compQ_4', 'comQ1_trials', 'comQ2_trials', 'comQ3_trials', 'comQ4_trials']
    preserve_unsubmitted_inputs = True

    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        return {
            'treatment': player.participant.treatment,
            'testing': player.session.config['testing'],
            'correlatedAssets': ast.literal_eval(player.correlatedAssets),
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

class clientProfile(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1 or player.round_number == 1 + C.NUM_ROUNDS_PER_CLIENT

    @staticmethod
    def vars_for_template(player):
        if player.round_number == 1:
            clientNum = 1
        else:
            clientNum = 2

        if clientNum == 1:
            clientInfo = player.participant.customer1
        else:
            clientInfo = player.participant.customer2

        print(clientInfo)

        tmpGender = clientInfo['gender']
        tmpAge = clientInfo['age']
        tmpRiskAversion = clientInfo['riskAversion']

        showGender = "female" if tmpGender == 'F' else "male"
        pronoun = "she" if tmpGender == 'F' else "he"
        showRiskAversion = ""
        showAgeText = ""

        if tmpRiskAversion == 'Low':
            showRiskAversion = "I am willing to take above average financial risks expecting to earn above-average returns"
        elif tmpRiskAversion == 'Med':
            showRiskAversion = "I am willing to take average financial risks expecting to earn average returns"
        elif tmpRiskAversion == 'High':
            showRiskAversion = "I am willing to take below average financial risks expecting to earn below-average returns"

        if tmpAge == 'Young':
            showAgeText = "between 18 and 34 years old"
        elif tmpAge == 'Mid':
            showAgeText = "between 35 and 54 years old"
        elif tmpAge == 'Old':
            showAgeText = "above 55 years old"

        return {
            'testing': player.session.config['testing'],
            'clientNum' : clientNum,
            'showGender': showGender,
            'showAgeText': showAgeText,
            'showRiskAversion': showRiskAversion,
            'pronoun': pronoun,
        }


class invPage(Page):
    form_model = 'player'
    preserve_unsubmitted_inputs = True

    @staticmethod
    def get_form_fields(player):
        if is_advice_round(player):
            return ['performancePrediction1', 'performancePrediction2', 'performancePrediction3', 'performancePrediction4', 'performancePrediction5',
             'chart_image', 'adviceSituation', 'adviceAllocation', 'adviceReason', 'showAdviceClicked']

    @staticmethod
    def is_displayed(player: Player):
        if not player.isInitialize:
            player.isInitialize = True
            if player.round_number == 1 or player.round_number == 1 + C.NUM_ROUNDS_PER_CLIENT:
                player.adviseeWealthBOP = 10000 # Start with 10,000 at the beginning of the period
                player.w1 = 0
                player.w2 = 0
                player.w3 = 0
                player.w4 = 0
                player.w5 = 0
                player.w6 = 100

            else:
                prePlayer = player.in_previous_rounds()[-1]
                # Carry over the portfolio weights from the previous period
                player.w1 = prePlayer.w1
                player.w2 = prePlayer.w2
                player.w3 = prePlayer.w3
                player.w4 = prePlayer.w4
                player.w5 = prePlayer.w5
                player.w6 = prePlayer.w6
                
                player.adviseeWealthBOP = get_wealth_update(player)

        return True
    
    @staticmethod
    def js_vars(player):
        thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2
        thisKey = "p1" if thisClient == 1 else "p2"
        currentPeriod = player.round_number - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT # This is the index for the end of the period
        prevPeriod = currentPeriod - 1

        ### PORTFOLIO LOGIC ###

        ## Get Prices for the current and previous period
        prevPrices = inv_trade_prices(player, thisClient, prevPeriod)
        currentPrices = inv_trade_prices(player, thisClient, currentPeriod)

        ## Get the holdings as number of shares
        oldWealth = player.adviseeWealthBOP
        prevDollarHoldings, prevHoldings = get_advisee_holdings(player, oldWealth, player.w1, player.w2, player.w3, player.w4, player.w5, player.w6, prevPeriod)
        
        if currentPeriod > 1:
            prevPlayer = player.in_previous_rounds()[-1]
            oldWealth = prevPlayer.adviseeWealthBOP
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
                label = "Not invested",
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
            'currentState': "Investment" if currentPeriod - C.NUM_PREVRROUNDS >= 0 else "Observation",
            'investmentOptions' : investmentOptions,
            'riskFreeAsset' : riskFreeAsset,
            'initialPortfolio': initialPortfolio,
            'id_in_group': player.id_in_group,
            'assetCharacteristics': assetCharacteristics,
            'isAdvisor': True,
            'isAdviceRound': is_advice_round(player),
            'beliefsBefore': player.participant.beliefsBefore,
        }

    @staticmethod
    def vars_for_template(player):
        ## Get characteristics of the investment options
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

        thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2
        effectiveRound = player.round_number - 1 - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT

        if thisClient == 1:
            clientInfo = player.participant.customer1
        else:
            clientInfo = player.participant.customer2

        tmpGender = clientInfo['gender']
        tmpAge = clientInfo['age']
        tmpRiskAversion = clientInfo['riskAversion']

        showGender = "female" if tmpGender == 'F' else "male"
        pronoun = "she" if tmpGender == 'F' else "he"
        showRiskAversion = ""
        showAgeText = ""

        if tmpRiskAversion == 'Low':
            showRiskAversion = "I am willing to take above average financial risks expecting to earn above-average returns"
        elif tmpRiskAversion == 'Med':
            showRiskAversion = "I am willing to take average financial risks expecting to earn average returns"
        elif tmpRiskAversion == 'High':
            showRiskAversion = "I am willing to take below average financial risks expecting to earn below-average returns"

        if tmpAge == 'Young':
            showAgeText = "between 18 and 34 years old"
        elif tmpAge == 'Mid':
            showAgeText = "between 35 and 54 years old"
        elif tmpAge == 'Old':
            showAgeText = "above 55 years old"

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
            'advicePeriod': is_advice_round(player),
            'currentPeriod': effectiveRound + 1 - C.NUM_PREVRROUNDS,
            'thisClient': thisClient,
            'showGender': showGender,
            'pronoun': pronoun,
            'showRiskAversion': showRiskAversion,
            'showAgeText': showAgeText,
        }

    @staticmethod
    async def live_method(player, data):
        if data['type'] == 'advice':
            if player.participant.treatment != 1: ## Only for treatment 1
                yield {
                    player.id_in_group: ""
                }
            
            chart_image = data['chart_image']
            ## Send prompt to OpenAI --> needs to be done here to have the chart image available
            player.chart_image = chart_image

            ## Generate the investment advice
            advice = ""
            if is_advice_round(player):
                ## Get client profile
                thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2
                thisKey = "p1" if thisClient == 1 else "p2"
                currentPeriod = player.round_number - (thisClient - 1) * C.NUM_ROUNDS_PER_CLIENT

                if thisClient == 1:
                    clientInfo = player.participant.customer1
                else:
                    clientInfo = player.participant.customer2
                
                tmpGender = clientInfo['gender']
                tmpAge = clientInfo['age']
                tmpRiskAversion = clientInfo['riskAversion']

                showGender = "female" if tmpGender == 'F' else "male"
                showRiskAversion = ""
                showAgeText = ""

                if tmpRiskAversion == 'Low':
                    showRiskAversion = "I am willing to take above average financial risks expecting to earn above-average returns"
                elif tmpRiskAversion == 'Med':
                    showRiskAversion = "I am willing to take average financial risks expecting to earn average returns"
                elif tmpRiskAversion == 'High':
                    showRiskAversion = "I am willing to take below average financial risks expecting to earn below-average returns"

                if tmpAge == 'Young':
                    showAgeText = "between 18 and 34 years old"
                elif tmpAge == 'Mid':
                    showAgeText = "between 35 and 54 years old"
                elif tmpAge == 'Old':
                    showAgeText = "above 55 years old"

                # Get price development
                prices_data = {
                    'Option 1': ast.literal_eval(player.participant.investmentOption1Prices[thisKey])[:currentPeriod + 1],
                    'Option 2': ast.literal_eval(player.participant.investmentOption2Prices[thisKey])[:currentPeriod + 1],
                    'Option 3': ast.literal_eval(player.participant.investmentOption3Prices[thisKey])[:currentPeriod + 1],
                    'Option 4': ast.literal_eval(player.participant.investmentOption4Prices[thisKey])[:currentPeriod + 1],
                    'Option 5': ast.literal_eval(player.participant.investmentOption5Prices[thisKey])[:currentPeriod + 1],
                }

                tmpPrices = pd.DataFrame(prices_data)
                tmpPrices.index.name = "Year"

                prompt = generate_prompt(player, showAgeText, showGender, showRiskAversion, tmpPrices, player.chart_image)
                if not player.adviceChat:
                    advice = await generate_text(prompt)           
                    player.adviceChat = json.dumps(advice)
                    player.prompt = str(prompt)

                    print(player.prompt)
                    print(player.adviceChat)

                ## Create structured advice for page
                retAdvice = create_structured_advice(player.adviceChat)
                yield {
                    player.id_in_group: {
                        'type': 'advice',
                        'advice': retAdvice,
                    }
                }
        else:
            if data['type'] == 'changeShares':
                newAllocation, newNumShares, newHoldings = updatePortfolio(player, data, 'change')
            elif data['type'] == 'setShares':
                newAllocation, newNumShares, newHoldings = updatePortfolio(player, data, 'set')

            retData = {
                'type': 'portfolio',
                'portfolio': {
                    'dollarHoldings': newHoldings,
                    'numShares': newNumShares,
                    'allocation': newAllocation,}
            }

            player.adviceAllocation = str(newAllocation) ## Only updated in allocation rounds
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
        return player.round_number == C.NUM_ROUNDS_PER_CLIENT or player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player):
        thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2

        finalWealth = player.adviseeWealthBOP

        return {
            'testing': player.session.config['testing'],
            'clientNum' : thisClient,
            'finalWealth': finalWealth,
        }
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        paidClient = player.participant.paidCustomer
        thisClient = 1 if player.round_number <= C.NUM_ROUNDS_PER_CLIENT else 2

        if paidClient == thisClient:
            player.participant.payoffWealth = player.adviseeWealthBOP
        


#### PAGE SEQUENCE ####

page_sequence = [
    startPage,
    explanations,
    compQuestions, 
    atnQuest,
    attentionScreen,
    clientProfile,
    invPage,
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
    lastWealth = prevPlayer.adviseeWealthBOP

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

    totalWealth = player.adviseeWealthBOP

    dollarHoldings = [allocation[i] * totalWealth / 100 for i in range(len(allocation))]
    currentPrices = inv_trade_prices(player, thisClient, currentPeriod)

    numShares = [dollarHoldings[i] / currentPrices[i] for i in range(len(dollarHoldings))]


    newHoldings = dollarHoldings.copy()
    newNumShares = numShares.copy()

    if inType == 'change':
        ## Button was used to change holdings / shares
        changedAsset = int(data['asset']) - 1
        direction = data['direction']

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
        "reason": {"type": "string"},
    },
    "required": ["situation", "allocation", "reason"],
    "$defs": {
        "asset": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "percentage": {"type": "number"},
                "expected_outcome": {"type": "number"},
            },
            "required": [
                "percentage",
                "expected_outcome",
            ],
        },
        "not_invested": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "percentage": {"type": "number"},
                "expected_outcome": {"type": "number"},
            },
            "required": ["percentage", "expected_outcome"],
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

                
def generate_prompt(player, ageText, genderText, riskAversionText, prices, chart):
    tmpOrder = player.participant.assetOrder
    assetDictionary = assetParams.assetDictionary

    # Prepare assetParameters as a list of dicts, then convert to DataFrame and format columns as needed for prompt
    assetParameters_list = [
        {
            'Price increase (%)': assetDictionary[i]['x_up'] * 100,
            'Price decrease (%)': assetDictionary[i]['x_down'] * 100,
            'Chance of price increase (%)': assetDictionary[i]['p_up'] * 100,  # display as percentage
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

    prompt = f"""
    Your client is { genderText } and { ageText }.
    
    In addition, when asked "Which of the following statements comes closest to describing the amount of financial risk that you are willing to take when you save or make investments?"
    your client answered "{ riskAversionText }".

    Your client has five different investment options (Option 1 to Option 5). 
    Uninvested wealth does not earn any interest.
    
    In each period, the price of each option can either increase or decrease with a known probability.
    {json.dumps(assetParameters_json, indent=2)}

    The price changes of all investment options except for Option 
    { correlatedAssets[0] } and Option 
    { correlatedAssets[1] } are independent of each other. 
    Options { correlatedAssets[0] } and { correlatedAssets[1] } are 
    correlated with a correlation coefficient of { corrCoeff }, 
    which means that the
    price of Option { correlatedAssets[0] } 
    tends to decrease when the price of Option { correlatedAssets[1] } increases,
    and vice versa.

    Moreover, all price changes are independent of previous periods. 
    Before the experiment, a computer has 
    randomly determined the price changes for each period according to the 
    specific probabilities of each investment option. 
    This also means that the client's choices do not influence how prices change.

    All this information is known to you and your client.

    **Recent price history:**
    {json.dumps(assetPrices_json, indent=2)}

    Your client has also reviewed a chart of the price history (attached), and knows 
    the properties of the investment options.

    ---

    Based on this, write a brief, personalized investment recommendation for this client. 

    - **situation**: Start the advice by briefly summarizing the situation, mentioning characteristics of the advisee or the options as you wish. Keep the description short and concise.
    - **allocation**: For each option, specify the recommended portfolio weight in percentage of total wealth. The remaining wealth is not invested. 
    - **reason**: Please give a short explanation for your recommendation.

    In addition, for each option, please answer the following question: 
    "Suppose you invest $1,000.00 into this option. How much money do you expect to have in five periods?"
    Save this information in the "expected_outcome" field of the allocation entry for each option.
    """

    input_data = [
        {
            "role": "system",
            "content": "You are a financial advisor certified in Canada, meeting with a client for investment advice."
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
        'Not invested': _advice_allocation_row_payload(alloc['Not invested']),
    }
    retAdvice['reason'] = tmpAdvice['reason']
    return retAdvice