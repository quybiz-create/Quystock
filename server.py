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
            'symbol':       symbol.upper(),
            'pe':           getval('p_e'),
            'pb':           getval('p_b'),
            'eps':          getval('trailing_eps'),
            'roe':          getval('roe',  pct=True),
            'roa':          getval('roa',  pct=True),
            'gross_margin': getval('gross_profit_margin', pct=True),
            'net_margin':   getval('net_profit_margin',   pct=True),
            'debt_equity':  getval('debt_to_equity'),
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
            'symbol':    symbol.upper(),
            'shortName': str(row.get('shortName', '')),
            'exchange':  str(row.get('exchange',  '')),
            'industry':  str(row.get('industryName', '')),
            'website':   str(row.get('website',   '')),
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
            t1 = round(last_c + diff,   2)
            t2 = round(last_c + 2*diff, 2)
            t3 = round(last_c + 4*diff, 2)
        else:
            signal = 'SELL' if sell else 'SHORT'
            t1 = round(last_c - diff,   2)
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

@app.route('/api/ai', methods=['POST'])
def ai_analyze():
    try:
        import requests as req
        data     = request.get_json()
        prompt   = data.get('prompt', '')
        groq_key = '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'
        r = req.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': 'Bearer '+groq_key, 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile',
                  'messages': [{'role':'user','content':prompt}], 'max_tokens': 1000},
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

SCAN_SYMBOLS = list(set([
    "ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG",
    "MBB","MSN","MWG","NVL","PDR","PLX","PNJ","POW","SAB","SHB",
    "SSI","STB","TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM",
    "VPB","VRE","VND","DXG","KDH","LPB","OCB","REE","SJS","VCI",
    "AGG","AGR","AMD","ANV","ASM","BCG","BSR","BWE","CAV","CEO",
    "CII","CMG","CMX","CNG","CSV","CTD","CTI","CTR","CTS","DAG",
    "DAT","DBC","DCM","DGC","DGW","DHC","DIG","DPG","DPM","DPR",
    "DRC","EIB","ELC","EVE","EVF","FLC","GDT","GEG","GEX","GMD",
    "HAG","HAH","HAX","HBC","HCM","HDC","HDG","HHP","HHS","HID",
    "HLD","HMC","HNG","HPX","HQC","HTN","HVN","ICT","IDC","IDI",
    "IJC","IMP","IPA","IPH","ITC","IVS","KBC","KDC","KHG","KOS",
    "KSB","KTC","LCG","LDG","LEC","LGC","LHG","LIX","LSS","LTG",
    "MCP","MDG","MIG","MSB","MST","MTV","NAB","NAF","NAG","NBB",
    "NCT","NKG","NLG","NNC","NSC","NT2","NTL","NVB","NVT","OGC",
    "OPC","PAC","PAN","PC1","PCT","PET","PGC","PGD","PGI","PGV",
    "PHC","PHR","PIT","PJT","PLC","POM","PRC","PRE","PSH","PSI",
    "PTC","PTL","PVD","PVI","PVP","PVS","PVT","QCG","QNS","RAL",
    "RDP","RIC","SAF","SAM","SAV","SBT","SC5","SCD","SCR","SCS",
    "SDG","SDT","SEA","SGN","SGT","SHI","SHP","SIC","SII","SKG",
    "SLS","SMB","SMC","SPM","SRF","SSB","SSC","STC","STG","STK",
    "STP","SVD","SZC","SZG","TAC","TBC","TCH","TCL","TCM","TDG",
    "TDH","TDM","TDP","TDW","TEG","TIG","TIX","TLG","TLH","TMP",
    "TMS","TMT","TNA","TNT","TON","TPC","TRA","TRC","TSC","TTB",
    "TTC","TTF","TTP","TV2","TVD","TVS","TYA","UDC","UIC","VCA",
    "VCF","VCG","VCS","VDS","VFG","VGC","VGS","VGT","VHC","VHL",
    "VID","VIP","VIR","VIX","VMC","VMD","VNE","VNL","VNS","VNT",
    "VOS","VPG","VPH","VPI","VPS","VRC","VRG","VSC","VSG","VSH",
    "VTB","VTJ","VTO","VTS","YEG","NKG","VGI","HUT","DXS",
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
                if df is None or df.empty or len(df) < 30:
                    return None
                closes = list(df['close'].values.astype(float))
                vols   = list(df['volume'].values)

                ma20 = sma(closes, 20)
                if ma20[-1] is None or closes[-1] <= ma20[-1]:
                    return None

                e12  = ema(closes, 12)
                e26  = ema(closes, 26)
                macd = [e12[i] - e26[i] for i in range(len(closes))]
                sig  = ema(macd, 9)
                if macd[-1] <= sig[-1]:
                    return None

                pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                vol = int(float(vols[-1]))
                if vol < 1000: vol = vol * 1000

                return {
                    'symbol':         sym,
                    'close':          round(closes[-1], 2),
                    'ma20':           round(ma20[-1],   2),
                    'pct':            round(pct, 2),
                    'volume':         vol,
                    'macd':           round(macd[-1], 2),
                    'signal_line':    round(sig[-1],  2),
                    'above_ma20_pct': round((closes[-1]-ma20[-1])/ma20[-1]*100, 2)
                }
            except:
                return None

        results = []
        with ThreadPoolExecutor(max_workers=20) as ex:
            for f in as_completed({ex.submit(check, s): s for s in SCAN_SYMBOLS}):
                r = f.result()
                if r: results.append(r)

        results.sort(key=lambda x: x['above_ma20_pct'], reverse=True)
        return jsonify({'count': len(results), 'total_scanned': len(SCAN_SYMBOLS), 'results': results})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("  QuyStock Pro — Bloomberg Edition")
    print(f"  http://localhost:{port}")
    print("="*50)
    app.run(host='0.0.0.0', port=port, debug=False)
 
