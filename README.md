# Inter-city bus (國道客運) travel time prediction 
**Status** *70%* finished. Currently scaling the model to *1500+ bus routes*. Unfinished parts are marked with (*to be finished*)

## Executive Summary
1. Problem: Intercity-busses losing passengers due to unpredictability of travel time
2. Target Audience: Potentail inter-city passengers who want to more accurately estimate their travel time beforehand
3. Solution: Build predictive models to provide more precise **estimates of travel time** using government datasets
4. Result: My model in single routes (eg. 7500) improves the baseline guessing (with mean/median) by **22.33%** and **29.88%** when using a loose and strict **custom metrics** respectively. 

## Data
[Transport Data eXchange (by Ministry of Transportation and Communication)](https://tdx.transportdata.tw/)
- More than **200 million** rows, **370+ csv** files, **60+ GB**
- Multiple datasets containing information about bus stops, bus routes, GPS location, bus action (arrival vs departure), time etc.
- Messy data with tons of missing values, typos, and some data corruption

## Tech Stack
- polars: highly optimized data manipulation 
- plotly: professional grade data visualization
- parquet: for highly optimized data storage and querying combined with `pl.scan_parquet`
- lightgbm: predictive model choice
- scikit-learn: cross validation, ML metrics
- joblib: (*to be finished*) for model deployment
- streamlit: (*to be finished*) simple GUI webapp for users to predict travel time for their target route
- scipy: `KDTree` to efficiently match each GPS location to the closest bus stop
- numpy/pandas: for last minute conversion to `np.ndarray` or `pd.DataFrame` for sklearn model trainings

## Technical Challenges
1. **Massive datasets**
- **Problem 1** Loading and transforming **365 csv files (60GB+)** into a single parquet file. Certain files were also corrupted coming out of the data source.
- **Solution 1** Try catch error to identify which files are corrupted. Then utilize `pl.read_csv().sink_parquet()` to stream csv data directly into the parquet file without actually loading data into RAM. Specify the full schema for higher efficiency parquet storage (eg. `pl.Category` instead of `pl.String`) 
- **Result** Turned **60GB+** multiple csv files into a **single 4.9GB** parquet file. (**94% space saving**) 
- **Problem 2** Need to efficently query and transform dataframes for EDA
- **Solution 2** Switched from *pandas* to *polars* providing **10-30X** speed up. Use `pl.LazyFrame` framework as upstream as possible and only convert to `pl.DataFrame` immediately before visualization or back-and-forth data wrangling.
- **Result** What would take *pandas* **30+ seconds** operations turn into **sub-second** tasks (**97% time saving**), which makes iterative EDA possible. Avoided crashing the laptop when a sub-optimal operation is carried out.
2. **Calculating Travel Time**
- **Dataset schema (after cleaning)** bus plate number, bus route ID, direction, time, bus stop, bus action (arriving/departing)
- **Problem 1** If no passengers get on/off at a stop, then no action was logged, meaning it's impossible to calculate the travel time for that trip. This is especially a problem for stops with few passengers.
- **Solution 1** (*to be finished*) for each bus route, filter for popular bus stops (as indicated by many logged records). This way, it's only able to predict travel time between popular stops, which intuitively is a benefit as the travel time between every single stop will be noisy and potentially affect the overall capability of the model.
- **Problem 2** How to reliably tell if two rows belong to the same trip (so that travel time can be caluclated)
- **Solution 2** Use `pl.join_asof` on Plate number with tolerance set at an appropriate level for polars to figure out which records belong to the same trip. 
- **Result** After manual inspection of some routes, the resulting dataframe *correctly* calculate the travel time. Combined with `pl.collect(engine='streaming')`, the complex join can be done within minutes. 
- **Next Step** (*to be finished*) Perform the join on entire dataset along with `pl.sink_parquet` to calculate travel time without running into OOM issues.
3. **Mapping GPS pings to Nearest Bus Stop**
- **Problem** How to map millions of GPS location to nearest bus stop (out of 20k bus stops) and accurately calculate the corresponding distance in meters.
- **Solution** Use `scipy.spatial.KDTree` for highly optimized tree searching. First, build a KDTree for each bus routes (so each bus ping only matches to bus stops that belong to that route). Use `pl.collect(engine='streaming')` to batch assign nearest to avoid out-of-memory (OOM) errors.
- **Result** Assigning bus stops to a **700k+ GPS pings** takes less than **3 seconds**. The assignment can easily scale to millions of rows.
- **Note** Due to the presence of excessive missing values and inherent GPS measurement errors, this dataset was abandoned for a simpler dataset.

## Exploratory Data Analysis (EDA)

The following results come mostly from EDA on route 1728 (1 hour) and 7500 (4 hours +).
1. Long tail distribution due to traffic in certain time (eg. morning/evening rush hours)
- insert image
2. Clear pattern distinction between weekdays and weekends.
- insert image
3. There exist outliers across every time interval, suggesting naive guessing with mean/median would lead to low accuracy
- insert image


## Modeling Approach
1. Model Selection: **LightGBM**
- extreme computatoin efficiency (essential for data this scale)
- native support for **1000+ categories** (for bus route IDs)
- industry default for tabular data that focuses on pure accuracy
2. Regression metrics: RMSE, R^2
3. *Custom metrics*
- Passengers care about how consistently they can get to destinations with some threshold of tolerance (longer for longer routes, vice versa)
- *Loose criterion (L1)*: predicted time off by at most *10%* of mean travel time of the route
- *Strict criterion (L2)*: predicted time off by at most *5%* of mean travel time of the route
4. Naive Baseline guessing: always predict mean/median travel time of the route (in training set)
5. Features
- Week of day
- Time in a day (in minutes after 00:00)
6. Abandoned features: despite seemingly effective explanatory power, including them actually worsens the model performance
- is_holiday
- is_long holiday
7. Time series cross validation
- Training set: 2025/2/26 ~ 2025/12/31
- Test set: 2026/1/1 ~ 2026/2/25
8. Fine-tune hyperparameters of LightGBM
- (*to be finished*) 5-fold CV with grid search

### Single Route Test Set Performance Comparison (bus #7500 台北轉運站 to 台南轉運站)

1. Loose criterion accuracy
- Baseline: 69.10%
- My Model: **90.22%** (improved by **30.56%**)
2. Strict criterion accuracy
- Baseline: 33.27%
- My Model: **66.09%** (improved by **98.65%**)
3. Observations
- The model's accuracy on strict criterion improved significantly 
- => *2 out of 3* predictions would *feel* pretty accurate from the passengers' perspective. (5% travel time error is acceptable for inter-city busses)
4. ML Rergression Metrics (*Baseline vs My Model*)
- r^2: -0.00 vs **0.52**
- RMSE: 27.53 vs **19.03** (decreased by **30.88%**)
- MAE: 21.50 vs **12.56** (decreased by **41.58%**)

## Future Roadmap (updated on 3/16)
1. Scale the model to train on all bus routes
2. Deploy the model with a streamlit GUI webapp


## Project Structure
```
04-BUSTIME/
├── .venv/
├── archive/
├── data/
│   ├── bus_event_time.parquet
│   ├── bus_routes_mar3.csv
│   └── bus_stops_mar3.csv

├── src/
│   ├── 01_initial_ETL.ipynb
│   ├── 02_initial_EDA.ipynb
│   ├── 03_quantile_travel_time.ipynb
│   ├── 04_GPS_EDA.ipynb
│   ├── constants.py
│   ├── helpers.py
│   └── try.ipynb
├── .env
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
├── to_do.md
└── uv.lock
```