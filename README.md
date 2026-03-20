[跳至中文翻譯](#國道客運旅行時間預測)

# Inter-city Bus (國道客運) Travel Time Prediction
*Solo project · End-to-end ownership from data engineering, modeling, to deployment*

*Core engine complete*; currently in Phase 2, implementing automated hyperparameter tuning and multi-route scaling to 1,500+ routes. (Updated on 2026/3/16)

---
## Executive Summary
1. Problem: Intercity-busses losing passengers due to unpredictability of travel time (down by [40%](https://www.rti.org.tw/news?uid=3&pid=186039) since 2016)
2. Target Audience: Potential inter-city passengers who want to more accurately estimate travel time beforehand
3. Solution: Build predictive models to provide more precise **estimates of travel time** using government datasets

---
## Results
- Reduced 60GB+ raw data (365 CSV files) to a single 4.2GB Parquet file (**93% compression**)
- Improved strict-criterion prediction accuracy from **33% → 66%** over baseline (bus 7500)
- Improved loose-criterion prediction accuracy from **69% → 90%** over baseline (bus 7500)
- Reduced RMSE by **30%** and MAE by **41%** over baseline (bus 7500)
- Provide per-route prediction error guarantees — e.g. for route 1728, **90%** of predictions are off by no more than **10 minutes**.
- Currently scaling to **1,000+ bus routes** nationwide
---
## Data
[Transport Data eXchange (Ministry of Transportation and Communication)](https://tdx.transportdata.tw/)
- More than **200 million** rows, **370+ csv** files, **60+ GB**
- Multiple datasets containing information about bus stops, bus routes, GPS location, bus action (arrival vs departure), time etc.
- Messy data with tons of missing values, typos, and some data corruption
---
## Tech Stack
**Data** · Polars, Parquet, NumPy, Pandas  
**Modeling** · LightGBM, Scikit-learn  
**Visualization** · Plotly  
**Deployment** *(Phase 2)* · Streamlit, Joblib

---
## Technical Challenges

1. **Massive Dataset (60GB+)**
   Streamed 370 CSV files directly into a single Parquet file using `pl.read_csv().sink_parquet()`, avoiding RAM overload. Switched from Pandas to Polars for **10-30x speedup**, turning 30-second operations into sub-second tasks. Result: **94% storage reduction** (60+GB → 4.9GB).

2. **Calculating Travel Time**
   Raw data only logs bus actions when passengers board/alight, leaving gaps for low-traffic stops. Used `pl.join_asof` on plate numbers to reliably match records to the same trip, then filtered for high-traffic stops only to reduce noise. Complex joins complete in minutes via `pl.collect(engine='streaming')`.

3. **Mapping GPS Pings to Bus Stops**
   Built per-route `scipy.KDTree` indexes to match 700k+ GPS pings to their nearest stop in under 3 seconds. *(Dataset ultimately replaced by a cleaner alternative due to excessive missing values and GPS noise.)*
---
## Exploratory Data Analysis (EDA)

The following results come mostly from EDA on route 1728 (1 hour) and 7500 (4 hours +).
1. Heavy tail distribution due to traffic in certain time (eg. morning/evening rush hours)
- insert image of A Histogram with a KDE plot showing the skewness of travel times.
2. Clear pattern distinction between weekdays and weekends.
- insert image of A Boxplot or Violin plot side-by-side.
3. There exist outliers across every time interval, suggesting naive guessing with mean/median would lead to low accuracy
- insert image of A Scatter plot of Time of Day vs. Travel Time.


---
## Modeling Approach

**Model:** LightGBM — chosen for computation efficiency at scale, native support for 1000+ category features (bus route IDs), and strong out-of-the-box performance on tabular data.

**Features**
| Feature | Description |
|---|---|
| Day of week | Captures weekday vs. weekend patterns |
| Time of day | Minutes elapsed since midnight |
| Route Target encoding (*Phase 2*) | Mean and Standard deviation of the route |

*Abandoned: `is_holiday`, `is_long_holiday` — despite intuitive explanatory power, both degraded model performance.*

**Evaluation**
- **Standard:** RMSE, R²
- **Custom (passenger-centric):**
  - *Loose (L1):* prediction within 10% of mean route travel time
  - *Strict (L2):* prediction within 5% of mean route travel time
- **Baseline:** always predicting the training set mean/median travel time

**Validation:** Time series split — trained on Feb–Dec 2025, tested on Jan–Feb 2026.

**Hyperparameter tuning:** Automated hyperparameter optimization using Optuna (*Phase 2*)

---

### Single Route Performance — Bus #7500 (台南轉運站 → 台北轉運站)

| Metric | Baseline | My Model | Improvement |
|---|---|---|---|
| Loose criterion (±25 min) | 69.10% | **90.22%** | +30.56% |
| Strict criterion (±13 min) | 33.27% | **66.09%** | +98.65% |
| RMSE | 27.53 | **19.03** | −30.88% |
| MAE | 21.50 | **12.56** | −41.58% |
| R² | −0.00 | **0.52** | — |

*2 out of 3 predictions fall within 5% of actual travel time — the threshold at which passengers would consider an estimate reliable.*

*90% of predictions are off by no more than 25 minutes*

### Short Route Performance - Bus #1728 (新竹轉運站 → 龍潭運動公園)

| Metric | Baseline | My Model | Improvement |
|---|---|---|---|
| Loose criterion (±5 min) | 51.68% | **74.30%** | +43.71% |
| Strict criterion (±2.5 min) | 26.37% | **43.70%** | +65.72%  |

*90% of predictions are off by no more than 10 minutes*

---

## Future Roadmap
- [  ] Scalability: Transitioning to Phase 2 to handle 1,500+ nationwide routes via LightGBM training.
- [  ] Optimization: Implementing automated hyperparameter tuning (Optuna) to refine per-route accuracy.
- [  ] Deployment: Building a Streamlit-based interface for real-time inference.


# 國道客運旅行時間預測
*獨立專案 · 負責從 Data Engineering、Modeling 到 Deployment 的end-to-end開發*

*核心引擎已完成*；目前處於 Phase 2，正在導入Optuna Hyperparameter Tuning 並將規模擴展至 1,500+ 條路線。（更新日期：2026/3/16）

---
## 執行摘要
1. **問題點**：因旅行時間的不確定性，導致國道客運乘客流失（自 2016 年以來下滑約 [40%](https://www.rti.org.tw/news?uid=3&pid=186039)）。
2. **目標受眾**：希望在出發前能更精確預估旅行時間的潛在客運乘客。
3. **解決方案**：利用政府開放資料集構建 Predictive Models，提供更精準的**旅行時間評估**。

---
## 專案成果
- 將 60GB+ 的 Raw Data（365 個 CSV 檔案）壓縮至單個 4.2GB 的 Parquet 檔案（**達 93% 壓縮率**）。
- 在 Strict-criterion（嚴格準則）下，預測準確度從 Baseline 的 **33% 提升至 66%**。(客運7500號)
- 在 Loose-criterion（寬鬆準則）下，預測準確度從 Baseline 的 **69% 提升至 90%**。(客運7500號)
- 相較於 Baseline，**RMSE 降低了 30%**，**MAE 降低了 41%**。(客運7500號)
- 提供各路線預測誤差保證 — 以1728路為例，**90%** 的預測誤差不超過 **10分鐘**。
- 目前正在擴展至全國 **1,000+ 條客運路線**。

---
## 資料集
[交通部 TDX 運輸資料流通服務平台 (Transport Data eXchange)](https://tdx.transportdata.tw/)
- 超過 **2 億**數據點、**370+ 個 CSV** 檔案、容量達 **60+ GB**。
- 包含多個資料集：客運站點、路線、GPS 定位、靠站動作（抵達 vs. 出發）、時間戳記等。
- 原始資料較為凌亂，含有大量缺失值（Missing Values）、錯字及部分毀損資料。

---
## 技術棧 (Tech Stack)
**Data** · Polars, Parquet, NumPy, Pandas  
**Modeling** · LightGBM, Scikit-learn  
**Visualization** · Plotly  
**Deployment** *(Phase 2)* · Streamlit, Joblib

---
## 技術挑戰

1. **巨量資料集 (60GB+)**
   使用 `pl.read_csv().sink_parquet()` 將 370 個 CSV 檔案直接串流（Streaming）寫入單個 Parquet 檔案，避免 RAM 過載。將 Pandas 切換為 Polars 後獲得 **10-30 倍的加速**，使原本需 30 秒的運算縮短至 1 秒內。最終實現 **94% 的空間節省**（60+GB → 4.9GB）。

2. **旅行時間計算**
   原始資料僅在乘客上下車時記錄動作，導致低流量站點出現資料缺失。利用 `pl.join_asof` 對車牌號碼進行配對，可靠地將紀錄分類至同一趟行程（Trip），並篩選高流量站點以減少 Noise。透過 `pl.collect(engine='streaming')`，複雜的 Joins 操作權資料集可在數分鐘內完成。

3. **GPS Ping 值與站點映射**
   針對每條路線建立 `scipy.KDTree` 索引，在 3 秒內將 70 萬個以上的 GPS Pings 匹配至最近站點。（註：該資料集最終因過多缺失值因此被更乾淨的替代資料集取代。）

---
## 探索性資料分析 (EDA)

以下結果主要基於 1728 路線（1 小時車程）與 7500 路線（4小時以上車程）的 EDA。

1. **Heavy Tail Distribution (厚尾分布)**：受特定時段（如早晚尖峰）交通狀況影響，呈現長尾分佈。


2. **平假日差異**：平日與週末之間有明顯的模式區別。


3. **離群值 (Outliers)**：每個時間段均存在離群值，顯示若單純以 Mean/Median 進行平均猜測（Naive guessing）會導致準確率偏低。


---
## 建模方法

**Model:** 選用 **LightGBM** —— 著眼於其大規模運算效率、對 1000+ 個 Category Features（客運路線 ID）的native support，以及在 Tabular Data 上強大的 Out-of-the-box 性能。

**特徵工程 (Features)**
| Feature | Description |
|---|---|
| Day of week | 捕捉週一至週日的模式差異 |
| Time of day | 自午夜起算的累計分鐘數 |
| Route Target encoding (*Phase 2*) | 該路線的 Mean 與 Standard deviation |

*捨棄features：`is_holiday`、`is_long_holiday` —— 儘管直覺上具解釋力，但實際訓練卻會降低模型表現。*

**評估指標 (Evaluation)**
- **Standard:** RMSE, R²
- **客製化metrics:**
  - *Loose (L1):* 預測值與該路線平均旅行時間誤差在 10% 以內。
  - *Strict (L2):* 預測值與該路線平均旅行時間誤差在 5% 以內。
- **Baseline:** 一律預測該公車路線的平均旅行時間。

**驗證方式 (Validation):** Time series split —— 使用 2025 年 2 月至 12 月資料進行訓練，2026 年 1 月至 2 月資料進行測試。

**Hyperparameter fine-tune:** 使用 Optuna 進行自動化 Hyperparameter Optimization (*Phase 2*)。

---

### 單一路線表現 — 7500 路線 (台南轉運站 → 台北轉運站)

| 指標 | 基準模型 | 我的模型 | 改善幅度 |
|---|---|---|---|
| 寬鬆標準 (±25 分鐘) | 69.10% | **90.22%** | +30.56% |
| 嚴格標準 (±13 分鐘) | 33.27% | **66.09%** | +98.65% |
| RMSE | 27.53 | **19.03** | −30.88% |
| MAE | 21.50 | **12.56** | −41.58% |
| R² | −0.00 | **0.52** | — |

*每 3 次預測中就有 2 次誤差在 5% 以內 —— 這是乘客認為預估資訊具備可信度的門檻。*

*90% 的預測誤差不超過 25 分鐘*

### 短途路線表現 - 1728路 (新竹轉運站 → 龍潭運動公園)

| 指標 | 基準模型 | 我的模型 | 改善幅度 |
|---|---|---|---|
| 寬鬆標準 (±5 分鐘) | 51.68% | **74.30%** | +43.71% |
| 嚴格標準 (±2.5 分鐘) | 26.37% | **43.70%** | +65.72% |

*90% 的預測誤差不超過 10 分鐘*

---

## 未來發展藍圖
- [  ] **Scalability (擴展性)**：轉向 Phase 2，透過 LightGBM Training 處理全國 1,500+ 條路線。
- [  ] **Optimization (優化)**：導入 Optuna 自動化調參，精煉每條路線的預測精度。
- [  ] **Deployment (部署)**：構建基於 Streamlit 的介面，實現即時推論（Real-time inference）。