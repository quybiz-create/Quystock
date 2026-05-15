from vnstock.api.quote import Quote
from datetime import datetime, timedelta

end = datetime.today().strftime('%Y-%m-%d')
start = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

try:
    df = Quote(symbol='ACB', source='VCI').history(start=start, end=end, interval='1D')
    print("OK - So dong:", len(df))
    print(df.tail(2))
except Exception as e:
    print("LOI:", e)
