from otree.api import *
import random
import numpy as np
import requests
import pandas as pd

from otree.settings import RECAPTCHA_SECRET_KEY, RECAPTCHA_SITE_KEY

doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'welcome'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    NUM_TREATMENTS = 4

    SAMPLE_FRUITS = ['C', 'R', 'Z', 'V', 'Y', 'N', 'R', 'P']
    SAMPLE_AUDIO = ['Country', 'Government', 'People', 'Question', 'Service']


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass

##### TREATMENT ASSIGNMENT #####

def creating_session(subsession):
    if subsession.round_number == 1:
        for player in subsession.get_players():
            # Assign order of trust game
            trustGameOrder = random.choice([0, 1])
            player.trustGameOrder = trustGameOrder
            player.participant.trustGameOrder = trustGameOrder

            ## Attention Checks
            player.fruit = random.choice(C.SAMPLE_FRUITS)
            player.audio_file = random.choice(C.SAMPLE_AUDIO)

            ## Determine if asked for beliefs before or after the investment task
            beliefsBefore = random.choice([True, False])
            player.participant.beliefsBefore = beliefsBefore

            if player.session.config['testing']:
                usableID = player.participant.id_in_session - 1

                # Assign treatment
                treatment = usableID % C.NUM_TREATMENTS ## 0 - No Advice,1 - FP; 2 - FP + ChatGPT; 3 - ChatGPT
                player.participant.treatment = treatment

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
    priceChart = models.IntegerField()
    trustGameOrder = models.IntegerField()

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

    '''
    @staticmethod
    def is_displayed(Player):
        return not Player.session.config['testing']
    '''

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
