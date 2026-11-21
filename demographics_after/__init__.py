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
        widget=widgets.RadioSelectHorizontal,
    )

    aiLit_2 = models.IntegerField(
        label='In which area does AI typically excel?',
        widget=widgets.RadioSelectHorizontal,
    )

    aiLit_3 = models.IntegerField(
        label='What is a common form of knowledge representation in AI?',
        widget=widgets.RadioSelectHorizontal,
    )

    aiLit_4 = models.IntegerField(
        label='Which is a key ethical issue surrounding AI?',
        widget=widgets.RadioSelectHorizontal,
    )

    ## Usage of GenAI
    genAI_HeardOf = models.StringField(blank=False)
    genAI_Used = models.StringField(blank=False)
    noGenAI_Reason = models.StringField(blank=True)
    genAI_Applications = models.StringField(blank=True)
    genAI_usefulness = models.IntegerField(
        label='In general, how useful have generative AI tools been for you?',
        widget=widgets.RadioSelectHorizontal,
        blank=True,
    )

    ## Financial advice
    finAdvice_who = models.IntegerField(
        label='Who would you say primarily handles your household’s financial matters?',
        widget=widgets.RadioSelect,
        blank=False,
    )
    
    finAdvice_FinAdvisor = models.IntegerField(
        label='Do you have a financial advisor who guides you in your household’s financial matters?',
        widget=widgets.RadioSelectHorizontal,
        blank=False,
    )

    finAdvice_FinAdvisor_Compensation = models.IntegerField(
        label='What is your financial advisor’s method of compensation?',
        widget=widgets.RadioSelect,
        blank=True,
    )
    
    finAdvice_FinAdvisor_FinInstitution = models.IntegerField(
        label='Is your financial advisor tied to your financial institution?',
        widget=widgets.RadioSelectHorizontal,
        blank=True,
    )

    finAdvice_FinAdvisor_ReasonsNo = models.StringField(blank=True)

    finAdvice_InvestmentAmount = models.IntegerField(
        label= "Please provide your best estimate of the current value of any investments you own (including in registered and non-registered investment accounts; in $).",
        min = 0,
        blank=True,
    )

    finAdvice_InvestmentAmount_Range = models.IntegerField(
        label= "Please select the range that best matches your investment amount.",
        blank=True,
    )

    ## Financial literacy
    finLit_1 = models.IntegerField(
        label='Suppose you had $100 in a savings account and the interest rate was 2% per year. After 5 years, how much do you think you would have in the account if you left the money to grow during these 5 years?',
        widget=widgets.RadioSelect,
        blank=False,
    )
    
    finLit_2 = models.IntegerField(
        label='Imagine that the interest rate on your savings account was 1% per year and inflation was 2% per year. After 1 year, with the money in this account, would you be able to buy…',
        widget=widgets.RadioSelect,
        blank=False,
    )

    finLit_3 = models.IntegerField(
        label='Do you think the following statement is true or false?“Buying a single company’s stock usually provides a safer return than a stock mutual fund.”',
        widget=widgets.RadioSelect,
        blank=False,
    )


def aiLit_1_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, 'Self-driving cars'],
            [2, "Google's search algorithm"],
            [3, 'A basic calculator'],
            [4, 'Chatbots'],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, 'Les voitures autonomes'],
            [2, "L'algorithme de recherche de Google"],
            [3, 'Une calculatrice de base'],
            [4, 'Les agents conversationnels'],
        ]

def aiLit_2_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, 'Emotional understanding'],
            [2, 'Pattern recognition'],
            [3, 'Moral reasoning'],
            [4, 'Creativity'],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, 'La compréhension des émotions'],
            [2, 'La reconnaissance des motifs'],
            [3, 'Le raisonnement moral'],
            [4, 'La créativité'],
        ]

def aiLit_3_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, 'Neural networks'],
            [2, 'Waterfall model'],
            [3, 'Agile methodology'],
            [4, 'SWOT analysis'],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, 'Les réseaux de neurones'],
            [2, 'Le modèle en cascade'],
            [3, 'La méthodologie agile'],
            [4, 'L’analyse FFOM'],
        ]

def aiLit_4_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, 'Algorithmic efficiency'],
            [2, 'CPU usage'],
            [3, 'Privacy'],
            [4, 'Code readability'],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, 'L’efficacité algorithmique'],
            [2, 'L’utilisation du processeur'],
            [3, 'La protection de la vie privée'],
            [4, 'La lisibilité du code'],
        ]

def genAI_usefulness_choices(player):
    if player.participant.lang == 'en':
        return [
            [1, 'Not at all useful'],
            [2, 'Slightly useful'],
            [3, 'Moderately useful'],
            [4, 'Very useful'],
            [5, 'Extremely useful'],
        ]
    elif player.participant.lang == 'fr':
        return [
            [1, 'Pas du tout utiles'],
            [2, 'Légèrement utiles'],
            [3, 'Modérément utiles'],
            [4, 'Très utiles'],
            [5, 'Extrêmement utiles'],
        ]

