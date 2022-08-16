import numpy as np
import pandas as pd
import time
import subprocess
import os

def wknnEstimation(samples, query, positions, k):
    samplRows = samples.shape[0]
    queryRows = query.shape[0]
    prediction = np.zeros([queryRows, 3])

    if k > samplRows:
        k = samplRows

    for i in range(queryRows):
        repQuery = np.tile(query[i, :], (samplRows, 1))
        sumDist = np.sqrt(np.sum(np.square(samples - repQuery), axis=1))

        idx = np.argsort(sumDist)[0:k]
        val = sumDist[idx]

        pos = positions[idx, :]
        if val[0] == 0:
            prediction[i, :] = pos[0, :]
        else:
            w = 1 / val
            w = w / np.sum(w)
            prediction[i, :] = np.sum(w * pos.T, axis=1)

    return prediction

def unique_return_inverse_2D_viewbased(a):
    a = np.ascontiguousarray(a)
    void_dt = np.dtype((np.void, a.dtype.itemsize * np.prod(a.shape[1:])))
    return np.unique(a.view(void_dt).ravel(), return_inverse=1)[1]

def process_csv(test_csv_name, save_train_name, save_test_name, initial_data):
    test_csv = pd.read_csv(test_csv_name, index_col=False)
    test_csv.drop(test_csv[test_csv["MAC_Seq"].map(len) <= 16].index, inplace=True)
    test_csv['MAC_Seq'] = test_csv['MAC_Seq'].str[0:17]

    test_csv = test_csv.groupby('MAC_Seq').tail(N_SAMPLE_PER_TEST_SAMPLE)
    test_csv.sort_values(by=['MAC_Seq'], inplace=True)

    test_csv = test_csv[(test_csv != 0).sum(1) > 6]

    coordinate = zip(test_csv['X'].values, test_csv['Y'].values, test_csv['Z'].values)
    feature = (zip(test_csv['RPI%d_RSSI' % i].values for i in range(N_MON)))
    feature = np.array([*feature]).T
    feature = feature.reshape(feature.shape[0], feature.shape[2])
    XYZ = np.array([*coordinate])
    RP_ID = unique_return_inverse_2D_viewbased(XYZ)
    RP_N = np.unique(RP_ID).shape[0]

    test_feature = list()
    test_pos = list()
    for RP in range(RP_N):
        test_feature.append(feature[RP_ID == RP])
        test_pos.append(XYZ[RP_ID == RP])

    test_feature, test_pos = np.array(test_feature), np.array(test_pos)
    test_MAC = test_csv['MAC_Seq']
    with open(save_test_name, 'wb') as f:
        np.savez(f, feature=test_feature, pos=test_pos, MAC=test_MAC)
    data = np.load(save_test_name, allow_pickle=True)

    feature = data['feature']
    Test_RP_N = feature.shape[0]
    data_MAC = pd.DataFrame(data['MAC'], columns=['MAC_Seq'])

    test_feature = feature
    test_feature = np.concatenate(list(test_feature), axis=0)
    test_feature = test_feature.astype(np.float64)
    test_feature[test_feature == 0] = np.nan
    test_feature = test_feature[:, :N_MON]
    test_feature = (test_feature - RSSI_min) / (RSSI_max - RSSI_min)
    test_feature = np.nan_to_num(test_feature, nan=0.)

    result = wknnEstimation(samples=train_feature, query=test_feature, positions=train_pos, k=k_knn)

    result_X = pd.DataFrame(result[..., 0], columns=['X'])
    result_Y = pd.DataFrame(result[..., 1], columns=['Y'])
    result_Z = pd.DataFrame(result[..., 2], columns=['Z'])

    test_feature_df = pd.DataFrame(test_feature,
                                   columns=['RPI0_RSSI', 'RPI1_RSSI', 'RPI2_RSSI', 'RPI3_RSSI', 'RPI4_RSSI',
                                            'RPI5_RSSI','RPI6_RSSI', 'RPI7_RSSI', 'RPI8_RSSI', 'RPI9_RSSI',
                                            'RPI10_RSSI','RPI11_RSSI', 'RPI12_RSSI', 'RPI13_RSSI', 'RPI14_RSSI',
                                            'RPI15_RSSI', 'RPI16_RSSI', 'RPI17_RSSI', 'RPI18_RSSI', 'RPI19_RSSI'])


    while True:
        try:
            assert (data_MAC.shape[0] == test_feature_df.shape[0] == result_X.shape[0] == result_Y.shape[0] ==
                    result_Z.shape[0]), "Error message"
            break
        except AssertionError:
            print('assertion error')
            break

    concat_df = pd.concat([data_MAC, test_feature_df, result_X, result_Y, result_Z], axis=1)

    X_mean = concat_df.groupby('MAC_Seq', as_index=False)['X'].last()
    Y_mean = concat_df.groupby('MAC_Seq', as_index=False)['Y'].last()
    Z_mean = concat_df.groupby('MAC_Seq', as_index=False)['Z'].last()
    if os.path.exists('./initial_predicted.csv'):
        data_t = pd.read_csv('./initial_predicted.csv')
        past_unique_mac = pd.unique(data_t['MAC_Seq'])

        current_unique_mac = pd.unique(concat_df['MAC_Seq'])

        for i,mac in enumerate(current_unique_mac):
            if mac in past_unique_mac:
                past_index = list(past_unique_mac).index(mac)
                x_current = X_mean['X'][i]
                y_current = Y_mean['Y'][i]
                z_current = Z_mean['Z'][i]
                x_past = data_t['X'][past_index]
                y_past = data_t['Y'][past_index]
                z_past = data_t['Z'][past_index]
                distance = (((x_current) - (x_past)) ** 2 + ((y_current) - (y_past)) ** 2) ** 0.5 + 1e-8
                d = 0.4
                if distance > d:
                    X_mean['X'][i] = d / distance * x_current + (distance - d) / distance * x_past
                    Y_mean['Y'][i] = d / distance * y_current + (distance - d) / distance * y_past
                    Z_mean['Z'][i] = d / distance * z_current+ (distance - d) / distance * z_past

    uniq_MAC = pd.DataFrame(pd.unique(concat_df['MAC_Seq']), columns=['MAC_Seq'])

    predicted_df = pd.concat(
        [uniq_MAC, X_mean['X'], Y_mean['Y'], Z_mean['Z']],
        axis=1)
    predicted_df['W'] = ''
    predicted_df = predicted_df[
        ["X", "Y", "Z", "W", "MAC_Seq"]]
    predicted_df.to_csv("./predicted.csv", index=False)
    cur_csv_file_df = predicted_df
    cur_csv_file_df['Time'] = ''

    cur_csv_file_df = cur_csv_file_df[cur_csv_file_df['X'].notna()]
    cur_csv_file_df = cur_csv_file_df[cur_csv_file_df['Y'].notna()]
    cur_csv_file_df = cur_csv_file_df[cur_csv_file_df['Z'].notna()]
    cur_csv_file_df = cur_csv_file_df[cur_csv_file_df['MAC_Seq'].notna()]
    cur_csv_file_df = cur_csv_file_df.reset_index(drop=True)

    while True:
        try:
            df = pd.read_csv(initial_data)
            break
        except pd.errors.EmptyDataError:
            print('No columns to parse from file')
            continue
        except FileNotFoundError:
            print('initial data file not found, use current predicted file as initial')
            df = cur_csv_file_df
            break

    while True:
        try:
            whitelist = pd.read_csv('./Testing/whitelist.csv')
            whitelist = whitelist['0'].tolist()
            break
        except pd.errors.EmptyDataError:
            continue
        except FileNotFoundError:
            continue
        except PermissionError:
            print('permission error, whitelist is saving.')
            continue

    df = df.reset_index(drop=True)
    prev_MAC = []
    for num, row in df.iterrows():
        prev_MAC.append(row['MAC_Seq'])

    for num, row in cur_csv_file_df.iterrows():
        if row['MAC_Seq'] not in prev_MAC:
            row = row.copy()
            row['Time'] = time.time()
            df.loc[len(df.index)] = row
            prev_MAC.append(row['MAC_Seq'])

        elif row['MAC_Seq'] in prev_MAC and row['MAC_Seq'] in whitelist:
            row = row.copy()
            row['Time'] = time.time()
            df[df['MAC_Seq'] == row['MAC_Seq']] = row.to_frame().T.values
    for num, row in df.iterrows():
        if row['MAC_Seq'] not in whitelist:
            print('removed MAC due to not connected', row.to_frame().T['MAC_Seq'])
            df.drop(df.loc[df['MAC_Seq'] == row['MAC_Seq']].index, inplace=True)
            cur_csv_file_df.drop(cur_csv_file_df.loc[cur_csv_file_df['MAC_Seq'] == row['MAC_Seq']].index, inplace=True)
            prev_MAC.remove(row['MAC_Seq'])

    for num, row in df.iterrows():
        if row['MAC_Seq'] in blackList:
            df.drop(df.loc[df['MAC_Seq'] == row['MAC_Seq']].index, inplace=True)
    print(df[['MAC_Seq', 'X', 'Y', 'Z']])

    log_predicted_copy.append(list(df))
    df.to_csv("./initial_predicted.csv", index=False)
    df.to_csv('./log_initial_predicted_copy.csv', mode='a', header=df.columns, index=False)

    print('time elapsed', time.time() - initial_time)
    return result, uniq_MAC


