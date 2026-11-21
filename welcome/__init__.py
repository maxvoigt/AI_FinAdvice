from otree.api import *
import random
import numpy as np
import requests
import pandas as pd

from otree.settings import RECAPTCHA_SECRET_KEY, RECAPTCHA_SITE_KEY

doc = """
Your app description
"""

FRUITS = {
    # letter: (English, French incl. article "de la / du / de l'")
    'C': ('apple',      'de la pomme'),
    'R': ('avocado',    "de l'avocat"),     # check image, see note above
    'Z': ('mango',      'de la mangue'),
    'V': ('raspberry',  'de la framboise'),
    'Y': ('blueberry',  'du bleuet'),
    'N': ('blackberry', 'de la mûre'),
    'P': ('tangerine',  'de la mandarine'),
}

AUDIO_FR = {'Country': 'Pays', 'Government': 'Gouvernement', 
            'People': 'Population', 'Question': 'Question'}

class C(BaseConstants):
    NAME_IN_URL = 'welcome'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    NUM_TREATMENTS = 4

    SAMPLE_FRUITS = ['C', 'R', 'Z', 'V', 'Y', 'N', 'R', 'P']
    SAMPLE_AUDIO = ['Country', 'Government', 'People', 'Question']


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

            ## Determine when asked for beliefs
            player.participant.beliefsRound = random.choice([1, 2]) # Asked after first or second choice
            

##### DEFINE FUNCTIONS #####
def recaptcha_valid(response_token):
        # Test if captcha is valid
        res = requests.post("https://www.google.com/recaptcha/api/siteverify", data={
            'secret': RECAPTCHA_SECRET_KEY,
            'response': response_token
        })
        return res.json()["success"]


class Player(BasePlayer):
    priceChart = models.IntegerField()
    trustGameOrder = models.IntegerField()

    # ReCaptcha Verification
    captchaVerified = models.BooleanField(initial=False)

    # Attention Checks
    fruit = models.StringField(initial='blank')
    audio_file = models.StringField(initial='blank')
    
    answer_fruit = models.StringField(label='', max_length=1)
    answer_her = models.IntegerField(label='', widget=widgets.RadioSelect)
    answer_audio = models.StringField(label='', max_length=20)

    attention_fruit = models.BooleanField(initial=False)
    attention_her = models.BooleanField(initial=False)
    attention_audio = models.BooleanField(initial=False)
    all_attention_checks = models.BooleanField(initial=False)

    browser_first = models.StringField(initial='', blank=True)

### French language responses
def answer_her_choices(player):
    if player.participant.lang == 'fr':
        return [[1, 'La mère de Tatyana'], [2, 'Grand-maman'], [3, 'Tatyana']]
    return [[1, "Tatyana's mother"], [2, 'Grandma'], [3, 'Tatyana']]


# PAGES
class welcomePage(Page):
    form_model = 'player'
    form_fields = ['browser_first']

    @staticmethod
    def is_displayed(player):
        return player.session.config.get('recruiter') != 'prolific'

    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'lang': player.participant.lang
        }

class welcomePage_Prolific(Page):
    form_model = 'player'
    form_fields = ['browser_first']

    @staticmethod
    def is_displayed(player):
        return player.session.config.get('recruiter') == 'prolific'

    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'lang': player.participant.lang
        }


class enterCaptcha(Page):
    def vars_for_template(player):
        return dict(
            site_key = RECAPTCHA_SITE_KEY,
            lang = player.participant.lang
        )

    def live_method(player, data):
        if recaptcha_valid(data["response_token"]):
            player.captchaVerified = True
        return {player.id_in_group: player.captchaVerified}

    @staticmethod
    def error_message(player, values):
        if not player.captchaVerified: 
            if player.participant.lang == 'fr':
                return "Vous n'avez pas complété correctement la vérification du CAPTCHA."
            return 'You did not solve the captcha.'

class attentionCheck_Fruit(Page):
    form_model = 'player'
    form_fields = ['answer_fruit']

    @staticmethod
    def vars_for_template(player):
        en, fr = FRUITS[player.fruit]
        return {
            'fruit': fr if player.participant.lang == 'fr' else en,
            'lang': player.participant.lang,
            'testing': player.session.config['testing'],
        }

    @staticmethod
    def js_vars(player):
        return dict(fruit=FRUITS[player.fruit][0],
                    fruitletter={k: v[0] for k, v in FRUITS.items()})              
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.attention_fruit = (player.fruit == (player.answer_fruit or '').upper())

class attentionCheck_Her(Page):
    form_model = 'player'
    form_fields = ['answer_her']
    
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config["testing"],
            'lang': player.participant.lang,
            }
    
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
        if player.participant.lang == 'fr':
            audio_path = 'global/audio/fr/{}.mp3'.format(AUDIO_FR[player.audio_file])
        else:
            audio_path = 'global/audio/{}.mp3'.format(player.audio_file)

        return {
                'audio_file': audio_path,
                'testing': player.session.config["testing"],
                'lang': player.participant.lang,
                }

    @staticmethod
    def js_vars(player):
        return {
                'solution_audio': audio_solution(player),
                'testing': player.session.config["testing"]}

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.attention_audio = (_norm_word(audio_solution(player)) == _norm_word(player.answer_audio))
        player.all_attention_checks = bool(player.attention_fruit and player.attention_her and player.attention_audio)

class attentionCheck_Results(Page):
    @staticmethod
    def is_displayed(player):
        return not player.all_attention_checks 
    
    @staticmethod
    def vars_for_template(player):
        return {
            'lang': player.participant.lang,
            'recruiter': player.session.config.get('recruiter'),
        }

page_sequence = [
    welcomePage,
    welcomePage_Prolific,
    enterCaptcha,
    attentionCheck_Fruit,
    attentionCheck_Her,
    attentionCheck_Audio,
    attentionCheck_Results
]

### Attention helpers
import unicodedata
def _norm_word(s):
    s = unicodedata.normalize('NFKD', (s or '').strip().upper())
    return ''.join(c for c in s if not unicodedata.combining(c))

def audio_solution(player):
    return AUDIO_FR[player.audio_file] if player.participant.lang == 'fr' else player.audio_file
