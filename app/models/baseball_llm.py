from typing import Dict, Optional
import logging
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseballLLM:
    def __init__(self):
        """初始化棒球助手"""
        self.data = {}
        self.initialized = False
        try:
            # 初始化 Ollama 模型
            self.llm = Ollama(model="llama2")
            # 定義提示模板
            self.prompt_template = PromptTemplate(
                input_variables=["context", "query"],
                template="""
                你是一個專業的棒球教練助手，擅長回答關於中華職棒的問題。
                
                你有以下資訊可以參考：
                {context}
                
                請根據以上資訊回答問題：
                {query}
                
                如果問題涉及數值計算，請明確列出計算步驟。
                """
            )
            self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
            self.llm_initialized = True
            logger.info("LLM 初始化成功")
        except Exception as e:
            logger.error(f"LLM 初始化失敗: {str(e)}")
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

    def extract_numbers(self, text: str) -> list:
        """從文字中提取數字"""
        numbers = re.findall(r'\d+\.?\d*', text)
        return [float(num) for num in numbers]

    def handle_calculation(self, question: str) -> Optional[str]:
        """處理數值計算"""
        # 打擊率計算
        if "打擊率" in question:
            numbers = self.extract_numbers(question)
            if len(numbers) >= 2:
                hits, at_bats = numbers[:2]
                avg = hits / at_bats if at_bats > 0 else 0
                return f"打擊率計算：{hits} 支安打 / {at_bats} 打數 = {avg:.3f}"
        
        # 防禦率計算
        if "防禦率" in question:
            numbers = self.extract_numbers(question)
            if len(numbers) >= 2:
                earned_runs, innings = numbers[:2]
                era = (earned_runs * 9) / innings if innings > 0 else 0
                return f"防禦率計算：({earned_runs} * 9) / {innings} 局 = {era:.2f}"
        
        return None

    def query(self, question: str) -> str:
        """處理查詢"""
        try:
            # 檢查是否需要數值計算
            calculation_result = self.handle_calculation(question)
            if calculation_result:
                return calculation_result

            # 基於規則的快速回應
            response = self._rule_based_response(question)
            if response:
                return response
            
            # 如果有初始化 LLM，使用 LLM 生成回應
            if self.llm_initialized:
                context = str(self.data)  # 可以優化成更結構化的內容
                response = self.chain.run(context=context, query=question)
                return response
                
            # 如果都沒有匹配，返回預設回應
            return "我建議您詢問更具體的球隊、球員相關資訊，或是進行數據計算。"
            
        except Exception as e:
            logger.error(f"查詢處理失敗: {str(e)}")
            return f"抱歉，我現在無法回答這個問題。"

    # [保持原有的 _rule_based_response 方法不變]