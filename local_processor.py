import datetime
import json
import pathlib
from collections import defaultdict

import requests
from termcolor import colored


def report(s, color='white'):
    print(colored(s, color))


colors = {'W': 'white', 'G': 'green', 'B': 'yellow', 'U': 'blue', 'R': 'red'}

worth = {
    1: 15,
    2: 10,
    3: 8,
    4: 3,
    5: 2,
    6: 1,
    7: 0,
    8: 0,
    9: 0,
    10: 0,
    11: 0,
    12: 0,
    13: 0,
    14: 0,
    15: 0
    }

muls = {
    2: 0,
    3: 0.2,
    4: 0.35,
    5: 0.5,
    6: 0.7,
    7: 0.85,
    8: 1,
    9: 1.3,
    10: 1.5,
    11: 1.7,
    12: 1.8,
    13: 2,
    14: 2.2,
    15: 2.5
    }


class Processor:

    """
    Requires database.json from MTG Arena tool. Could be found after installing MTG Arena tool
    (https://mtgatool.com/) could find in it github :(
    """

    def __init__(self):
        with open('resources/database.json', encoding='utf8') as db_file:
            self.db = json.load(db_file)

        try:
            self.load_rankings()
        except FileNotFoundError:
            self.fetch_rankings()

        self.process_rankings()

        self.draft_id = None
        self.picks = {}
        self.signals = defaultdict(int)

    def fetch_rankings(self):
        url = "https://www.17lands.com/card_ratings/data"

        params = {
            'expansion': 'AFR',
            'format': 'PremierDraft',
            'start_date': '2021-03-17',
            'end_date': datetime.datetime.now().strftime("%Y-%m-%d")
            }
        response = requests.get(url=url, params=params)
        self.raw_rankings = response.json()
        with open('resources/rankings.json', 'w') as f:
            json.dump(self.raw_rankings, f)

    def calc_score(self, pick, avg_pick):
        return worth[int(avg_pick)] * muls[pick]

    def load_rankings(self):
        fname = pathlib.Path("resources/rankings.json")
        mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime)
        if mtime < datetime.datetime.now() - datetime.timedelta(days=1):
            self.fetch_rankings()
        else:
            with open(fname) as f:
                self.raw_rankings = json.load(f)

    def process_rankings(self):
        self.ranking_lookup = {}
        for item in self.raw_rankings:
            self.ranking_lookup[item['name']] = item

    def ranking(self, card_id: int):
        card = self.card(card_id)
        name = card['name']
        return self.ranking_lookup[name]

    def card(self, card_id: int):
        return self.db['cards'][str(card_id)]

    def human_draft_pick(self, doc):
        self.picks[(doc['pack_number'], doc['pick_number'])] = doc['card_id']

    def human_draft_pack(self, doc):
        if doc['draft_id'] != self.draft_id:
            report('Starting a new draft')
            self.draft_id = doc['draft_id']
            self.picks = {}
            self.signals = defaultdict(int)

        self.process_pack(doc)
        # report(self.picks)

    def print_by_winrate_improvement(self, pack):
        cards = [card for card in pack["card_ids"] if
                 self.ranking(card)['ever_drawn_game_count'] > 500]
        for card_id in sorted(cards,
                              key=lambda card_id: self.ranking(card_id)[
                                  'drawn_improvement_win_rate'],
                              reverse=True):
            card = self.card(card_id)
            ranking = self.ranking(card_id)
            color = ranking['color']

            report(f"Color: {color}, "
                   f"Name: {card['name']}, "
                   f"Winrate improvement: {ranking['drawn_improvement_win_rate']:.0%}, "
                   f"Average Pick: {ranking['avg_pick']:.2f}, ",
                   color=colors.get(color, 'white'))

    def process_pack(self, doc):
        pack, pick = doc["pack_number"], doc["pick_number"]
        report(f'\nPack {pack}, Pick: {pick}')

        for card_id in sorted(doc["card_ids"],
                              key=lambda card_id: self.ranking(card_id)['avg_pick']):
            card = self.card(card_id)
            ranking = self.ranking(card_id)
            color = ranking['color']

            if doc["pack_number"] == 1:
                score = self.calc_score(doc["pick_number"], ranking['avg_pick'])
                self.signals[color] += score

            report(f"Color: {color}, "
                   f"Name: {card['name']}, "
                   f"Average Pick: {ranking['avg_pick']:.2f}, "
                   f"Winrate opening hand: {ranking['opening_hand_win_rate']:.2f}, "
                   f"Winrate drawn: {ranking['drawn_win_rate']:.2f}, "
                   f"Winrate improvement: {ranking['drawn_improvement_win_rate']:.0%}",
                   color=colors.get(color, 'white'))

        print("====> Sorted by winrate")
        self.print_by_winrate_improvement(doc)
        print("====> Signals")

        self.print_signals()

        if pack == 3 and pick == 14:
            self.print_inventory()

    def print_signals(self):
        for k, v in sorted(self.signals.items(), key=lambda t: t[1], reverse=True):
            print(f"{k}: {v:.2f}")

    def print_inventory(self):
        print("Printing inventory")
        document = {"card_ids": list(self.picks.values())}
        self.print_by_winrate_improvement(document)

