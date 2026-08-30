#!/usr/bin/env python3
"""Phase 7 v0.5 補遺: 分岐閾値・K3プロキシ・ε/為替グリッド・シナリオ間隔"""
import sys
sys.path.insert(0,'scripts')
from datetime import date, timedelta
from params import *
from phase7_forecast import simulate, value_at, annual_mean, SCEN, build, END, CYC7_MEAN, wavg

print("=== A. 2027年4〜6月（8.0の3〜5ヶ月後）の予測値 → 分岐閾値 ===")
d9=E8_ASSUMED+timedelta(days=927)
band={}
for lab,rho,im,w in SCEN:
    ser=simulate(rho,im,(E8_ASSUMED,d9))
    vs=[value_at(ser,date(2027,m,15)) for m in (4,5,6)]
    band[lab]=vs
    print(f"  {lab:5s}: 4月 {vs[0]:,.0f}  5月 {vs[1]:,.0f}  6月 {vs[2]:,.0f}  (幅 {min(vs):,.0f}〜{max(vs):,.0f})")
print("\n  → 重ならない帯を引く（隣接シナリオの中点）")
for a,b in [('Bear','Base'),('Base','Bull')]:
    mid=(max(band[a])+min(band[b]))/2
    print(f"    {a}/{b} 境界: ({max(band[a]):,.0f} + {min(band[b]):,.0f})/2 = {mid:,.0f}  → 丸め {round(mid,-4):,.0f}")
print(f"  足切り再改定時（×{CUTOFF_STEP['total']:.4f}）の閾値:")
for a,b in [('Bear','Base'),('Base','Bull')]:
    mid=(max(band[a])+min(band[b]))/2
    print(f"    {a}/{b}: {round(mid,-4):,.0f} → {round(mid,-4)*CUTOFF_STEP['total']:,.0f}")

print("\n=== A2. Base/Bull の分離可能性 ===")
sep=[]
for y,m in [(2027,5),(2027,10),(2028,3),(2028,9),(2029,3)]:
    t=date(y,m,15)
    v={lab:value_at(simulate(rho,im,(E8_ASSUMED,d9)),t) for lab,rho,im,w in SCEN}
    print(f"  {y}-{m:02d}: Bear {v['Bear']:,.0f} / Base {v['Base']:,.0f} / Bull {v['Bull']:,.0f}"
          f"   Base→Bull {v['Bull']/v['Base']-1:+.1%}  Bear→Base {v['Base']/v['Bear']-1:+.1%}")
print(f"  ※ 足切り1回改定の機械的段差は {1-CUTOFF_STEP['total']:.1%}。Base/Bull の乖離はこれと同オーダー。")

print("\n=== B. K3 下限プロキシ（拡張『開始』数 = 0.916 × K1、単位整合済み）===")
r=build()
for lab in ['Bear','Base','Bull']:
    print(f"  {lab:5s}: {r[lab]['fy2030']*0.916:,.0f}")

print("\n=== G. 谷・ピークの位置と観測レンジ外判定 ===")
print(f"  観測レンジ(norm64, **Lv80超統一**): {K1_RANGE_OBS[0]:,}〜{K1_RANGE_OBS[1]:,}")
for lab in ['Bear','Base','Bull']:
    d=r[lab]
    flag="**レンジ下限を下回る外挿**" if d['trough']<K1_RANGE_OBS[0] else "レンジ内"
    print(f"  {lab:5s}: 谷 {d['trough']:,.0f} {flag} / ピーク {d['peak']:,.0f}")
# 谷の日付
for lab,rho,im,w in SCEN:
    ser=simulate(rho,im,(E8_ASSUMED,d9))
    seg=[(dt,v) for dt,v in ser if E8_ASSUMED<dt<d9]
    dt,v=min(seg,key=lambda x:x[1])
    print(f"  {lab:5s} 谷の日付: {dt}  ({v:,.0f})  9.0想定日 {d9} の {(d9-dt).days}日前")
