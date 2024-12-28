import streamlit as st
import json
from pathlib import Path
import pandas as pd
import sys
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from bs4 import BeautifulSoup
import logging
from models.baseball_llm import BaseballLLM
from models.calculator import BaseballCalculator
from models.player_stats import PlayerStats
from scrapers.cpbl_scraper import CPBLScraper

# 設置日誌記錄
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseballCoach:
    def __init__(self):
        """初始化教練助手"""
        try:
            self.data_path = Path(__file__).parent / "data" / "cpbl_teams.json"
            self.calculator = BaseballCalculator()
            self.player_stats = PlayerStats()
            self.scraper = self._init_scraper()
            self.llm_assistant = BaseballLLM()
            self.load_data()
            if hasattr(self, 'data'):
                self.llm_assistant.initialize_knowledge(self.data)
            logger.info("BaseballCoach 初始化成功")
        except Exception as e:
            logger.error(f"BaseballCoach 初始化失敗: {str(e)}")
            raise

    @staticmethod
    @st.cache_resource
    def _init_scraper():
        """初始化並快取 scraper 實例"""
        try:
            scraper = CPBLScraper()
            logger.info("Scraper 初始化成功")
            return scraper
        except Exception as e:
            logger.error(f"Scraper 初始化失敗: {str(e)}")
            raise

    def load_data(self):
        """載入球隊資料"""
        try:
            # 定義球隊ID對應
            team_ids = {
                'ACN': '中信兄弟',
                'ADD': '統一7-ELEVEn獅',
                'AJL': '樂天桃猿',
                'AEO': '富邦悍將',
                'AAA': '味全龍',
                'AKP': '台鋼雄鷹'
            }
            
            # 檢查本地檔案時間戳
            if self.data_path.exists():
                file_age = datetime.now() - datetime.fromtimestamp(self.data_path.stat().st_mtime)
                if file_age < timedelta(hours=1):  # 如果資料小於1小時
                    try:
                        with open(self.data_path, 'r', encoding='utf-8') as f:
                            self.data = json.load(f)
                        # 重新設置 current_team_code 來確保成立年份正確
                        for team_id in self.data.keys():
                            self.scraper.current_team_code = team_id
                            debug_file = Path(__file__).parent / "data" / f"{team_id.lower()}_debug.html"
                            if debug_file.exists():
                                with open(debug_file, encoding='utf-8') as f:
                                    soup = BeautifulSoup(f, 'html.parser')
                                    self.data[team_id]['team_info'] = self.scraper._parse_team_info(soup)
                        logger.info("已從本地檔案載入最新資料")
                        return
                    except json.JSONDecodeError:
                        logger.warning("本地檔案損壞，將重新抓取資料")
                        self.data_path.unlink()
            
            # 從網站抓取資料
            self.data = {}
            for team_id, team_name in team_ids.items():
                try:
                    logger.info(f"正在載入 {team_name} 的資料...")
                    team_data = self.scraper.fetch_team_data(team_id)
                    if team_data:
                        self.data[team_id] = team_data
                        logger.info(f"成功載入 {team_name} 的資料")
                    else:
                        logger.warning(f"{team_name} 無可用資料")
                except Exception as e:
                    logger.error(f"載入 {team_name} 資料時發生錯誤: {str(e)}")
                    continue
            
            # 儲存到本地文件
            if self.data:
                self.data_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.data_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                logger.info("已將資料儲存至本地文件")
            else:
                logger.error("無法載入任何球隊資料")
                
        except Exception as e:
            logger.error(f"載入資料時發生錯誤: {str(e)}")
            self.data = {}

    def chat_interface(self):
        """聊天介面"""
        st.title("⚾ CPBL 教練助手")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # 顯示聊天歷史
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # 用戶輸入
        if prompt := st.chat_input("請輸入您的問題"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response = self.llm_assistant.query(prompt)
                st.markdown(response)
                
            st.session_state.messages.append({"role": "assistant", "content": response})

    def main_page(self):
        """主頁面"""
        try:
            st.title("🏟️ CPBL 教練助手")
            
            # 側邊欄選單
            with st.sidebar:
                st.title("功能選單")
                page = st.selectbox(
                    "選擇功能",
                    ["智能助手", "球隊分析", "球員查詢", "數據統計"]
                )
                st.write(f"選擇的功能：{page}")

            # 根據選擇顯示不同頁面
            if page == "智能助手":
                st.write("載入智能助手...")
                self.chat_interface()
            elif page == "球隊分析":
                st.write("載入球隊分析...")
                self.team_analysis()
            elif page == "球員查詢":
                st.write("載入球員查詢...")
                self.player_search()
            elif page == "數據統計":
                st.write("載入數據統計...")
                self.statistics()
                
        except Exception as e:
            logger.error(f"頁面載入錯誤：{str(e)}")
            st.error(f"頁面載入錯誤：{str(e)}")

    # [其餘方法保持不變...]

def main():
    """主程式"""
    try:
        # 設定頁面配置
        st.set_page_config(
            page_title="CPBL 教練助手",
            page_icon="⚾",
            layout="wide"
        )

        # 初始化並運行應用
        app = BaseballCoach()
        app.main_page()
        
    except Exception as e:
        logger.error(f"程式執行錯誤：{str(e)}")
        st.error("程式執行發生錯誤，請稍後再試或聯繫管理員。")

if __name__ == "__main__":
    main()