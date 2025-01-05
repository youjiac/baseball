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
            self.data = baseball_data  # 保留原始字典結構
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

            # 提取關鍵字
            keywords = self.extract_keywords(question)
            relevant_data = self.filter_data_by_keywords(keywords)

            # 根據問題類型進行處理
            if any(position in question for position in ["投手", "捕手", "內野手", "外野手", "游擊手", "一壘手", "二壘手", "三壘手", "中外野手", "教練", "總教練", "內野教練", "外野教練", "打擊教練", "投手教練", "牛棚教練", "跑壘教練"]):
                relevant_data = self.filter_by_position(relevant_data, question)
            elif any(keyword in keywords for keyword in ["最佳", "最高效", "表現出色", "出色的", "最高效的"]):
                relevant_data = self.filter_best_performers(relevant_data)

            # 在這裡格式化數據
            formatted_data = self._format_data_for_llm(relevant_data)

            # 添加調試日誌
            logger.debug(f"篩選後的資料: {formatted_data}")

            # 檢查篩選後的數據是否為空
            if not relevant_data:
                return "目前沒有公開發布最新的總教練資料。為了提供準確的資訊，我建議您查閱最新消息或官方網站。"

            prompt = f"""你是CPBL教練助手，請根據以下資料回答問題。請簡潔專業，像教練回答球迷提問。回答請使用繁體中文，若有不符合中華職棒或CPBL的問題請不必回答，並告知使用者超出範圍。

            資料：{formatted_data}

            問題：{question}

            請直接回答："""

            response = ollama.chat(
                model='llama3.1',
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            return response['message']['content']

        except Exception as e:
            logger.error(f"查詢處理失敗: {str(e)}")
            return "系統處理出現問題，請稍後再試。"

    def extract_keywords(self, question: str) -> list:
        """提取問題中的隊伍名稱或其他關鍵字"""
        keywords = []
        for team_id, team_info in self.data.items():
            team_name = team_info['team_info']['name']
            if team_name in question:
                keywords.append(team_id)
        # 添加额外的关键字匹配，包括同義詞和變體
        performance_keywords = ["表現出色", "最高效", "最佳", "出色的", "最高效的"]
        for keyword in performance_keywords:
            if keyword in question:
                keywords.append(keyword)
        # 添加日志以查看提取的关键字
        logger.debug(f"提取的关键字: {keywords}")
        return keywords

    def filter_data_by_keywords(self, keywords: list) -> Dict:
        """根據關鍵字篩選相關的隊伍資料"""
        filtered_data = {key: self.data[key] for key in keywords if key in self.data}
        return filtered_data

    def filter_by_category(self, data: Dict, category: str) -> Dict:
        """根據球員類型篩選資料"""
        filtered_data = {}
        for team_id, team_info in data.items():
            players = team_info.get('players', {})
            if category_players := players.get(category):
                filtered_data[team_id] = team_info
        return filtered_data

    def filter_by_position(self, data: Dict, question: str) -> Dict:
        """根據球員位置篩選資料，包含具體教練職位，處理同義詞"""
        positions = ["投手", "捕手", "內野手", "外野手", "游擊手", "一壘手", "二壘手", "三壘手", "中外野手", "教練", "總教練", "內野教練", "外野教練", "打擊教練", "投手教練", "牛棚教練", "跑壘教練"]
        synonyms = {
            "總教練": ["一軍總教練", "總教練"],
            "內野教練": ["一軍內野教練", "內野教練"],
            "外野教練": ["一軍外野教練", "外野教練"],
            "打擊教練": ["一軍打擊教練", "打擊教練"],
            "投手教練": ["一軍投手教練", "投手教練"],
            "牛棚教練": ["一軍牛棚教練", "牛棚教練"],
            "跑壘教練": ["一軍跑壘教練", "跑壘教練"],
            "教練": ["一軍教練", "教練", "首席教練"]
        }
        filtered_data = {}
        for team_id, team_info in data.items():
            players = team_info.get('players', {})
            for category, player_list in players.items():
                for player in player_list:
                    position = player.get('position', '')
                    if any(pos in position for pos in positions if pos in question):
                        if team_id not in filtered_data:
                            filtered_data[team_id] = {'team_info': team_info['team_info'], 'players': {category: []}}
                        filtered_data[team_id]['players'][category].append(player)
                    else:
                        # Check synonyms
                        for key, syn_list in synonyms.items():
                            if any(syn in position for syn in syn_list) and key in question:
                                if team_id not in filtered_data:
                                    filtered_data[team_id] = {'team_info': team_info['team_info'], 'players': {category: []}}
                                filtered_data[team_id]['players'][category].append(player)

        logger.debug(f"过滤后的数据: {filtered_data}")
        return filtered_data

    def filter_best_performers(self, data: Dict) -> Dict:
        """篩選出本賽季表現出色的球員，使用更複雜的計算方法"""
        filtered_data = {}
        for team_id, team_info in data.items():
            players = team_info.get('players', {})
            for category, player_list in players.items():
                for player in player_list:
                    try:
                        # 檢查數據完整性
                        if not all(k in player for k in ['batting_average', 'pitching_efficiency', 'defensive_ability']):
                            logger.warning(f"缺少數據字段: {player}")
                            continue

                        # 使用多個指標進行計算，例如擊球率、投球效率等
                        batting_average = player['batting_average']
                        pitching_efficiency = player['pitching_efficiency']
                        defensive_ability = player['defensive_ability']

                        # 加權平均計算綜合得分
                        performance_score = (
                            0.4 * batting_average +
                            0.3 * pitching_efficiency +
                            0.3 * defensive_ability
                        )

                        # 設定一個門檻值來篩選出色的球員
                        if performance_score > 0.7:  # 門檻值可以根據需要調整
                            if team_id not in filtered_data:
                                filtered_data[team_id] = {'team_info': team_info['team_info'], 'players': {category: []}}
                            filtered_data[team_id]['players'][category].append(player)
                    except Exception as e:
                        logger.error(f"計算表現分數失敗: {str(e)}")
        logger.debug(f"最佳表現球員: {filtered_data}")
        return filtered_data