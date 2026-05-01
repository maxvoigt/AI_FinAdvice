from otree.api import *


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'surveyBefore'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    amount_to_send_AI = models.IntegerField(
        label = 'In this situation, how much of your $1,000 would you want to send?',
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
    pass

class trustGame(Page):
    form_model = 'player'
    form_fields = ['amount_to_send_AI']

    @staticmethod
    def vars_for_template(player):
        return {
            'testing': player.session.config['testing']
        }



page_sequence = [
    startPage, 
    trustGame]