LABELS = {
    'en': {
        'finAdvice_who': 'Who would you say primarily handles your household’s financial matters?',
        'finAdvice_FinAdvisor': 'Do you have a financial advisor who guides you in your household’s financial matters?',
        'finAdvice_FinAdvisor_Compensation': 'What is your financial advisor’s method of compensation?',
        'finAdvice_FinAdvisor_FinInstitution': 'Is your financial advisor tied to your financial institution?',
        'finAdvice_InvestmentAmount': 'Please provide your best estimate of the current value of any investments you own (including in registered and non-registered investment accounts; in $).',
        'finAdvice_InvestmentAmount_Range': 'Please select the range that best matches your investment amount.',
        'finLit_1': 'Suppose you had $100 in a savings account and the interest rate was 2% per year. After 5 years, how much do you think you would have in the account if you left the money to grow during these 5 years?',
        'finLit_2': 'Imagine that the interest rate on your savings account was 1% per year and inflation was 2% per year. After 1 year, with the money in this account, would you be able to buy…',
        'finLit_3': 'Do you think the following statement is true or false? “Buying a single company’s stock usually provides a safer return than a stock mutual fund.”',
    },
    'fr': {
        'finAdvice_who': 'Selon vous, qui s’occupe principalement des questions financières de votre ménage?',
        'finAdvice_FinAdvisor': 'Avez-vous un conseiller ou une conseillère en finances qui vous guide dans les questions financières de votre ménage?',
        'finAdvice_FinAdvisor_Compensation': 'Quel est le mode de rémunération de votre conseiller(-ère)?',
        'finAdvice_FinAdvisor_FinInstitution': 'Votre conseiller(-ère) est-il/elle lié(e) à votre institution financière?',
        'finAdvice_InvestmentAmount': 'Veuillez fournir votre meilleure estimation de la valeur actuelle de tous vos placements (y compris dans des comptes de placement enregistrés et non enregistrés; en $).',
        'finAdvice_InvestmentAmount_Range': 'Veuillez sélectionner la tranche qui correspond le mieux au montant de vos placements.',
        'finLit_1': 'Supposons que vous ayez 100$ dans un compte d’épargne et que le taux d’intérêt soit de 2% par année. Après 5 ans, combien pensez-vous avoir dans ce compte si vous laissez l’argent fructifier pendant ces 5 ans?',
        'finLit_2': 'Imaginez que le taux d’intérêt de votre compte d’épargne soit de 1% par année et que l’inflation soit de 2% par année. Après 1 an, avec l’argent de ce compte, pourriez-vous acheter…',
        'finLit_3': 'Pensez-vous que l’énoncé suivant est vrai ou faux? «L’achat d’actions d’une seule entreprise procure habituellement un rendement plus sûr qu’un fonds commun de placement en actions.»',
    },
}

CHOICES = {
    'finAdvice_who': {
        'en': [[1, 'I do'], [2, 'My partner does'], [3, 'My partner and I equally do'],
               [4, 'Someone else does, for example, a relative, friend, or financial advisor'], [5, 'I prefer not to say']],
        'fr': [[1, 'Moi'], [2, 'Mon ou ma partenaire'], [3, 'Mon ou ma partenaire et moi, à parts égales'],
               [4, 'Quelqu’un d’autre, par exemple un membre de la famille, un(e) ami(e), ou un conseiller ou une conseillère en finances'],
               [5, 'Je préfère ne pas répondre']],
    },
    'yesno4': {
        'en': [[1, 'Yes'], [2, 'No'], [3, 'I don’t know'], [4, 'I prefer not to say']],
        'fr': [[1, 'Oui'], [2, 'Non'], [3, 'Je ne sais pas'], [4, 'Je préfère ne pas répondre']],
    },
    'compensation': {
        'en': [[1, 'Commission (% on trades, investments, etc.)'], [2, 'Commission ($ on trades, investments, etc.)'],
               [3, 'Fee for service ($ per year, depending on asset value)'], [4, 'Fee for service ($ per hour)'],
               [5, 'Fee for service (% of portfolio value, per year)'], [6, 'My financial institution pays my advisor'],
               [7, 'My financial advisor does not manage this asset'], [7777, 'I don’t know'], [8888, 'I prefer not to say']],
        'fr': [[1, 'Commission (% sur les transactions, les placements, etc.)'], [2, 'Commission ($ sur les transactions, les placements, etc.)'],
               [3, 'Honoraires (en $ par année, selon la valeur des actifs)'], [4, 'Honoraires (en $ par heure)'],
               [5, 'Honoraires (en % de la valeur du portefeuille, par année)'], [6, 'Mon institution financière rémunère mon conseiller(-ère)'],
               [7, 'Mon conseiller(-ère) ne gère pas cet actif'], [7777, 'Je ne sais pas'], [8888, 'Je préfère ne pas répondre']],
    },
    'invRange': {
        'en': [[1, 'Under $10,000'], [2, '$10,000–$19,999'], [3, '$20,000–$49,999'], [4, '$50,000–$99,999'],
               [5, '$100,000 or more'], [7777777, 'Don’t know'], [8888888, 'Prefer not to answer']],
        'fr': [[1, 'Moins de 10 000$'], [2, '10 000$–19 999$'], [3, '20 000$–49 999$'], [4, '50 000$–99 999$'],
               [5, '100 000$ ou plus'], [7777777, 'Je ne sais pas'], [8888888, 'Je préfère ne pas répondre']],
    },
    'finLit_1': {
        'en': [[1, 'More than $102'], [2, 'Exactly $102'], [3, 'Less than $102'], [7777777, 'Don’t know'], [8888888, 'Refuse to answer']],
        'fr': [[1, 'Plus de 102$'], [2, 'Exactement 102$'], [3, 'Moins de 102$'], [7777777, 'Je ne sais pas'], [8888888, 'Je refuse de répondre']],
    },
    'finLit_2': {
        'en': [[1, '... more than today.'], [2, '... exactly as much as today.'], [3, '... less than today.'],
               [7777777, 'Don’t know'], [8888888, 'Refuse to answer']],
        'fr': [[1, '… plus qu’aujourd’hui.'], [2, '… exactement autant qu’aujourd’hui.'], [3, '… moins qu’aujourd’hui.'],
               [7777777, 'Je ne sais pas'], [8888888, 'Je refuse de répondre']],
    },
    'finLit_3': {
        'en': [[1, 'True'], [2, 'False'], [7777777, 'Don’t know'], [8888888, 'Refuse to answer']],
        'fr': [[1, 'Vrai'], [2, 'Faux'], [7777777, 'Je ne sais pas'], [8888888, 'Je refuse de répondre']],
    },
}

