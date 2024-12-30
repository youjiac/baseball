# app/models/baseball_llm.py
import logging
from typing import Dict
import ollama

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
            self.data = self._format_data_for_llm(baseball_data)
            logger.info("知識庫初始化成功")
            return True
        except Exception as e:
            logger.error(f"知識庫初始化失敗: {str(e)}")
            return False

    def _format_data_for_llm(self, data: Dict) -> str:
        """將球隊資料格式化為LLM易理解的形式"""
        try:
            formatted_data = []
            for team_id, team_info in data.items():
                team_info = team_info.get('team_info', {})
                players = data[team_id].get('players', {})
                
                team_data = [
                    f"【{team_info.get('name', '未知球隊')}】",
                    f"主場: {team_info.get('home', '未知')}",
                    f"總教練: {team_info.get('coach', '未知')}",
                    "\n球員名單:"
                ]

                for category, title in [
                    ('pitchers', '投手'),
                    ('catchers', '捕手'),
                    ('infielders', '內野手'),
                    ('outfielders', '外野手')
                ]:
                    if category_players := players.get(category):
                        team_data.append(f"\n{title}:")
                        for player in category_players:
                            team_data.append(
                                f"- {player.get('name', '未知')} "
                                f"(背號: {player.get('number', '未知')}, "
                                f"位置: {player.get('position', '未知')})"
                            )

                formatted_data.append("\n".join(team_data))

            return "\n\n===\n\n".join(formatted_data)
        except Exception as e:
            logger.error(f"資料格式化失敗: {str(e)}")
            return "資料格式化失敗"

    def query(self, question: str) -> str:
        """處理查詢"""
        try:
            # 基本問候
            if any(greeting in question.lower() for greeting in ["你好", "哈囉", "嗨", "hi", "hello"]):
                return "你好！我是CPBL教練助手，我有中華職棒所有球隊的最新資料。您想了解什麼呢？"

            if not self.initialized:
                return "系統尚未準備就緒，請稍後再試。"

            prompt = f"""你是CPBL教練助手，請根據以下資料回答問題。請簡潔專業，像教練回答球迷提問。

資料：
{self.data}

問題：{question}

請直接回答："""

            response = ollama.chat(
                model='mistral',
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            return response['message']['content']

        except Exception as e:
            logger.error(f"查詢處理失敗: {str(e)}")
            return "系統處理出現問題，請稍後再試。"