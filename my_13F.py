## The goal of this program is to extract the holdings of the top fund managers
## on 13info.com using beautifulsoup

import sys
import time
import datetime

import pandas as pd
import numpy as np

from bs4 import BeautifulSoup
import requests
import json

import matplotlib.pyplot as plt

pd.set_option('display.max_rows',None)
pd.set_option('display.max_columns',None)
pd.set_option('display.width',None)

requests.packages.urllib3.disable_warnings()


def get_quarter_holdings(filing_id):
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Sec-Ch-Ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    url = 'https://13f.info/data/13f/' + filing_id
    r = requests.get(url, headers=headers, verify=False)
    r.raise_for_status()
    r.encoding = r.apparent_encoding

    json_data = json.loads(r.text)
    data = json_data['data']

    result = [d for d in data]

    df = pd.DataFrame(result)
    df.columns = ['ticker', 'name', 'class', 'CUSIP', 'value_usd_k','percent','shares', 'principal', 'option_type']
    df = df.dropna(subset=['ticker'])
    return df

def get_df_combined(name, url):

# use beautiful soup tp scrap the data
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find_all('table')[0]

    column_names = [th.text for th in table.find_all('th')]

    # Extract each row from the table body
    rows = [[td.text for td in row.find_all('td')] for row in table.find_all('tr')]
    rows = rows[1:]

    df_root = pd.DataFrame(rows, columns=column_names)
    df_root['Date Filed'] = pd.to_datetime(df_root['Date Filed'], format='%m/%d/%Y')

    df_list = []
    for i in df_root.index[::-1]:
        date      = df_root.at[i,'Date Filed']
        filing_id = df_root.at[i,'Filing ID']
        form_type = df_root.at[i,'Form Type']
        # we only need the 13F form type
        if form_type == '13F-HR':
            # use the function created above to request the data
            df = get_quarter_holdings(filing_id)

            df = df[['ticker', 'value_usd_k']]
            df['ticker'] = df['ticker'].drop_duplicates(keep='last')
            df = df.set_index('ticker').T
            df.columns.name = None
            df.index = pd.Index([date])

            # combining the holdings by quarter
            df_list.append(df)
            df_combined = pd.concat(df_list)

            ffilled_df = df_combined.ffill()
            cond1 = df_combined.notna().shift(-1) & df_combined.notna().shift(1)  # condition 1: previous and next row are not NaN
            cond2 = df_combined.shift(-1).notna()  # condition 2: row is not the last row
            df_combined = df_combined.where(~cond1 | ~cond2, ffilled_df)

            print(df_combined)
            print('--------------')
            time.sleep(0.5)

    # save as a csv file
    print(df_combined)
    df_combined.to_csv(name + '.csv')


if __name__ == '__main__':

#put the url of the fund managers that you are interested into the dictionary
    name_dict = {
        'berkshire-hathaway-inc'    : "https://13f.info/manager/0001067983-berkshire-hathaway-inc",
        #'bridgewater-associates-lp' : "https://13f.info/manager/0001350694-bridgewater-associates-lp",
        #'scion-asset-management-llc' : "https://13f.info/manager/0001649339-scion-asset-management-llc",
        #'pershing-square-capital-management-l-p' : "https://13f.info/manager/0001336528-pershing-square-capital-management-l-p",
        #'renaissance-technologies-llc' : "https://13f.info/manager/0001037389-renaissance-technologies-llc",
    }

    for name, url in name_dict.items():
       get_df_combined(name, url)

# plot a chart of the historical holdings
    for name, url in name_dict.items():
        df = pd.read_csv(name+'.csv')
        df = df.rename(columns={df.columns[0]:'date'})
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
        df = df.set_index('date')

        df_t = df.T

        df_t = df_t.sort_values(by=df_t.columns[-1], ascending=False)
        row_list = df_t.index[0:10]

        df = df.fillna(0)

        plt.figure(figsize=(10, 6.18))

        for col in row_list:
            plt.plot(df[col], label=col)

        plt.title('Warren Buffett line chart')
        plt.xlabel('Index')
        plt.ylabel('Invested_Value(USD_thousand)')

        plt.grid(True)
        plt.legend()
        plt.show()
