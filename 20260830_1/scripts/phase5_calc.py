#!/usr/bin/env python3
"""Phase 5 の計算を再現する。使い方: python3 scripts/phase5_calc.py"""
import csv, re, statistics as st
from datetime import date
def D(s):
    y,m,d=map(int,s.split('-')); return date(y,m,d)
STEP={'new':5/8}
REGIDX={'Lv36以上':0,'Lv60超':1,'Lv70超':2,'Lv80超':3}
CEN=[r for r in csv.DictReader(open('data/census_normalized.csv')) if r['new_scaled']]
BY={r['date']:r for r in CEN}
def n64(d,unm=1.0):
    r=BY[d]; i=REGIDX[r['regime']]; f=1.0
    for s in range(i): f*= STEP['new'] if s==2 else unm
    return float(r['new_scaled'])*(64/float(r['window_days']))/f

def s1_platform():
    print("=== §2-3 新PF追加の自然実験（64日換算＋足切り補正） ===")
    pre=['2023-07-22','2023-10-08','2023-12-24']
    b=st.mean(n64(d) for d in pre)
    print(f"Xbox版(2024-03-21) 発売前ベースライン平均 = {b:,.0f}")
    for d,note in [('2024-03-31','発売10日後・育成ラグ'),('2024-06-12','**分離可能な唯一の窓**'),
                   ('2024-08-27','7.0後・分離不能'),('2024-11-04','7.0後の谷・分離不能')]:
        print(f"  {d}  {n64(d):8,.0f}  比 {n64(d)/b:.2f}  {note}")
    pre5=['2021-02-07','2021-04-11']; b5=st.mean(n64(d) for d in pre5)
    print(f"\nPS5版(2021-05-25) 発売前ベースライン平均 = {b5:,.0f}")
    for d,note in [('2021-07-18','フリートライアル紅蓮拡大が同一窓に混入'),('2021-11-05','WoW難民＋暁月予約')]:
        print(f"  {d}  {n64(d):8,.0f}  比 {n64(d)/b5:.2f}  {note}")

def s2_margin():
    print("\n=== §4 MMO四半期 営業利益率 ===")
    rows=[r for r in csv.DictReader(open('data/mmo_financials_quarterly.csv')) if r['op_standalone_oku']]
    for r in rows[-9:]:
        rev=float(r['rev_standalone_oku']); op=float(r['op_standalone_oku'])
        print(f"  {r['fiscal_year']} {r['quarter']}: 売上{rev:4.0f} 営利{op:3.0f} 利益率{op/rev:6.1%}")
    d={(r['fiscal_year'],r['quarter']):(float(r['rev_standalone_oku']),float(r['op_standalone_oku'])) for r in rows}
    (r1,o1),(r0,o0)=d[('FY2027.3','Q1')],d[('FY2026.3','Q1')]
    print(f"  → FY2027.3 Q1 前年同期比: 売上{r1/r0-1:+.1%} 営利{o1/o0-1:+.1%} 利益率{o0/r0:.1%}→{o1/r1:.1%}")

def s3_regional():
    print("\n=== §5 note列の地域記載の走査 ===")
    rows=list(csv.DictReader(open('data/census_breakdown_full.csv')))
    # 【第15次】v0.2 は「オセアニアを含めて再走査し 11回/3点」としたが、実際に
    # 地域記載を含む回を数え直すと **10回**である（旧スクリプトの 9回 も v0.2 の 11回 も誤り）。
    # 「地域別」の語を必須にして、ワールド間テレポ等の誤検出を除く。
    pat=r'地域別'
    hits=[r['survey_date'] for r in rows if re.search(pat,(r.get('note','') or '')+(r.get('method_change_note','') or ''))]
    print(f"  地域記載のある回: {len(hits)} / {len(rows)}  → {hits}")
    print("  うち **絶対値**が取れるのは4回: 2019-10-23(EU約25万・JP40万) / 2022-04-10(オセアニアDC約4万弱)")
    print("    / 2024-06-12(JP 39.7万) / 2024-08-27(Dynamis DC 7万)")
    print("  **JP の絶対値**に限れば 2019-10-23 と 2024-06-12 の **2点のみ**。残りは増減・比率・DC単位。")
    for d,jp in [('2019-10-23',400000),('2024-06-12',397000)]:
        tot=float([r['raw_total'] for r in CEN if r['date']==d][0])
        print(f"  {d}: 総数{tot:,.0f} JP{jp:,} → シェア {jp/tot:.1%}")

def s4_price():
    print("\n=== §3-2 価格 ===")
    usd, jp_price, na_price = 159.4, 1628, 14.99
    print(f"  日本 ¥{jp_price} / 北米 ${na_price} (=¥{na_price*usd:,.0f}) → 日本は北米の {jp_price/(na_price*usd):.1%}")
    print(f"  売上税7%込みでは {jp_price/(na_price*usd*1.07):.1%}")
    print(f"  Switch2併用時の実質月額: ¥{jp_price} → ¥{jp_price+750} = {(jp_price+750)/jp_price-1:+.1%}")

if __name__=='__main__':
    s1_platform(); s2_margin(); s3_regional(); s4_price()
