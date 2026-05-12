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

        def ema(arr, n):
            k = 2/(n+1)
            out = [arr[0]]
            for i in range(1, len(arr)):
                out.append(arr[i]*k + out[-1]*(1-k))
            return np.array(out)

        def stdev(arr, n):
            out = [0]*n
            for i in range(n, len(arr)):
                out.append(float(np.std(arr[i-n:i])))
            return np.array(out)

        n = 7
        ys1 = (o + h + l + c*9) / 4
        rk3 = ema(ys1, n)
        rk4 = stdev(ys1, n)
        rk4 = np.where(rk4==0, 0.001, rk4)
        rk5 = (ys1 - rk3) * 100 / rk4
        rk6 = ema(rk5, n)
        up = ema(rk6, n)
        down = ema(up, n)

        n_bars = 12
        hhv = max(h[-n_bars-1:-1])
        llv = min(l[-n_bars-1:-1])

        buy = bool(h[-1] > hhv and h[-2] <= max(h[-n_bars-2:-2]))
        sell = bool(l[-1] < llv and l[-2] >= min(l[-n_bars-2:-2]))

        in_long = up[-1] > down[-1]
        in_short = up[-1] < down[-1]

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
# ===== THEM DOAN NAY VAO server.py (truoc dong "if __name__") =====

# Danh sach ma HoSE va HNX
HOSE_SYMBOLS = [
    "ACB","BCM","BID","BVH","CTG","FPT","GAS","GVR","HDB","HPG",
    "MBB","MSN","MWG","NVL","PDR","PLX","PNJ","POW","SAB","SHB",
    "SSI","STB","TCB","TPB","VCB","VHM","VIB","VIC","VJC","VNM",
    "VPB","VRE","VND","DXG","KDH","LPB","OCB","REE","SJS","VCI",
    "AGG","AGR","AMD","ANV","ASM","ADS","BAF","BBC","BCG","BFC",
    "BSR","BTP","BWE","C4G","CAV","CCI","CCL","CEO","CII","CLC",
    "CMG","CMX","CNG","CSV","CTD","CTF","CTI","CTR","CTS","DAG",
    "DAH","DAT","DBC","DBD","DBT","DC4","DCL","DCM","DGC","DGW",
    "DHC","DHP","DHT","DIG","DL1","DLG","DMC","DPG","DPM","DPR",
    "DQC","DRC","DRH","DSC","DSE","DST","DTA","DTL","DXS","EIB",
    "ELC","EMC","EVE","EVF","EVG","FBC","FDC","FID","FIT","FLC",
    "GDT","GEG","GEX","GMD","GSP","GTN","GVR","HAG","HAH","HAP",
    "HAX","HBC","HCM","HDC","HDG","HHP","HHS","HID","HII","HLD",
    "HMC","HNG","HOT","HPX","HQC","HSL","HTG","HTI","HTN","HTV",
    "HUT","HVN","ICT","IDC","IDI","IJC","IMP","IPA","IPH","ITC",
    "ITD","IVS","KBC","KDC","KHG","KMR","KOS","KPF","KSB","KSF",
    "KTC","KTT","LCG","LCS","LDG","LEC","LGC","LHC","LHG","LIG",
    "LIX","LM8","LSS","LTG","MAC","MCP","MDG","MIG","MIM","MSB",
    "MST","MTV","NAB","NAF","NAG","NAV","NBB","NCT","NKG","NLG",
    "NNC","NPM","NRC","NSC","NT2","NTL","NVB","NVT","OGC","OPC",
    "PAC","PAN","PC1","PCI","PCM","PCT","PDC","PET","PGC","PGD",
    "PGI","PGV","PHC","PHR","PIT","PJT","PLC","PLO","PMG","PMP",
    "PNC","POM","PPY","PRC","PRE","PSH","PSI","PTC","PTL","PVB",
    "PVC","PVD","PVG","PVI","PVP","PVS","PVT","QCG","QNS","RAL",
    "RDP","RIC","ROC","S55","SAF","SAM","SAV","SBA","SBT","SC5",
    "SCD","SCR","SCS","SDC","SDG","SDT","SEA","SGN","SGP","SGT",
    "SHI","SHP","SHX","SIC","SII","SKG","SLS","SMB","SMC","SNC",
    "SPM","SRF","SSB","SSC","STC","STG","STK","STP","SVD","SVT",
    "SZC","SZG","SZL","TAC","TBC","TCH","TCL","TCM","TCO","TDG",
    "TDH","TDM","TDP","TDW","TEG","TGG","TGM","TIG","TIP","TIX",
    "TLG","TLH","TMP","TMS","TMT","TNA","TNT","TON","TPC","TRA",
    "TRC","TSC","TTB","TTC","TTF","TTP","TV2","TVD","TVS","TYA",
    "UDC","UIC","VCA","VCF","VCG","VCS","VDS","VFG","VGC","VGS",
    "VGT","VHC","VHG","VHL","VID","VIP","VIR","VIX","VJC","VKC",
    "VMC","VMD","VNE","VNL","VNS","VNT","VOS","VPG","VPH","VPI",
    "VPS","VRC","VRG","VSC","VSG","VSH","VTB","VTJ","VTO","VTS",
    "WHS","WSB","YEG"
]

