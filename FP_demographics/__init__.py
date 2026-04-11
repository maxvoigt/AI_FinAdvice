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
    NAME_IN_URL = 'demographics'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    ## Demographics
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
            [1, 'I am willing to take above average financial risks expecting to earn above-average returns.'],
            [2, 'I am willing to take average financial risks expecting to earn average returns.'],
            [3, 'I am willing to take below average financial risks expecting to earn below-average returns.'],
        ])

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
    genAI_Used = models.IntegerField(
        label='Have you used one of the generative AI tools above before this survey?',
        choices=[
            [1, 'Yes, only for work.'],
            [2, 'Yes, only for leisure.'],
            [3, 'Yes, for my work and leisure.'],
            [4, 'No, I have not used any of the generative AI tools.'],
        ],
        widget=widgets.RadioSelect,
        blank=False
        )
    
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

    genAI_usefulness_others = models.IntegerField(
        label='According to your opinion, how useful are chatbots for the average financial planner?',
        choices=[
            [1, 'Not at all useful'],
            [2, 'Slightly useful'],
            [3, 'Moderately useful'],
            [4, 'Very useful'],
            [5, 'Extremely useful'],
        ],
        widget=widgets.RadioSelectHorizontal,
        blank=False,
    )

    ## Providing financial advice
    workplace = models.IntegerField(
        label='Please indicate which one of the following best describes your place of employment.',
        choices=[
            [1, 'Accounting Firm'],
            [2, 'Credit Union'],
            [3, 'Financial Planning Firm'],
            [4, 'Insurance Company'],
            [5, 'Bank'],
            [6, 'Educational Institution'],
            [7, 'Investment / Mutual Fund Company'],
            [8, 'Managing General Agency (MGA)'],
            [9, 'Self-employed'],
            [10, 'Currently not working'],
            [11, 'Other'],
            [7777777, "Don’t know"],
            [8888888, "Prefer not to say"],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )

    mainCertifications = models.StringField(blank=False)
    otherCertifications = models.StringField(blank=True)

    workExperience = models.IntegerField(
        label= 'How long have you been working as a financial planner? Please indicate your work experience in number of years.',
        min=0,
        max=80,
        blank=True,
    )
    workExperience_special = models.StringField(blank=True)

    servicesProvided = models.IntegerField(
        label= 'Which services do you predominantly provide as a financial planner?',
        choices=[
            [1, 'Advice on insurance'],
            [2, 'Advice on investments'],
            [3, 'Holistic financial planning (without implementation of advice)'],
            [4, 'Holistic financial planning including implementation of advice (product advice and sales)'],
            [7777777, 'Don’t know'],
            [8888888, 'Prefer not to say'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )

    compensationMethod = models.IntegerField(
        label= 'How are you primarily compensated for your services as a financial planner? If none of the available options applies, choose “other”.',
        choices=[
            [1, 'Salary only'],
            [2, 'Salary plus bonus based on achieving sales targets'],
            [3, 'Primarily commissions'],
            [4, 'Primarily Assets under Management'],
            [5, 'Primarily fee for advice'],
            [6, 'Other'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )

    referringClients = models.IntegerField(
        label= 'How often do you consult with or refer clients to other experts, such as a lawyer or an accountant?',
        choices=[
            [1, 'Frequently'],
            [2, 'Occasionally'],
            [3, 'Rarely'],
            [4, 'Very Rarely'],
            [5, 'Never'],
            [7777777, 'Don’t know'],
            [8888888, 'Prefer not to say'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )

    specialties = models.StringField(blank=False)
    
    adviceQuality = models.IntegerField(
        label= 'Please indicate how you would assess your own financial advice compared to other financial planners.',
        choices=[
            [1, 'It is better than average'],
            [2, 'It is about the same'],
            [3, 'It is worse than the average'],
            [7777777, 'Don’t know'],
            [8888888, 'Prefer not to say'],
        ],
        widget=widgets.RadioSelect,
        blank=False,
    )

class startPage(Page):
    pass


class demographicsPage(Page):
    preserve_unsubmitted_inputs = True
    form_model = 'player'
    form_fields = ['age', 'gender', 'gender_other', 'territory', 'patience', 'finRiskTaking']

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
        gender = values.get('gender')
        gender_other = values.get('gender_other')
        
        if gender == 3:
            if not (isinstance(gender_other, str) and gender_other.strip()):
                return "Please specify your gender."

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
    form_fields = ['genAI_HeardOf', 'genAI_Used', 'noGenAI_Reason', 'genAI_Applications', 'genAI_usefulness', 'genAI_usefulness_others']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
        }

class financialAdvice(Page):
    form_model = 'player'
    form_fields = ['workplace', 'mainCertifications', 'otherCertifications', 'workExperience', 'workExperience_special', 'servicesProvided', 'compensationMethod', 'referringClients', 'specialties', 'adviceQuality']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing'],
        }

page_sequence = [
    startPage,
    demographicsPage,
    aiLiteracy,
    chatbotSurvey,
    financialAdvice,
]
