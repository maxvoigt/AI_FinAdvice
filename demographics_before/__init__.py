from otree.api import *
import json
import random
import time
import pandas as pd

doc = """
Your app description
"""

SLOT_FILE = '_static/clients/client_slots.csv'
SLOT_TIMEOUT_MIN = 90          # set a bit above the Prolific time limit

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
            [1, 'I am willing to take above average financial risks expecting to earn above-average returns.'],
            [2, 'I am willing to take average financial risks expecting to earn average returns.'],
            [3, 'I am willing to take below average financial risks expecting to earn below-average returns.'],
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

    slot_id = models.StringField(blank=True)
    block_id = models.StringField(blank=True)
    arm = models.IntegerField(blank=True)
    cell = models.StringField(blank=True)

def creating_session(subsession):
    if subsession.round_number == 1:
        load_slots(subsession.session.config.get('slot_pool', 'test'))

def client_cell(player):
    """Cell label as in client_slots.csv, e.g. 'F-Mid-Med'. Returns (cell, gender_imputed)."""
    age = 'Young' if player.age <= 34 else ('Mid' if player.age <= 54 else 'Old')
    risk = {1: 'Low', 2: 'Med', 3: 'High'}[player.finRiskTaking]
    imputed = False
    if player.gender == 1:
        gender = 'M'
    elif player.gender == 2:
        gender = 'F'
    else:
        gender, imputed = random.choice(['M', 'F']), True
    return f'{gender}-{age}-{risk}', imputed



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
        assign_slot(player)

class trustGame(Page):
    # Participant is always the sender, either paired with a financial planner or a generative AI system
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        if player.participant.trustGameOrder + 1 == player.round_number:
            return ['amount_to_send_finAdvisor']
        else:
            return ['amount_to_send_AI']

    @staticmethod
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
            'testing': player.session.config['testing'],
            'lang': player.participant.lang
        }
    
    @staticmethod
    def js_vars(player):
        if player.participant.trustGameOrder + 1 == player.round_number:
            return {
                'field_name': 'id_amount_to_send_finAdvisor',
            }
        else:
            return {
                'field_name': 'id_amount_to_send_AI',
            }

page_sequence = [
    startPage,
    demographicsPage,
    trustGame
    ]

### Treatment Assignment Functions ###
class Slot(ExtraModel):
    # No Link to Subsession on purpose: one pool shared by all sessions.
    pool = models.StringField()
    slot_id = models.StringField()
    block_id = models.StringField()
    record_id = models.IntegerField()
    cell = models.StringField()
    arm = models.IntegerField()
    perm_rank = models.IntegerField()
    assetOrder = models.StringField()
    opt1_prices = models.LongStringField()
    opt2_prices = models.LongStringField()
    opt3_prices = models.LongStringField()
    opt4_prices = models.LongStringField()
    opt5_prices = models.LongStringField()
    adv_w_d1 = models.LongStringField()
    adv_w_d2 = models.LongStringField()
    adv_factors_d1 = models.LongStringField()
    adv_factors_d2 = models.LongStringField()
    n_active = models.IntegerField()            # live reservations + completions
    n_released = models.IntegerField()          # how often this slot was freed after a dropout

class SlotUse(ExtraModel):
    pool = models.StringField()
    cell = models.StringField()
    slot_id = models.StringField()
    participant_code = models.StringField()
    status = models.StringField()               # 'reserved', 'completed', 'released'
    reserved_at = models.FloatField()
    completed_late = models.BooleanField()

def load_slots(pool):
    """Load client_slots.csv into the database, once per pool."""
    if Slot.objects_filter(pool=pool).first():
        return                                   # already loaded by an earlier session
    df = pd.read_csv(SLOT_FILE, keep_default_na=False)
    for r in df.itertuples():
        Slot.create(
            pool=pool, slot_id=r.slot_id, block_id=r.block_id, record_id=int(r.record_id),
            cell=r.cell, arm=int(r.arm), perm_rank=int(r.perm_rank), assetOrder=r.assetOrder,
            opt1_prices=r.opt1_prices, opt2_prices=r.opt2_prices, opt3_prices=r.opt3_prices,
            opt4_prices=r.opt4_prices, opt5_prices=r.opt5_prices,
            adv_w_d1=r.adv_w_d1, adv_w_d2=r.adv_w_d2,
            adv_factors_d1=r.adv_factors_d1, adv_factors_d2=r.adv_factors_d2,
            n_active=0, n_released=0,
        )

