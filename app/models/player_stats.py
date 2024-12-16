import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import logging
import streamlit as st

class PlayerStats:
    def __init__(self):
        self.base_url = "https://www.cpbl.com.tw/stats/recordall"
        self.logger = self._setup_logger()
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def _cached_fetch(year, position, record_type, active, defence_type):
        """靜態方法處理緩存"""
        instance = PlayerStats()
        return instance.fetch_player_stats(
            year=str(year),
            position=position,
            record_type=record_type,
            active=active,
            defence_type=defence_type
        )
    
    def get_cached_stats(self, year, position, record_type, active, defence_type):
        """對外的介面方法"""
        return self._cached_fetch(
            year=year,
            position=position,
            record_type=record_type,
            active=active,
            defence_type=defence_type
        )
        
    def _setup_logger(self):
        """設置日誌記錄器"""
        logger = logging.getLogger('player_stats')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger

    def fetch_player_stats(self, year='2024', position='01', record_type='A', active='01', defence_type='99'):
        """抓取球員統計資料"""
        try:
            # 設定請求標頭
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
                'Referer': 'https://www.cpbl.com.tw/',
            }

            # 建立請求參數
            data = {
                'Length': 0,
                'ExecAction': 'Q',
                'Online': active,
                'KindCode': record_type,
                'Year': year,
                'Position': position,
                'DefenceType': defence_type,
                'Sortby': '01',  # 預設以打擊率排序
                'GameType': '01',  # 一軍
                'Index': 0,
                'PageSize': 30
            }

            # 發送 POST 請求
            response = requests.post(
                'https://www.cpbl.com.tw/stats/recordallaction',
                headers=headers,
                data=data
            )
            response.raise_for_status()
            
            # 解析網頁內容
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取表格數據
            players_data = self._parse_table(soup)
            
            return {
                'success': True,
                'data': players_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except requests.RequestException as e:
            self.logger.error(f"抓取數據時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': f"網路請求錯誤: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"處理數據時發生錯誤: {str(e)}")
            return {
                'success': False,
                'error': f"數據處理錯誤: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }

    def _parse_table(self, soup):
        """解析HTML表格數據"""
        players = []
        table = soup.find('div', class_='RecordTable')
        
        if not table:
            self.logger.warning("未找到數據表格")
            return players
            
        rows = table.find_all('tr')[1:]  # 跳過表頭
        
        for row in rows:
            try:
                cols = row.find_all('td')
                if len(cols) > 0:
                    player_info = cols[0].find('div', class_='player-w-logo')
                    if player_info:
                        name_elem = player_info.find('span', class_='name')
                        team_elem = player_info.find('span', class_='team_logo')
                        
                        if name_elem and team_elem:
                            player = {
                                'name': name_elem.text.strip(),
                                'team': team_elem.text.strip(),
                                'stats': {
                                    'avg': cols[1].text.strip() or '0',        # 打擊率
                                    'games': cols[2].text.strip() or '0',      # 出賽數
                                    'pa': cols[3].text.strip() or '0',         # 打席數
                                    'ab': cols[4].text.strip() or '0',         # 打數
                                    'runs': cols[5].text.strip() or '0',       # 得分
                                    'rbi': cols[6].text.strip() or '0',        # 打點
                                    'hits': cols[7].text.strip() or '0',       # 安打數
                                    'singles': cols[8].text.strip() or '0',    # 一安
                                    'doubles': cols[9].text.strip() or '0',    # 二安
                                    'triples': cols[10].text.strip() or '0',   # 三安
                                    'hr': cols[11].text.strip() or '0',        # 全壘打
                                    'tb': cols[12].text.strip() or '0',        # 壘打數
                                    'xbh': cols[13].text.strip() or '0',       # 長打數
                                    'bb': cols[14].text.strip() or '0',        # 保送
                                    'so': cols[17].text.strip() or '0',        # 三振
                                    'sb': cols[21].text.strip() or '0',        # 盜壘
                                    'cs': cols[22].text.strip() or '0',        # 盜壘刺
                                    'obp': cols[23].text.strip() or '0',       # 上壘率
                                    'slg': cols[24].text.strip() or '0',       # 長打率
                                    'ops': cols[25].text.strip() or '0'        # 整體攻擊指數
                                }
                            }
                            players.append(player)
            except Exception as e:
                self.logger.error(f"解析球員數據時發生錯誤: {str(e)}")
                continue
                
        return players