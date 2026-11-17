from otree.api import *
import requests


doc = """
Your app description
"""

class C(BaseConstants):
    NAME_IN_URL = 'language'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    lang = models.StringField(
        choices=[('en', 'English'), ('fr', 'Français')],
        widget=widgets.RadioSelectHorizontal,
        label="Please select your language. // Veuillez sélectionner la langue de votre choix pour l'enquête.",
    )

    participantID = models.StringField()
    


# PAGES
class LanguageSelection(Page):
    form_model = 'player'
    form_fields = ['lang']

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.lang = player.lang
        player.participant.url_state = player.participant.label or 'genericURL'
        player.participantID = player.participant.label

page_sequence = [LanguageSelection]
