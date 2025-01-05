import logging
from typing import Dict, List, Optional
import ollama
import json

# 設置日誌記錄
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseballLLM:
    def __init__(self):
        """初始化棒球助手"""
        self.data = {}
        self.initialized = False
        try:
            self.initialized = True
            logger.info("LLM 系統初始化成功")
        except Exception as e:
            logger.error(f"LLM 初始化失敗: {str(e)}")

    def initialize_knowledge(self, baseball_data: Dict) -> bool:
        """初始化知識庫"""
        try:
            self.data = baseball_data
            logger.info("知識庫初始化成功")
            return True
        except Exception as e:
            logger.error(f"知識庫初始化失敗: {str(e)}")
            return False

    def extract_keywords(self, question: str) -> List[str]:
        """提取問題中的關鍵字，包括球員名稱和球隊名稱"""
        keywords = []
        try:
            # 1. 提取球隊名稱
            for team_id, team_info in self.data.items():
                team_name = team_info.get('team_info', {}).get('name', '')
                if team_name and team_name in question:
                    keywords.append(team_id)
                    keywords.append(team_name)

            # 2. 提取球員名稱
            for team_id, team_info in self.data.items():
                players = team_info.get('players', {})
                for category in ['coaches', 'pitchers', 'catchers', 'infielders', 'outfielders']:
                    for player in players.get(category, []):
                        player_name = player.get('name', '')
                        if player_name and player_name in question:
                            if team_id not in keywords:
                                keywords.append(team_id)
                            keywords.append(player_name)

            # 3. 提取位置關鍵字
            positions = [
                "投手", "捕手", "內野手", "外野手", "游擊手", 
                "一壘手", "二壘手", "三壘手", "中外野手", "左外野手", "右外野手",
                "教練", "總教練", "內野教練", "外野教練", "打擊教練", "投手教練"
            ]
            keywords.extend([pos for pos in positions if pos in question])

            # 4. 提取表現關鍵字
            performance_words = ["表現", "最佳", "優秀", "出色", "強", "厲害", "好"]
            keywords.extend([word for word in performance_words if word in question])

            logger.debug(f"提取的關鍵字: {keywords}")
            return list(set(keywords))  # 去重

        except Exception as e:
            logger.error(f"關鍵字提取失敗: {str(e)}")
            return []

    def get_player_info(self, player_name: str) -> Optional[Dict]:
        """獲取球員詳細信息"""
        try:
            for team_id, team_data in self.data.items():
                players = team_data.get('players', {})
                for category in ['coaches', 'pitchers', 'catchers', 'infielders', 'outfielders']:
                    for player in players.get(category, []):
                        if player.get('name', '') == player_name:
                            return {
                                'team': team_data['team_info']['name'],
                                'position': player.get('position', '未知'),
                                'number': player.get('number', '未知'),
                                'category': category
                            }
            return None
        except Exception as e:
            logger.error(f"獲取球員信息失敗: {str(e)}")
            return None

    def _format_team_data(self, team_data: Dict) -> str:
        """格式化單個球隊數據"""
        try:
            team_info = team_data.get('team_info', {})
            players = team_data.get('players', {})
            
            formatted = [
                f"【{team_info.get('name', '未知球隊')}】",
                f"主場: {team_info.get('home', '未知')}",
                f"總教練: {team_info.get('coach', '未知')}\n"
            ]

            # 格式化球員資料
            categories = {
                'coaches': '教練團',
                'pitchers': '投手群',
                'catchers': '捕手群',
                'infielders': '內野手',
                'outfielders': '外野手'
            }

            for category, title in categories.items():
                if category_players := players.get(category):
                    formatted.append(f"{title}:")
                    for player in category_players:
                        formatted.append(
                            f"- {player.get('name', '未知')} "
                            f"(背號: {player.get('number', '未知')}, "
                            f"位置: {player.get('position', '未知')})"
                        )
                    formatted.append("")  # 添加空行

            return "\n".join(formatted)
        except Exception as e:
            logger.error(f"球隊數據格式化失敗: {str(e)}")
            return "數據格式化失敗"

    def _format_data_for_llm(self, data: Dict) -> str:
        """將數據格式化為LLM易於理解的形式"""
        try:
            if not data:
                return ""
            formatted_teams = []
            for team_id, team_data in data.items():
                formatted_team = self._format_team_data(team_data)
                formatted_teams.append(formatted_team)
            return "\n===\n\n".join(formatted_teams)
        except Exception as e:
            logger.error(f"數據格式化失敗: {str(e)}")
            return "數據格式化失敗"

    def _is_player_query(self, question: str, keywords: List[str]) -> bool:
        """判斷是否為球員查詢"""
        player_query_keywords = ['誰是', '在哪', '效力', '位置', '背號']
        return any(keyword in question for keyword in player_query_keywords)

    def query(self, question: str) -> str:
        """處理用戶查詢"""
        try:
            # 1. 基本問候處理
            greetings = ["你好", "哈囉", "嗨", "hi", "hello"]
            if any(greeting in question.lower() for greeting in greetings):
                return "你好！我是CPBL教練助手，我有中華職棒所有球隊的最新資料。您想了解什麼呢？"

            # 2. 系統狀態檢查
            if not self.initialized:
                return "系統尚未準備就緒，請稍後再試。"

            # 3. 關鍵字提取
            keywords = self.extract_keywords(question)
            logger.info(f"提取到的關鍵字: {keywords}")

            # 4. 球員查詢處理
            if self._is_player_query(question, keywords):
                for keyword in keywords:
                    if player_info := self.get_player_info(keyword):
                        return (
                            f"{keyword}目前效力於{player_info['team']}，"
                            f"守備位置是{player_info['position']}，"
                            f"背號{player_info['number']}。"
                        )

            # 5. 數據過濾與格式化
            relevant_data = {
                team_id: self.data[team_id]
                for team_id in self.data
                if team_id in keywords or any(
                    keyword in json.dumps(self.data[team_id], ensure_ascii=False)
                    for keyword in keywords
                )
            }

            formatted_data = self._format_data_for_llm(relevant_data)

            # 6. 處理無數據情況
            if not formatted_data:
                return "抱歉，我找不到相關的資訊。請嘗試用其他方式詢問，或確認名稱是否正確。"

            # 7. 生成 Prompt
            prompt = f"""你是CPBL教練助手，請根據以下資料回答問題。
            請簡潔專業，像教練回答球迷提問。回答請使用繁體中文。
            
            資料：
            {formatted_data}

            問題：{question}

            請直接回答："""

            # 8. 呼叫 LLM 生成回應
            response = ollama.chat(
                model='llama3.1',
                messages=[{'role': 'user', 'content': prompt}]
            )

            return response['message']['content']

        except Exception as e:
            logger.error(f"查詢處理失敗: {str(e)}")
            return f"系統處理出現問題，請稍後再試。錯誤信息: {str(e)}"

    def filter_by_position(self, data: Dict, position: str) -> Dict:
        """根據守備位置過濾數據"""
        try:
            filtered_data = {}
            for team_id, team_info in data.items():
                players = team_info.get('players', {})
                for category, player_list in players.items():
                    for player in player_list:
                        if position in player.get('position', ''):
                            if team_id not in filtered_data:
                                filtered_data[team_id] = {
                                    'team_info': team_info['team_info'],
                                    'players': {category: []}
                                }
                            if category not in filtered_data[team_id]['players']:
                                filtered_data[team_id]['players'][category] = []
                            filtered_data[team_id]['players'][category].append(player)
            return filtered_data
        except Exception as e:
            logger.error(f"位置過濾失敗: {str(e)}")
            return {}