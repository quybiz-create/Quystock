import requests
import numpy as np
from datetime import datetime, timedelta

FIREANT_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IkdYdExONzViZlZQakdvNERWdjV4QkRITHpnSSIsImtpZCI6IkdYdExONzViZlZQakdvNERWdjV4QkRITHpnSSJ9.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmZpcmVhbnQudm4iLCJhdWQiOiJodHRwczovL2FjY291bnRzLmZpcmVhbnQudm4vcmVzb3VyY2VzIiwiZXhwIjoxODg5NjIyNTMwLCJuYmYiOjE1ODk2MjI1MzAsImNsaWVudF9pZCI6ImZpcmVhbnQudHJhZGVzdGF0aW9uIiwic2NvcGUiOlsiYWNhZGVteS1yZWFkIiwiYWNhZGVteS13cml0ZSIsImFjY291bnRzLXJlYWQiLCJhY2NvdW50cy13cml0ZSIsImJsb2ctcmVhZCIsImNvbXBhbmllcy1yZWFkIiwiZmluYW5jZS1yZWFkIiwiaW5kaXZpZHVhbHMtcmVhZCIsImludmVzdG9wZWRpYS1yZWFkIiwib3JkZXJzLXJlYWQiLCJvcmRlcnMtd3JpdGUiLCJwb3N0cy1yZWFkIiwicG9zdHMtd3JpdGUiLCJzZWFyY2giLCJzeW1ib2xzLXJlYWQiLCJ1c2VyLWRhdGEtcmVhZCIsInVzZXItZGF0YS13cml0ZSIsInVzZXJzLXJlYWQiXSwianRpIjoiMjYxYTZhYWQ2MTQ5Njk1ZmJiYzcwODM5MjM0Njc1NWQifQ.dA5-HVzWv-BRfEiAd24uNBiBxASO-PAyWeWESovZm_hj4aXMAZA1-bWNZeXt88dqogo18AwpDQ-h6gefLPdZSFrG5umC1dVWaeYvUnGm62g4XS29fj6p01dhKNNqrsu5KrhnhdnKYVv9VdmbmqDfWR8wDgglk5cJFqalzq6dJWJInFQEPmUs9BW_Zs8tQDn-i5r4tYq2U8vCdqptXoM7YgPllXaPVDeccC9QNu2Xlp9WUvoROzoQXg25lFub1IYkTrM66gJ6t9fJRZToewCt495WNEOQFa_rwLCZ1QwzvL0iYkONHS_jZ0BOhBCdW9dWSawD6iF1SIQaFROvMDH1rg'

headers = {'Authorization': 'Bearer ' + FIREANT_TOKEN}
end = datetime.today().strftime('%Y-%m-%d')
start = (datetime.today() - timedelta(days=60)).strftime('%Y-%m-%d')

# Test với VNM
sym = 'VNM'
url = f'https://restv2.fireant.vn/symbols/{sym}/historical-quotes'
r = requests.get(url, headers=headers,
    params={'startDate':start,'endDate':end,'offset':0,'limit':60,'type':1},
    timeout=10)

data = list(reversed(r.json()))
print(f"So phien: {len(data)}")
print(f"Phien cuoi: {data[-1]}")

c = np.array([d['priceClose'] for d in data], dtype=float)
v = np.array([d.get('dealVolume', d.get('totalVolume',0)) for d in data], dtype=float)
i = len(c) - 1

price = float(c[i])
vol = float(v[i])
prev_close = float(c[i-1])
pct = (price - prev_close) / prev_close * 100
ma_vol10 = np.mean(v[i-10:i])
ma5 = np.mean(c[max(0,i-4):i+1])

print(f"\nVNM:")
print(f"  Gia: {price}")
print(f"  Volume: {vol}")
print(f"  % thay doi: {pct:.2f}%")
print(f"  Vol/TB10: {vol/ma_vol10:.2f}x")
print(f"  MA5: {ma5:.2f}")
print(f"\nDK1 Vol>100k: {vol > 100000}")
print(f"DK2 Gia>5000: {price > 5000}")
print(f"DK3 Vol>80%TB10: {vol >= 0.8*ma_vol10}")
print(f"DK4 Gia tang>1.5%: {pct >= 1.5}")
print(f"DK6 Gia>MA5: {price >= ma5}")