HNX_SYMBOLS = [
    "ACE","ACM","ACS","AGC","AGF","AGL","AGX","AIC","ALT","ALV",
    "AMC","AME","AMV","APC","APP","APS","APT","ART","ASA","ASG",
    "ASP","AVF","AXB","BAB","BAX","BBS","BCC","BCF","BDB","BED",
    "BHC","BHN","BIC","BII","BKC","BKG","BKH","BMI","BMS","BNA",
    "BNC","BNW","BPC","BQB","BSA","BSH","BSP","BST","BTC","BTD",
    "BTH","BTT","BVL","BVS","BXH","C12","C21","C22","C32","C47",
    "C69","CAB","CAN","CAP","CBI","CCM","CEC","CHP","CID","CJC",
    "CKG","CKV","CLH","CLM","CLX","CMS","CMV","CMW","CMZ","CNA",
    "CNC","CNN","CNT","COM","CPC","CPH","CPI","CQN","CRE","CSC",
    "CST","CTB","CTC","CTW","CVN","CX8","DAC","DAD","DAN","DAP",
    "DAS","DAT","DBC","DBW","DC2","DCF","DCR","DCS","DDG","DDM",
    "DFC","DGP","DHN","DHP","DHS","DIC","DIN","DLD","DLT","DMT",
    "DNA","DNC","DNL","DNS","DNY","DPC","DPS","DQN","DSN","DSP",
    "DTC","DTD","DTK","DTT","DTV","DXL","DXN","DZM","EBS","EFI",
    "EFT","EID","EIN","ENE","FCM","FCN","FCS","FDT","FGL","FHH",
    "FIR","FIT","FMC","GDC","GED","GEG","GGG","GHA","GHC","GIC",
    "GKM","GLT","GLX","GMX","GNT","GPC","GPD","GPM","GPS","GTC",
    "GTS","GVT","HAD","HAI","HAM","HAN","HAS","HAT","HAY","HBD",
    "HBH","HBS","HBT","HCC","HCI","HCT","HDA","HDM","HDS","HFC",
    "HFX","HGM","HHC","HHG","HHR","HHX","HIG","HIM","HJS","HKB",
    "HKT","HLA","HLC","HLD","HLG","HLT","HLY","HMH","HMR","HNF",
    "HNM","HOM","HPB","HPC","HPI","HPM","HPP","HPT","HPW","HQC",
    "HRC","HRB","HSG","HTC","HTL","HTM","HTT","HU1","HU3","HUT",
    "HVA","HVT","HWS","ICG","ICS","IDJ","IDV","IHK","ILS","IME",
    "INC","INN","ISG","ISH","IST","ITA","ITQ","IVB","IVC","JAV",
    "JVC","KAC","KBT","KDM","KHL","KHS","KHT","KKC","KLF","KLW",
    "KMT","KNI","KPK","KSQ","KTB","KVC","L10","L14","L18","L35",
    "L43","L44","L61","L62","LAS","LAW","LBE","LBM","LCD","LCS",
    "LDP","LGM","LHC","LHS","LIG","LIT","LJC","LLC","LLM","LMC",
    "LMH","LMS","LNC","LNH","LNL","LOC","LPL","LQN","LSC","LSE",
    "LTC","LUT","LWS","MAF","MAS","MBG","MBS","MCC","MCF","MCL",
    "MDC","MDF","MDN","MEC","MHL","MHC","MIM","MIN","MKV","MLC",
    "MLS","MMB","MMC","MNC","MNB","MND","MPC","MPT","MPY","MQN",
    "MRC","MSC","MSH","MTC","MTG","MVB","MVC","MVN","MWF","NAC",
    "NAG","NAP","NAW","NBB","NCP","NDN","NET","NFG","NFW","NGC",
    "NHC","NHP","NHT","NIS","NJC","NKG","NLC","NLT","NMT","NNC",
    "NPS","NSH","NST","NTP","NTS","NTW","NVB","NVN","NVP","OCH",
    "OGC","ONE","ONW","ORS","PAI","PAP","PAS","PAT","PBC","PBP",
    "PCG","PCN","PCR","PDB","PDN","PDS","PEC","PEN","PGN","PGS",
    "PHB","PHH","PHN","PHP","PHT","PID","PIV","PJC","PKG","PLC",
    "PLO","PLP","PLT","PMB","PMC","PMJ","PMN","PMP","PMS","PNA",
    "PND","PNP","PPI","PPP","PPT","PSB","PSC","PSI","PSP","PSW",
    "PTC","PTG","PTN","PTQ","PTS","PTV","PVA","PVE","PVH","PVK",
    "PVL","PVM","PVN","PVO","PVR","PVX","PXL","PXM","PXT","QBS",
    "QCC","QHD","QNC","QNT","QPH","QPS","QST","QTC","QTP","RAC",
    "RBC","RCL","RGC","RHC","SAB","SAC","SAE","SAH","SAL","SAP",
    "SAR","SAT","SBB","SBC","SBD","SBS","SBV","SCL","SCO","SCY",
    "SDG","SDJ","SDN","SDU","SED","SEM","SGC","SGD","SGH","SHB",
    "SHC","SHN","SHT","SIC","SIF","SIH","SIM","SJD","SJE","SJG",
    "SJS","SKS","SKV","SLT","SMA","SMN","SNG","SNH","SNP","SNS",
    "SOV","SPC","SPD","SPH","SPI","SPP","SPS","SQC","SQH","SQN",
    "SRB","SRC","SRG","SRT","SSB","SSG","SSN","SSP","STA","STB",
    "STC","STH","STL","STT","STV","SUG","SVC","SVL","SVN","SWC",
    "SYM","TAH","TAL","TAW","TBC","TBD","TBH","TBR","TBT","TCJ",
    "TCK","TCL","TCN","TCP","TCR","TCT","TCW","TDA","TDL","TDN",
    "TDS","TDT","TED","TEL","TER","TET","TGT","TH1","THB","THD",
    "THG","THM","THT","THU","TIC","TIE","TIN","TIS","TIX","TKG",
    "TLC","TLK","TLT","TMB","TMC","TMS","TMX","TNA","TNB","TNC",
    "TNH","TNM","TNP","TNS","TNT","TNW","TOC","TOT","TPC","TPH",
    "TPP","TPS","TQL","TQN","TRA","TRB","TRC","TRS","TRT","TSB",
    "TSJ","TSP","TST","TTC","TTG","TTH","TTL","TTN","TTP","TTS",
    "TTZ","TUD","TUG","TUN","TV1","TV4","TV6","TVA","TVB","TVC",
    "TVG","TVH","TVL","TVN","TVP","TVT","TWC","TYA","UBC","UIC",
    "UNI","VC1","VC2","VC3","VC5","VC6","VC7","VC9","VCA","VCF",
    "VCM","VCR","VCS","VDB","VDP","VDS","VDT","VEC","VET","VFB",
    "VFR","VFS","VGP","VGS","VHE","VHL","VHM","VHN","VHR","VHS",
    "VIG","VIN","VIP","VIR","VIS","VIT","VIV","VIW","VKC","VLA",
    "VLG","VLW","VMG","VMI","VMK","VMM","VMP","VMR","VMS","VNB",
    "VNC","VND","VNE","VNF","VNG","VNI","VNK","VNL","VNM","VNP",
    "VNR","VNS","VNT","VNW","VOC","VOP","VOS","VPC","VPD","VPG",
    "VPH","VPI","VPK","VPL","VPN","VPS","VPX","VRG","VRS","VSA",
    "VSB","VSC","VSG","VSH","VSM","VSN","VSP","VST","VTC","VTD",
    "VTE","VTG","VTH","VTI","VTJ","VTK","VTL","VTM","VTN","VTO",
    "VTP","VTQ","VTR","VTS","VTT","VTV","VTX","VTZ","VUA","VUG",
    "VXB","VXL","WAT","WCS","WEB","WSB","WTC","XHC","XMC","XNH",
    "YBC","YBM","YEG","Z17"
]

