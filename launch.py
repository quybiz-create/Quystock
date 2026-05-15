import subprocess
import webbrowser
import time
import sys
import os
import threading
import socket

def is_port_open(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except:
        return False

def open_browser():
    for i in range(25):
        time.sleep(1)
        if is_port_open(5000):
            webbrowser.open('http://localhost:5000')
            return

def run_flask():
    # Import va chay Flask truc tiep
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(base_dir)
    sys.path.insert(0, base_dir)
    
    # Chay server trong cung process
    from flask import Flask, jsonify, request, send_from_directory
    from flask_cors import CORS
    from datetime import datetime, timedelta
    import traceback
    
    app = Flask(__name__)
    CORS(app)

    @app.route('/')
    def index():
        return send_from_directory(base_dir, 'stock_dashboard.html')

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
                    'open':   round(float(row['open']),  0),
                    'high':   round(float(row['high']),  0),
                    'low':    round(float(row['low']),   0),
                    'close':  round(float(row['close']), 0),
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

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    if is_port_open(5000):
        webbrowser.open('http://localhost:5000')
        sys.exit(0)

    t = threading.Thread(target=open_browser)
    t.daemon = True
    t.start()

    run_flask()