if __name__ == "__main__":

    save_train_name = './train_.npz'       
    save_test_name = './test_.npz'
    AP_CHANNEL = 100
    N_MON = 20
    N_SAMPLE_PER_TRAIN_SAMPLE = 20
    N_SAMPLE_PER_TEST_SAMPLE = 20
    k_knn = 10
    working_dir1 = "./"
    initial_predicted_csv = "./initial_predicted.csv"

    data = np.load(save_train_name, allow_pickle=True)
    feature, pos = data['feature'], data['pos']
    RP_N = feature.shape[0]
    train_feature, train_pos = feature, pos

    for i in range(len(train_feature)):
        train_feature[i] = train_feature[i][:N_SAMPLE_PER_TRAIN_SAMPLE]
        train_pos[i] = train_pos[i][:N_SAMPLE_PER_TRAIN_SAMPLE]
    train_feature = np.concatenate(list(train_feature), axis=0)
    train_pos = np.concatenate(list(train_pos), axis=0)
    train_feature = train_feature.astype(np.float64)
    train_feature = train_feature[:, :N_SAMPLE_PER_TRAIN_SAMPLE]
    train_pos = train_pos[:, :N_SAMPLE_PER_TRAIN_SAMPLE]
    train_feature[train_feature == 0] = np.nan
    RSSI_min = np.nanmin(train_feature)
    RSSI_max = np.nanmax(train_feature)
    train_feature = (train_feature - RSSI_min) / (RSSI_max - RSSI_min)
    train_feature = np.nan_to_num(train_feature, nan=0.)

    blackList = ['B8:27:EB:78:BB:33', 'B8:27:EB:F0:96:53', 'B8:27:EB:1C:19:34', 'B8:27:EB:56:D1:02', 'B8:27:EB:E2:7C:53', 'DC:A6:32:8E:23:43',
                '00:11:32:E3:39:11', '50:EB:F6:00:03:01', 'B8:27:EB:83:29:79', 'B8:27:EB:25:34:21', 'B8:27:EB:D1:E3:34', 'B8:27:EB:9F:76:29', 
                'B8:27:EB:74:15:23', 'B8:27:EB:85:11:14', 'B8:27:EB:C2:06:75', 'B8:27:EB:0F:92:62', '12:11:32:E3:3A:63', '5A:91:9D:6D:67:50']

    log_predicted_copy = []
    
    while True:
        try:
            command_result = subprocess.run('tar -xvzf ./Testing/ch.tar.gz', shell=True)
            if command_result.returncode != 0:
                continue
        except subprocess.CalledProcessError as e:
            continue
        try:
            ch = pd.read_csv(working_dir1 + 'Channel_%s.csv' % AP_CHANNEL)
            if ch.empty == True:
                print('empty channel file dataframe')
                continue
        except FileNotFoundError:
            print('channel file not found')
            continue
        initial_time = time.time()
        rslt, unique_mac_df = process_csv(working_dir1 + 'Channel_%s.csv' % AP_CHANNEL, save_train_name, save_test_name,
                                          initial_predicted_csv)