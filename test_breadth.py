from vnstock.api.quote import Quote
from datetime import datetime, timedelta

end = datetime.today().strftime('%Y-%m-%d')
start = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')

def sma(arr, n):
    result = []
    for i in range(len(arr)):
        if i < n-1: result.append(None)
        else: result.append(sum(arr[i-n+1:i+1]) / n)
    return result

def get_date(df, i):
    try:
        row = df.iloc[i]
        # Try 'time' column first
        if 'time' in df.columns:
            return str(row['time'])[:10]
        elif 'date' in df.columns:
            return str(row['date'])[:10]
        else:
            return str(df.index[i])[:10]
    except:
        return ''

# Test voi ACB
df = Quote(symbol='ACB', source='VCI').history(start=start, end=end, interval='1D')
print("Columns:", list(df.columns))
print("Index type:", type(df.index[0]))
print("Row 0:", df.iloc[0])
print()

# Test get_date
for i in range(min(3, len(df))):
    print(f"Date {i}:", get_date(df, i))

# Test logic
closes = list(df['close'].values.astype(float))
ma20 = sma(closes, 20)
ma50 = sma(closes, 50)
print("\nLast close:", closes[-1])
print("Last MA20:", ma20[-1])
print("Last MA50:", ma50[-1])
print("Above MA20:", closes[-1] > ma20[-1] if ma20[-1] else 'N/A')
print("Above MA50:", closes[-1] > ma50[-1] if ma50[-1] else 'N/A')
print("\nOK!")
