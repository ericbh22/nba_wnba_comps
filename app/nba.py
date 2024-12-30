import numpy as np
import pandas as pd
import math 

from typing import Type
from nba_api.stats.static import players #static data set to get unique endpoints
from nba_api.stats.endpoints import PlayerCareerStats #endpoint to get player game logs
from nba_api.stats.endpoints import commonplayerinfo
from nba_api.stats.endpoints import playerprofilev2
from nba_api.stats.endpoints import shotchartdetail
from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.endpoints import draftcombinestats
from nba_api.stats.endpoints import homepageleaders
from nba_api.stats.endpoints import playerdashboardbyshootingsplits



class Player:
    def __init__(self,name: str,year: str):
        """General Information about the player"""
        self.name = name
        self.player_id = self.get_player_id(name)
        self.player_info = commonplayerinfo.CommonPlayerInfo(player_id=self.player_id).get_data_frames()[0]
        self.player_stats = self.get_player_stats(year)
        self.career_stats = PlayerCareerStats(self.player_id).get_data_frames()[0]
        self.team_id = self.get_player_team_id(year) # 2021-22 type formating 
        self.team_stats = self.get_team_stats(year) # so we need to get a players debut year 
        self.debut_year = self.player_info["FROM_YEAR"]
        self.draft_stats = draftcombinestats.DraftCombineStats("00",self.debut_year).get_data_frames()[0]# some players dont attend draft combine, thjis is certainly flawed, it also takes a year to get the data, so we need to find the year they were at the combine 
        self.league_averages = homepageleaders.HomePageLeaders().get_data_frames()[1] # this is the league averages for the current season, we can use this to compare players to the league average, no point changing season, what r we gunna do ? check all of a players seasons? makes no sense 
        self.league_three_pt_percentage = self.league_averages['FG3_PCT'].iloc[0]
        self.league_field_goal_percentage = self.league_averages['FG_PCT'].iloc[0]
        self.league_free_throw_percentage = self.league_averages['FT_PCT'].iloc[0]

        # we need to find their stats
        self.filtered_draft_stats = self.draft_stats[self.draft_stats['PLAYER_ID'] == self.player_id]
        """Stats for the player"""
        self.ast = self.player_stats['AST'] # so for each of these are want ONE SPECIFIC NUMBER, we can do this w loc or a filter? we r essetnially looking to sort based on SEASON_ID then get the value of the stat we want, so get_player_stats() should realistically only be one season
        self.tov = self.player_stats['TOV']
        self.pts= self.player_stats['PTS']
        self.three_pt_percentage = self.player_stats['FG3_PCT']
        self.three_pt_attempt = self.player_stats['FG3A']  
        self.fga = self.player_stats['FGA']
        self.fta = self.player_stats['FTA']
        self.oreb = self.player_stats['OREB']
        attempt_scalar = 2 / (1 + math.exp(-self.three_pt_attempt)) - 1
        self.three_pt_prof = self.three_pt_percentage * attempt_scalar
        self.mp = self.player_stats['MIN'] 
        self.height = self.player_info['HEIGHT'][0]

        if len(self.height) == 3:
            self.height = int(self.height[0]) * 30.48 + int(self.height[2]) * 2.54
        else:
            self.height = int(self.height[0]) * 30.48 + int(self.height[2:]) * 2.54

        self.weight = self.player_info['WEIGHT']
        self.field_goal_percentage = self.player_stats['FG_PCT']
        try:
            self.vertical = self.filtered_draft_stats['MAX_VERTICAL_LEAP'].iloc[0] #  using iloc 0 because its returning a pandas series , but we need to have error handling https://chatgpt.com/c/674250c8-9290-800a-85ed-19734811767a to explain why pandas always returns a df
        except IndexError:
            self.vertical = "N/A"
        try:
            self.wingspan = self.filtered_draft_stats['WINGSPAN'].iloc[0] #  using iloc 0 because its returning a pandas series , but we need to have error handling 
        except IndexError:
            self.wingspan = "N/A"
        self.standardised_three_pt_percentage = (self.three_pt_percentage - self.league_three_pt_percentage) / 0.05
        self.standardised_field_goal_percentage = (self.player_stats['FG_PCT'] - self.league_field_goal_percentage) / 0.1
        self.standardised_free_throw_percentage = (self.player_stats['FT_PCT'] - self.league_free_throw_percentage) / 0.1
        self.padded_three_pt_percentage = ((self.standardised_three_pt_percentage + 3) / 6 )* 100
        self.padded_free_throw_percentage = ((self.standardised_free_throw_percentage + 3) / 6 )* 100
        self.blended_percentage = (5* self.padded_three_pt_percentage + self.padded_free_throw_percentage) / 6 
        self.spacing = (self.three_pt_attempt * (((self.three_pt_percentage*1.5)*1.5)-0.535))
        self.shooting_splits = playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits(player_id = self.player_id, season=year).get_data_frames()[2] # define specific season and years 
        self.filtered_splits = []
        for index, row in self.shooting_splits.iterrows(): # looping through pandas dataframes
            self.filtered_splits.append(round(row['FGA']*100/self.fga,2))
        self.shooting_quality = ((self.spacing * 2) + ((self.padded_free_throw_percentage+ self.padded_three_pt_percentage) *5)) / 7
        
        """Stats for the team""" 
        self.team_mp = self.team_stats['MIN']  * 5 # my own formula to account for OT
        self.team_fga = self.team_stats['FGA']
        self.team_fta = self.team_stats['FTA'] 
        self.team_tov = self.team_stats['TOV']

        self.possesions = (self.fga + self.tov + 0.44 * self.fta - self.oreb)  # can consider doing *0.96 for more accurate possesions, this is for a signular player?
        self.teampossesions = 0.96*(self.team_fga + self.team_tov + 0.44 * self.team_fta - self.team_stats['OREB']) # this is for the team
        """Adjusted per 100 personal stats"""
        self.asth = self.ast*100 / self.teampossesions
        self.ptsh = self.pts*100 / self.teampossesions
        self.tovh = self.tov*100 / self.teampossesions
        self.fgah = self.fga*100 / self.teampossesions
        self.ftah = self.fta*100 / self.teampossesions
        """Stats used in formulas"""
        self.box_creation = self.find_box_creation()
        self.offensive_load = self.find_offensive_load()
        self.usage_rate = self.find_usage_rate()
        self.accum = [self.shooting_quality, self.box_creation,self.offensive_load,self.usage_rate,self.height,self.wingspan,self.spacing,self.filtered_splits]
    
    """
    Usage and creation metrics calculators
    """
    def find_box_creation(self): 
        """
        Box Creation formula from Ben Taylor
        Uses per 100 team possession stats
        Should output values between 0 and ~20 (Westbrook's historic season)
        """
        # Constants from the formula
        AST_COEF = 0.1843
        SCORING_COEF = 0.0969
        THREE_PROF_COEF = -2.3021
        INTERACTION_COEF = 0.0582
        INTERCEPT = -1.1942
        
        # Calculate main terms
        ast_term = self.asth * AST_COEF
        scoring_term = (self.ptsh + self.tovh) * SCORING_COEF
        three_prof_term = THREE_PROF_COEF * self.three_pt_prof
        interaction_term = INTERACTION_COEF * (self.asth * (self.ptsh + self.tovh) * self.three_pt_prof)
        
        box = ast_term + scoring_term + three_prof_term + interaction_term + INTERCEPT
        return max(0, box)
    
    def find_offensive_load(self):
        """
        Offensive Load calculation using the formula:
        Offensive Load = (Assists-(0.38*Box Creation))*0.75 + FGA + FTA*0.44 + Box Creation + Turnovers
        All stats are per 100 possessions
        Should output values between 0 and 100
        """
        # Convert all stats to per 100 possession rates if they aren't already
        assists_per_100 = self.asth
        fga_per_100 = self.fgah
        fta_per_100 = self.ftah
        tov_per_100 = self.tovh
        box_creation = self.box_creation * 1.5  # assuming this is already scaled properly # 1.5 cuz? 

        # Following the exact formula with proper parentheses:
        # (Assists-(0.38*Box Creation))*0.75 + FGA + FTA*0.44 + Box Creation + Turnovers
        offensive_load = (
            ((assists_per_100 - (0.38 * box_creation)) * 0.75) +  # Assist component
            fga_per_100 +                                         # Field goal attempts
            (fta_per_100 * 0.44) +                               # Free throw attempts
            box_creation +                                        # Box creation
            tov_per_100                                          # Turnovers
        )
        
        return offensive_load
    # if box creation is wrong, offensive load is wrong as offensive load uses box creation 
    def find_usage_rate(self):
        usage_rate = 100* (self.fga + 0.44 * self.fta + self.tov) * (self.team_mp / 5) / (self.mp * (self.team_fga + 0.44 * self.team_fta + self.team_tov))
        #usage_rate = 100*(0.33*self.ast + self.fga + 0.44 * self.fta + self.tov )/ self.teampossesions
        return usage_rate 

    def get_player_id(self,name):
        player = [player for player in players.get_players() if player['full_name'] == name][0]
        return player['id']
    def get_player_stats(self,season_id):
        career = PlayerCareerStats(self.player_id).get_data_frames()[0]
        filtered_career = career[career['SEASON_ID'] == season_id]
        return filtered_career.iloc[0]
    def get_player_team_id(self, season_id):
        # Filter rows by SEASON_ID to get the correct team
        # filtered_stats = self.career_stats[self.career_stats['SEASON_ID'] == season_id] # this filters to our correcrt season
        filtered_stats = self.player_stats
        if not filtered_stats.empty:
            return filtered_stats['TEAM_ID'] # this gets the team id for the season, by using iloc 0 , im pretty sure there is ONLY one row, so iloc 0 works well 
        else:
            raise ValueError(f"No team found for {self.name} in season {season_id}.")

    def get_team_stats(self, year):
        # Fetch all team stats for the given season
        team_stats = leaguedashteamstats.LeagueDashTeamStats(season=year).get_data_frames()[0]
        
        # Filter for the team corresponding to self.team_id
        filtered_stats = team_stats[team_stats['TEAM_ID'] == self.team_id] 
        
        # Ensure the team exists and return the first row of stats as a Series
        if not filtered_stats.empty:
            return filtered_stats.iloc[0]
        else:
            raise ValueError(f"Team stats for team_id {self.team_id} not found in season {year}.")


    
    
    def __str__(self):
        #return f"Player: {self.name}, Box Creation: {self.box_creation}, Offensive Load: {self.offensive_load}, Usage Rate: {self.usage_rate} Height: {self.height}, Weight: {self.weight}, wingspan: {self.wingspan} " # im getting a weird output here, its a pandas dframe?
        #return f"height {self.height} weight {self.weight} wingspan {self.wingspan} " # ??? if u just call these it doesnt work, but if ucall it w the self.name it works 
        #return f"player: {self.name} wingspan {self.wingspan} " # this treturns wingspans on every player in the draft 
        #return f" playername : {self.name} standardised fg {self.standardised_field_goal_percentage} fgpct {self.field_goal_percentage} league average {self.league_field_goal_percentage}" # this returns the league averages for the current season, we can use this to compare players to the league average
        #return f"spacing {self.spacing} " # this returns the spacing and shooting quality for the player
        return f"  splits {self.filtered_splits} " # this returns the splits for the player
        # self.ast will return his assists for EVERY SEASON  he has played in, so we need to filter it to the season we care abt 
