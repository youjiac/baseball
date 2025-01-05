import requests
from bs4 import BeautifulSoup

class TeamScraper:
    def __init__(self):
        self.base_url = "https://www.cpbl.com.tw/team"
    
    def get_team_data(self, team_id):
        """獲取球隊資料"""
        try:
            # 設置請求參數
            params = {
                'ClubNo': team_id,
                'KindCode': 'A'  # 一軍
            }
            
            # 設置請求標頭
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # 發送請求
            response = requests.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            
            # 解析網頁
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 取得球隊基本資訊
            team_info = self._parse_team_info(soup)
            
            # 取得球員資料
            players = {
                'coaches': self._parse_player_section(soup, "coach"),
                'pitchers': self._parse_player_section(soup, "pitcher"),
                'catchers': self._parse_player_section(soup, "catcher"),
                'infielders': self._parse_player_section(soup, "infielder"),
                'outfielders': self._parse_player_section(soup, "outfielder")
            }
            
            return {
                'team_info': team_info,
                'players': players
            }
            
        except Exception as e:
            print(f"Error fetching team data: {str(e)}")
            return None
    
    def _parse_team_info(self, soup):
        """解析球隊基本資訊"""
        info = {}
        try:
            team_brief = soup.find('div', class_='TeamBrief')
            if team_brief:
                info['name'] = team_brief.find('div', class_='name').text.strip()
                
                # 解析詳細資訊
                for item in team_brief.find_all('dd'):
                    label = item.find('div', class_='label').text.strip()
                    desc = item.find('div', class_='desc').text.strip()
                    
                    if '總教練' in label:
                        info['coach'] = desc
                    elif '主球場' in label:
                        info['home'] = desc
                    elif '球團網站' in label:
                        info['website'] = desc
        except Exception as e:
            print(f"Error parsing team info: {str(e)}")
        
        return info
    
    def _parse_player_section(self, soup, section_id):
        """解析特定類型的球員資料"""
        players = []
        try:
            section = soup.find('div', {'id': section_id})
            if section:
                for player in section.find_all('div', class_='item'):
                    player_data = {
                        'name': player.find('div', class_='name').text.strip(),
                        'number': player.find('div', class_='number').text.strip(),
                        'position': player.find('div', class_='pos').text.strip()
                    }
                    
                    # 取得其他可能的資訊
                    if img := player.find('img'):
                        player_data['image'] = img.get('src', '')
                        
                    players.append(player_data)
        except Exception as e:
            print(f"Error parsing {section_id} section: {str(e)}")
        
        return players