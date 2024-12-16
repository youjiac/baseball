
class TeamAnalyzer:
    def __init__(self, data):
        self.data = data

    def get_team_stats(self, team_id):
        """獲取球隊統計資料"""
        team_data = self.data.get(team_id)
        if team_data:
            return {
                "total_players": sum(len(players) for players in team_data['players'].values()),
                "positions": {
                    "pitchers": len(team_data['players']['pitchers']),
                    "catchers": len(team_data['players']['catchers']),
                    "infielders": len(team_data['players']['infielders']),
                    "outfielders": len(team_data['players']['outfielders'])
                }
            }
        return None