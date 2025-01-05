import requests
from bs4 import BeautifulSoup
import logging
from pathlib import Path
from datetime import datetime, timedelta

class CPBLScraper:
    def __init__(self):
        """初始化"""
        self.base_url = "https://www.cpbl.com.tw/team"
        self.standings_url = "https://www.cpbl.com.tw/standings/regular"
        self.schedule_url = "https://www.cpbl.com.tw/schedule"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.logger = self._setup_logger()
        self.current_team_code = None

    def _setup_logger(self):
        """設置日誌記錄器"""
        logger = logging.getLogger('CPBLScraper')
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def fetch_team_data(self, team_id):
        """抓取球隊資料"""
        try:
            self.current_team_code = team_id
            params = {'ClubNo': team_id}
            
            self.logger.info(f"正在抓取 {team_id} 的資料")
            
            # 發送請求並保存調試信息
            response = requests.get(self.base_url, params=params, headers=self.headers)
            response.encoding = 'utf-8'
            
            debug_path = Path(__file__).parent.parent / "app" / "data"
            debug_path.mkdir(parents=True, exist_ok=True)
            debug_file = debug_path / f"{team_id.lower()}_debug.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 取得各項資料
            team_info = self._parse_team_info(soup)
            players_data = {
                'coaches': self._parse_category(soup, 'coach'),
                'pitchers': self._parse_category(soup, 'pitcher'),
                'catchers': self._parse_category(soup, 'catcher'),
                'infielders': self._parse_category(soup, 'infielder'),
                'outfielders': self._parse_category(soup, 'outfielder')
            }
            standings_data = self.fetch_standings().get(team_id, {})
            venue_data = self.fetch_venue_stats().get(team_id, {})
            recent_games = self.fetch_recent_games().get(team_id, [])
            
            return {
                'team_info': team_info,
                'players': players_data,
                'record': standings_data,
                'venue_stats': venue_data,
                'trends': recent_games
            }
            
        except Exception as e:
            self.logger.error(f"抓取 {team_id} 資料時發生錯誤: {str(e)}")
            raise

    def fetch_standings(self):
        """抓取戰績資料"""
        try:
            self.logger.info("正在抓取戰績資料")
            response = requests.get(self.standings_url, headers=self.headers)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            standings = {}
            
            # 防禦性查找
            standings_table = None
            tables = soup.find_all('table')
            for table in tables:
                if table.find('tr'):  # 找到含有行的表格
                    standings_table = table
                    break
                    
            if standings_table:
                rows = standings_table.find_all('tr')[1:]  # 跳過表頭
                for row in rows:
                    try:
                        cols = row.find_all('td')
                        if len(cols) >= 5:
                            # 更靈活的隊名查找
                            team_name = None
                            team_div = row.find('div', class_=['team-w-trophy', 'team'])
                            if team_div:
                                team_name = team_div.get_text(strip=True)
                                
                            if team_name:
                                team_id = self._get_team_id(team_name)
                                if team_id:
                                    # 提取數據，提供默認值
                                    wins = 0
                                    losses = 0
                                    ratio = "0.000"
                                    
                                    # 嘗試解析勝負場次
                                    record_text = cols[2].get_text(strip=True)
                                    if '-' in record_text:
                                        parts = record_text.split('-')
                                        if len(parts) >= 3:
                                            wins = int(parts[0])
                                            losses = int(parts[2])
                                            
                                    # 嘗試解析勝率
                                    ratio_text = cols[3].get_text(strip=True)
                                    if ratio_text:
                                        ratio = ratio_text
                                        
                                    standings[team_id] = {
                                        'rank': int(cols[0].find('div', class_='rank').text.strip()) if cols[0].find('div', class_='rank') else 0,
                                        'wins': wins,
                                        'losses': losses,
                                        'ratio': ratio
                                    }
                    except Exception as e:
                        self.logger.error(f"處理球隊數據時發生錯誤: {str(e)}")
                        continue
                        
            return standings
                        
        except Exception as e:
            self.logger.error(f"抓取戰績資料失敗: {str(e)}")
            return {}

    def fetch_venue_stats(self):
        """抓取主客場戰績"""
        try:
            self.logger.info("正在抓取主客場戰績")
            response = requests.get(self.standings_url, headers=self.headers)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            venue_stats = {}
            
            # 修正: 使用正確的表格定位方式
            table = soup.find('div', class_='RecordTable').find('table')
            if table:
                rows = table.find_all('tr')[1:]  # 跳過表頭
                for row in rows:
                    cols = row.find_all('td')
                    team_name = cols[0].find('div', class_='team-w-trophy').find('a').text.strip()
                    team_id = self._get_team_id(team_name)
                    
                    if team_id:
                        home_data = cols[-2].text.strip().split('-')
                        away_data = cols[-1].text.strip().split('-')
                        
                        venue_stats[team_id] = {
                            'home': {
                                'wins': int(home_data[0]),
                                'losses': int(home_data[1]),
                                'ratio': f"{float(home_data[0])/(float(home_data[0])+float(home_data[1])):.3f}"
                            },
                            'away': {
                                'wins': int(away_data[0]),
                                'losses': int(away_data[1]),
                                'ratio': f"{float(away_data[0])/(float(away_data[0])+float(away_data[1])):.3f}"
                            }
                        }
            return venue_stats
                
        except Exception as e:
            self.logger.error(f"抓取主客場戰績失敗: {str(e)}")
            return {}

    def fetch_recent_games(self):
        """抓取近期比賽"""
        try:
            self.logger.info("正在抓取近期比賽")
            recent_games = {}
            
            # 取得最近30天的比賽
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            params = {
                'date': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d')
            }
            
            response = requests.get(self.schedule_url, headers=self.headers, params=params)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            for game in soup.find_all('div', class_='game'):
                try:
                    date = game.find('div', class_='date').text.strip()
                    teams = game.find_all('div', class_='team')
                    score = game.find('div', class_='score').text.strip()
                    
                    if len(teams) == 2:
                        home_team = teams[0].text.strip()
                        away_team = teams[1].text.strip()
                        home_id = self._get_team_id(home_team)
                        away_id = self._get_team_id(away_team)
                        
                        if home_id and away_id:
                            scores = score.split(':')
                            if len(scores) == 2:
                                home_score = int(scores[0])
                                away_score = int(scores[1])
                                
                                game_data = {
                                    'date': date,
                                    'result': 'W' if home_score > away_score else 'L',
                                    'score': f"{home_score}-{away_score}"
                                }
                                
                                # 添加到兩隊的記錄
                                recent_games.setdefault(home_id, []).append(game_data)
                                # 為客隊添加相反的勝負結果
                                away_game_data = game_data.copy()
                                away_game_data['result'] = 'L' if home_score > away_score else 'W'
                                recent_games.setdefault(away_id, []).append(away_game_data)
                except Exception as e:
                    self.logger.error(f"處理比賽資料時發生錯誤: {str(e)}")
                    continue
            
            # 限制每隊最多顯示10場比賽
            for team_id in recent_games:
                recent_games[team_id] = sorted(
                    recent_games[team_id],
                    key=lambda x: x['date'],
                    reverse=True
                )[:10]
                
            return recent_games
            
        except Exception as e:
            self.logger.error(f"抓取近期比賽失敗: {str(e)}")
            return {}

    def fetch_head_to_head(self):
        """抓取對戰紀錄"""
        try:
            self.logger.info("正在抓取對戰紀錄")
            head_to_head = {}
            
            # 取得最近60天的比賽
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            params = {
                'date': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d')
            }
            
            response = requests.get(self.schedule_url, headers=self.headers, params=params)
            response.encoding = 'utf-8'
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            for game in soup.find_all('div', class_='game'):
                try:
                    date = game.find('div', class_='date').text.strip()
                    teams = game.find_all('div', class_='team')
                    score = game.find('div', class_='score').text.strip()
                    
                    if len(teams) == 2:
                        home_team = teams[0].text.strip()
                        away_team = teams[1].text.strip()
                        home_id = self._get_team_id(home_team)
                        away_id = self._get_team_id(away_team)
                        
                        if home_id and away_id:
                            game_data = {
                                'date': date,
                                'home': home_team,
                                'away': away_team,
                                'score': score.replace(':', '-')
                            }
                            
                            key = f"{min(home_id, away_id)}_{max(home_id, away_id)}"
                            head_to_head.setdefault(key, []).append(game_data)
                except Exception as e:
                    self.logger.error(f"處理對戰資料時發生錯誤: {str(e)}")
                    continue
            
            # 限制每對戰組合最多顯示10場比賽
            for key in head_to_head:
                head_to_head[key] = sorted(
                    head_to_head[key],
                    key=lambda x: x['date'],
                    reverse=True
                )[:10]
                
            return head_to_head
            
        except Exception as e:
            self.logger.error(f"抓取對戰紀錄失敗: {str(e)}")
            return {}

    def _get_team_id(self, team_name):
        """從球隊名稱取得ID"""
        team_mapping = {
            '中信兄弟': 'ACN',
            '統一7-ELEVEn獅': 'ADD',
            '樂天桃猿': 'AJL',
            '富邦悍將': 'AEO',
            '味全龍': 'AAA',
            '台鋼雄鷹': 'AKP'
        }
        return team_mapping.get(team_name)

    def _parse_team_info(self, soup):
        """解析球隊基本資訊"""
        info = {}
        team_established_years = {
            'ACN': '1990',  # 中信兄弟 (原兄弟象)
            'ADD': '1990',  # 統一7-ELEVEn獅 (原統一獅)
            'AJL': '2003',  # 樂天桃猿 (原第一金剛)
            'AEO': '1993',  # 富邦悍將 (原俊國熊)
            'AAA': '1990',  # 味全龍
            'AKP': '2023'   # 台鋼雄鷹
        }

        try:
            self.logger.debug(f"目前處理的球隊代碼: {self.current_team_code}")
            
            team_brief = soup.find('div', class_='TeamBrief')
            if team_brief:
                # 解析基本資訊
                name_div = team_brief.find('div', class_='name')
                if name_div:
                    info['name'] = name_div.text.strip()
                
                desc_div = team_brief.find('div', class_='desc')
                if desc_div:
                    info['history'] = desc_div.text.strip()
                
                info['established'] = team_established_years.get(
                    self.current_team_code, 'N/A')
                
                # 解析其他資訊
                for item in team_brief.find_all('dd'):
                    label_div = item.find('div', class_='label')
                    desc_div = item.find('div', class_='desc')
                    if label_div and desc_div:
                        label = label_div.text.strip()
                        desc = desc_div.text.strip()
                        
                        if '主球場' in label:
                            info['home'] = desc
                        elif '總教練' in label:
                            info['coach'] = desc
                            
        except Exception as e:
            self.logger.error(f"解析球隊資訊時發生錯誤: {str(e)}")
            return info
        
    def _parse_category(self, soup, category):
            """解析特定類別的球員"""
            players = []
            try:
                # 找到類別區塊
                category_title = soup.find('a', {'name': category})
                if category_title:
                    # 找到球員列表的容器
                    players_list = category_title.find_next('div', class_='TeamPlayersList')
                    if players_list:
                        # 遍歷所有球員項目
                        for player_item in players_list.find_all('div', class_='item'):
                            player_data = self._extract_player_data(player_item)
                            if player_data:
                                players.append(player_data)
                
            except Exception as e:
                self.logger.error(f"解析 {category} 球員時發生錯誤: {str(e)}")
                
            return players

    def _extract_player_data(self, player_item):
        """從球員區塊提取資料"""
        try:
                cont_div = player_item.find('div', class_='cont')
                if not cont_div:
                    return None
                
                player_data = {
                    'name': '',
                    'number': '',
                    'position': ''
                }
                
                # 提取名字
                name_div = cont_div.find('div', class_='name')
                if name_div:
                    # 如果有連結，從連結取得名字
                    name_link = name_div.find('a')
                    if name_link:
                        player_data['name'] = name_link.text.strip()
                    else:
                        player_data['name'] = name_div.text.strip()
                
                # 提取背號
                number_div = cont_div.find('div', class_='number')
                if number_div:
                    player_data['number'] = number_div.text.strip()
                
                # 提取守備位置
                pos_div = cont_div.find('div', class_='pos')
                if pos_div:
                    player_data['position'] = pos_div.text.strip()
                
                # 提取照片 URL（如果有的話）
                img_div = player_item.find('div', class_='img')
                if img_div:
                    img_span = img_div.find('span')
                    if img_span and 'style' in img_span.attrs:
                        style = img_span['style']
                        if 'background-image:url(' in style:
                            url = style.split('url(')[1].split(')')[0].strip("'")
                            player_data['photo'] = url
                
                return player_data if any(player_data.values()) else None
                
        except Exception as e:
                self.logger.error(f"提取球員資料時發生錯誤: {str(e)}")
                return None