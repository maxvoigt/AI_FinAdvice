from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'demographics_before'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 2  #We do the trust game twice, once for the financial advisor and once for the AI


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    gender = models.IntegerField(label='What is your gender?', 
        choices=[
            [1, 'Male'],
            [2, 'Female'],
            [3, 'Prefer to self-describe'],
            [4, 'Prefer not to say'],
        ]
    )

    gender_other = models.StringField(label='If you prefer to self-describe, please specify:', blank=True)

    age = models.IntegerField(label='What is your age?', min=18, max=100)

    territory = models.IntegerField(label='Which province or territory do you live in?',
        choices=[
            [1, 'British Columbia'],
            [2, 'Alberta'],
            [3, 'Saskatchewan'],
            [4, 'Manitoba'],
            [5, 'Ontario'],
            [6, 'Quebec'],
            [7, 'New Brunswick'],
            [8, 'Nova Scotia'],
            [9, 'Prince Edward Island'],
            [10, 'Newfoundland and Labrador'],
            [11, 'Northwest Territories'],
            [12, 'Nunavut'],
            [13, 'Yukon'],
            [14, 'None of the above'],
        ]
    )

    income = models.IntegerField(
        label='What is your best estimate of your personal income for 2025, from all sources, before taxes and deductions?',
        min=0,
        max=10000000,
        blank=True
    )

    income_choice = models.BooleanField(initial=False)

    income_bracket = models.IntegerField(
        label='If you are not sure of the exact amount, please select the range that best describes your total household income in 2025, before taxes and deductions.',
        choices=[
            [0, 'Less than $30,000'],
            [1, '$30,000 - $59,999'],
            [2, '$60,000 - $89,999'],
            [3, '$90,000 - $119,999'],
            [4, 'More than $120,000'],
            [30, 'I do not know'],
            [40, 'I prefer not to say'],
        ],
        blank=True
    )

    householdSize = models.IntegerField(
        label='Including yourself, how many people living in your household are supported by this income?',
        choices=[
            [1, '1'],
            [2, '2'],
            [3, '3'],
            [4, '4'],
            [5, '5'],
            [6, '6'],
            [7, '7'],
            [8, '8'],
            [9, '9'],
            [10, '10'],
            [11, '11'],
            [12, '12'],
            [13, '13'],
            [14, '14'],
            [15, '15'],
            [16, '16'],
            [17, '17'],
            [18, '18'],
            [19, '19'],
            [20, '20'],
            [30, 'I do not know'],
            [40, 'I prefer not to say'],
        ]
    )

    patience = models.IntegerField(
        label = "Please evaluate your patience when it comes to making financial decisions for yourself or your household.",
        choices = [
            [1, 'Very impatient'],
            [2, 'Impatient'],
            [3, 'Patient'],
            [4, 'Very patient'],
            [5, 'I don\'t know'],
        ])
    
    finRiskTaking = models.IntegerField(
        label = "Which of the following statements comes closest to describing the amount of financial risk that you are willing to take when you save or make investments?",
        choices = [
            [1, 'I am willing to take substantial financial risks expecting to earn substantial returns.'],
            [2, 'I am willing to take above average financial risks expecting to earn above-average returns.'],
            [3, 'I am willing to take average financial risks expecting to earn average returns.'],
            [4, 'I am willing to take below average financial risks expecting to earn below-average returns.'],
            [5, 'I am not willing to take any risk, knowing I will earn a small but certain return.'],
        ])

    amount_to_send_finAdvisor = models.IntegerField(
        label = 'In this situation, how much of your $1,000 do you want to send?',
        choices = [
            [0, '$0'],
            [100, '$100'],
            [200, '$200'],
            [300, '$300'],
            [400, '$400'],
            [500, '$500'],
            [600, '$600'],
            [700, '$700'],
            [800, '$800'],
            [900, '$900'],
            [1000, '$1000'],
        ]
    )
    
    amount_to_send_AI = models.IntegerField(
        label = 'In this situation, how much of your $1,000 do you want to send?',
        choices = [
            [0, '$0'],
            [100, '$100'],
            [200, '$200'],
            [300, '$300'],
            [400, '$400'],
            [500, '$500'],
            [600, '$600'],
            [700, '$700'],
            [800, '$800'],
            [900, '$900'],
            [1000, '$1000'],
        ]
    )
    
    
# PAGES
class startPage(Page):
    def is_displayed(player):
        return player.round_number == 1

class demographicsPage(Page):
    preserve_unsubmitted_inputs = True
    form_model = 'player'
    form_fields = ['age', 'gender', 'gender_other', 'territory', 'income', 'income_choice', 'income_bracket', 'householdSize', 'patience', 'finRiskTaking']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
        }
    
    
    @staticmethod
    def error_message(player, values):
        choice = values.get('income_choice')
        income = values.get('income')
        bracket = values.get('income_bracket')
        gender = values.get('gender')
        gender_other = values.get('gender_other')
        
        # `income_choice` is a BooleanField:
        # - True  => user prefers not to say income amount => must choose `income_bracket`
        # - False => user enters an amount            => must choose `income`
        #
        # Note: both `income` and `income_bracket` can legitimately be 0, so we must check
        # against `is None` (not truthiness).
        if choice is True:
            if bracket is None:
                return "Please select an income range."
        elif choice is False:
            if income is None:
                return "Please enter your income."
        
        if gender == 3:
            if not (isinstance(gender_other, str) and gender_other.strip()):
                return "Please specify your gender."

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.age = player.age
        player.participant.gender = player.gender
        player.participant.riskAversion = player.finRiskTaking

class trustGame(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if player.participant.trustGameOrder + 1 == player.round_number:
            return ['amount_to_send_finAdvisor']
        else:
            return ['amount_to_send_AI']

    def vars_for_template(player):
        if player.participant.trustGameOrder + 1 == player.round_number:
            partner_type = 'a financial advisor'
            partner_type_text = 'financial advisor'
        else:
            partner_type = 'a generative AI system, such as ChatGPT'
            partner_type_text = 'generative AI system'
        

        return {
            'partner_type': partner_type,
            'partner_type_text': partner_type_text,
            'round_number': player.round_number,
            'testing': player.session.config['testing']
        }

page_sequence = [
    startPage,
    demographicsPage,
    trustGame
    ]
