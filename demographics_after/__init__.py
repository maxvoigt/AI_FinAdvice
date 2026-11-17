from otree.api import *


doc = """
Your app description
"""


GENAI_USAGE_CHOICES = [
    [1, 'Never'],
    [2, 'Rarely (less than once a month)'],
    [3, 'Sometimes (a few times a month)'],
    [4, 'Often (weekly or more)'],
]


class C(BaseConstants):
    NAME_IN_URL = 'demographics_after'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    aiLit_1 = models.IntegerField(
        label='Which of the following is NOT powered by AI?',
        choices=[
            [1, 'Self-driving cars'],
            [2, "Google's search algorithm"],
            [3, 'A basic calculator'],
            [4, 'Chatbots'],
        ],
        widget=widgets.RadioSelectHorizontal,
    )

    aiLit_2 = models.IntegerField(
        label='In which area does AI typically excel?',
        choices=[
            [1, 'Emotional understanding'],
            [2, 'Pattern recognition'],
            [3, 'Moral reasoning'],
            [4, 'Creativity'],
        ],
        widget=widgets.RadioSelectHorizontal,
    )

    aiLit_3 = models.IntegerField(
        label='What is a common form of knowledge representation in AI?',
        choices=[
            [1, 'Neural networks'],
            [2, 'Waterfall model'],
            [3, 'Agile methodology'],
            [4, 'SWOT analysis'],
        ],
        widget=widgets.RadioSelectHorizontal,
    )

    aiLit_4 = models.IntegerField(
        label='Which is a key ethical issue surrounding AI?',
        choices=[
            [1, 'Algorithmic efficiency'],
            [2, 'CPU usage'],
            [3, 'Privacy'],
            [4, 'Code readability'],
        ],
        widget=widgets.RadioSelectHorizontal,
    )

    ## Usage of GenAI
    genAI_HeardOf = models.StringField(blank=False)
    genAI_Used = models.StringField(blank=False)
    noGenAI_Reason = models.StringField(blank=True)
    genAI_Applications = models.StringField(blank=True)
    genAI_usefulness = models.IntegerField(
        label='In general, how useful have generative AI tools been for you?',
        choices=[
            [1, 'Not at all useful'],
            [2, 'Slightly useful'],
            [3, 'Moderately useful'],
            [4, 'Very useful'],
            [5, 'Extremely useful'],
        ],
        widget=widgets.RadioSelectHorizontal,
        blank=True,
    )

    ## Financial advice
    finAdvice_who = models.IntegerField(
        label='Who would you say primarily handles your household’s financial matters?',
        choices=[
            [1, 'I do'],
            [2, 'My partner does'],
            [3, 'My partner and I equally do'],
            [4, 'Someone else does, for example, a relative, friend, or financial advisor'],
            [5, 'I prefer not to say'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )
    
    finAdvice_FinAdvisor = models.IntegerField(
        label='Do you have a financial advisor who guides you in your household’s financial matters?',
        choices=[
            [1, 'Yes'],
            [2, 'No'],
            [3, 'I don\'t know'],
            [4, 'I prefer not to say'],
        ],
        widget=widgets.RadioSelectHorizontal,
        blank=False,
    )

    finAdvice_FinAdvisor_Compensation = models.IntegerField(
        label='What is your financial advisor’s method of compensation?',
        choices=[
            [1, 'Commission (% on trades, investments, etc.)'],
            [2, 'Commission ($ on trades, investments, etc.)'],
            [3, 'Fee for service ($ per year, depending on asset value)'],
            [4, 'Fee for service ($ per hour)'],
            [5, 'Fee for service (% of portfolio value, per year)'],
            [6, 'My financial institution pays my advisor'],
            [7, 'My financial advisor does not manage this asset'],
            [7777, 'I don’t know'],
            [8888, 'I prefer not to say'],
        ],
        widget=widgets.RadioSelect,
        blank=True,
    )
    
    finAdvice_FinAdvisor_FinInstitution = models.IntegerField(
        label='Is your financial advisor tied to your financial institution?',
        choices=[
            [1, 'Yes'],
            [2, 'No'],
            [3, 'I don’t know'],
            [4, 'I prefer not to say'],
        ],
        widget=widgets.RadioSelectHorizontal,
        blank=True,
    )

    finAdvice_FinAdvisor_ReasonsNo = models.StringField(blank=True)

    finAdvice_InvestmentStrategy_Ranking = models.StringField(blank=True)

    finAdvice_InvestmentAmount = models.IntegerField(
        label= "Please provide your best estimate of the current value of any investments you own (including in registered and non-registered investment accounts; in $).",
        min = 0,
        blank=True,
    )

    finAdvice_InvestmentAmount_Range = models.IntegerField(
        label= "Please select the range that best matches your investment amount.",
        choices=[
            [1, 'Under $10,000'],
            [2, '$10,000–$19,999'],
            [3, '$20,000–$49,999'],
            [4, '$50,000–$99,999'],
            [5, '$100,000 or more'],
            [7777777, 'Don’t know'],
            [8888888, 'Prefer not to answer'],
        ],
        blank=True,
    )

    ## Financial literacy
    finLit_1 = models.IntegerField(
        label='Suppose you had $100 in a savings account and the interest rate was 2% per year. After 5 years, how much do you think you would have in the account if you left the money to grow during these 5 years?',
        choices=[
            [1, 'More than $102'],
            [2, 'Exactly $102'],
            [3, 'Less than $102'],
            [7777777, 'Don’t know'],
            [8888888, 'Refuse to answer'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )
    
    finLit_2 = models.IntegerField(
        label='Imagine that the interest rate on your savings account was 1% per year and inflation was 2% per year. After 1 year, with the money in this account, would you be able to buy…',
        choices=[
            [1, '... more than today.'],
            [2, '... exactly as much as today.'],
            [3, '... less than today.'],
            [7777777, 'Don’t know'],
            [8888888, 'Refuse to answer'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )

    finLit_3 = models.IntegerField(
        label='Do you think the following statement is true or false?“Buying a single company’s stock usually provides a safer return than a stock mutual fund.”',
        choices=[
            [1, 'True'],
            [2, 'False'],
            [7777777, 'Don’t know'],
            [8888888, 'Refuse to answer'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )


class startPage(Page):
    pass


class aiLiteracy(Page):
    form_model = 'player'
    form_fields = ['aiLit_1', 'aiLit_2', 'aiLit_3', 'aiLit_4']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
        }


class chatbotSurvey(Page):
    form_model = 'player'
    form_fields = ['genAI_HeardOf', 'genAI_Used', 'noGenAI_Reason', 'genAI_Applications', 'genAI_usefulness']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
        }

class financialAdvice(Page):
    form_model = 'player'
    form_fields = ['finAdvice_who', 'finAdvice_FinAdvisor', 'finAdvice_FinAdvisor_Compensation', 'finAdvice_FinAdvisor_FinInstitution', 'finAdvice_FinAdvisor_ReasonsNo', 'finAdvice_InvestmentStrategy_Ranking', 'finAdvice_InvestmentAmount', 'finAdvice_InvestmentAmount_Range']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
        }

class finLit(Page):
    form_model = 'player'
    form_fields = ['finLit_1', 'finLit_2', 'finLit_3']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
        }

class finalPage(Page):
    @staticmethod
    def vars_for_template(player):
        wealth = player.participant.vars.get('payoffWealth') or 0
        return {
            'finalWealth': wealth,
            'bonus': wealth / player.session.config['clientExchangeRate'],
            'completion_url': player.session.config.get('prolific_completion_url', ''),
        }

page_sequence = [
    #startPage,
    aiLiteracy,
    chatbotSurvey,
    financialAdvice,
    finLit,
    finalPage,
]
