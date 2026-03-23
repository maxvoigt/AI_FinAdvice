from os import environ

SESSION_CONFIGS = [
    dict(
        name='finAdvice',
        app_sequence=[
            'welcome',
            'demographics_before',
            'investmentGame'],
        num_demo_participants=4,
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, 
    participation_fee=0.00, 
    testing=True,
    doc=""
)

PARTICIPANT_FIELDS = [
    'treatment',
    'priceChart',
    'investmentOption1Prices',
    'investmentOption2Prices',
    'investmentOption3Prices',
    'investmentOption4Prices',
    'investmentOption5Prices',
    'trustGameOrder',
    'age',
    'gender',
    'riskAversion',
]
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'
THOUSAND_SEPARATOR = ","

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '8171517305603'


RECAPTCHA_SITE_KEY = "6LeTI9QpAAAAAFjvQxfChGZiVVsqRrfSdvhCMhcU"
RECAPTCHA_SECRET_KEY = "6LeTI9QpAAAAAFBa_ZB8DdTVjTSLeZcD3QE_pbmy"
# Once deployed to server, use
#RECAPTCHA_SITE_KEY = environ.get('RECAPTCHA_SITE_KEY', '')
#RECAPTCHA_SECRET_KEY = environ.get('RECAPTCHA_SECRET_KEY', '')

## OPEN AI KEY
api_key = environ.get("OPENAI_API_KEY")