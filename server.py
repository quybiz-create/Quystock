from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import traceback, os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'stock_dashboard.html')

@app.route('/api/history/<symbol>')
def get_history(symbol):
    try:
        from vnstock.api.quote import Quote
        days = int(request.args.get('days', 250))
        end = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=days+60)).strftime('%Y-%m-%d')
        q = Quote(symbol=symbol, source='VCI')
        df = q.history(start=start, end=end, interval='1D')
        if df is None or df.empty:
            return jsonify({'error': 'Khong co du lieu'}), 404
        result = []
        for _, row in df.iterrows():
            date_val = row.get('time', row.get('date', ''))
            result.append({
                'date':   str(date_val)[:10],
               'open':   round(float(row['open']), 2),
               'high':   round(float(row['high']), 2),
               'low':    round(float(row['low']),  2),
               'close':  round(float(row['close']),2),
               'volume': int(row['volume'])
            })
        return jsonify({'symbol': symbol.upper(), 'data': result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/fundamental/<symbol>')
def get_fundamental(symbol):
    try:
        from vnstock import Vnstock
        s = Vnstock().stock(symbol=symbol, source='KBS')
        ratio = s.finance.ratio(period='year')
        cols = [c for c in ratio.columns if c not in ['item', 'item_id']]
        def getval(item_id, pct=False):
            try:
                row = ratio[ratio['item_id'] == item_id]
                if row.empty:
                    return None
                val = round(float(row[cols[0]].values[0]), 2)
                if pct:
                    val = round(val / 100, 4)
                return val
            except:
                return None
        return jsonify({
            'symbol':       symbol.upper(),
            'pe':           getval('p_e'),
            'pb':           getval('p_b'),
            'eps':          getval('trailing_eps'),
            'roe':          getval('roe', pct=True),
            'roa':          getval('roa', pct=True),
            'gross_margin': getval('gross_profit_margin', pct=True),
            'net_margin':   getval('net_profit_margin', pct=True),
            'debt_equity':  getval('debt_to_equity'),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profile/<symbol>')
def get_profile(symbol):
    try:
        from vnstock import Vnstock
        s = Vnstock().stock(symbol=symbol, source='VCI')
        ov = s.company.overview()
        if ov is None or ov.empty:
            return jsonify({'error': 'Khong co thong tin'}), 404
        row = ov.iloc[0]
        return jsonify({
            'symbol':    symbol.upper(),
            'shortName': str(row.get('shortName', '')),
            'exchange':  str(row.get('exchange', '')),
            'industry':  str(row.get('industryName', '')),
            'website':   str(row.get('website', '')),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai', methods=['POST'])
def ai_analyze():
    try:
        import requests as req
        data = request.get_json()
        prompt = data.get('prompt', '')
        groq_key = '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'
        r = req.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': 'Bearer ' + groq_key,
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 1000
            },
            timeout=30
        )
        result = r.json()
        if 'choices' in result:
            reply = result['choices'][0]['message']['content']
        elif 'error' in result:
            reply = 'Loi: ' + result['error'].get('message', 'Unknown')
        else:
            reply = 'Loi: ' + str(result)
        return jsonify({'reply': reply})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
@app.route('/api/signal/<symbol>')
def get_signal(symbol):
    try:
        from vnstock.api.quote import Quote
        from datetime import datetime, timedelta
        import numpy as np
        
        end = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        q = Quote(symbol=symbol, source='VCI')
        df = q.history(start=start, end=end, interval='1D')
        if df is None or df.empty:
            return jsonify({'error': 'No data'}), 404

        c = df['close'].values.astype(float)
        h = df['high'].values.astype(float)
        l = df['low'].values.astype(float)
        o = df['open'].values.astype(float)

        # EMA
        def ema(arr, n):
            k = 2/(n+1)
            out = [arr[0]]
            for i in range(1, len(arr)):
                out.append(arr[i]*k + out[-1]*(1-k))
            return np.array(out)

        # StDev
        def stdev(arr, n):
            out = [0]*n
            for i in range(n, len(arr)):
                out.append(float(np.std(arr[i-n:i])))
            return np.array(out)

        # Trade with Target logic
        n = 7
        ys1 = (o + h + l + c*9) / 4
        rk3 = ema(ys1, n)
        rk4 = stdev(ys1, n)
        rk4 = np.where(rk4==0, 0.001, rk4)
        rk5 = (ys1 - rk3) * 100 / rk4
        rk6 = ema(rk5, n)
        up = ema(rk6, n)
        down = ema(up, n)

        # Tín hiệu
       # Tín hiệu dựa trên Pivot (Auto Buy/Sell)
        n_bars = 12
        hhv = max(h[-n_bars-1:-1])
        llv = min(l[-n_bars-1:-1])
        
        # Buy: gia vuot HHV (breakout len)
        buy = bool(h[-1] > hhv and h[-2] <= max(h[-n_bars-2:-2]))
        # Sell: gia pha LLV (breakout xuong)
        sell = bool(l[-1] < llv and l[-2] >= min(l[-n_bars-2:-2]))
        
        # Xu huong hien tai
        in_long = up[-1] > down[-1]
        in_short = up[-1] < down[-1]

        # Trailing Stop Loss
        no = 10
        res = [max(h[max(0,i-no):i+1]) for i in range(len(h))]
        sup = [min(l[max(0,i-no):i+1]) for i in range(len(l))]
        avd = []
        for i in range(len(c)):
            if i == 0:
                avd.append(0)
            elif c[i] > res[i-1]:
                avd.append(1)
            elif c[i] < sup[i-1]:
                avd.append(-1)
            else:
                avd.append(avd[-1])
        
        tsl = []
        for i in range(len(c)):
            if avd[i] == 1:
                tsl.append(sup[i])
            else:
                tsl.append(res[i])

        last_c = float(c[-1])
        last_tsl = float(tsl[-1])
        diff = abs(last_c - last_tsl)

        # Targets
        if in_long:
            entry = last_c
            sl = last_tsl
            t1 = round(entry + diff, 2)
            t2 = round(entry + 2*diff, 2)
            t3 = round(entry + 4*diff, 2)
            signal = 'BUY' if buy else 'DANG TANG'
        else:
            entry = last_c
            sl = last_tsl
            t1 = round(entry - diff, 2)
            t2 = round(entry - 2*diff, 2)
            t3 = round(entry - 4*diff, 2)
            signal = 'SELL' if sell else 'DANG GIAM'

        return jsonify({
            'symbol': symbol.upper(),
            'signal': signal,
            'entry':  round(last_c, 2),
            'sl':     round(last_tsl, 2),
            't1':     t1,
            't2':     t2,
            't3':     t3,
            'in_long': bool(in_long),
            'new_signal': bool(buy or sell)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    print("="*50)
    print("  QuyStock Server dang chay...")
    print("  Mo Chrome vao: http://localhost:5000")
    print("="*50)
    app.run(host='0.0.0.0', port=5000, debug=False)