# testcases
lebron = Player("LeBron James","2019-20")
print(lebron)
davis = Player("Anthony Davis","2019-20")
# start our comparison function
def fraction_converter(stat1,stat2):
    stat1 = int(stat1)
    stat2 = int(stat2)
    if stat2 > stat1:
        return stat1/stat2 * 100
    else:
        return (stat2 / stat1) * 100
def splits_converter(split1,split2):
    total = 0 
    for i in range(len(split1)):
        if split1[i] > split2[i]:
            total = total + ((split2[i] / split1[i]) * 100)
        else:
            total = total + ((split1[i] / split2[i]) * 100)
    return total / len(split1)
            
def compare_players(player1: Type[Player], player2: Type[Player]):
    # Compare the box creation of two players

    # print(f"Comparing {player1.name} and {player2.name}:")
    # print(f"Box Creation: {player1.box_creation} vs. {player2.box_creation}")
    # print(f"Offensive Load: {player1.offensive_load} vs. {player2.offensive_load}")
    # print(f"Usage Rate: {player1.usage_rate} vs. {player2.usage_rate}")
    # print(f"Height: {player1.height} vs. {player2.height}")
    # print(f"wingspan: {player1.wingspan} vs. {player2.wingspan}")
    # print(f"spacing: {player1.spacing} vs. {player2.spacing}")
    # print(f"splits {player1.filtered_splits} vs {player2.filtered_splits}")
    # get these numbers, and then find how similar they are to the player 1, so fractions of the player 1 stats, depending on whos bigger 
    total = 0
    for i in range(0,len(player1.accum)-1):
        total = total + fraction_converter(player1.accum[i],player2.accum[i])
    total = total + splits_converter(player1.filtered_splits,player2.filtered_splits)
    return total / len(player1.accum)

#print(compare_players(lebron,davis)) # this is a test case to see if the function works, it should return the same values for both players

korver = Player("Kyle Korver","2017-18")
thompson = Player("Klay Thompson","2017-18")

print(compare_players(korver,thompson)) # this is a test case to see if the function works, it should return the same values for both players