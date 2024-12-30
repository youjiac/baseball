import logging
from typing import Dict, Optional
from dataclasses import dataclass
import requests
import json
import streamlit as st

# 設置日誌記錄
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

@dataclass
class LLMConfig:
    """LLM配置"""
    api_url: str = "http://localhost:11434/api/chat"
    model_name: str = "mistral"
    temperature: float = 0.7
    max_tokens: int = 1000
    system_prompt: str = (
        "你現在是一位專業的棒球教練助手，負責回答關於中華職棒的問題。"
        "請使用專業且友善的口吻，像一位經驗豐富的棒球教練一樣回答問題。"
        "回答要簡潔清晰，避免重複內容。必須使用繁體中文回答。"
    )

class BaseballLLM:
    def __init__(self):
        """初始化棒球助手"""
        st.write("開始初始化 BaseballLLM...")  # 使用 streamlit 顯示
        self.initialized = False
        try:
            self.config = LLMConfig()
            self.data: Dict = {}
            self.formatted_data: Optional[str] = None
            
            # 基本問候語模板
            self.greetings = {
                "default": "你好！我是CPBL教練助手，我有中華職棒所有球隊的最新資料。您想了解什麼呢？",
                "morning": "早安！很高興能在一早為您提供CPBL的相關資訊。",
                "evening": "晚上好！讓我們來聊聊今天的棒球話題吧！"
            }
            
            # 嘗試連接 Ollama 服務
            with st.spinner("正在連接到 Ollama 服務..."):
                self._check_model_status()
                self.initialized = True
                st.write("BaseballLLM 初始化成功")
                logger.info("BaseballLLM 初始化成功")
        except Exception as e:
            logger.error(f"BaseballLLM 初始化失敗: {str(e)}")
            st.write(f"BaseballLLM 初始化失敗: {str(e)}")

    def _check_model_status(self):
        """檢查模型狀態"""
        try:
            response = requests.get(f"{self.config.api_url}/status")
            response.raise_for_status()
            status = response.json()
            if not status.get("ready", False):
                raise ModelNotReadyError("模型未準備就緒")
        except requests.RequestException as e:
            raise ModelNotReadyError(f"無法連接到模型服務: {str(e)}")

    def query(self, prompt: str) -> str:
        """處理查詢並返回回應"""
        if not self.initialized:
            raise ModelNotReadyError("模型未準備就緒")

        try:
            response = requests.post(
                self.config.api_url,
                json={
                    "model": self.config.model_name,
                    "prompt": prompt,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "system_prompt": self.config.system_prompt
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "無法獲取回應")
        except requests.RequestException as e:
            raise QueryProcessingError(f"查詢處理失敗: {str(e)}")

    def initialize_knowledge(self, baseball_data: Dict) -> bool:
        """初始化知識庫"""
        try:
            self.data = baseball_data
            self.formatted_data = self._format_data(baseball_data)
            print("知識庫初始化成功")
            return True
        except Exception as e:
            print(f"知識庫初始化失敗: {str(e)}")
            return False

    def _format_data(self, data: Dict) -> str:
        """格式化球隊資料"""
        try:
            formatted = []
            for team_id, team_info in data.items():
                team_basic = team_info.get('team_info', {})
                formatted.append(f"【{team_basic.get('name', '未知球隊')}】")
                formatted.append(f"主場：{team_basic.get('home', '未知')}")
                formatted.append(f"總教練：{team_basic.get('coach', '未知')}")
                
                # 添加球員資訊
                if 'players' in team_info:
                    formatted.append("\n球員名單：")
                    for category, title in [
                        ('pitchers', '投手'),
                        ('catchers', '捕手'),
                        ('infielders', '內野手'),
                        ('outfielders', '外野手')
                    ]:
                        if players := team_info['players'].get(category):
                            formatted.append(f"\n{title}:")
                            for player in players:
                                formatted.append(
                                    f"- {player.get('name', '未知')} "
                                    f"(背號: {player.get('number', '未知')}, "
                                    f"位置: {player.get('position', '未知')})"
                                )
                formatted.append("\n---\n")
            
            return "\n".join(formatted)
        except Exception as e:
            print(f"格式化資料失敗: {str(e)}")
            return ""