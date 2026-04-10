from otree.api import *
import random
import numpy as np
import requests
import pandas as pd
import ast

from otree.settings import RECAPTCHA_SECRET_KEY, RECAPTCHA_SITE_KEY

doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'startPages'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    NUM_TREATMENTS = 4

    SAMPLE_FRUITS = ['C', 'R', 'Z', 'V', 'Y', 'N', 'R', 'P']
    SAMPLE_AUDIO = ['Country', 'Government', 'People', 'Question', 'Service']

    fpAssignments = pd.read_csv('_static/fp/fp_master_table.csv')




class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass

##### TREATMENT ASSIGNMENT #####

def creating_session(subsession):
    if subsession.round_number == 1:
        for player in subsession.get_players():
            fpID = player.participant.id_in_session

            # Find the row in fpAssignments where the fpID matches, and retrieve that row
            assignmentRow = C.fpAssignments.loc[C.fpAssignments['fp_id'] == fpID]

            aiTreatment = assignmentRow['ai'].values[0]

            ## Get customer 1 information
            customer1 = assignmentRow['cell_1'].values[0]
            customer1Info = {
                'gender': assignmentRow['cell_1_gender'].values[0],
                'age': assignmentRow['cell_1_age'].values[0],
                'riskAversion': assignmentRow['cell_1_risk_av'].values[0],
            }

            ## Get customer 2 information
            customer2 = assignmentRow['cell_2'].values[0]
            customer2Info = {
                'gender': assignmentRow['cell_2_gender'].values[0],
                'age': assignmentRow['cell_2_age'].values[0],
                'riskAversion': assignmentRow['cell_2_risk_av'].values[0],
            }

            ## Get path information
            path1 = assignmentRow['path_1'].values[0]
            path1Info = {
                1: assignmentRow['IndAsset_p1'].values[0],
                2: assignmentRow['Dominated_p1'].values[0],
                3: assignmentRow['PosSkew_p1'].values[0],
                4: assignmentRow['NegSkew_p1'].values[0],
                5: assignmentRow['Hedge_p1'].values[0],
            }

            path2 = assignmentRow['path_2'].values[0]
            path2Info = {
                1: assignmentRow['IndAsset_p2'].values[0],
                2: assignmentRow['Dominated_p2'].values[0],
                3: assignmentRow['PosSkew_p2'].values[0],
                4: assignmentRow['NegSkew_p2'].values[0],
                5: assignmentRow['Hedge_p2'].values[0],
            }

            ## Get pay information
            pay = assignmentRow['pay'].values[0]
            payCustomer = assignmentRow['pay_customer'].values[0]

            ## Randomize the order of the assets on an individual level
            shuffled_options = ast.literal_eval(assignmentRow['assetOrder'].values[0])

            ## Save information to player
            player.treatment = int(aiTreatment)
            player.customer1 = int(customer1)
            player.customer1Info = str(customer1Info)
            player.customer2 = int(customer2)
            player.customer2Info = str(customer2Info)
            player.path1 = int(path1)
            player.path1Info = str(path1Info)
            player.path2 = int(path2)
            player.path2Info = str(path2Info)
            player.shuffledOptions = str(shuffled_options)
            
            ## Save information to participant
            player.participant.treatment = aiTreatment
            player.participant.customer1 = customer1Info
            player.participant.customer2 = customer2Info
            player.participant.path1 = path1Info
            player.participant.path2 = path2Info
            player.participant.assetOrder = shuffled_options

            player.participant.investmentOption1Prices = {
                'p1': path1Info[shuffled_options[0]],
                'p2': path2Info[shuffled_options[0]],
            }
            
            player.participant.investmentOption2Prices = {
                'p1': path1Info[shuffled_options[1]],
                'p2': path2Info[shuffled_options[1]],
            }
            
            player.participant.investmentOption3Prices = {
                'p1': path1Info[shuffled_options[2]],
                'p2': path2Info[shuffled_options[2]],
            }

            player.participant.investmentOption4Prices = {
                'p1': path1Info[shuffled_options[3]],
                'p2': path2Info[shuffled_options[3]],
            }

            player.participant.investmentOption5Prices = {
                'p1': path1Info[shuffled_options[4]],
                'p2': path2Info[shuffled_options[4]],
            }

            ## Save pay information to participant
            player.participant.isPaid = pay
            player.participant.paidCustomer = payCustomer

            ## Attention Checks
            player.fruit = random.choice(C.SAMPLE_FRUITS)
            player.audio_file = random.choice(C.SAMPLE_AUDIO)

            ## Determine if asked for beliefs before or after the investment task
            beliefsBefore = random.choice([True, False])
            player.participant.beliefsBefore = beliefsBefore

##### DEFINE FUNCTIONS #####

