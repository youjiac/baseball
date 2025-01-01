import logging
from typing import Dict, Optional, List, Set
from dataclasses import dataclass
import streamlit as st
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseballLLMError(Exception):
    """BaseballLLM相關錯誤的基類"""
    pass

class ModelNotReadyError(BaseballLLMError):
    """模型未準備就緒時拋出的錯誤"""
    pass

class QueryProcessingError(BaseballLLMError):
    """查詢處理失敗時拋出的錯誤"""
    pass

class BaseballLLM:
    def __init__(self):
        """初始化棒球助手"""
        st.write("開始初始化 BaseballLLM...")
        self.initialized = False
        self.data = {}
        
        # 球隊ID和名稱對應表
        self.team_mapping = {
            'ACN': '中信兄弟',
            'ADD': '統一7-ELEVEn獅',
            'AJL': '樂天桃猿',
            'AEO': '富邦悍將',
            'AAA': '味全龍',
            'AKP': '台鋼雄鷹'
        }
        
        # 球隊名稱別名對照表
        self.team_aliases = {
            'ACN': ['中信兄弟', '兄弟', '中信'],
            'ADD': ['統一7-ELEVEn獅', '統一獅', '統一', '統一7-11獅'],
            'AJL': ['樂天桃猿', '樂天', '桃猿'],
            'AEO': ['富邦悍將', '富邦', '悍將'],
            'AAA': ['味全龍', '味全', '龍隊'],
            'AKP': ['台鋼雄鷹', '台鋼', '雄鷹']
        }
        
        # 基本響應模板
        self.templates = {
            "greeting": "你好！我是CPBL教練助手，我有中華職棒所有球隊的最新資料。您想了解什麼呢？",
            "team_basic": "{team_name}的基本資料：\n主場：{home}\n總教練：{coach}",
            "team_roster": "{team_name}的{position}名單：\n{players}",
            "error": "抱歉，我無法理解您的問題。請試著用其他方式詢問。",
            "trend_analysis": "{team_name}的近期走勢：\n{trend_data}",
            "head_to_head": "{team1}與{team2}的對戰紀錄：\n{match_records}",
            "home_away": "{team_name}的主客場戰績：\n主場：{home_record}\n客場：{away_record}",
            "league_ranking": "目前聯盟排名：\n{rankings}"
        }
        
        # 查詢關鍵字
        self.keywords = {
            "basic": ["主場", "基本資料", "在哪裡", "是哪裡"],
            "roster": ["名單", "球員", "陣容", "有哪些"],
            "trend": ["走勢", "趨勢", "近期", "最近", "變化"],
            "head_to_head": ["交手", "對戰", "紀錄"],
            "home_away": ["主場", "客場", "主客場"],
            "positions": {
                "投手": "pitchers",
                "捕手": "catchers",
                "內野手": "infielders",
                "外野手": "outfielders",
                "教練團": "coaches"
            }
        }
        
        self.initialized = True
        st.success("BaseballLLM 初始化成功")

    def _format_trend_data(self, trend_data: List[Dict]) -> str:
        """格式化趨勢數據"""
        if not trend_data:
            return "無近期數據"
        
        formatted = []
        for data in trend_data:
            formatted.append(
                f"{data['date']}: {'勝' if data['result'] == 'W' else '敗'} "
                f"({data['score']})"
            )
        return "\n".join(formatted)

    def _format_match_records(self, records: List[Dict]) -> str:
        """格式化對戰紀錄"""
        if not records:
            return "無近期對戰紀錄"
        
        formatted = []
        for record in records:
            formatted.append(
                f"{record['date']}: {record['home']} {record['score']} {record['away']}"
            )
        return "\n".join(formatted)

    def _format_venue_record(self, record: Dict) -> str:
        """格式化主客場戰績"""
        return f"勝場：{record['wins']}場 敗場：{record['losses']}場 勝率：{record['ratio']}"

    def _handle_trend_query(self, team_id: str, team_name: str) -> str:
        """處理趨勢分析查詢"""
        try:
            trend_data = self.data.get(team_id, {}).get('trends', [])
            if not trend_data:
                return f"{team_name}的趨勢分析資料暫時無法取得。"
            return self.templates["trend_analysis"].format(
                team_name=team_name,
                trend_data=self._format_trend_data(trend_data)
            )
        except Exception as e:
            logger.error(f"趨勢分析處理失敗: {str(e)}")
            return f"{team_name}的趨勢分析資料暫時無法取得。"

    def _handle_head_to_head_query(self, team1_id: str, team2_id: str) -> str:
        """處理對戰紀錄查詢"""
        matches = self.data.get('head_to_head', {}).get(f"{team1_id}_{team2_id}", [])
        return self.templates["head_to_head"].format(
            team1=self.data[team1_id]['team_info']['name'],
            team2=self.data[team2_id]['team_info']['name'],
            match_records=self._format_match_records(matches)
        )

    def _handle_home_away_query(self, team_id: str, team_name: str) -> str:
        """處理主客場分析查詢"""
        venue_stats = self.data[team_id].get('venue_stats', {})
        return self.templates["home_away"].format(
            team_name=team_name,
            home_record=self._format_venue_record(venue_stats.get('home', {})),
            away_record=self._format_venue_record(venue_stats.get('away', {}))
        )

    def _handle_ranking_query(self, question: str) -> str:
        """處理戰績相關查詢"""
        # 如果是整體排名查詢
        if "排名" in question and not any(team in question for team in self.team_aliases):
            rankings = []
            for team_id, team_data in self.data.items():
                team_name = team_data.get('team_info', {}).get('name', '')
                record = team_data.get('record', {})
                if record:
                    rankings.append({
                        'name': team_name,
                        'ratio': record.get('ratio', 0),
                        'rank': record.get('rank', 0)
                    })
            
            rankings.sort(key=lambda x: x['rank'])
            ranking_text = "\n".join([
                f"{i+1}. {team['name']} (勝率: {team['ratio']})"
                for i, team in enumerate(rankings)
            ])
            
            return self.templates["league_ranking"].format(rankings=ranking_text)
        
        # 如果是球隊比較查詢
        if any(kw in question for kw in self.keywords["comparison"]):
            teams = []
            for team_name in self.team_aliases:
                if team_name in question:
                    teams.append(team_name)
            
            if len(teams) == 2:
                team1_data = next((data for _, data in self.data.items() 
                                if data.get('team_info', {}).get('name') == teams[0]), None)
                team2_data = next((data for _, data in self.data.items() 
                                if data.get('team_info', {}).get('name') == teams[1]), None)
                
                if team1_data and team2_data:
                    return self.templates["team_comparison"].format(
                        team1=teams[0],
                        ratio1=team1_data.get('record', {}).get('ratio', 'N/A'),
                        rank1=team1_data.get('record', {}).get('rank', 'N/A'),
                        team2=teams[1],
                        ratio2=team2_data.get('record', {}).get('ratio', 'N/A'),
                        rank2=team2_data.get('record', {}).get('rank', 'N/A')
                    )
        
        return None

    def _find_team(self, question: str) -> tuple:
        """尋找問題中提到的球隊"""
        for team_id, aliases in self.team_aliases.items():
            if any(alias in question for alias in aliases):
                team_data = self.data.get(team_id)
                if team_data:
                    team_info = team_data.get('team_info', {})
                    if team_info:
                        full_name = team_info.get('name', '')
                        if full_name:
                            return team_id, full_name
        return None, None

    def query(self, question: str) -> str:
        """處理用戶查詢"""
        try:
            # 檢查初始化狀態
            if not self.initialized:
                logger.error("系統尚未初始化")
                return "系統尚未準備就緒，請稍後再試。"

            # 檢查數據是否存在
            if not self.data:
                logger.error("數據為空")
                return "系統數據未載入，請稍後再試。"

            # 基本問候處理
            if any(word in question.lower() for word in ["你好", "哈囉", "嗨", "hi", "hello"]):
                return self.templates["greeting"]

            # 清理問題文字
            question = question.replace("？", "").replace("?", "").strip()
            logger.info(f"處理查詢: {question}")

            # 識別球隊
            team_id, team_name = self._find_team(question)
            if not team_id:
                logger.info("未找到球隊")
                return "請告訴我您想查詢哪支球隊的資訊。"

            logger.info(f"找到球隊: {team_name} ({team_id})")

            # 檢查球隊數據是否存在
            team_data = self.data.get(team_id, {})
            if not team_data:
                logger.error(f"未找到 {team_name} 的數據")
                return f"未找到 {team_name} 的數據"

            team_info = team_data.get('team_info', {})
            if not team_info:
                team_info = {}  # 確保 team_info 不會是 None

            # 準備回應
            responses = []

            # 檢查是否是球員名單查詢
            if any(kw in question for kw in self.keywords["roster"]):
                positions = []
                for pos in self.keywords["positions"].keys():
                    if pos in question:
                        positions.append(pos)
                
                if not positions:  # 如果沒有指定位置，則查詢所有位置
                    positions = list(self.keywords["positions"].keys())

                for position in positions:
                    position_key = self.keywords["positions"][position]
                    players = team_data.get('players', {}).get(position_key, [])
                    if players:
                        player_list = "\n".join([
                            f"* {p.get('name', '未知')} (背號:{p.get('number', '未知')})"
                            for p in players
                        ])
                        responses.append(f"{team_name}的{position}名單：\n{player_list}")
                    else:
                        responses.append(f"{team_name}目前無{position}資料")

            # 檢查是否是基本資料查詢
            if (not responses) or any(kw in question for kw in self.keywords["basic"]):
                responses.extend([
                    f"{team_name}的基本資料：",
                    f"主場：{team_info.get('home', '未知')}",
                    f"總教練：{team_info.get('coach', '未知')}"
                ])

            # 檢查戰績資料
            record = team_data.get('record', {})
            if record:
                responses.append(
                    f"目前戰績：{record.get('wins', 0)}勝{record.get('losses', 0)}敗 "
                    f"勝率{record.get('ratio', '0.000')}"
                )

            # 合併所有回應
            final_response = "\n".join(responses)
            logger.info(f"生成回應: {final_response}")
            return final_response

        except Exception as e:
            logger.error(f"查詢處理發生錯誤: {str(e)}", exc_info=True)
            return "抱歉，處理您的問題時發生錯誤，請稍後再試。"

    def _identify_positions(self, question: str) -> List[str]:
        """識別問題中提到的所有位置"""
        positions = []
        
        # 檢查單一位置
        for pos in self.keywords["positions"].keys():
            if pos in question:
                positions.append(pos)
        
        # 檢查位置組合
        for i, pos1 in enumerate(list(self.keywords["positions"].keys())):
            for pos2 in list(self.keywords["positions"].keys())[i+1:]:
                if (f"{pos1}和{pos2}" in question or 
                    f"{pos1}與{pos2}" in question or
                    (pos1 in question and pos2 in question and 
                     ("和" in question or "與" in question))):
                    if pos1 not in positions:
                        positions.append(pos1)
                    if pos2 not in positions:
                        positions.append(pos2)
        
        return positions

    def _format_player_list(self, players: List[Dict]) -> str:
        """格式化球員列表"""
        if not players:
            return "無資料"
        return "\n".join([
            f"* {p.get('name', '未知')} (背號:{p.get('number', '未知')})"
            for p in players
        ])

    def initialize_knowledge(self, baseball_data: Dict) -> bool:
        """初始化知識庫"""
        try:
            self.data = {}
            
            # 複製數據並確保所有必要的字段都存在
            for team_id, team_data in baseball_data.items():
                if team_id == 'head_to_head':
                    self.data[team_id] = team_data
                    continue
                    
                self.data[team_id] = {
                    'team_info': team_data.get('team_info', {
                        'name': '',
                        'home': '',
                        'coach': ''
                    }),
                    'players': team_data.get('players', {
                        'coaches': [],
                        'pitchers': [],
                        'catchers': [],
                        'infielders': [],
                        'outfielders': []
                    }),
                    'record': team_data.get('record', {
                        'wins': 0,
                        'losses': 0,
                        'ratio': '0.000',
                        'rank': 0
                    }),
                    'trends': team_data.get('trends', []),
                    'venue_stats': team_data.get('venue_stats', {
                        'home': {'wins': 0, 'losses': 0, 'ratio': '0.000'},
                        'away': {'wins': 0, 'losses': 0, 'ratio': '0.000'}
                    })
                }
            
            # 確保 head_to_head 數據存在
            if 'head_to_head' not in self.data:
                self.data['head_to_head'] = {}
            
            logger.info("知識庫初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"知識庫初始化失敗: {str(e)}")
            return False