def finAdvice_who_choices(player):                       return CHOICES['finAdvice_who'][player.participant.lang]
def finAdvice_FinAdvisor_choices(player):                return CHOICES['yesno4'][player.participant.lang]
def finAdvice_FinAdvisor_FinInstitution_choices(player): return CHOICES['yesno4'][player.participant.lang]
def finAdvice_FinAdvisor_Compensation_choices(player):   return CHOICES['compensation'][player.participant.lang]
def finAdvice_InvestmentAmount_Range_choices(player):    return CHOICES['invRange'][player.participant.lang]
def finLit_1_choices(player): return CHOICES['finLit_1'][player.participant.lang]
def finLit_2_choices(player): return CHOICES['finLit_2'][player.participant.lang]
def finLit_3_choices(player): return CHOICES['finLit_3'][player.participant.lang]

class startPage(Page):
    pass


class aiLiteracy(Page):
    form_model = 'player'
    form_fields = ['aiLit_1', 'aiLit_2', 'aiLit_3', 'aiLit_4']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'lang': player.participant.lang,
        }


class chatbotSurvey(Page):
    form_model = 'player'
    form_fields = ['genAI_HeardOf', 'genAI_Used', 'noGenAI_Reason', 'genAI_Applications', 'genAI_usefulness']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'lang': player.participant.lang,
        }

class financialAdvice(Page):
    form_model = 'player'
    form_fields = ['finAdvice_who', 'finAdvice_FinAdvisor', 'finAdvice_FinAdvisor_Compensation', 'finAdvice_FinAdvisor_FinInstitution', 'finAdvice_FinAdvisor_ReasonsNo', 'finAdvice_InvestmentAmount', 'finAdvice_InvestmentAmount_Range']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'lang': player.participant.lang,
            'L': LABELS[player.participant.lang],
        }

class finLit(Page):
    form_model = 'player'
    form_fields = ['finLit_1', 'finLit_2', 'finLit_3']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
            'lang': player.participant.lang,
        }

class finalPage(Page):
    @staticmethod
    def vars_for_template(player):
        wealth = player.participant.vars.get('payoffWealth') or 0
        bonus = wealth / player.session.config['clientExchangeRate']
        lang = player.participant.lang
        return {
            'finalWealth': wealth, 'bonus': bonus,
            'finalWealthTxt': money(wealth, lang), 'bonusTxt': money(bonus, lang),
            'completion_url': player.session.config.get('completion_url', ''),
            'lang': lang,
            'recruiter': player.session.config.get('recruiter'),
        }

page_sequence = [
    #startPage,
    aiLiteracy,
    chatbotSurvey,
    financialAdvice,
    finLit,
    finalPage,
]


### French language helper
def money(x, lang):
    """$12,345.67 (en) / 12 345,67$ (fr, FP style: no space before $)."""
    x = float(x or 0)
    if lang == 'fr':
        return f"{x:,.2f}".replace(',', '\u00a0').replace('.', ',') + '$'
    return f"${x:,.2f}"