ALL_SYMBOLS = list(set(HOSE_SYMBOLS + HNX_SYMBOLS))

@app.route('/api/scan')
def scan_stocks():
    try:
        from vnstock.api.quote import Quote
        from datetime import datetime, timedelta
        import numpy as np
        from concurrent.futures import ThreadPoolExecutor, as_completed

        end = datetime.today().strftime('%Y-%m-%d')
        start = (datetime.today() - timedelta(days=120)).strftime('%Y-%m-%d')

        def ema(arr, n):
            k = 2 / (n + 1)
            out = [arr[0]]
            for i in range(1, len(arr)):
                out.append(arr[i] * k + out[-1] * (1 - k))
            return out

        def sma(arr, n):
            result = []
            for i in range(len(arr)):
                if i < n - 1:
                    result.append(None)
                else:
                    result.append(sum(arr[i-n+1:i+1]) / n)
            return result

        def check_symbol(sym):
            try:
                q = Quote(symbol=sym, source='VCI')
                df = q.history(start=start, end=end, interval='1D')
                if df is None or df.empty or len(df) < 26:
                    return None
                closes = df['close'].values.astype(float)
                
                # MA20
                ma20 = sma(list(closes), 20)
                lma20 = ma20[-1]
                lma20_prev = ma20[-2]
                last_close = closes[-1]
                prev_close = closes[-2]
                
                # Dieu kien 1: Gia > MA20
                if lma20 is None or last_close <= lma20:
                    return None
                
                # Dieu kien 2: MA20 dang doc len
                #if lma20_prev is None or lma20 <= lma20_prev:
                #   return None
                
                # Dieu kien 3: MACD cat len
                e12 = ema(list(closes), 12)
                e26 = ema(list(closes), 26)
                macd = [e12[i] - e26[i] for i in range(len(closes))]
                signal_line = ema(macd, 9)
                
                # MACD cat len: hom nay MACD > Signal, hom qua MACD < Signal
                if macd[-1] <= signal_line[-1] or macd[-2] >= signal_line[-2]:
                    return None
                
                # Tinh % thay doi
                pct = (last_close - prev_close) / prev_close * 100
                volume = int(df['volume'].values[-1])
                
                return {
                    'symbol': sym,
                    'close': round(float(last_close), 2),
                    'ma20': round(float(lma20), 2),
                    'pct': round(pct, 2),
                    'volume': volume,
                    'macd': round(float(macd[-1]), 2),
                    'signal': round(float(signal_line[-1]), 2),
                    'above_ma20_pct': round((last_close - lma20) / lma20 * 100, 2)
                }
            except:
                return None

        results = []
        # Quet song song, toi da 20 luong cung luc
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(check_symbol, sym): sym for sym in ALL_SYMBOLS}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        # Sap xep theo % vuot MA20
        results.sort(key=lambda x: x['above_ma20_pct'], reverse=True)
        
        return jsonify({
            'count': len(results),
            'total_scanned': len(ALL_SYMBOLS),
            'results': results
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("="*50)
    print("  QuyStock Server dang chay...")
    print(f"  Port: {port}")
    print("="*50)
    app.run(host='0.0.0.0', port=port, debug=False)