def recaptcha_valid(response_token):
        # Test if captcha is valid
        res = requests.post("https://www.google.com/recaptcha/api/siteverify", data={
            'secret': RECAPTCHA_SECRET_KEY,
            'response': response_token
        })
        return res.json()["success"]


class Player(BasePlayer):
    prolID = models.StringField(label='Please enter your Prolific ID:', min_length=24, max_length=24)
    treatment = models.IntegerField()
    customer1 = models.IntegerField()
    customer1Info = models.StringField()
    customer2 = models.IntegerField()
    customer2Info = models.StringField()
    path1 = models.IntegerField()
    path1Info = models.StringField()
    path2 = models.IntegerField()
    path2Info = models.StringField()
    shuffledOptions = models.StringField()

    investmentOption1Prices = models.StringField()
    investmentOption2Prices = models.StringField()
    investmentOption3Prices = models.StringField()
    investmentOption4Prices = models.StringField()
    investmentOption5Prices = models.StringField()

    # ReCaptcha Verification
    captchaVerified = models.BooleanField(initial=False)

    # Attention Checks
    fruit = models.StringField(initial='blank')
    audio_file = models.StringField(initial='blank')
    
    answer_fruit = models.StringField(label='', max_length=1)
    answer_her = models.IntegerField(
        label='',
        choices=[[1, "Tatyana's mother"], [2, "Grandma"], [3, "Tatyana"]],
        widget=widgets.RadioSelect,
    )
    answer_audio = models.StringField(label='', max_length=10)

    attention_fruit = models.BooleanField(initial=False)
    attention_her = models.BooleanField(initial=False)
    attention_audio = models.BooleanField(initial=False)
    all_attention_checks = models.BooleanField(initial=False)

# PAGES
class welcomePage(Page):
    form_model = 'player'
    form_fields = ['prolID']

    def vars_for_template(player):
        return {
            'testing': player.session.config['testing']
        }

    def is_displayed(player):
        return True

class enterCaptcha(Page):
    def vars_for_template(player):
        return dict(
            site_key = RECAPTCHA_SITE_KEY,
        )

    def live_method(player, data):
        if recaptcha_valid(data["response_token"]):
            player.captchaVerified = True
        return {player.id_in_group: player.captchaVerified}

    @staticmethod
    def error_message(player, values):
        if not player.captchaVerified:
            return 'You did not solve the captcha.'

    @staticmethod
    def is_displayed(player):
        return not player.session.config['testing']


class attentionCheck_Fruit(Page):
    form_model = 'player'
    form_fields = ['answer_fruit']

    @staticmethod
    def vars_for_template(player):
        fruitletter = dict(
            dict(
                zip(
                    ['C', 'R', 'Z', 'V', 'Y', 'N', 'R', 'P'],
                    [
                        'apple',
                        'strawberry',
                        'mango',
                        'raspberry',
                        'blueberry',
                        'blackberry',
                        'avocado',
                        'tangerine',
                    ],
                )
            )
        )
        for i in fruitletter:
            if player.fruit == i:
                return {'fruit': fruitletter.get(i),
                        'testing': player.session.config["testing"]}

    @staticmethod
    def js_vars(player):
        fruitletter = dict(
            dict(
                zip(
                    ['C', 'R', 'Z', 'V', 'Y', 'N', 'R', 'P'],
                    [
                        'apple',
                        'strawberry',
                        'mango',
                        'raspberry',
                        'blueberry',
                        'blackberry',
                        'avocado',
                        'tangerine',
                    ],
                )
            )
        )

        for i in fruitletter:
            if player.fruit == i:
                return dict(
                    fruit = fruitletter.get(i),
                    fruitletter = fruitletter,
                )                 
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.attention_fruit = (player.fruit == player.answer_fruit.upper())

class attentionCheck_Her(Page):
    form_model = 'player'
    form_fields = ['answer_her']
    
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):

        return {
                'testing': player.session.config["testing"]}
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.attention_her = (player.answer_her == 1)

class attentionCheck_Audio(Page):
    form_model = 'player'
    form_fields = ['answer_audio']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        
        audio_path='global/audio/{}.mp3'.format(player.audio_file)

        return {
                'audio_file': audio_path,
                'testing': player.session.config["testing"]}

    @staticmethod
    def js_vars(player):
        return {
                'solution_audio': player.audio_file,
                'testing': player.session.config["testing"]}

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.attention_audio = (player.audio_file.upper() == player.answer_audio.upper())

        if (player.attention_fruit and player.attention_her and player.attention_audio):
            player.all_attention_checks = True
        else:
            player.all_attention_checks = False

class attentionCheck_Results(Page):
    @staticmethod
    def is_displayed(player):
        return not player.all_attention_checks 

page_sequence = [
    welcomePage,
    enterCaptcha,
    attentionCheck_Fruit,
    attentionCheck_Her,
    attentionCheck_Audio,
    attentionCheck_Results
]
