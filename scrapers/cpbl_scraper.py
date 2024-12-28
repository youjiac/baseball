import requests
from bs4 import BeautifulSoup
import logging
from pathlib import Path

class CPBLScraper:
    def __init__(self):
        self.base_url = "https://www.cpbl.com.tw/team"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.logger = self._setup_logger()
        self.current_team_code = None  # 新增隊伍代碼屬性

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
            # 設置當前處理的球隊代碼
            self.current_team_code = team_id
            
            # 設置請求參數
            params = {'ClubNo': team_id}
            
            self.logger.info(f"正在抓取 {team_id} 的資料")
            
            # 發送請求
            response = requests.get(self.base_url, params=params, headers=self.headers)
            response.encoding = 'utf-8'
            
            # 保存調試信息
            debug_path = Path(__file__).parent.parent / "app" / "data"
            debug_path.mkdir(parents=True, exist_ok=True)
            debug_file = debug_path / f"{team_id.lower()}_debug.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # 檢查響應狀態
            response.raise_for_status()
            
            # 解析網頁
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 取得球隊基本資訊
            team_info = self._parse_team_info(soup)
            
            # 取得球員資料
            players_data = {
                'coaches': self._parse_category(soup, 'coach'),
                'pitchers': self._parse_category(soup, 'pitcher'),
                'catchers': self._parse_category(soup, 'catcher'),
                'infielders': self._parse_category(soup, 'infielder'),
                'outfielders': self._parse_category(soup, 'outfielder')
            }
            
            return {
                'team_info': team_info,
                'players': players_data
            }
            
        except Exception as e:
            self.logger.error(f"抓取 {team_id} 資料時發生錯誤: {str(e)}")
            raise

    def _parse_team_info(self, soup):
        """解析球隊基本資訊"""
        info = {}
        
        # 設定球隊成立年份對照表
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
            self.logger.debug(f"成立年份對照表: {team_established_years}")
            
            team_brief = soup.find('div', class_='TeamBrief')
            if team_brief:
                # 解析基本資訊
                name_div = team_brief.find('div', class_='name')
                if name_div:
                    info['name'] = name_div.text.strip()
                
                desc_div = team_brief.find('div', class_='desc')
                if desc_div:
                    info['history'] = desc_div.text.strip()
                
                # 從球隊代碼查詢成立年份
                info['established'] = team_established_years.get(self.current_team_code, 'N/A')
                
                self.logger.debug(f"設置的成立年份: {info['established']}")
                
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