from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseballLLM:
    def __init__(self):
        """初始化棒球助手"""
        self.data = {}
        self.initialized = False
        self.llm_initialized = False
        
    def initialize_knowledge(self, baseball_data: Dict) -> bool:
        """初始化知識庫"""
        try:
            self.data = baseball_data
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"知識庫初始化失敗: {str(e)}")
            return False

    def query(self, question: str) -> str:
        """處理查詢"""
        try:
            # 基於規則的快速回應
            response = self._rule_based_response(question)
            if response:
                return response
                
            # 如果沒有匹配的規則，返回預設回應
            return "我建議您詢問更具體的球隊或球員相關資訊。"
            
        except Exception as e:
            logger.error(f"查詢處理失敗: {str(e)}")
            return f"抱歉，我現在無法回答這個問題。"

    def _rule_based_response(self, question: str) -> Optional[str]:
        """基於規則的回應"""
        if not self.initialized:
            return "資料庫尚未初始化"
            
        # 快速關鍵字匹配
        for team_id, team_data in self.data.items():
            team_info = team_data.get('team_info', {})
            team_name = team_info.get('name', '')
            
            # 球隊相關查詢
            if team_name in question:
                # 投手相關查詢
                if any(keyword in question for keyword in [
                    "先發", "救援", "中繼", "終結者", "左投", "右投", 
                    "王牌", "投手群", "投手", "輪值", "牛棚"
                ]):
                    pitchers = team_data.get('players', {}).get('pitchers', [])
                    if pitchers:
                        # 特殊投手查詢
                        if "先發" in question:
                            starter_list = [f"• {p.get('name')} (背號{p.get('number')})" 
                                        for p in pitchers 
                                        if "先發" in p.get('position', '').lower() or 
                                           "先發" in p.get('name', '').lower()]
                            if starter_list:
                                return (f"{team_name}的先發投手群：\n\n" + 
                                    "\n".join(starter_list) + 
                                    f"\n\n共有 {len(starter_list)} 名先發投手")
                        
                        # 一般列出所有投手
                        pitcher_list = [f"• {p.get('name')} (背號{p.get('number')})" 
                                    for p in pitchers]
                        return (f"{team_name}的投手群：\n\n" + 
                               "\n".join(pitcher_list) + 
                               f"\n\n共有 {len(pitcher_list)} 名投手")

                # 打者相關查詢
                elif any(keyword in question for keyword in [
                    "打者", "打擊", "長打", "安打王", "全壘打王",
                    "左打", "右打", "指定打擊", "代打", "主力打者"
                ]):
                    batters = []
                    for pos in ['infielders', 'outfielders']:
                        batters.extend(team_data.get('players', {}).get(pos, []))
                    if batters:
                        batter_list = [f"• {p.get('name')} (背號{p.get('number')})" 
                                     for p in batters]
                        return (f"{team_name}的打者群：\n\n" + 
                               "\n".join(batter_list) + 
                               f"\n\n共有 {len(batter_list)} 名打者")

                # 守備位置查詢
                elif "內野手" in question:
                    infielders = team_data.get('players', {}).get('infielders', [])
                    if infielders:
                        infielder_list = [f"• {p.get('name')} (背號{p.get('number')})" 
                                        for p in infielders]
                        return (f"{team_name}的內野手：\n\n" + 
                               "\n".join(infielder_list) + 
                               f"\n\n共有 {len(infielder_list)} 名內野手")
                
                elif "外野手" in question:
                    outfielders = team_data.get('players', {}).get('outfielders', [])
                    if outfielders:
                        outfielder_list = [f"• {p.get('name')} (背號{p.get('number')})" 
                                         for p in outfielders]
                        return (f"{team_name}的外野手：\n\n" + 
                               "\n".join(outfielder_list) + 
                               f"\n\n共有 {len(outfielder_list)} 名外野手")
                
                elif "捕手" in question:
                    catchers = team_data.get('players', {}).get('catchers', [])
                    if catchers:
                        catcher_list = [f"• {p.get('name')} (背號{p.get('number')})" 
                                      for p in catchers]
                        return (f"{team_name}的捕手群：\n\n" + 
                               "\n".join(catcher_list) + 
                               f"\n\n共有 {len(catcher_list)} 名捕手")

                # 球隊基本資訊查詢
                elif any(keyword in question for keyword in [
                    "主場", "教練", "總教練", "戰績", "勝場", "敗場",
                    "客場", "排名", "成立", "歷史"
                ]):
                    if "主場" in question:
                        return f"{team_name}的主場是{team_info.get('home', '未知')}"
                    elif "教練" in question:
                        return f"{team_name}的總教練是{team_info.get('coach', '未知')}"
                    else:
                        return (f"{team_name}是一支中華職棒的球隊，\n"
                               f"主場在{team_info.get('home', '未知')}，\n"
                               f"總教練是{team_info.get('coach', '未知')}")
                        
            # 特定球員查詢
            players = team_data.get('players', {})
            for category in ['pitchers', 'catchers', 'infielders', 'outfielders']:
                for player in players.get(category, []):
                    if player.get('name', '') in question:
                        return (f"球員：{player.get('name')}\n"
                               f"背號：{player.get('number')}\n"
                               f"守備位置：{player.get('position')}\n"
                               f"所屬球隊：{team_name}")
        
        return None