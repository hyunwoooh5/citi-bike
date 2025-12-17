import pandas as pd
import sys
import numpy as np

def preprocess(df):
    df = df.dropna()

    df = df.drop(columns=['ride_id', 'start_station_id', 'end_station_id', 'start_lat', 'start_lng', 'end_lat', 'end_lng', 'member_casual'])

    return df

def remove_outlier(df):
    df['started_at'] = pd.to_datetime(df['started_at'], format='mixed')
    df['ended_at'] = pd.to_datetime(df['ended_at'], format='mixed')

    df['start_time'] = df['started_at'].dt.hour + df['started_at'].dt.minute/60 + df['started_at'].dt.second / 3600
    df['end_time'] = df['ended_at'].dt.hour + df['ended_at'].dt.minute/60 + df['ended_at'].dt.second / 3600

    df['duration'] = df['ended_at'] - df['started_at']

    df['duration'] = df['duration'].dt.total_seconds() / 60

    df = df[np.abs((df['duration']-df['duration'].mean())/df['duration'].std())<=2]

    return df

def feature_engineering(df):
    top3_stations = df.groupby('start_station_name').size().reset_index(name='count').sort_values(by='count', ascending=False)['start_station_name'].head(3).tolist()

    # Outflow (-1) / Inflow (+1)
    outflow = df[df['start_station_name'].isin(top3_stations)].copy()
    outflow = outflow[['started_at', 'start_station_name', 'rideable_type']]
    outflow.columns = ['time', 'station', 'rideable_type']
    outflow['flow'] = -1

    inflow = df[df['end_station_name'].isin(top3_stations)].copy()
    inflow = inflow[['ended_at', 'end_station_name', 'rideable_type']]
    inflow.columns = ['time', 'station', 'rideable_type']
    inflow['flow'] = 1

    combined = pd.concat([outflow, inflow])

    # Resampling (15 mins)
    net_flow_df = combined.groupby([
        pd.Grouper(key='time', freq='15min'),
        'station',
        'rideable_type'
    ])['flow'].sum().unstack(['station', 'rideable_type'], fill_value=0)

    # Reindexing to fill every 15 min
    start_date = net_flow_df.index.min().floor('D')
    end_date = net_flow_df.index.max().ceil('D')

    full_time_idx = pd.date_range(start=start_date, end=end_date, freq='15min', inclusive='left') 
    net_flow_df = net_flow_df.reindex(full_time_idx, fill_value=0)


    # Initial stock: Restore at every 00:00
    initial_stock = 10
    daily_cumsum = net_flow_df.groupby(pd.Grouper(freq='D')).cumsum()

    stock_df = initial_stock + daily_cumsum

    stock_df = stock_df[24*4:]

    return stock_df

def wide_to_long(df):
    df = df.stack(level=[0, 1], future_stack=True).reset_index()
    df.columns = ['time', 'station', 'rideable_type', 'stock']

    return df


if __name__ == "__main__":
    df = pd.read_csv(sys.argv[1])

    df = preprocess(df)
    df = remove_outlier(df)

    df = feature_engineering(df)
    df.to_csv(sys.argv[2], index=True)

    long_df = wide_to_long(df)
    long_df.to_csv(sys.argv[3], index=False)