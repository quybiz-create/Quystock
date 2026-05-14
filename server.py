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
        days  = int(request.args.get('days', 250))
        end   = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=days+60)).strftime('%Y-%m-%d')
        df    = Quote(symbol=symbol, source='VCI').history(start=start, end=end, interval='1D')
        if df is None or df.empty:
            return jsonify({'error': 'No data'}), 404
        result = []
        for _, row in df.iterrows():
            date_val = row.get('time', row.get('date', ''))
            result.append({
                'date':   str(date_val)[:10],
                'open':   round(float(row['open']),  2),
                'high':   round(float(row['high']),  2),
                'low':    round(float(row['low']),   2),
                'close':  round(float(row['close']), 2),
                'volume': int(float(row['volume']))
            })
        return jsonify({'symbol': symbol.upper(), 'data': result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/fundamental/<symbol>')
def get_fundamental(symbol):
    try:
        from vnstock import Vnstock
        s     = Vnstock().stock(symbol=symbol, source='KBS')
        ratio = s.finance.ratio(period='year')
        cols  = [c for c in ratio.columns if c not in ['item', 'item_id']]
        def getval(item_id, pct=False):
            try:
                row = ratio[ratio['item_id'] == item_id]
                if row.empty: return None
                val = round(float(row[cols[0]].values[0]), 2)
                return round(val/100, 4) if pct else val
            except: return None
        return jsonify({
            'symbol': symbol.upper(),
            'pe': getval('p_e'), 'pb': getval('p_b'),
            'eps': getval('trailing_eps'),
            'roe': getval('roe', pct=True), 'roa': getval('roa', pct=True),
            'gross_margin': getval('gross_profit_margin', pct=True),
            'net_margin': getval('net_profit_margin', pct=True),
            'debt_equity': getval('debt_to_equity'),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/profile/<symbol>')
def get_profile(symbol):
    try:
        from vnstock import Vnstock
        s  = Vnstock().stock(symbol=symbol, source='VCI')
        ov = s.company.overview()
        if ov is None or ov.empty:
            return jsonify({'error': 'No info'}), 404
        row = ov.iloc[0]
        return jsonify({
            'symbol': symbol.upper(),
            'shortName': str(row.get('shortName', '')),
            'exchange': str(row.get('exchange', '')),
            'industry': str(row.get('industryName', '')),
            'website': str(row.get('website', '')),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/signal/<symbol>')
def get_signal(symbol):
    try:
        from vnstock.api.quote import Quote
        import numpy as np

        end   = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        df    = Quote(symbol=symbol, source='VCI').history(start=start, end=end, interval='1D')
        if df is None or df.empty:
            return jsonify({'error': 'No data'}), 404

        c = df['close'].values.astype(float)
        h = df['high'].values.astype(float)
        l = df['low'].values.astype(float)
        o = df['open'].values.astype(float)

        def ema(arr, n):
            k, out = 2/(n+1), [arr[0]]
            for i in range(1, len(arr)):
                out.append(arr[i]*k + out[-1]*(1-k))
            return np.array(out)

        def stdev(arr, n):
            out = [0]*n
            for i in range(n, len(arr)):
                out.append(float(np.std(arr[i-n:i])))
            return np.array(out)

        n   = 7
        ys1 = (o + h + l + c*9) / 4
        rk3 = ema(ys1, n)
        rk4 = stdev(ys1, n)
        rk4 = np.where(rk4 == 0, 0.001, rk4)
        rk5 = (ys1 - rk3) * 100 / rk4
        up   = ema(ema(rk5, n), n)
        down = ema(up, n)

        n_bars = 12
        hhv = max(h[-n_bars-1:-1])
        llv = min(l[-n_bars-1:-1])
        buy  = bool(h[-1] > hhv and h[-2] <= max(h[-n_bars-2:-2]))
        sell = bool(l[-1] < llv and l[-2] >= min(l[-n_bars-2:-2]))
        in_long = up[-1] > down[-1]

        no  = 10
        res = [max(h[max(0,i-no):i+1]) for i in range(len(h))]
        sup = [min(l[max(0,i-no):i+1]) for i in range(len(l))]
        avd = [0]
        for i in range(1, len(c)):
            if   c[i] > res[i-1]: avd.append(1)
            elif c[i] < sup[i-1]: avd.append(-1)
            else:                  avd.append(avd[-1])

        tsl = [sup[i] if avd[i]==1 else res[i] for i in range(len(c))]
        last_c, last_tsl = float(c[-1]), float(tsl[-1])
        diff = abs(last_c - last_tsl)

        if in_long:
            signal = 'BUY' if buy else 'LONG'
            t1 = round(last_c + diff, 2)
            t2 = round(last_c + 2*diff, 2)
            t3 = round(last_c + 4*diff, 2)
        else:
            signal = 'SELL' if sell else 'SHORT'
            t1 = round(last_c - diff, 2)
            t2 = round(last_c - 2*diff, 2)
            t3 = round(last_c - 4*diff, 2)

        return jsonify({
            'symbol': symbol.upper(), 'signal': signal,
            'entry': round(last_c, 2), 'sl': round(last_tsl, 2),
            't1': t1, 't2': t2, 't3': t3,
            'in_long': bool(in_long), 'new_signal': bool(buy or sell)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/vpa/<symbol>')
def get_vpa(symbol):
    try:
        from vnstock.api.quote import Quote
        import numpy as np

        end   = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=400)).strftime('%Y-%m-%d')
        df    = Quote(symbol=symbol, source='VCI').history(start=start, end=end, interval='1D')
        if df is None or df.empty:
            return jsonify({'error': 'No data'}), 404

        o = df['open'].values.astype(float)
        h = df['high'].values.astype(float)
        l = df['low'].values.astype(float)
        c = df['close'].values.astype(float)
        v = df['volume'].values.astype(float)
        n = len(c)

        def ma(arr, p):
            r = np.full(len(arr), np.nan)
            for i in range(p-1, len(arr)):
                r[i] = np.mean(arr[i-p+1:i+1])
            return r

        def linreg_val(arr, p):
            """Linear regression value (last point of regression line)"""
            r = np.full(len(arr), np.nan)
            x = np.arange(p, dtype=float)
            for i in range(p-1, len(arr)):
                y = arr[i-p+1:i+1]
                slope, intercept = np.polyfit(x, y, 1)
                r[i] = slope * (p-1) + intercept
            return r

        def linreg_slope(arr, p):
            r = np.full(len(arr), np.nan)
            x = np.arange(p, dtype=float)
            for i in range(p-1, len(arr)):
                y = arr[i-p+1:i+1]
                slope, _ = np.polyfit(x, y, 1)
                r[i] = slope
            return r

        def ema_arr(arr, p):
            k = 2/(p+1)
            out = np.full(len(arr), np.nan)
            out[p-1] = np.mean(arr[:p])
            for i in range(p, len(arr)):
                out[i] = arr[i]*k + out[i-1]*(1-k)
            return out

        def atr_arr(p=14):
            tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
            tr = np.concatenate([[h[0]-l[0]], tr])
            return ma(tr, p)

        # ── VPA Basic ──
        vol_avg    = ma(v, 90)
        avg_spread = ma(h - l, 90)
        spread     = h - l
        wide_range  = spread > (1.5 * avg_spread)
        narrow_range = spread < (0.7 * avg_spread)
        up_bar   = np.concatenate([[False], c[1:] > c[:-1]])
        down_bar = np.concatenate([[False], c[1:] < c[:-1]])
        up_close   = c >= (spread * 0.7 + l)
        down_close = c <= (spread * 0.3 + l)
        mid_close  = (c > (spread*0.3+l)) & (c < (spread*0.7+l))
        above_close = c > (spread*0.5+l)
        below_close = c < (spread*0.5+l)
        high_volume = np.concatenate([[False,False], (v[2:]>v[1:-1])&(v[1:-1]>v[:-2])])
        low_volume  = np.concatenate([[False,False], (v[2:]<v[1:-1])&(v[2:]<v[:-2])])
        vb = (v > vol_avg) | np.concatenate([[False], v[1:] > v[:-1]])

        # ── Trend (LinReg based like AFL) ──
        j5 = ma(c, 5)
        # Short term: LinReg(20) + EMA(5) — like AFL p1=20, p2=5
        tl1 = linreg_val(j5, 20)   # Short trend line 1
        tl2 = ema_arr(np.where(np.isnan(tl1), 0, tl1), 5)  # Short trend line 2
        # Long term: LinReg(80) + EMA(20) — like AFL p3=80, p4=20
        tl3 = linreg_val(j5, 80)   # Long trend line 1
        tl4 = ema_arr(np.where(np.isnan(tl3), 0, tl3), 20)  # Long trend line 2

        # Trend direction (slope based)
        trend_short_slope = linreg_slope(j5, 3)
        trend_med_slope   = linreg_slope(j5, 10)
        trend_long_slope  = linreg_slope(j5, 40)

        # Short/Long trend status
        short_up = tl1 > tl2
        long_up  = tl3 > tl4

        # ── VPA Signals ──
        def hhv(arr, p): return np.array([max(arr[max(0,i-p+1):i+1]) for i in range(len(arr))])
        def llv(arr, p): return np.array([min(arr[max(0,i-p+1):i+1]) for i in range(len(arr))])

        fresh_hi = c > hhv(h, 5)
        fresh_lo = c < llv(l, 5)

        up_thrust      = wide_range & down_close & (trend_short_slope > 0) & np.concatenate([[False], h[1:]>h[:-1]])
        up_thrust_true = wide_range & down_close & long_up & np.concatenate([[False], h[1:]>h[:-1]])
        strength_down  = np.concatenate([[False], (v[1:]>v[:-1]) & down_bar[:-1] & up_bar[1:] & (up_close[1:]|mid_close[1:]) & (trend_short_slope[1:]<0) & (trend_med_slope[1:]<0)])
        strength_down1 = np.concatenate([[False], (trend_long_slope[1:]<0) & (v[1:]>vol_avg[1:]*1.5) & down_bar[:-1] & up_bar[1:] & (up_close[1:]|mid_close[1:]) & (trend_short_slope[1:]<0) & (trend_med_slope[1:]<0)])
        no_demand  = up_bar & narrow_range & low_volume & below_close
        no_supply  = down_bar & narrow_range & low_volume & below_close
        stop_vol   = (l == llv(l, 5)) & (up_close|mid_close) & (v > 1.5*vol_avg) & (trend_long_slope < 0)
        bull_bar   = vb & np.where(spread>0, (c-l)/spread>0.5, False) & up_bar
        bear_bar   = vb & down_close & down_bar & (spread > avg_spread)
        distribute = (v > 2*vol_avg) & down_close & up_bar & (trend_short_slope>0) & (trend_med_slope>0)
        low_vol_test = (l == llv(l, 5)) & up_close & low_volume
        effort_up   = np.concatenate([[False], (h[1:]>h[:-1])&(l[1:]>l[:-1])&(c[1:]>c[:-1])&np.where(spread[1:]>0,(c[1:]-l[1:])/spread[1:]>0.7,False)&(spread[1:]>avg_spread[1:])&(v[1:]>v[:-1])])
        effort_down = np.concatenate([[False], (h[1:]<h[:-1])&(l[1:]<l[:-1])&(c[1:]<c[:-1])&np.where(spread[1:]>0,(c[1:]-l[1:])/spread[1:]<0.25,False)&(spread[1:]>avg_spread[1:])&(v[1:]>v[:-1])])

        # ── Bar Colors ──
        bar_colors = []
        for i in range(n):
            if up_thrust_true[i]:                    bar_colors.append('upthrust_true')
            elif up_thrust[i]:                       bar_colors.append('upthrust')
            elif distribute[i]:                      bar_colors.append('distribute')
            elif low_vol_test[i]:                    bar_colors.append('test')
            elif bull_bar[i]:                        bar_colors.append('bull')
            elif bear_bar[i]:                        bar_colors.append('bear')
            elif no_demand[i]:                       bar_colors.append('no_demand')
            elif no_supply[i]:                       bar_colors.append('no_supply')
            elif effort_up[i]:                       bar_colors.append('effort_up')
            elif effort_down[i]:                     bar_colors.append('effort_down')
            elif strength_down1[i] or strength_down[i]: bar_colors.append('strength')
            elif stop_vol[i]:                        bar_colors.append('stop_vol')
            elif up_bar[i]:                          bar_colors.append('up')
            elif down_bar[i]:                        bar_colors.append('down')
            else:                                    bar_colors.append('neutral')

        # ── Supertrend ──
        atr_p, atr_m = 5, 2.0
        atr_v = atr_arr(atr_p)
        cp    = (h + l) / 2
        st_up   = np.full(n, np.nan)
        st_down = np.full(n, np.nan)
        phase   = 0
        for i in range(atr_p+1, n):
            bu = cp[i] + atr_m * atr_v[i]
            bl = cp[i] - atr_m * atr_v[i]
            if phase == 0:
                st_up[i] = cp[i]; st_down[i] = cp[i]
            if phase != 1 and not np.isnan(st_down[i-1]) and c[i] > st_down[i-1]:
                phase = 1; st_up[i] = bl; st_up[i-1] = st_down[i-1]
            if phase != -1 and not np.isnan(st_up[i-1]) and c[i] < st_up[i-1]:
                phase = -1; st_down[i] = bu; st_down[i-1] = st_up[i-1]
            if phase == 1 and not np.isnan(st_up[i-1]):
                st_up[i] = bl if bl > st_up[i-1] else st_up[i-1]
            if phase == -1 and not np.isnan(st_down[i-1]):
                st_down[i] = bu if bu < st_down[i-1] else st_down[i-1]

        # ── TWT Oscillator ──
        def ema_s(arr, n):
            k, out = 2/(n+1), [float(arr[0])]
            for i in range(1, len(arr)):
                out.append(float(arr[i])*k + out[-1]*(1-k))
            return np.array(out)

        def stdev_r(arr, n):
            out = np.zeros(len(arr))
            for i in range(n, len(arr)):
                out[i] = float(np.std(arr[i-n:i]))
            return out

        twt_n = 7
        ys1   = (o + h + l + c*9) / 4
        rk3   = ema_s(ys1, twt_n)
        rk4   = stdev_r(ys1, twt_n)
        rk4   = np.where(rk4 == 0, 0.001, rk4)
        rk5   = (ys1 - rk3) * 100 / rk4
        rk6   = ema_s(rk5, twt_n)
        twt_up   = ema_s(rk6, twt_n)
        twt_down = ema_s(twt_up, twt_n)
        twt_hist = twt_up - twt_down

        # ── S/R Lines ──
        sens = 6
        peaks, troughs = [], []
        for i in range(sens, n-sens):
            if all(h[i] >= h[i-j] for j in range(1,sens+1)) and all(h[i] >= h[i+j] for j in range(1,sens+1)):
                peaks.append({'idx':i,'val':float(h[i])})
            if all(l[i] <= l[i-j] for j in range(1,sens+1)) and all(l[i] <= l[i+j] for j in range(1,sens+1)):
                troughs.append({'idx':i,'val':float(l[i])})
        lc = float(c[-1])
        res_lines = sorted([p for p in peaks   if p['val']>lc], key=lambda x:x['val'])[:5]
        sup_lines = sorted([p for p in troughs if p['val']<lc], key=lambda x:-x['val'])[:5]

        # ── Fibo ──
        look = min(120, n)
        rh = float(np.max(h[-look:])); rl = float(np.min(l[-look:]))
        d = rh - rl
        fibo = {'0':rh,'23.6':rh-d*.236,'38.2':rh-d*.382,'50':rh-d*.5,'61.8':rh-d*.618,'78.6':rh-d*.786,'100':rl}

        # ── Signal Box — Pivot-based (giong AFL) ──
        # AFL: Buy = trough pivot, Sell = peak pivot
        # Them VPA filter: Buy phai co strength/test, Sell phai co weakness
        n_piv = 12  # lookback for pivot detection

        pivot_buy  = np.zeros(n, dtype=bool)
        pivot_sell = np.zeros(n, dtype=bool)

        for i in range(n_piv, n - n_piv):
            # Peak pivot = Sell signal
            if h[i] == max(h[max(0,i-n_piv):i+n_piv+1]):
                pivot_sell[i] = True
            # Trough pivot = Buy signal
            if l[i] == min(l[max(0,i-n_piv):i+n_piv+1]):
                pivot_buy[i] = True

        # ExRem: remove consecutive signals of same type
        buy_arr  = np.zeros(n, dtype=bool)
        sell_arr = np.zeros(n, dtype=bool)
        last_sig = None
        for i in range(n):
            if pivot_buy[i] and last_sig != 'buy':
                buy_arr[i] = True; last_sig = 'buy'
            elif pivot_sell[i] and last_sig != 'sell':
                sell_arr[i] = True; last_sig = 'sell'

        # VPA enhancement: also include VPA-based signals
        vpa_buy  = strength_down | strength_down1 | stop_vol | (low_vol_test & up_bar)
        vpa_sell = up_thrust_true | distribute

        # Combine: pivot signals + VPA signals
        combined_buy  = buy_arr  | vpa_buy
        combined_sell = sell_arr | vpa_sell

        # ExRem again on combined
        final_buy  = np.zeros(n, dtype=bool)
        final_sell = np.zeros(n, dtype=bool)
        last_sig2 = None
        for i in range(n):
            if combined_buy[i] and last_sig2 != 'buy':
                final_buy[i] = True; last_sig2 = 'buy'
            elif combined_sell[i] and last_sig2 != 'sell':
                final_sell[i] = True; last_sig2 = 'sell'

        lbi = int(np.where(final_buy)[0][-1])  if np.any(final_buy)  else -1
        lsi = int(np.where(final_sell)[0][-1]) if np.any(final_sell) else -1

        if lbi > lsi:
            stype='BUY'; sprice=float(c[lbi]); sidx=lbi
        elif lsi >= 0:
            stype='SELL'; sprice=float(c[lsi]); sidx=lsi
        else:
            stype='NEUTRAL'; sprice=lc; sidx=n-1

        # Current P/L
        cpl = lc-sprice if stype=='BUY' else sprice-lc if stype=='SELL' else 0

        # Targets (% based like AFL)
        entry = sprice
        t1 = round(entry*(1+0.005)  if stype=='BUY' else entry*(1-0.005),  2)
        t2 = round(entry*(1+0.0092) if stype=='BUY' else entry*(1-0.0112), 2)
        t3 = round(entry*(1+0.0179) if stype=='BUY' else entry*(1-0.0212), 2)

        # Buy/Sell arrays for plotting arrows (last 5 signals)
        buy_signals  = [{'idx':int(i),'price':round(float(c[i]),2)} for i in np.where(final_buy)[0][-5:]]
        sell_signals = [{'idx':int(i),'price':round(float(c[i]),2)} for i in np.where(final_sell)[0][-5:]]

        # ── VPA Description ──
        vpa_desc = []
        i = n-1
        if up_thrust_true[i]:    vpa_desc.append('Upthrust sau uptrend - Dau hieu yeu ro rang')
        elif up_thrust[i]:       vpa_desc.append('Upthrust - Dau hieu yeu')
        if distribute[i]:        vpa_desc.append('Phan phoi - Smart money dang ban')
        if no_demand[i]:         vpa_desc.append('Khong co cau - Dau hieu yeu')
        if no_supply[i]:         vpa_desc.append('Khong co cung - Dau hieu manh')
        if bull_bar[i]:          vpa_desc.append('Bull bar - Manh')
        if bear_bar[i]:          vpa_desc.append('Bear bar - Yeu')
        if stop_vol[i]:          vpa_desc.append('Stopping volume - Co the dao chieu tang')
        if low_vol_test[i]:      vpa_desc.append('Test cung thanh cong')
        if strength_down[i] or strength_down1[i]: vpa_desc.append('Suc manh quay lai sau down trend')
        if effort_up[i]:         vpa_desc.append('Effort to Rise - Bullish')
        if effort_down[i]:       vpa_desc.append('Effort to Fall - Bearish')
        if not vpa_desc:         vpa_desc.append('Thanh binh thuong')

        def safe(x):
            if hasattr(x, 'item'): return x.item()
            return float(x) if x is not None and not (isinstance(x, float) and (x != x)) else None

        return jsonify({
            'symbol': symbol.upper(), 'n': n,
            'bar_colors': bar_colors,
            # Short trend lines (green/red based on direction)
            'tl1': [None if (x!=x or x is None) else round(float(x),2) for x in tl1],
            'tl2': [None if (x!=x or x is None) else round(float(x),2) for x in tl2],
            'tl1_up': [bool(b) for b in short_up],
            # Long trend lines (blue/red based on direction)
            'tl3': [None if (x!=x or x is None) else round(float(x),2) for x in tl3],
            'tl4': [None if (x!=x or x is None) else round(float(x),2) for x in tl4],
            'tl3_up': [bool(b) for b in long_up],
            # Supertrend
            'st_up':   [None if (x!=x) else round(float(x),2) for x in st_up],
            'st_down': [None if (x!=x) else round(float(x),2) for x in st_down],
            # TWT
            'twt_up':   [round(float(x),4) for x in twt_up],
            'twt_down': [round(float(x),4) for x in twt_down],
            'twt_hist': [round(float(x),4) for x in twt_hist],
            # Levels
            'res_lines': res_lines, 'sup_lines': sup_lines,
            'fibo': {k: round(float(v_),2) for k,v_ in fibo.items()},
            # Trend status
            'trend_long':  'UP' if float(trend_long_slope[-1])  > 0 else 'DOWN',
            'trend_med':   'UP' if float(trend_med_slope[-1])   > 0 else 'DOWN',
            'trend_short': 'UP' if float(trend_short_slope[-1]) > 0 else 'DOWN',
            'short_trend_str': 'Uptrend' if bool(short_up[-1]) else 'Downtrend',
            'long_trend_str':  'Uptrend' if bool(long_up[-1])  else 'Downtrend',
            # Signal
            'signal': {
                'type': stype, 'price': round(sprice,2), 'bars_since': n-1-sidx,
                'current_pl': round(cpl,2),
                'tar1': round(t1,2), 'tar2': round(t2,2), 'tar3': round(t3,2),
            },
            'vpa_desc': vpa_desc,
            'buy_signals':  buy_signals,
            'sell_signals': sell_signals,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai', methods=['POST'])
def ai_analyze():
    try:
        import requests as req
        data     = request.get_json()
        prompt   = data.get('prompt', '')
        groq_key = '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'
        r = req.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization':'Bearer '+groq_key,'Content-Type':'application/json'},
            json={'model':'llama-3.3-70b-versatile','messages':[{'role':'user','content':prompt}],'max_tokens':1000},
            timeout=30
        )
        result = r.json()
        if 'choices' in result: reply = result['choices'][0]['message']['content']
        elif 'error' in result: reply = 'Loi: ' + result['error'].get('message','Unknown')
        else: reply = 'Loi: ' + str(result)
        return jsonify({'reply': reply})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

SCAN_SYMBOLS = list(set([
    "ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG",
    "MBB","MSN","MWG","NVL","PDR","PLX","PNJ","POW","SAB","SHB",
    "SSI","STB","TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM",
    "VPB","VRE","VND","DXG","KDH","LPB","OCB","REE","SJS","VCI",
    "AGG","AGR","AMD","ANV","ASM","BCG","BSR","BWE","CAV","CEO",
    "CII","CMG","CMX","CNG","CSV","CTD","CTI","CTR","DAG","DAT",
    "DBC","DCM","DGC","DGW","DHC","DIG","DPG","DPM","DPR","DRC",
    "EIB","ELC","EVE","EVF","FLC","GDT","GEG","GEX","GMD","HAG",
    "HAH","HAX","HBC","HCM","HDC","HDG","HHP","HHS","HID","HLD",
    "HMC","HNG","HPX","HQC","HTN","HVN","ICT","IDC","IDI","IJC",
    "IMP","IPA","IPH","ITC","IVS","KBC","KDC","KHG","KOS","KSB",
    "KTC","LCG","LDG","LEC","LGC","LHG","LIX","LSS","LTG","MCP",
    "MDG","MIG","MSB","MST","MTV","NAB","NAF","NAG","NBB","NCT",
    "NKG","NLG","NNC","NSC","NT2","NTL","NVB","NVT","OGC","OPC",
    "PAC","PAN","PC1","PCT","PET","PGC","PGD","PGI","PGV","PHC",
    "PHR","PIT","PJT","PLC","POM","PRC","PRE","PSH","PSI","PTC",
    "PTL","PVD","PVI","PVP","PVS","PVT","QCG","QNS","RAL","RDP",
    "RIC","SAF","SAM","SAV","SBT","SC5","SCD","SCR","SCS","SDG",
    "SDT","SEA","SGN","SGT","SHI","SHP","SIC","SII","SKG","SLS",
    "SMB","SMC","SPM","SRF","SSB","SSC","STC","STG","STK","STP",
    "SVD","SZC","SZG","TAC","TBC","TCH","TCL","TCM","TDG","TDH",
    "TDM","TDP","TDW","TEG","TIG","TIX","TLG","TLH","TMP","TMS",
    "TMT","TNA","TNT","TON","TPC","TRA","TRC","TSC","TTB","TTC",
    "TTF","TTP","TV2","TVD","TVS","TYA","UDC","UIC","VCA","VCF",
    "VCG","VCS","VDS","VFG","VGC","VGS","VGT","VHC","VHL","VID",
    "VIP","VIR","VIX","VMC","VMD","VNE","VNL","VNS","VNT","VOS",
    "VPG","VPH","VPI","VPS","VRC","VRG","VSC","VSG","VSH","VTB",
    "VTJ","VTO","VTS","YEG","NKG","VGI","HUT","DXS",
]))

@app.route('/api/scan')
def scan_stocks():
    try:
        from vnstock.api.quote import Quote
        from concurrent.futures import ThreadPoolExecutor, as_completed
        end   = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=120)).strftime('%Y-%m-%d')

        def ema(arr, n):
            k, out = 2/(n+1), [arr[0]]
            for i in range(1, len(arr)):
                out.append(arr[i]*k + out[-1]*(1-k))
            return out

        def sma(arr, n):
            return [None if i<n-1 else sum(arr[i-n+1:i+1])/n for i in range(len(arr))]

        def check(sym):
            try:
                df = Quote(symbol=sym, source='VCI').history(start=start, end=end, interval='1D')
                if df is None or df.empty or len(df) < 30: return None
                closes = list(df['close'].values.astype(float))
                vols   = list(df['volume'].values)
                ma20 = sma(closes, 20)
                if ma20[-1] is None or closes[-1] <= ma20[-1]: return None
                e12  = ema(closes, 12); e26 = ema(closes, 26)
                macd = [e12[i]-e26[i] for i in range(len(closes))]
                sig  = ema(macd, 9)
                if macd[-1] <= sig[-1]: return None
                pct = (closes[-1]-closes[-2])/closes[-2]*100
                vol = int(float(vols[-1]))
                if vol < 1000: vol = vol * 1000
                return {'symbol':sym,'close':round(closes[-1],2),'ma20':round(ma20[-1],2),
                        'pct':round(pct,2),'volume':vol,'macd':round(macd[-1],2),
                        'signal_line':round(sig[-1],2),'above_ma20_pct':round((closes[-1]-ma20[-1])/ma20[-1]*100,2)}
            except: return None

        results = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            for f in as_completed({ex.submit(check,s):s for s in SCAN_SYMBOLS}):
                r = f.result()
                if r: results.append(r)
        results.sort(key=lambda x: x['above_ma20_pct'], reverse=True)
        return jsonify({'count':len(results),'total_scanned':len(SCAN_SYMBOLS),'results':results})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ── MARKET BREADTH ───────────────────────────────────────────────────────────
# FireAnt token - set qua environment variable tren Render
# Local: tao file .env hoac thay truc tiep o day
FIREANT_TOKEN = os.environ.get('FIREANT_TOKEN', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IkdYdExONzViZlZQakdvNERWdjV4QkRITHpnSSIsImtpZCI6IkdYdExONzViZlZQakdvNERWdjV4QkRITHpnSSJ9.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmZpcmVhbnQudm4iLCJhdWQiOiJodHRwczovL2FjY291bnRzLmZpcmVhbnQudm4vcmVzb3VyY2VzIiwiZXhwIjoxODg5NjIyNTMwLCJuYmYiOjE1ODk2MjI1MzAsImNsaWVudF9pZCI6ImZpcmVhbnQudHJhZGVzdGF0aW9uIiwic2NvcGUiOlsiYWNhZGVteS1yZWFkIiwiYWNhZGVteS13cml0ZSIsImFjY291bnRzLXJlYWQiLCJhY2NvdW50cy13cml0ZSIsImJsb2ctcmVhZCIsImNvbXBhbmllcy1yZWFkIiwiZmluYW5jZS1yZWFkIiwiaW5kaXZpZHVhbHMtcmVhZCIsImludmVzdG9wZWRpYS1yZWFkIiwib3JkZXJzLXJlYWQiLCJvcmRlcnMtd3JpdGUiLCJwb3N0cy1yZWFkIiwicG9zdHMtd3JpdGUiLCJzZWFyY2giLCJzeW1ib2xzLXJlYWQiLCJ1c2VyLWRhdGEtcmVhZCIsInVzZXItZGF0YS13cml0ZSIsInVzZXJzLXJlYWQiXSwianRpIjoiMjYxYTZhYWQ2MTQ5Njk1ZmJiYzcwODM5MjM0Njc1NWQifQ.dA5-HVzWv-BRfEiAd24uNBiBxASO-PAyWeWESovZm_hj4aXMAZA1-bWNZeXt88dqogo18AwpDQ-h6gefLPdZSFrG5umC1dVWaeYvUnGm62g4XS29fj6p01dhKNNqrsu5KrhnhdnKYVv9VdmbmqDfWR8wDgglk5cJFqalzq6dJWJInFQEPmUs9BW_Zs8tQDn-i5r4tYq2U8vCdqptXoM7YgPllXaPVDeccC9QNu2Xlp9WUvoROzoQXg25lFub1IYkTrM66gJ6t9fJRZToewCt495WNEOQFa_rwLCZ1QwzvL0iYkONHS_jZ0BOhBCdW9dWSawD6iF1SIQaFROvMDH1rg')

BREADTH_SYMBOLS = list(set([
    "ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG",
    "MBB","MSN","MWG","NVL","PDR","PLX","PNJ","POW","SAB","SHB",
    "SSI","STB","TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM",
    "VPB","VRE","VND","DXG","KDH","LPB","OCB","REE","SJS","VCI",
    "AGG","AGR","AMD","ANV","ASM","BCG","BSR","BWE","CAV","CEO",
    "CII","CMG","CMX","CNG","CSV","CTD","CTI","CTR","DAG","DAT",
    "DBC","DCM","DGC","DGW","DHC","DIG","DPG","DPM","DPR","DRC",
    "EIB","ELC","EVE","EVF","FLC","GDT","GEG","GEX","GMD","HAG",
    "HAH","HAX","HBC","HCM","HDC","HDG","HHP","HHS","HID","HLD",
    "HMC","HNG","HPX","HQC","HTN","HVN","ICT","IDC","IDI","IJC",
    "IMP","IPA","IPH","ITC","IVS","KBC","KDC","KHG","KOS","KSB",
    "KTC","LCG","LDG","LEC","LGC","LHG","LIX","LSS","LTG","MCP",
    "MDG","MIG","MSB","MST","MTV","NAB","NAF","NAG","NBB","NCT",
    "NKG","NLG","NNC","NSC","NT2","NTL","NVB","NVT","OGC","OPC",
    "PAC","PAN","PC1","PCT","PET","PGC","PGD","PGI","PGV","PHC",
    "PHR","PIT","PJT","PLC","POM","PRC","PRE","PSH","PSI","PTC",
    "PTL","PVD","PVI","PVP","PVS","PVT","QCG","QNS","RAL","RDP",
    "RIC","SAF","SAM","SAV","SBT","SC5","SCD","SCR","SCS","SDG",
    "SDT","SEA","SGN","SGT","SHI","SHP","SIC","SII","SKG","SLS",
    "SMB","SMC","SPM","SRF","SSB","SSC","STC","STG","STK","STP",
    "SVD","SZC","SZG","TAC","TBC","TCH","TCL","TCM","TDG","TDH",
    "TDM","TDP","TDW","TEG","TIG","TIX","TLG","TLH","TMP","TMS",
    "TMT","TNA","TNT","TON","TPC","TRA","TRC","TSC","TTB","TTC",
    "TTF","TTP","TV2","TVD","TVS","TYA","UDC","UIC","VCA","VCF",
    "VCG","VCS","VDS","VFG","VGC","VGS","VGT","VHC","VHL","VID",
    "VIP","VIR","VIX","VMC","VMD","VNE","VNL","VNS","VNT","VOS",
    "VPG","VPH","VPI","VPS","VRC","VRG","VSC","VSG","VSH","VTB",
    "VTJ","VTO","VTS","YEG","NKG","VGI","HUT","DXS",
]))

@app.route('/api/breadth')
def get_breadth():
    try:
        import requests as req
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from collections import defaultdict

        days = int(request.args.get('days', 60))
        end_dt   = datetime.today()
        start_dt = end_dt - timedelta(days=days+60)
        end_str   = end_dt.strftime('%Y-%m-%d')
        start_str = start_dt.strftime('%Y-%m-%d')

        headers = {
            'Authorization': 'Bearer ' + FIREANT_TOKEN,
            'Content-Type': 'application/json'
        }

        def sma(arr, n):
            result = []
            for i in range(len(arr)):
                if i < n-1: result.append(None)
                else: result.append(sum(arr[i-n+1:i+1]) / n)
            return result

        def check_sym_fireant(sym):
            try:
                url = f'https://restv2.fireant.vn/symbols/{sym}/historical-quotes'
                params = {
                    'startDate': start_str,
                    'endDate':   end_str,
                    'offset': 0,
                    'limit': 200,
                    'type': 1
                }
                r = req.get(url, headers=headers, params=params, timeout=10)
                if r.status_code != 200: return None
                data = r.json()
                if not data or len(data) < 25: return None

                # FireAnt returns newest first, reverse
                data = list(reversed(data))
                closes = [float(d['priceClose']) for d in data]
                dates  = [str(d['date'])[:10] for d in data]
                ma20 = sma(closes, 20)
                ma50 = sma(closes, 50)

                daily = []
                for i in range(len(closes)):
                    if ma20[i] is None or ma50[i] is None: continue
                    chg = (closes[i]-closes[i-1])/closes[i-1]*100 if i > 0 else 0
                    daily.append({
                        'date': dates[i],
                        'above_ma20': closes[i] > ma20[i],
                        'above_ma50': closes[i] > ma50[i],
                        'up': chg > 0.5,
                        'down': chg < -0.5,
                    })
                return daily
            except: return None

        all_data = {}
        with ThreadPoolExecutor(max_workers=30) as ex:
            futures = {ex.submit(check_sym_fireant, s): s for s in BREADTH_SYMBOLS}
            for f in as_completed(futures):
                r = f.result()
                if r: all_data[futures[f]] = r

        if not all_data:
            return jsonify({'error': 'No data from FireAnt'}), 500

        date_agg = defaultdict(lambda: {'up':0,'down':0,'flat':0,'above_ma20':0,'below_ma20':0,'above_ma50':0,'below_ma50':0,'total':0})
        for sym, daily in all_data.items():
            for d in daily:
                dt = d['date']
                date_agg[dt]['total'] += 1
                if d['up']:        date_agg[dt]['up']   += 1
                elif d['down']:    date_agg[dt]['down']  += 1
                else:              date_agg[dt]['flat']  += 1
                if d['above_ma20']: date_agg[dt]['above_ma20'] += 1
                else:               date_agg[dt]['below_ma20'] += 1
                if d['above_ma50']: date_agg[dt]['above_ma50'] += 1
                else:               date_agg[dt]['below_ma50'] += 1

        sorted_dates = sorted(date_agg.keys())[-days:]
        rdates, rup, rdown, rad, rma20, rma50, rtotal = [],[],[],[],[],[],[]
        for dt in sorted_dates:
            a = date_agg[dt]
            if a['total'] < 10: continue
            rdates.append(dt); rup.append(a['up']); rdown.append(a['down'])
            rad.append(a['up']-a['down'])
            rma20.append(round(a['above_ma20']/a['total']*100,1))
            rma50.append(round(a['above_ma50']/a['total']*100,1))
            rtotal.append(a['total'])

        # VNI overlay via FireAnt
        vni = [None]*len(rdates)
        try:
            r = req.get('https://restv2.fireant.vn/symbols/VNINDEX/historical-quotes',
                        headers=headers,
                        params={'startDate':start_str,'endDate':end_str,'offset':0,'limit':200,'type':1},
                        timeout=10)
            if r.status_code == 200:
                vni_data = list(reversed(r.json()))
                vm = {str(d['date'])[:10]: float(d['priceClose']) for d in vni_data}
                vni = [vm.get(dt) for dt in rdates]
        except: pass

        latest = {}
        if rdates:
            latest = {'date':rdates[-1],'up':rup[-1],'down':rdown[-1],'ad':rad[-1],
                      'ma20_pct':rma20[-1],'ma50_pct':rma50[-1],'total':rtotal[-1],
                      'symbols_scanned':len(all_data)}

        return jsonify({'dates':rdates,'up':rup,'down':rdown,'ad':rad,
                        'ma20_pct':rma20,'ma50_pct':rma50,'total':rtotal,
                        'vni':vni,'latest':latest})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── SECTOR HEATMAP ──────────────────────────────────────────────────────────
SECTORS = {
    'Ngan hang': ['ACB','BID','CTG','EIB','HDB','LPB','MBB','MSB','NAB','NVB','OCB','SHB','SSB','STB','TCB','TPB','VCB','VIB','VPB'],
    'Bat dong san': ['BCG','CEO','CII','DIG','DXG','DXS','GEX','HDC','HDG','HQC','IJC','KBC','KDH','KHG','LDG','LGC','NLG','NVL','NVT','PDR','PHR','QCG','SCR','SJS','SZC','TDH','VHM','VIC','VRE'],
    'Chung khoan': ['BSR','CTS','FTS','HBS','HCM','MBS','ORS','PSI','SBS','SSI','TVS','VCI','VDS','VIX','VND','VPS'],
    'Thep': ['HPG','HSG','NKG','POM','SMC','TLH','TVN'],
    'Dau khi': ['BSR','CNG','GAS','OIL','PGC','PGD','PGS','PLX','POW','PVC','PVD','PVI','PVP','PVS','PVT'],
    'Hang tieu dung': ['MCH','MSN','MWG','PNJ','SAB','VNM'],
    'Cong nghe': ['CMG','ELC','FPT','ICT','SAM','ST8','VGI'],
    'Xay dung': ['CTD','CTI','CTR','FCN','HBC','HTN','LCG','PC1','REE','SC5','VCG'],
    'Thuc pham': ['ANV','DBC','HAG','HNG','IDI','LSS','MSN','NAF','PAN','QNS','SAF','TAC','VNM'],
    'Van tai': ['GMD','HAH','HHR','HVN','PJT','SCS','SGN','TMS','VIP','VOS','VSC'],
    'Dien': ['GEG','NT2','POW','REE','SBA','TBC','TV2','VSH'],
    'Hoa chat': ['CSV','DCM','DGC','DPM','LAS','PAC','PHC','PLC','SFG'],
    'Det may': ['EVE','GIL','MSH','STK','TCM','TNG','VGT'],
    'Duoc pham': ['DBD','DHT','IMP','OPC','TRA','VMD'],
}

@app.route('/api/sector')
def get_sector():
    try:
        import requests as req
        from concurrent.futures import ThreadPoolExecutor, as_completed

        headers = {'Authorization': 'Bearer ' + FIREANT_TOKEN}

        def get_price(sym):
            try:
                url = f'https://restv2.fireant.vn/symbols/{sym}/historical-quotes'
                r = req.get(url, headers=headers,
                           params={'startDate': (datetime.today()-timedelta(days=5)).strftime('%Y-%m-%d'),
                                   'endDate': datetime.today().strftime('%Y-%m-%d'),
                                   'offset':0,'limit':5,'type':1},
                           timeout=8)
                if r.status_code != 200: return None
                data = r.json()
                if not data or len(data) < 2: return None
                data = list(reversed(data))
                last  = data[-1]
                prev  = data[-2]
                pct = (last['priceClose'] - prev['priceClose']) / prev['priceClose'] * 100
                return {'sym': sym, 'close': last['priceClose'], 'pct': round(pct, 2),
                        'vol': last.get('dealVolume', 0)}
            except: return None

        # Get all symbols
        all_syms = list(set([s for syms in SECTORS.values() for s in syms]))
        results = {}
        with ThreadPoolExecutor(max_workers=30) as ex:
            futures = {ex.submit(get_price, s): s for s in all_syms}
            for f in as_completed(futures):
                r = f.result()
                if r: results[r['sym']] = r

        # Build sector data
        sector_data = []
        for sector, syms in SECTORS.items():
            stocks = []
            total_pct = 0
            count = 0
            for sym in syms:
                if sym in results:
                    stocks.append(results[sym])
                    total_pct += results[sym]['pct']
                    count += 1
            if count > 0:
                sector_data.append({
                    'name': sector,
                    'avg_pct': round(total_pct / count, 2),
                    'stocks': sorted(stocks, key=lambda x: x['pct'], reverse=True),
                    'count': count,
                    'up': sum(1 for s in stocks if s['pct'] > 0),
                    'down': sum(1 for s in stocks if s['pct'] < 0),
                })

        sector_data.sort(key=lambda x: x['avg_pct'], reverse=True)
        return jsonify({'sectors': sector_data, 'total_stocks': len(results)})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ── BACKTEST ─────────────────────────────────────────────────────────────────
@app.route('/api/backtest/<symbol>')
def run_backtest(symbol):
    try:
        from vnstock.api.quote import Quote
        import numpy as np

        strategy = request.args.get('strategy', 'both')
        days = int(request.args.get('days', 365))

        end   = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=days+60)).strftime('%Y-%m-%d')

        df = Quote(symbol=symbol, source='VCI').history(start=start, end=end, interval='1D')
        if df is None or df.empty or len(df) < 60:
            return jsonify({'error': 'Khong du du lieu'}), 404

        o = df['open'].values.astype(float)
        h = df['high'].values.astype(float)
        l = df['low'].values.astype(float)
        c = df['close'].values.astype(float)
        v = df['volume'].values.astype(float)
        dates = [str(df.iloc[i].get('time', df.iloc[i].get('date', '')))[:10] for i in range(len(df))]
        n = len(c)

        def ma(arr, p):
            r = np.full(len(arr), np.nan)
            for i in range(p-1, len(arr)):
                r[i] = np.mean(arr[i-p+1:i+1])
            return r

        def ema_fn(arr, p):
            k = 2/(p+1)
            out = np.full(len(arr), np.nan)
            out[p-1] = np.mean(arr[:p])
            for i in range(p, len(arr)):
                out[i] = arr[i]*k + out[i-1]*(1-k)
            return out

        def run_trades(buy_signals, sell_signals, closes, dates, name):
            """Run through signals and calculate trades"""
            trades = []
            in_trade = False
            entry_price = 0
            entry_date = ''
            entry_idx = 0

            for i in range(1, n):
                if not in_trade and buy_signals[i]:
                    in_trade = True
                    entry_price = closes[i]
                    entry_date = dates[i]
                    entry_idx = i
                elif in_trade and (sell_signals[i] or i == n-1):
                    exit_price = closes[i]
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                    hold_days = i - entry_idx
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': dates[i],
                        'entry': round(float(entry_price), 2),
                        'exit': round(float(exit_price), 2),
                        'pnl_pct': round(float(pnl_pct), 2),
                        'hold_days': int(hold_days),
                        'win': bool(pnl_pct > 0),
                        'strategy': name,
                    })
                    in_trade = False

            return trades

        results = {}

        # ── Strategy 1: VPA Signals ──
        if strategy in ['vpa', 'both']:
            vol_avg = ma(v, 20)
            avg_spread = ma(h - l, 20)
            spread = h - l
            up_bar = np.concatenate([[False], c[1:] > c[:-1]])
            down_bar = np.concatenate([[False], c[1:] < c[:-1]])
            up_close = c >= (spread * 0.6 + l)
            down_close = c <= (spread * 0.4 + l)
            low_volume = np.concatenate([[False,False], (v[2:]<v[1:-1])&(v[2:]<v[:-2])])
            wide_range = spread > (1.5 * avg_spread)
            narrow_range = spread < (0.7 * avg_spread)

            # Buy signals: strength, no_supply, stop_vol, bull_bar
            strength = np.concatenate([[False], (v[1:]>v[:-1]) & down_bar[:-1] & up_bar[1:] & up_close[1:]])
            no_supply = down_bar & narrow_range & low_volume & (c < (spread*0.5+l))
            stop_vol = (c > (spread*0.5+l)) & (v > 1.5*np.where(np.isnan(vol_avg), 1, vol_avg))
            bull_bar = np.where(np.isnan(vol_avg), False, v > vol_avg) & up_close & up_bar & wide_range

            vpa_buy = strength | no_supply | stop_vol | bull_bar

            # Sell signals: upthrust, distribute
            up_thrust = wide_range & down_close & np.concatenate([[False], h[1:]>h[:-1]])
            distribute = (v > 1.5*np.where(np.isnan(vol_avg), 1, vol_avg)) & down_close & up_bar

            vpa_sell = up_thrust | distribute

            vpa_trades = run_trades(vpa_buy, vpa_sell, c, dates, 'VPA')
            results['vpa'] = vpa_trades

        # ── Strategy 2: MA Cross ──
        if strategy in ['ma', 'both']:
            ma20 = ma(c, 20)
            ma50 = ma(c, 50)
            e12 = ema_fn(c, 12)
            e26 = ema_fn(c, 26)
            macd = e12 - e26
            signal = ema_fn(np.where(np.isnan(macd), 0, macd), 9)

            ma_buy  = np.zeros(n, dtype=bool)
            ma_sell = np.zeros(n, dtype=bool)

            for i in range(1, n):
                if np.isnan(ma20[i]) or np.isnan(ma50[i]): continue
                # Buy: MA20 cross above MA50 + MACD > signal
                if (ma20[i] > ma50[i] and ma20[i-1] <= ma50[i-1] and
                    not np.isnan(macd[i]) and macd[i] > signal[i]):
                    ma_buy[i] = True
                # Sell: MA20 cross below MA50
                if ma20[i] < ma50[i] and ma20[i-1] >= ma50[i-1]:
                    ma_sell[i] = True

            ma_trades = run_trades(ma_buy, ma_sell, c, dates, 'MA Cross')
            results['ma'] = ma_trades

        # ── Combine and calculate stats ──
        def calc_stats(trades):
            if not trades: return {'trades': [], 'total': 0, 'win_rate': 0, 'total_pnl': 0, 'avg_pnl': 0, 'max_win': 0, 'max_loss': 0, 'avg_hold': 0, 'equity': []}
            total = len(trades)
            wins  = sum(1 for t in trades if t['win'])
            pnls  = [t['pnl_pct'] for t in trades]
            # Equity curve (compound)
            equity = [100.0]
            for t in trades:
                equity.append(round(equity[-1] * (1 + t['pnl_pct']/100), 2))
            max_dd = 0
            peak = equity[0]
            for e in equity:
                if e > peak: peak = e
                dd = (peak - e) / peak * 100
                if dd > max_dd: max_dd = dd
            return {
                'trades': trades,
                'total': total,
                'win_rate': round(wins/total*100, 1),
                'total_pnl': round(sum(pnls), 2),
                'avg_pnl': round(sum(pnls)/total, 2),
                'max_win': round(max(pnls), 2),
                'max_loss': round(min(pnls), 2),
                'avg_hold': round(sum(t['hold_days'] for t in trades)/total, 1),
                'max_drawdown': round(max_dd, 2),
                'equity': equity,
            }

        response = {
            'symbol': symbol.upper(),
            'days': days,
            'price_data': [{'date': dates[i], 'close': round(float(c[i]),2)} for i in range(n)],
        }
        if 'vpa' in results:
            response['vpa'] = calc_stats(results['vpa'])
        if 'ma' in results:
            response['ma'] = calc_stats(results['ma'])

        return jsonify(response)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500



# ── VPA SIGNAL SCANNER ───────────────────────────────────────────────────────
@app.route('/api/vpascan')
def vpa_scan():
    try:
        import requests as req
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import numpy as np

        end   = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=200)).strftime('%Y-%m-%d')

        headers = {'Authorization': 'Bearer ' + FIREANT_TOKEN}

        def sma(arr, p):
            r = np.full(len(arr), np.nan)
            for i in range(p-1, len(arr)):
                r[i] = np.mean(arr[i-p+1:i+1])
            return r

        def check_vpa(sym):
            try:
                url = f'https://restv2.fireant.vn/symbols/{sym}/historical-quotes'
                r = req.get(url, headers=headers,
                    params={'startDate':start,'endDate':end,'offset':0,'limit':200,'type':1},
                    timeout=10)
                if r.status_code != 200: return None
                data = list(reversed(r.json()))
                if not data or len(data) < 25: return None

                o = np.array([d['priceOpen']  for d in data], dtype=float)
                h = np.array([d['priceHigh']  for d in data], dtype=float)
                l = np.array([d['priceLow']   for d in data], dtype=float)
                c = np.array([d['priceClose'] for d in data], dtype=float)
                v = np.array([d.get('dealVolume', d.get('totalVolume',0)) for d in data], dtype=float)
                n = len(c)

                vol_avg    = sma(v, 20)
                avg_spread = sma(h - l, 20)
                spread     = h - l

                def vavg(i): return vol_avg[i] if not np.isnan(vol_avg[i]) else np.mean(v[max(0,i-5):i+1])
                def savg(i): return avg_spread[i] if not np.isnan(avg_spread[i]) else np.mean(spread[max(0,i-5):i+1])

                i = n - 1
                if i < 5: return None

                signals = []
                # Check last 3 bars
                for idx in range(max(5, n-3), n):
                    ii = idx
                    va = vavg(ii); sa = savg(ii)
                    if va == 0: continue

                    # BUY
                    if c[ii-1]<c[ii-2] and c[ii]>c[ii-1] and v[ii]>va*0.8 and c[ii]>(l[ii]+spread[ii]*0.5):
                        if 'Strength' not in signals: signals.append('Strength')
                    if c[ii]<c[ii-1] and spread[ii]<sa*0.9 and v[ii]<va*0.9 and c[ii]>(l[ii]+spread[ii]*0.3):
                        if 'NoSupply' not in signals: signals.append('NoSupply')
                    if v[ii]>va*1.2 and c[ii]>(l[ii]+spread[ii]*0.5) and l[ii]<=min(l[max(0,ii-5):ii+1]):
                        if 'StopVol' not in signals: signals.append('StopVol')
                    if c[ii]>c[ii-1] and spread[ii]>sa*0.7 and v[ii]>va*0.6 and c[ii]>(l[ii]+spread[ii]*0.6):
                        if 'Bull' not in signals: signals.append('Bull')
                    if v[ii]<va*0.8 and l[ii]<=min(l[max(0,ii-3):ii]) and c[ii]>(l[ii]+spread[ii]*0.5):
                        if 'Test' not in signals: signals.append('Test')
                    # SELL
                    if spread[ii]>sa*0.7 and c[ii]<(l[ii]+spread[ii]*0.5) and h[ii]>=max(h[max(0,ii-3):ii]):
                        if 'UpThrust' not in signals: signals.append('UpThrust')
                    if v[ii]>va*1.1 and c[ii]>c[ii-1] and c[ii]<(l[ii]+spread[ii]*0.5):
                        if 'Distribute' not in signals: signals.append('Distribute')
                    if c[ii]>c[ii-1] and spread[ii]<sa*0.9 and v[ii]<va*0.8:
                        if 'NoDemand' not in signals: signals.append('NoDemand')

                if not signals: return None

                buy_set  = {'Strength','NoSupply','StopVol','Bull','Test'}
                sell_set = {'UpThrust','Distribute','NoDemand'}
                has_buy  = any(s in buy_set  for s in signals)
                has_sell = any(s in sell_set for s in signals)

                if has_buy and not has_sell:   sig_type = 'BUY'
                elif has_sell and not has_buy: sig_type = 'SELL'
                else:                          sig_type = 'MIXED'

                # Win rate
                wins, total_bt = 0, 0
                for j in range(max(5, n-60), n-5):
                    entry = c[j]
                    if sig_type == 'BUY':
                        if max(c[j+1:j+6]) > entry*1.015: wins += 1
                        total_bt += 1
                    elif sig_type == 'SELL':
                        if min(c[j+1:j+6]) < entry*0.985: wins += 1
                        total_bt += 1

                win_rate = round(wins/total_bt*100,1) if total_bt>0 else 50
                pct = (c[-1]-c[-2])/c[-2]*100 if n>1 else 0
                ma20 = sma(c,20); ma50 = sma(c,50)
                trend = 'UP' if (not np.isnan(ma20[-1]) and not np.isnan(ma50[-1]) and ma20[-1]>ma50[-1]) else 'DOWN'

                return {
                    'sym': sym, 'signal': sig_type, 'signals': signals,
                    'close': round(float(c[-1]),2), 'pct': round(float(pct),2),
                    'volume': int(float(v[-1])), 'win_rate': win_rate,
                    'total_bt': total_bt, 'trend': trend,
                }
            except: return None

        results = []
        with ThreadPoolExecutor(max_workers=30) as ex:
            futures = {ex.submit(check_vpa, s): s for s in BREADTH_SYMBOLS}
            for f in as_completed(futures):
                r = f.result()
                if r: results.append(r)

        order = {'BUY':0,'SELL':1,'MIXED':2}
        
        # Quality filters
        filtered = []
        for r in results:
            # Win rate filter
            if r['win_rate'] < 52: continue
            # Trend alignment: BUY should be in uptrend, SELL in downtrend
            if r['signal'] == 'BUY'  and r['trend'] == 'DOWN': continue
            if r['signal'] == 'SELL' and r['trend'] == 'UP':   continue
            filtered.append(r)
        
        filtered.sort(key=lambda x: (order.get(x['signal'],3), -x['win_rate']))

        return jsonify({
            'count': len(filtered),
            'total_scanned': len(BREADTH_SYMBOLS),
            'total_found': len(results),
            'results': filtered
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("  QuyStock Pro — VPA Edition")
    print(f"  http://localhost:{port}")
    print("="*50)
    app.run(host='0.0.0.0', port=port, debug=False)
 
