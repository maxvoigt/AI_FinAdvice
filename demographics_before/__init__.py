from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'demographics_before'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    age = models.IntegerField(label='What is your age?')
    gender = models.StringField(label='What is your gender?', 
        choices=['Male', 'Female', 'Non-binary / third gender', 'Prefer not to say'])
    income = models.IntegerField(
        label='What is your best estimate of your personal income for 2025, from all sources, before taxes and deductions?',
        choices = [
            [0, 'Less than $30,000'],
            [1, '$30,000 - $60,000'],
            [2, '$60,000 - $90,000'],
            [3, '$90,000 - $120,000'],
            [4, '$120,000 - $150,000'],
            [5, 'More than $150,000'],
            [6, 'Prefer not to say'],]
        )

    financial_knowledge = models.IntegerField(
        label = 'Overall, how would you rate your knowledge about investing ? [1 – low, 7 – high]',
        choices=[1, 2, 3, 4, 5, 6, 7],
        widget=widgets.RadioSelectHorizontal
        )

    amount_to_send = models.IntegerField(
        label = 'Suppose you were selected to be Participant A and had the choice to send any amount that is a multiple of $100.',
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

    return_amount_100 = models.IntegerField(
        label = 'If participant A had sent $100, I would like to return:',
        choices = [
            [0, '$0'],
            [100, '$100'],
            [200, '$200'],
            [300, '$300'],
        ])
    return_amount_200 = models.IntegerField(
        label = 'If participant A had sent $200, I would like to return:',
        choices = [
            [0, '$0'],
            [100, '$100'],
            [200, '$200'],
            [300, '$300'],
            [400, '$400'],
            [500, '$500'],
            [600, '$600'],
        ])
    return_amount_300 = models.IntegerField(
        label = 'If participant A had sent $300, I would like to return:',
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
        ])
    return_amount_400 = models.IntegerField(
        label = 'If participant A had sent $400, I would like to return:',
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
            [1100, '$1100'],
            [1200, '$1200'],
        ])

    return_amount_500 = models.IntegerField(
        label = 'If participant A had sent $500, I would like to return:',
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
            [1100, '$1100'],
            [1200, '$1200'],
            [1300, '$1300'],
            [1400, '$1400'],
            [1500, '$1500'],
        ])

    return_amount_600 = models.IntegerField(
        label = 'If participant A had sent $600, I would like to return:',
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
            [1100, '$1100'],
            [1200, '$1200'],
            [1300, '$1300'],
            [1400, '$1400'],
            [1500, '$1500'],
            [1600, '$1600'],
            [1700, '$1700'],
            [1800, '$1800'],
        ])

    return_amount_700 = models.IntegerField(
        label = 'If participant A had sent $700, I would like to return:',
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
            [1100, '$1100'],
            [1200, '$1200'],
            [1300, '$1300'],
            [1400, '$1400'],
            [1500, '$1500'],
            [1600, '$1600'],
            [1700, '$1700'],
            [1800, '$1800'],
            [1900, '$1900'],
            [2000, '$2000'],
            [2100, '$2100'],
        ])
    
    return_amount_800 = models.IntegerField(
        label = 'If participant A had sent $800, I would like to return:',
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
            [1100, '$1100'],
            [1200, '$1200'],
            [1300, '$1300'],
            [1400, '$1400'],
            [1500, '$1500'],
            [1600, '$1600'],
            [1700, '$1700'],
            [1800, '$1800'],
            [1900, '$1900'],
            [2000, '$2000'],
            [2100, '$2100'],
            [2200, '$2200'],
            [2300, '$2300'],
            [2400, '$2400'],
        ])

    return_amount_900 = models.IntegerField(
        label = 'If participant A had sent $900, I would like to return:',
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
            [1100, '$1100'],
            [1200, '$1200'],
            [1300, '$1300'],
            [1400, '$1400'],
            [1500, '$1500'],
            [1600, '$1600'],
            [1700, '$1700'],
            [1800, '$1800'],
            [1900, '$1900'],
            [2000, '$2000'],
            [2100, '$2100'],
            [2200, '$2200'],
            [2300, '$2300'],
            [2400, '$2400'],
            [2500, '$2500'],
            [2600, '$2600'],
            [2700, '$2700'],
        ])

    return_amount_1000 = models.IntegerField(
        label = 'If participant A had sent $1000, I would like to return:',
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
            [1100, '$1100'],
            [1200, '$1200'],
            [1300, '$1300'],
            [1400, '$1400'],
            [1500, '$1500'],
            [1600, '$1600'],
            [1700, '$1700'],
            [1800, '$1800'],
            [1900, '$1900'],
            [2000, '$2000'],
            [2100, '$2100'],
            [2200, '$2200'],
            [2300, '$2300'],
            [2400, '$2400'],
            [2500, '$2500'],
            [2600, '$2600'],
            [2700, '$2700'],
            [2800, '$2800'],
            [2900, '$2900'],
            [3000, '$3000'],
        ])

    generalTrust = models.IntegerField(
        label = "Generally speaking, would you say that most people can be trusted or that you can't be too careful in dealing with people?",
        choices = [
            [1, 'Most people can be trusted'],
            [2, 'Can\'t be too careful'],
            [3, 'Don\'t know'],
        ])

    algoAversion = models.IntegerField(
        label = "In general, how useful has ChatGPT (or similar artificial intelligence systems) been for you? [1 - not at all, 7 - very useful]",
        choices=[1, 2, 3, 4, 5, 6, 7],
        widget=widgets.RadioSelectHorizontal
        )
        
    algoTrustInvestment = models.IntegerField(
        label = "In general, do you trust computer programs in financial matters? [1 - not at all, 7 - very much]",
        choices=[1, 2, 3, 4, 5, 6, 7],
        widget=widgets.RadioSelectHorizontal
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


# PAGES
class startPage(Page):
    def is_displayed(player):
        return player.round_number == 1

class demographicsPage(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'income', 'financial_knowledge']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing']
        }

class trustGame(Page):
    form_model = 'player'
    form_fields = ['amount_to_send', 'return_amount_100', 'return_amount_200', 'return_amount_300', 'return_amount_400', 'return_amount_500', 'return_amount_600', 'return_amount_700', 'return_amount_800', 'return_amount_900', 'return_amount_1000']

    def vars_for_template(player):
        tmpTreatment = player.participant.treatment
        partner_type = ''
        
        if tmpTreatment == 0:
            partner_type = 'another participant'
        elif tmpTreatment == 1:
            partner_type = 'a financial advisor'
        elif tmpTreatment >= 2:
            partner_type = 'a generative AI system, such as ChatGPT'

        return {
            'partner_type': partner_type,
            'testing': player.session.config['testing']
        }

class attitudesPage(Page):
    form_model = 'player'
    form_fields = ['generalTrust', 'algoAversion', 'algoTrustInvestment', 'patience', 'finRiskTaking']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing']
        }

page_sequence = [
    startPage,
    demographicsPage,
    trustGame,
    attitudesPage
    ]