def release_stale_slots(pool, cell):
    cutoff = time.time() - SLOT_TIMEOUT_MIN * 60
    for u in list(SlotUse.objects_filter(pool=pool, cell=cell, status='reserved')):
        if u.reserved_at < cutoff:
            slot = Slot.objects_filter(pool=pool, slot_id=u.slot_id).first()
            u.status = 'released'
            slot.n_active -= 1
            slot.n_released += 1

def assign_slot(player):
    """Reserve a slot for this participant and copy its content into participant fields."""
    participant = player.participant
    if participant.vars.get('slot_id'):          # already assigned (e.g. double submit)
        return
    config = player.session.config
    pool = config.get('slot_pool', 'test')

    cell, imputed = client_cell(player)
    participant.gender_imputed = imputed
    participant.cell = cell or ''
    participant.cell_full = False
    if cell is None:
        participant.cell_full = True
        return

    release_stale_slots(pool, cell)
    
    query = Slot.objects_filter(pool=pool, cell=cell)
    if config.get('testing') and config.get('force_arm') is not None:
        query = query.filter_by(arm=int(config['force_arm']))
    slot = query.order_by(Slot.n_active, Slot.perm_rank).first()

    if slot is None:                             # only if the cell has no slots at all
        participant.cell_full = True
        return

    slot.n_active += 1
    SlotUse.create(pool=pool, cell=cell, slot_id=slot.slot_id, participant_code=participant.code,
                status='reserved', reserved_at=time.time(), completed_late=False)

    participant.slot_id = slot.slot_id
    participant.block_id = slot.block_id
    participant.treatment = slot.arm
    participant.assetOrder = json.loads(slot.assetOrder)
    participant.investmentOption1Prices = {'p1': slot.opt1_prices}
    participant.investmentOption2Prices = {'p1': slot.opt2_prices}
    participant.investmentOption3Prices = {'p1': slot.opt3_prices}
    participant.investmentOption4Prices = {'p1': slot.opt4_prices}
    participant.investmentOption5Prices = {'p1': slot.opt5_prices}
    participant.advice_d1 = json.loads(slot.adv_w_d1) if slot.adv_w_d1 else []
    participant.advice_d2 = json.loads(slot.adv_w_d2) if slot.adv_w_d2 else []
    participant.adviceFactors_d1 = json.loads(slot.adv_factors_d1) if slot.adv_factors_d1 else []
    participant.adviceFactors_d2 = json.loads(slot.adv_factors_d2) if slot.adv_factors_d2 else []

    player.slot_id = slot.slot_id                # also in the player table for the normal export
    player.block_id = slot.block_id
    player.arm = slot.arm
    player.cell = cell

def complete_slot(player):
    participant = player.participant
    pool = player.session.config.get('slot_pool', 'test')
    use = SlotUse.objects_filter(pool=pool, participant_code=participant.code).first()
    if use is None:
        return False
    if use.status == 'released':                 # finished after the timeout: count the data again
        slot = Slot.objects_filter(pool=pool, slot_id=use.slot_id).first()
        slot.n_active += 1
        use.completed_late = True
    use.status = 'completed'
    return True

def custom_export(players):
    yield ['pool', 'slot_id', 'block_id', 'record_id', 'cell', 'arm', 'perm_rank', 'n_active', 'n_released',
           'participant_code', 'status', 'reserved_at', 'completed_late']
    uses = {}
    for u in SlotUse.filter():
        uses.setdefault((u.pool, u.slot_id), []).append(u)
    for s in Slot.filter():
        for u in uses.get((s.pool, s.slot_id), [None]):
            yield [s.pool, s.slot_id, s.block_id, s.record_id, s.cell, s.arm, s.perm_rank, s.n_active, s.n_released,
                   u.participant_code if u else '', u.status if u else '', u.reserved_at if u else '',
                   u.completed_late if u else '']