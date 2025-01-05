import numpy as np

class BaseballCalculator:
    def calculate_batting_avg(self, hits, at_bats):
        """計算打擊率"""
        if at_bats == 0:
            return 0.0
        return hits / at_bats

    def calculate_era(self, earned_runs, innings):
        """計算防禦率"""
        if innings == 0:
            return 0.0
        return (earned_runs * 9) / innings

    def predict_performance(self, recent_results):
        """
        基於最近比賽結果預測下一場勝率
        
        Parameters:
        recent_results: list of int, 最近的比賽結果 (1代表勝利，0代表失敗)
        
        Returns:
        float: 預測的勝率 (0-1 之間)
        """
        if not recent_results:
            return 0.5  # 如果沒有歷史數據，返回 0.5
            
        # 計算基本勝率
        base_win_rate = sum(recent_results) / len(recent_results)
        
        # 計算趨勢權重
        weights = np.linspace(0.5, 1.0, len(recent_results))  # 越近的比賽權重越大
        weighted_results = np.multiply(recent_results, weights)
        trend_win_rate = np.sum(weighted_results) / np.sum(weights)
        
        # 計算動能分數 (連勝/連敗的影響)
        momentum = self._calculate_momentum(recent_results)
        
        # 綜合預測
        prediction = (base_win_rate * 0.3 +  # 基本勝率佔 30%
                     trend_win_rate * 0.4 +  # 趨勢勝率佔 40%
                     momentum * 0.3)         # 動能分數佔 30%
        
        # 確保預測值在 0.1 到 0.9 之間（避免極端預測）
        return max(0.1, min(0.9, prediction))
    
    def _calculate_momentum(self, results):
        """
        計算球隊動能分數
        """
        if not results:
            return 0.5
            
        # 計算最近的連勝/連敗
        current_streak = 0
        for result in reversed(results):
            if result == results[-1]:  # 如果與最後一場結果相同
                current_streak += 1
            else:
                break
        
        # 連勝給予正向加成，連敗給予負向加成
        streak_factor = (current_streak / len(results)) * 0.2  # 最大影響為 ±0.2
        if results[-1] == 0:  # 如果是連敗
            streak_factor = -streak_factor
            
        return 0.5 + streak_factor
        
    def calculate_ops(self, obp, slg):
        """計算OPS (On-base Plus Slugging)"""
        return obp + slg

    def calculate_whip(self, walks, hits, innings):
        """計算WHIP (Walks plus Hits per Inning Pitched)"""
        if innings == 0:
            return 0.0
        return (walks + hits) / innings