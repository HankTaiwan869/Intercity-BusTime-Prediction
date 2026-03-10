# to do
1. get bus ping data of 2 months
- try 2 months first, if not enough, max extra budget is 400 dollars
2. transform the data
- use scan_csv + sink_parquet to convert it into a single parquet file (specify a proper schema)
- scan_parquet + sink_parquet to assign bus stop data to each ping
3. difficult parts
- how to get a clean bus trip schedule
- how to handle missing stops from a trip
4. easy parts
- how to calculate travel time (should be easy)
- prepare df for lightgbm training
- evaluate the accuracy
5. build streamlit webapp 
6. organize codes and do a write-up (README)

# things to consider
1. get rid of bus routes that have too few trips (maybe use simple sample quantile for that)
2. examine longer routes (3+ hours)
