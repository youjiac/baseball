# baseball_llm.py
import logging
from typing import Dict, Optional, List, Union
import streamlit as st
from transformers import AutoTokenizer, AutoModel
import torch
import os

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
    def __init__(self, model_name="THUDM/chatglm3-6b", use_cpu=True):
        """初始化棒球助手"""
        self.initialized = False
        self.data = {}
        
        # 初始化 logger
        self.logger = logging.getLogger(__name__)
        
        try:
            st.info("正在初始化 ChatGLM3，這可能需要幾分鐘...")
            
            # 設定模型
            self.model_name = model_name
            self.device = "cpu" if use_cpu else "cuda"
            
            # 加載 tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, 
                trust_remote_code=True
            )
            
            # 加載模型
            self.model = AutoModel.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                device_map='auto'  # 自動選擇設備
            )
            
            if not use_cpu:
                self.model = self.model.half()  # 半精度
            
            # 初始化系統提示詞
            self.system_prompt = """
            你是一個專業的CPBL中華職棒教練助理。我叫做小虎，是一個經驗豐富的棒球分析助手。
            我的主要職責是協助教練團隊和球迷了解比賽資訊。
            
            請注意以下幾點：
            1. 請使用正體中文回答
            2. 態度要親切有禮
            3. 如果資料中沒有某項資訊，請誠實告知
            4. 回答要準確且專業
            """
            
            self.initialized = True
            st.success("✅ ChatGLM3 初始化成功！")
            
        except Exception as e:
            self.logger.error(f"ChatGLM3 初始化失敗: {str(e)}")
            st.error(f"❌ ChatGLM3 初始化失敗: {str(e)}")
            raise ModelNotReadyError(f"模型初始化失敗: {str(e)}")

    def query(self, question: str) -> str:
        """處理用戶查詢"""
        try:
            if not self.initialized:
                raise ModelNotReadyError("系統尚未準備就緒，請稍後再試。")

            # 簡單的歡迎語處理
            if any(word in question for word in ["你好", "哈囉", "嗨", "hi", "hello"]):
                return """你好！我是小虎，是一個專業的CPBL中華職棒教練助理。
                我可以幫你查詢球隊資訊、球員資料、比賽數據等。請問有什麼我可以幫你的嗎？"""

            # 構建提示詞
            context = self._format_game_data() if self.data else "目前沒有可用的比賽資料。"
            
            prompt = f"""
            {self.system_prompt}
            
            以下是目前的資料：
            {context}
            
            用戶問題：{question}
            """
            
            # 生成回應
            with st.spinner("🤔 正在思考..."):
                try:
                    response, history = self.model.chat(
                        self.tokenizer,
                        prompt,
                        history=[],
                        temperature=0.7
                    )
                    return response.strip()
                except Exception as e:
                    self.logger.error(f"生成回應失敗: {str(e)}")
                    return "抱歉，目前無法生成回應，請稍後再試。"

        except Exception as e:
            self.logger.error(f"查詢處理失敗: {str(e)}")
            return "抱歉，系統處理問題時發生錯誤，請稍後再試。"

    def _format_game_data(self) -> str:
        """格式化遊戲資料"""
        if not self.data:
            return "目前沒有可用的資料。"

        formatted_data = []
        for team_id, team_info in self.data.items():
            if team_id == 'head_to_head' or not isinstance(team_info, dict):
                continue

            team_data = []
            # 基本資訊
            if 'team_info' in team_info and isinstance(team_info['team_info'], dict):
                info = team_info['team_info']
                team_data.append(f"球隊：{info.get('name', '未知')}")
                if 'home' in info:
                    team_data.append(f"主場：{info['home']}")
                if 'coach' in info:
                    team_data.append(f"總教練：{info['coach']}")

            # 戰績
            if 'record' in team_info and isinstance(team_info['record'], dict):
                record = team_info['record']
                wins = record.get('wins', 0)
                losses = record.get('losses', 0)
                ratio = record.get('ratio', '0.000')
                team_data.append(f"戰績：{wins}勝{losses}敗，勝率{ratio}")

            # 球員資料
            if 'players' in team_info and isinstance(team_info['players'], dict):
                for pos, players in team_info['players'].items():
                    if not players or not isinstance(players, list):
                        continue
                    player_names = [f"{p.get('name', '')}({p.get('number', '')})" 
                                  for p in players if p.get('name')]
                    if player_names:
                        team_data.append(f"{pos}：{', '.join(player_names)}")

            if team_data:
                formatted_data.append('\n'.join(team_data))

        if not formatted_data:
            return "目前沒有可用的資料。"
            
        return "\n\n".join(formatted_data)

    def initialize_knowledge(self, data: Dict):
        """初始化知識庫"""
        if not isinstance(data, dict):
            self.logger.error("初始化知識庫失敗：資料格式錯誤")
            return
            
        self.data = data
        self.logger.info("知識庫初始化完成")
        st.success("✅ 知識庫初始化完成")