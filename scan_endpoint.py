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
                if lma20_prev is None or lma20 <= lma20_prev:
                    return None
                
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
