import numpy as np
import pandas as pd

from nba_api.stats.static import players #static data set to get unique endpoints
from nba_api.stats.endpoints import PlayerCareerStats #endpoint to get player game logs
from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.endpoints import playerprofilev2
def get_player_id(name):
    player = [player for player in players.get_players() if player['full_name'] == name][0]
    return player['id']

def get_player_stats(name):
    nba_players = players.get_players()
    player_dict = [player for player in nba_players if player['full_name'] == name][0]
    career = PlayerCareerStats(player_dict['id'])

    return career.get_data_frames()[0]

def get_player_info(name):
    player = [player for player in players.get_players() if player['full_name'] == name][0]
    player_info = commonplayerinfo.CommonPlayerInfo(player_id=player['id'])
    return player_info.get_data_frames()[0]
"""
lebron_james = {
  'id': 2544,
  'full_name': 'LeBron James',
  'first_name': 'LeBron',
  'last_name': 'James',
  'is_active': True
}
example output for lebron james
"""
# def getCommonStats(name):
#     player = [player for player in players.get_active_players() if player['full_name'] == name][0]
#     player_info = playerprofilev2.PlayerProfileV2(player_id=player['id'])
#     return player_info.get_data_frames()[0]

#print(get_player_stats("Sue Bird")) # this is the output of the function , it is a pandas dataframe # cant get stats of wnba playuers
# print(players.get_wnba_players())
# print(players.find_wnba_players_by_last_name('Clark'))
print(get_player_stats("LeBron James"))
print(get_player_info("LeBron James"))