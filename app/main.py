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

# 添加專案根目錄到 Python 路徑
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from models.calculator import BaseballCalculator
from models.player_stats import PlayerStats
from scrapers.cpbl_scraper import CPBLScraper

class BaseballCoach:
    def __init__(self):
        """初始化教練助手"""
        self.data_path = Path(__file__).parent / "data" / "cpbl_teams.json"
        self.calculator = BaseballCalculator()
        self.player_stats = PlayerStats()
        self.scraper = self._init_scraper()
        self.load_data()

    @staticmethod
    @st.cache_resource
    def _init_scraper():
        """初始化並快取 scraper 實例"""
        return CPBLScraper()

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
                            self.data[team_id]['team_info'] = self.scraper._parse_team_info(
                                BeautifulSoup(open(Path(__file__).parent / "data" / f"{team_id.lower()}_debug.html", encoding='utf-8'), 'html.parser')
                            )
                        st.success("已從本地檔案載入最新資料")
                        return
                    except json.JSONDecodeError:
                        st.warning("本地檔案損壞，將重新抓取資料")
                        self.data_path.unlink()  # 刪除損壞的檔案
            
            # 從網站抓取資料
            self.data = {}
            progress_bar = st.progress(0)
            for idx, (team_id, team_name) in enumerate(team_ids.items()):
                progress = idx / len(team_ids)
                progress_bar.progress(progress)
                
                try:
                    with st.spinner(f"正在載入 {team_name} 的資料..."):
                        team_data = self.scraper.fetch_team_data(team_id)
                        if team_data:
                            self.data[team_id] = team_data
                            st.success(f"✅ 成功載入 {team_name} 的資料")
                        else:
                            st.warning(f"⚠️ {team_name} 無可用資料")
                except Exception as e:
                    st.error(f"❌ 載入 {team_name} 資料時發生錯誤: {str(e)}")
                    continue
            
            progress_bar.progress(1.0)
            
            # 儲存到本地文件
            if self.data:
                self.data_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.data_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                st.success("✅ 已將資料儲存至本地文件")
            else:
                st.error("❌ 無法載入任何球隊資料")

            # 在讀取本地檔案之後
            st.write("正在從本地檔案載入...")
            for team_id in self.data.keys():
                st.write(f"處理球隊 {team_id}")
                self.scraper.current_team_code = team_id
                st.write(f"設置 current_team_code: {self.scraper.current_team_code}")
                
        except Exception as e:
            st.error(f"載入資料時發生錯誤: {str(e)}")
            self.data = {}

    def main_page(self):
        """主頁面"""
        st.title("🏟️ CPBL 教練助手")
        
        # 側邊欄選單
        with st.sidebar:
            st.title("功能選單")
            page = st.selectbox(
                "選擇功能",
                ["球隊分析", "球員查詢", "數據統計", "對戰預測"]
            )

        # 根據選擇顯示不同頁面
        if page == "球隊分析":
            self.team_analysis()
        elif page == "球員查詢":
            self.player_search()
        elif page == "數據統計":
            self.statistics()
        else:
            self.prediction()

    def team_analysis(self):
        """球隊分析頁面"""
        st.header("球隊分析")
        
        # 選擇球隊
        if self.data:
            team_names = {
                team_id: info.get('team_info', {}).get('name', team_id) 
                for team_id, info in self.data.items()
            }
            
            selected_team = st.selectbox(
                "選擇球隊",
                list(team_names.keys()),
                format_func=lambda x: team_names[x]
            )

            if selected_team and selected_team in self.data:
                team_data = self.data[selected_team]
                
                # 使用頁籤組織內容
                tabs = st.tabs(["基本資訊", "球員名單", "團隊統計"])
                
                with tabs[0]:
                    self._show_team_basic_info(team_data)
                with tabs[1]:
                    self._show_team_roster(team_data)
                with tabs[2]:
                    self._show_team_statistics(team_data)

    def _show_team_basic_info(self, team_data):
        """顯示球隊基本資訊"""
        st.subheader("球隊資訊")
        info = team_data.get('team_info', {})
        
        # 定義球隊成立年份對照表
        team_established_years = {
            'ACN': '1990',  # 中信兄弟 (原兄弟象)
            'ADD': '1990',  # 統一7-ELEVEn獅 (原統一獅)
            'AJL': '2003',  # 樂天桃猿 (原第一金剛)
            'AEO': '1993',  # 富邦悍將 (原俊國熊)
            'AAA': '1990',  # 味全龍
            'AKP': '2023'   # 台鋼雄鷹
        }
        
        cols = st.columns(3)
        with cols[0]:
            st.metric("主場", info.get('home', 'N/A'))
        with cols[1]:
            # 找出目前的球隊 ID
            team_id = next((team_id for team_id in self.data.keys() 
                        if self.data[team_id]['team_info'].get('name') == info.get('name')), None)
            established_year = team_established_years.get(team_id, 'N/A') if team_id else 'N/A'
            st.metric("成立年份", established_year)
        with cols[2]:
            st.metric("總教練", info.get('coach', 'N/A'))

    def _show_team_roster(self, team_data):
        """顯示球隊名單"""
        st.subheader("球員名單")
        
        categories = {
            'coaches': '教練團',
            'pitchers': '投手群',
            'catchers': '捕手群',
            'infielders': '內野手',
            'outfielders': '外野手'
        }

        if 'players' in team_data:
            for category, title in categories.items():
                players = team_data['players'].get(category, [])
                with st.expander(f"{title} ({len(players)} 人)", expanded=(category == 'coaches')):
                    if players:
                        df = pd.DataFrame(players)
                        if not df.empty:
                            df = df.reindex(columns=['name', 'number', 'position']).rename(columns={
                                'name': '姓名',
                                'number': '背號',
                                'position': '守備位置'
                            })
                            st.dataframe(df, hide_index=True, use_container_width=True)
                            
                            if category != 'coaches':
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("人數", len(players))
                                with col2:
                                    avg_num = np.mean([
                                        int(p['number']) for p in players 
                                        if str(p.get('number', '')).isdigit()
                                    ])
                                    st.metric("平均背號", f"{avg_num:.1f}")
                    else:
                        st.info("目前沒有資料")

    def _show_team_statistics(self, team_data):
        """顯示團隊統計"""
        st.subheader("團隊統計")
        if 'players' in team_data:
            players = team_data['players']
            total_players = sum(
                len(players.get(cat, [])) 
                for cat in ['pitchers', 'catchers', 'infielders', 'outfielders']
            )
            total_coaches = len(players.get('coaches', []))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("球員總數", total_players)
            with col2:
                st.metric("教練團人數", total_coaches)

    @st.cache_data(ttl=3600)
    def _get_filtered_player_stats(self, year, position, record_type, active, defence_type):
        """獲取並快取球員統計資料"""
        result = self.player_stats.fetch_player_stats(
            year=str(year),
            position=position,
            record_type=record_type,
            active=active,
            defence_type=defence_type
        )
        return result

    def player_search(self):
        """球員查詢頁面"""
        st.header("球員查詢")
        
        # 使用 session_state 來保存搜尋狀態和結果
        if 'search_performed' not in st.session_state:
            st.session_state.search_performed = False
        if 'search_result' not in st.session_state:
            st.session_state.search_result = None
            
        # 搜尋條件
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                record_type = st.selectbox(
                    "比賽類型",
                    options=[
                        ('A', '一軍例行賽'),
                        ('C', '一軍總冠軍賽'),
                        ('E', '一軍季後挑戰賽'),
                        ('G', '一軍熱身賽')
                    ],
                    format_func=lambda x: x[1]
                )[0]
                
                year = st.selectbox(
                    "年度",
                    options=list(range(2024, 1989, -1))
                )
            
            with col2:
                position = st.selectbox(
                    "選手類型",
                    options=[
                        ('01', '野手成績'),
                        ('02', '投手成績')
                    ],
                    format_func=lambda x: x[1]
                )[0]
                
                active = st.selectbox(
                    "球員狀態",
                    options=[
                        ('01', '全部球員'),
                        ('02', '現役球員')
                    ],
                    format_func=lambda x: x[1]
                )[0]

            with col3:
                if position == '01':
                    defence_type = st.selectbox(
                        "守備位置",
                        options=[
                            ('99', '全部位置'),
                            ('0', '指定打擊'),
                            ('2', '捕手'),
                            ('3', '一壘手'),
                            ('4', '二壘手'),
                            ('5', '三壘手'),
                            ('6', '游擊手'),
                            ('7', '左外野手'),
                            ('8', '中外野手'),
                            ('9', '右外野手')
                        ],
                        format_func=lambda x: x[1]
                    )[0]
                else:
                    defence_type = '99'

        # 搜尋按鈕
        if st.button('搜尋', type='primary') or st.session_state.search_performed:
            if not st.session_state.search_performed:
                with st.spinner('載入數據中...'):
                    result = self.player_stats.get_cached_stats(
                        year=year,
                        position=position,
                        record_type=record_type,
                        active=active,
                        defence_type=defence_type
                    )
                    st.session_state.search_result = result
                    st.session_state.search_performed = True
            else:
                result = st.session_state.search_result

            if result['success']:
                players_data = result['data']
                
                if position == '01':
                    self.display_batter_stats(players_data)
                else:
                    self.display_pitcher_stats(players_data)
                
                st.caption(f"數據更新時間: {datetime.fromisoformat(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                st.error(f"獲取數據失敗: {result.get('error', '未知錯誤')}")
                st.session_state.search_performed = False
                
        # 重置按鈕
        if st.session_state.search_performed:
            if st.button('重新搜尋'):
                st.session_state.search_performed = False
                st.session_state.search_result = None
                st.experimental_rerun()

    def display_batter_stats(self, players_data):
        """顯示打者數據"""
        if not players_data:
            st.warning("沒有找到符合條件的數據")
            return

        try:
            df = pd.DataFrame([
                {
                    '球員': f"{p['name']} ({p['team']})",
                    '球隊': p['team'],
                    '打擊率': float(p['stats']['avg']),
                    '安打': int(p['stats']['hits']),
                    '全壘打': int(p['stats']['hr']),
                    '打點': int(p['stats']['rbi']),
                    '上壘率': float(p['stats']['obp']),
                    '長打率': float(p['stats']['slg']),
                    'OPS': float(p['stats']['ops']),
                    '盜壘': int(p['stats']['sb']),
                    '三振': int(p['stats']['so']),
                    '保送': int(p['stats']['bb']),
                    '打席數': int(p['stats']['pa'])
                } for p in players_data
            ])

            # 篩選條件
            with st.expander("數據篩選", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    min_pa = st.number_input("最少打席數", min_value=0, value=50)
                with col2:
                    sort_by = st.selectbox(
                        "排序依據",
                        ['打擊率', 'OPS', '全壘打', '打點', '安打', '上壘率', '長打率']
                    )
                with col3:
                    team_filter = st.multiselect(
                        "選擇球隊",
                        options=sorted(df['球隊'].unique()),
                        default=sorted(df['球隊'].unique())
                    )

            filtered_df = df[
                (df['打席數'] >= min_pa) & 
                (df['球隊'].isin(team_filter))
            ].copy()

            if filtered_df.empty:
                st.warning("沒有符合篩選條件的數據")
                return

            # 數據顯示
            # 數據顯示
            tabs = st.tabs(["排行榜", "數據分析", "球隊比較"])
            
            with tabs[0]:
                st.subheader("打者排行榜")
                styled_df = filtered_df.sort_values(sort_by, ascending=False).style.format({
                    '打擊率': '{:.3f}',
                    '上壘率': '{:.3f}',
                    '長打率': '{:.3f}',
                    'OPS': '{:.3f}',
                    '打點': '{:,.0f}',
                    '安打': '{:,.0f}',
                    '全壘打': '{:,.0f}',
                    '盜壘': '{:,.0f}',
                    '三振': '{:,.0f}',
                    '保送': '{:,.0f}',
                    '打席數': '{:,.0f}'
                })
                
                st.dataframe(
                    styled_df,
                    hide_index=True,
                    use_container_width=True
                )

            with tabs[1]:
                col1, col2 = st.columns(2)
                
                with col1:
                    # 打擊率前10名圖表
                    top_10_avg = filtered_df.nlargest(10, '打擊率')
                    fig_avg = px.bar(
                        top_10_avg,
                        x='球員',
                        y='打擊率',
                        title='打擊率前10名',
                        color='球隊',
                        text='打擊率'
                    )
                    fig_avg.update_layout(
                        xaxis_tickangle=-45,
                        showlegend=True,
                        height=400
                    )
                    fig_avg.update_traces(
                        texttemplate='%{text:.3f}',
                        textposition='outside'
                    )
                    st.plotly_chart(fig_avg, use_container_width=True)

                with col2:
                    # OPS vs 打點散點圖
                    fig_ops = px.scatter(
                        filtered_df,
                        x='OPS',
                        y='打點',
                        color='球隊',
                        size='打席數',
                        hover_data=['球員'],
                        title='OPS vs 打點分析',
                        labels={'OPS': 'OPS', '打點': '打點'}
                    )
                    fig_ops.update_layout(height=400)
                    st.plotly_chart(fig_ops, use_container_width=True)

            with tabs[2]:  # 球隊比較 tab
                # 統計數據選項清單
                stat_options = [
                    ('打擊率', 'batting_avg', 3),  # (顯示名稱, 欄位名稱, 小數位數)
                    ('上壘率', 'obp', 3),
                    ('長打率', 'slg', 3),
                    ('OPS', 'ops', 3),
                    ('全壘打', 'hr', 0),
                    ('安打', 'hits', 0),
                    ('打點', 'rbi', 0),
                    ('三振', 'so', 0),
                    ('保送', 'bb', 0),
                    ('盜壘', 'sb', 0),
                    ('打席數', 'pa', 0)
                ]

                col1, col2 = st.columns(2)
                with col1:
                    stat1 = st.selectbox(
                        "選擇第一個比較項目",
                        options=stat_options,
                        format_func=lambda x: x[0]
                    )
                
                with col2:
                    stat2 = st.selectbox(
                        "選擇第二個比較項目",
                        options=stat_options,
                        format_func=lambda x: x[0],
                        index=3  # 預設選擇 OPS
                    )

                # 計算球隊統計
                team_stats = filtered_df.groupby('球隊').agg({
                    '打擊率': 'mean',
                    'OPS': 'mean',
                    '全壘打': 'sum',
                    '安打': 'sum',
                    '打點': 'sum',
                    '上壘率': 'mean',
                    '長打率': 'mean',
                    '三振': 'sum',
                    '保送': 'sum',
                    '盜壘': 'sum',
                    '打席數': 'sum',
                    '球員': 'count'
                }).round(3)
                
                team_stats = team_stats.rename(columns={'球員': '人數'})

                col1, col2 = st.columns(2)
                
                with col1:
                    # 第一個統計數據比較圖表
                    fig_team_stat1 = px.bar(
                        team_stats.reset_index(),
                        x='球隊',
                        y=stat1[0],  # 使用顯示名稱作為y軸
                        title=f'球隊 {stat1[0]} 比較',
                        text=team_stats[stat1[0]]  # 直接使用數據
                    )
                    fig_team_stat1.update_traces(
                        texttemplate='%{text:.' + str(stat1[2]) + 'f}',  # 根據小數位數動態設置格式
                        textposition='outside'
                    )
                    st.plotly_chart(fig_team_stat1, use_container_width=True)
                
                with col2:
                    # 第二個統計數據比較圖表
                    fig_team_stat2 = px.bar(
                        team_stats.reset_index(),
                        x='球隊',
                        y=stat2[0],  # 使用顯示名稱作為y軸
                        title=f'球隊 {stat2[0]} 比較',
                        text=team_stats[stat2[0]]  # 直接使用數據
                    )
                    fig_team_stat2.update_traces(
                        texttemplate='%{text:.' + str(stat2[2]) + 'f}',  # 根據小數位數動態設置格式
                        textposition='outside'
                    )
                    st.plotly_chart(fig_team_stat2, use_container_width=True)

                # 球隊整體統計表格
                st.subheader("球隊整體統計")
                styled_team_stats = team_stats.style.format({
                    '打擊率': '{:.3f}',
                    '上壘率': '{:.3f}',
                    '長打率': '{:.3f}',
                    'OPS': '{:.3f}',
                    '全壘打': '{:,.0f}',
                    '安打': '{:,.0f}',
                    '打點': '{:,.0f}',
                    '三振': '{:,.0f}',
                    '保送': '{:,.0f}',
                    '盜壘': '{:,.0f}',
                    '打席數': '{:,.0f}',
                    '人數': '{:,.0f}'
                })
                st.dataframe(styled_team_stats, use_container_width=True)

        except Exception as e:
            st.error(f"處理數據時發生錯誤: {str(e)}")

    def display_pitcher_stats(self, players_data):
        """顯示投手數據"""
        if not players_data:
            st.warning("沒有找到符合條件的數據")
            return

        try:
            df = pd.DataFrame([
                {
                    '球員': f"{p['name']} ({p['team']})",
                    '球隊': p['team'],
                    '防禦率': float(p['stats']['era']),
                    '勝場': int(p['stats']['w']),
                    '敗場': int(p['stats']['l']),
                    '中繼點': int(p['stats']['hld']),
                    '救援成功': int(p['stats']['sv']),
                    '投球局數': float(p['stats']['ip']),
                    '三振': int(p['stats']['so']),
                    '保送': int(p['stats']['bb']),
                    'WHIP': float(p['stats'].get('whip', 0))
                } for p in players_data
            ])

            # 篩選條件
            with st.expander("數據篩選", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    min_ip = st.number_input("最少投球局數", min_value=0.0, value=20.0)
                with col2:
                    sort_by = st.selectbox(
                        "排序依據",
                        ['防禦率', '勝場', '中繼點', '救援成功', '三振', 'WHIP']
                    )
                with col3:
                    team_filter = st.multiselect(
                        "選擇球隊",
                        options=sorted(df['球隊'].unique()),
                        default=sorted(df['球隊'].unique())
                    )

            filtered_df = df[
                (df['投球局數'] >= min_ip) & 
                (df['球隊'].isin(team_filter))
            ].copy()

            if filtered_df.empty:
                st.warning("沒有符合篩選條件的數據")
                return

            # 排序方式
            ascending = sort_by in ['防禦率', 'WHIP']  # 這些數據越低越好
            styled_df = filtered_df.sort_values(sort_by, ascending=ascending).style.format({
                '防禦率': '{:.2f}',
                'WHIP': '{:.2f}',
                '投球局數': '{:.1f}',
                '勝場': '{:,.0f}',
                '敗場': '{:,.0f}',
                '中繼點': '{:,.0f}',
                '救援成功': '{:,.0f}',
                '三振': '{:,.0f}',
                '保送': '{:,.0f}'
            })

            st.dataframe(styled_df, hide_index=True, use_container_width=True)

        except Exception as e:
            st.error(f"處理數據時發生錯誤: {str(e)}")

    def statistics(self):
        """數據統計頁面"""
        st.header("數據統計與分析")
        
        tabs = st.tabs(["打者分析", "投手分析", "勝率預測"])
        
        with tabs[0]:
            self._batter_statistics()
        
        with tabs[1]:
            self._pitcher_statistics()
        
        with tabs[2]:
            self._win_prediction()

    def _batter_statistics(self):
        """打者數據分析"""
        st.subheader("打者數據計算")
        
        col1, col2 = st.columns(2)
        with col1:
            hits = st.number_input("安打數", min_value=0, value=0)
            at_bats = st.number_input("打數", min_value=1, value=1)
        
        if st.button("計算打擊率", key="calc_avg"):
            avg = self.calculator.calculate_batting_avg(hits, at_bats)
            st.success(f"打擊率: {avg:.3f}")
            
            if avg >= 0.300:
                st.info("🌟 表現優異！")
            elif avg >= 0.250:
                st.info("⚾ 穩定表現")
            else:
                st.info("需要加強")

    def _pitcher_statistics(self):
        """投手數據分析"""
        st.subheader("投手數據計算")
        
        col1, col2 = st.columns(2)
        with col1:
            earned_runs = st.number_input("自責分", min_value=0, value=0)
            innings = st.number_input("投球局數", min_value=0.1, value=1.0)
        
        if st.button("計算防禦率", key="calc_era"):
            era = self.calculator.calculate_era(earned_runs, innings)
            st.success(f"防禦率: {era:.2f}")
            
            if era < 3.00:
                st.info("🌟 王牌投手等級！")
            elif era < 4.00:
                st.info("⚾ 優秀表現")
            else:
                st.info("仍有進步空間")

    def _win_prediction(self):
        """勝率預測"""
        st.subheader("勝率預測")
        st.write("基於近期表現預測未來勝率")
        
        num_games = st.slider("要分析的比賽場數", 3, 10, 5)
        st.write("請輸入最近的比賽結果 (1代表勝利，0代表失敗):")
        
        cols = st.columns(num_games)
        recent_results = []
        for i in range(num_games):
            with cols[i]:
                result = st.selectbox(
                    f"比賽 {i+1}",
                    options=[0, 1],
                    key=f"game_{i}"
                )
                recent_results.append(result)
        
        if st.button("預測下一場勝率", key="predict"):
            prediction = self.calculator.predict_performance(recent_results)
            st.success(f"預測勝率: {prediction:.1%}")
            
            if prediction > 0.6:
                st.info("📈 球隊近期狀態優異！")
            elif prediction > 0.4:
                st.info("⚖️ 球隊表現穩定")
            else:
                st.info("需要調整，建議分析近期失利原因")

    def prediction(self):
        """對戰預測頁面"""
        st.header("對戰預測")
        st.info("🚧 功能開發中，敬請期待...")

def main():
    """主程式"""
    # 設定頁面配置
    st.set_page_config(
        page_title="CPBL 教練助手",
        page_icon="⚾",
        layout="wide"
    )

    # 初始化並運行應用
    app = BaseballCoach()
    app.main_page()

if __name__ == "__main__":
    main()