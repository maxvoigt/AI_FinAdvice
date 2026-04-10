from urllib.parse import quote

from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'FP_payment'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    finalWealth = models.FloatField()


# PAGES
class payment(Page):
    @staticmethod
    def vars_for_template(player):
        relCustomer = player.participant.paidCustomer
        if relCustomer == 1:
            paidCustomer = 'first'
        else:
            paidCustomer = 'second'

        payoffWealth = player.participant.payoffWealth
        exchangeRate = player.session.config['advisorExchangeRate']

        dollarPayoff = round(payoffWealth / exchangeRate, 2)

        # For testing
        is_paid = player.participant.isPaid == 1
        mailto_href = ''
        if is_paid:
            email = 'philippe.dastous@hec.ca'
            subject = 'Study participation — payment information'
            body = (
                'Please add your participant identifier (e.g. Prolific ID) below.\n\n'
                f'Client role for payment: {paidCustomer} client\n'
                f'Final wealth (experimental dollars): {round(float(payoffWealth), 2):.2f}\n'
                f'Final payment ($): {dollarPayoff:.2f}\n'
            )
            mailto_href = (
                f'mailto:{email}'
                f'?subject={quote(subject)}'
                f'&body={quote(body)}'
            )

        email = 'philippe.dastous@hec.ca'
        subject = 'Study participation — follow-up study'
        body = (
            'Please consider me for the follow-up study.\n'
        )
        follow_up_survey_href = (
            f'mailto:{email}'
            f'?subject={quote(subject)}'
            f'&body={quote(body)}'
        )

        return {
            'isPaid': is_paid,
            'relCustomer': relCustomer,
            'paidCustomer': paidCustomer,
            'payoffWealth': payoffWealth,
            'dollarPayoff': dollarPayoff,
            'mailto_href': mailto_href,
            'follow_up_survey_href': follow_up_survey_href,
        }


page_sequence = [payment]
