#!/usr/bin/env python3
"""Phase 3.5 の全計算を再現するスクリプト。
使い方: cd /home/claude/ffxiv-analysis && python3 scripts/phase3_5_calc.py
"""
import csv
import math
import random
import statistics as st
from collections import defaultdict
from datetime import date

CCU=defaultdict(dict)
with open('data/external/steam_ccu_monthly.csv') as _f:
    for r in csv.DictReader(_f):
        CCU[r['title']][r['year_month']]=int(r['peak_ccu'])
with open('data/census_normalized.csv') as _f:
    CEN=[r for r in csv.DictReader(_f)]

def add(ym,k):
    y,m=map(int,ym.split('-')); m+=k; y+=(m-1)//12; m=(m-1)%12+1
    return f'{y}-{m:02d}'
def win(s, l, a, b) -> float:
    v = [s[add(l, k)] for k in range(a, b + 1) if add(l, k) in s]
    return st.mean(v) if v else 0.0

def sec_expansion():
    print("=== §2-4 拡張 post/pre (Steam月次ピーク) ===")
    cases=[('FFXIV 5.0 漆黒',CCU['FFXIV'],'2019-06'),('FFXIV 6.0 暁月',CCU['FFXIV'],'2021-12'),
           ('FFXIV 7.0 黄金',CCU['FFXIV'],'2024-06'),('D2 Witch Queen',CCU['Destiny 2'],'2022-02'),
           ('D2 Lightfall',CCU['Destiny 2'],'2023-02'),('D2 Final Shape',CCU['Destiny 2'],'2024-06')]
    print(f"{'case':18s}{'+2..13(主)':>12s}{'+1..12':>9s}{'+3..14':>9s}")
    for n,s,l in cases:
        pre=win(s,l,-12,-1)
        print(f"{n:18s}{win(s,l,2,13)/pre:12.3f}{win(s,l,1,12)/pre:9.3f}{win(s,l,3,14)/pre:9.3f}")

def sec_calibration():
    print("\n=== §2-2 Steam/国勢調査 較正 ===")
    F=CCU['FFXIV']; excl={'2019-06','2019-07','2021-12','2022-01','2024-06','2024-07'}
    def build(minyear, drop):
        pts=[]
        for r in CEN:
            ym=r['date'][:7]
            if ym not in F or not r['normalized_64d']: continue
            if drop and ym in excl: continue
            y,m,d=map(int,r['date'].split('-'))
            if y<minyear: continue
            pts.append(((date(y,m,d)-date(2017,1,1)).days/365.25,
                        math.log(F[ym]/float(r['normalized_64d']))))
        return pts
    def ols(p):
        n=len(p); tb=st.mean(q[0] for q in p); yb=st.mean(q[1] for q in p)
        sxx=sum((q[0]-tb)**2 for q in p); b=sum((q[0]-tb)*(q[1]-yb) for q in p)/sxx
        a=yb-b*tb; res=[q[1]-(a+b*q[0]) for q in p]
        return b, math.sqrt(sum(x*x for x in res)/(n-2)/sxx), n
    for lab,mn,dr in [('2017+ excl launch',2017,True),('2017+ incl launch',2017,False),
                      ('2019+',2019,True),('2020+',2020,True),('2020+ incl launch',2020,False),('2021+',2021,True)]:
        b,se,n=ols(build(mn,dr))
        print(f"  {lab:20s} n={n:3d} 年率{math.exp(b)-1:+7.2%} t={b/se:5.2f}")
    for lab,lo,hi in [('2017-2018',2017,2018),('2019',2019,2019),('2020-2026',2020,2026)]:
        v=[CCU['FFXIV'][r['date'][:7]]/float(r['normalized_64d']) for r in CEN
           if r['normalized_64d'] and r['date'][:7] in CCU['FFXIV'] and lo<=int(r['date'][:4])<=hi
           and r['date'][:7] not in excl]
        print(f"  {lab:12s} n={len(v):2d} 平均比={st.mean(v):.4f} CV={st.stdev(v)/st.mean(v):.1%}")
    pts=build(2020,True); random.seed(7)
    bs=sorted(ols([random.choice(pts) for _ in pts])[0] for _ in range(4000))
    b=ols(pts)[0]; lo,hi=bs[100],bs[3900]
    print(f"  2020+ 3年係数 {math.exp(b*3):.3f} 95%CI [{math.exp(lo*3):.3f},{math.exp(hi*3):.3f}]")
    print(f"  Steam横ばい -> 国勢調査3年変化 {1/math.exp(b*3)-1:+.1%} (CI {1/math.exp(hi*3)-1:+.1%}..{1/math.exp(lo*3)-1:+.1%})")

def sec_conflict():
    print("\n=== §2-4 所見4 関数形を揃えた7.0比較 ===")
    L=date(2024,7,2)
    def D(s): y,m,d=map(int,s.split('-')); return date(y,m,d)
    for col in ['normalized_64d','continuing_dual_adj_64d','raw_total']:
        pre=[float(r[col]) for r in CEN if r[col] and -365<=(D(r['date'])-L).days<=-1]
        pos=[float(r[col]) for r in CEN if r[col] and 32<=(D(r['date'])-L).days<=395]
        print(f"  census {col:24s} post/pre={st.mean(pos)/st.mean(pre):.3f}")
    F=CCU['FFXIV']
    print(f"  Steam post/pre(+2..13)={win(F,'2024-06',2,13)/win(F,'2024-06',-12,-1):.3f}")
    print("  --- ピーク->直近 (2024-08 -> 2026-07) ---")
    print(f"  Steam {F['2026-07']/F['2024-08']-1:+.1%}")
    g=lambda dt,c:next(float(r[c]) for r in CEN if r['date']==dt)
    for col in ['raw_total','normalized_64d','continuing_dual_adj_64d']:
        print(f"  census {col:24s} {g('2026-07-20',col)/g('2024-08-27',col)-1:+.1%}")

def sec_ncsoft():
    print("\n=== §2-5 NCSoft 基準統一 ===")
    with open('data/external/ncsoft_title_revenue.csv') as _f:
        rows=[r for r in csv.reader(_f)
              if r and not r[0].startswith('#') and r[0]!='company']
    q=defaultdict(dict); a=defaultdict(dict)
    for r in rows:
        if not r[3]: continue
        (q if 'Q' in r[2] else a)[r[1]][r[2]]=float(r[3])
    print(f"  {'title':14s}{'CY22旧':>9s}{'CY25旧':>9s}{'旧基準3y':>10s}{'CY25新':>9s}{'混在(誤)':>10s}")
    for t in ['Aion','Guild Wars 2','Lineage','Lineage II']:
        o22=a[t]['CY2022']; o25=sum(q[t][f'CY2025Q{i}'] for i in range(1,5)); n25=a[t]['CY2025']
        print(f"  {t:14s}{o22:9.3f}{o25:9.3f}{o25/o22-1:10.1%}{n25:9.3f}{n25/o22-1:10.1%}")

def sec_floor():
    print("\n=== 床(年次最低月ピーク) ===")
    for t in ['FFXIV','Destiny 2']:
        print(' ',t, {y:min(v for k,v in CCU[t].items() if k.startswith(str(y)))
                      for y in range(2021,2027) if any(k.startswith(str(y)) for k in CCU[t])})

if __name__=='__main__':
    sec_expansion(); sec_calibration(); sec_conflict(); sec_ncsoft(); sec_floor()
