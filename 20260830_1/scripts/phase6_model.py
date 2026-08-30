#!/usr/bin/env python3
"""Phase 6 収益モデル（v0.4 時点の実装）。使い方: python3 scripts/phase6_model.py

【重要・Phase 8 第3次監査】本スクリプトの説明変数は `normalized_64d` をそのまま使って
おり、**足切り基準（Lv36以上〜Lv80超）が混在している。** Phase 6 v0.5 / Phase 7 v0.5 /
params.py が採用している値（B=24.7 / a=8,693円 / パルス40.1 / ε=0.751 / 真OOS 0/4）は
本スクリプトからは出ない。**足切りを統一した正典の再推定は `scripts/phase6_recalc.py`。**
本スクリプトは v0.4 の値の由来を追跡するために残してある。
"""
import csv, math, statistics as st, random, sys
from collections import defaultdict
sys.path.insert(0,'scripts')
from params import S_MMO, FX_INDEX   # 【Phase 8】正典登録簿から取得（0.62 のベタ書きを廃止）

def cc(nom, I, s=S_MMO): return nom*((1-s)+s/I)

# 実際に拡張が発売された四半期（is_expansion_quarter フラグは前後の四半期も含むため別途定義）
LAUNCH_Q={('FY2018.3','Q1'),('FY2020.3','Q2'),('FY2022.3','Q3'),('FY2025.3','Q2')}

def load(use_normalized=True):
    """use_normalized=True: 窓長正規化済み系列を説明変数に使う（v0.2で必須化）。
    生 census は窓長に汚染されており（corr=+0.52）、Phase 0 の禁止事項に抵触する。"""
    cen={r['date']:r for r in csv.DictReader(open('data/census_normalized.csv'))}
    out=[]
    for r in csv.DictReader(open('data/census_vs_revenue.csv')):
        if not r['mmo_rev_nominal_oku'] or not r['census']: continue
        cd=r['census_date']
        if use_normalized:
            if cd not in cen or not cen[cd]['normalized_64d']: continue
            x=float(cen[cd]['normalized_64d'])
        else:
            x=float(r['census'])
        nom=float(r['mmo_rev_nominal_oku']); I=float(r['fx_index'])
        out.append(dict(d=cd, fy=r['assigned_fy'], q=r['assigned_q'],
            c=x, nom=nom, I=I, cc=cc(nom,I),
            exp=r['is_expansion_quarter'].strip().upper() in ('TRUE','1','YES'),
            launch=(r['assigned_fy'],r['assigned_q']) in LAUNCH_Q))
    return out

def ols(xs,ys):
    n=len(xs); xb=st.mean(xs); yb=st.mean(ys)
    sxx=sum((x-xb)**2 for x in xs)
    a=sum((x-xb)*(y-yb) for x,y in zip(xs,ys))/sxx; b=yb-a*xb
    res=[y-(b+a*x) for x,y in zip(xs,ys)]
    s2=sum(r*r for r in res)/(n-2)
    tss=sum((y-yb)**2 for y in ys)
    return a,b,math.sqrt(s2/sxx),math.sqrt(s2),1-sum(r*r for r in res)/tss,n

def s1_overseas():
    print("=== §2 実効海外売上比率 s^MMO ===")
    rows=list(csv.DictReader(open('data/census_world/census_world_active.csv')))
    reg=defaultdict(lambda: defaultdict(int))
    for r in rows: reg[r['date']][r['region']]+=int(r['active_characters'])
    FX={'USD':159.4,'EUR':185.7}
    P={'JP':1628,'NA':14.99*FX['USD'],'EU':12.99*FX['EUR'],'OCE':14.99*FX['USD']}
    PAY={'JP':0.69,'NA':0.55,'EU':0.51,'OCE':0.55}
    v=[]
    for d in sorted(reg):
        rev={k:reg[d].get(k,0)*PAY[k]*P[k] for k in P}
        v.append(1-rev['JP']/sum(rev.values()))
    print(f"  FFXIV海外売上比率（継続課金率補正後）平均 {st.mean(v):.3f} 範囲 {min(v):.3f}〜{max(v):.3f}")
    for sh in (0.05,0.10,0.15,0.20,0.25):
        print(f"  DQX+FFXI={sh:.0%} → s^MMO = {(1-sh)*st.mean(v):.3f}")

def s2_model():
    print("\n=== §3 差分モデル: CC売上 = B + a×活動キャラ数（非拡張四半期） ===")
    d=load(); non=[x for x in d if not x['exp']]
    xs=[x['c'] for x in non]; ys=[x['cc'] for x in non]
    a,b,se,sd,r2,n=ols(xs,ys)
    print(f"  B={b:.1f}億/Q  a={a*1e6:.1f}円/キャラ/Q (t={a/se:.2f})  R²={r2:.3f} 残差SD={sd:.1f} n={n}")
    print(f"  観測レンジ {min(xs):,.0f}〜{max(xs):,.0f} → 切片は外挿。構造的な床と解釈しないこと")
    act=[x['cc']-(b+a*x['c']) for x in d if x['launch']]
    non_l=[x['cc']-(b+a*x['c']) for x in d if x['exp'] and not x['launch']]
    print(f"  【発売四半期のみ】n={len(act)} 平均{st.mean(act):+.1f}億 中央値{st.median(act):+.1f}億 ({st.mean(act)/sd:.1f}σ)")
    print(f"  【拡張フラグだが発売なし】n={len(non_l)} 平均{st.mean(non_l):+.1f}億 → フラグを混ぜると希釈される")
    return a,b,sd,non,st.median(act)

def s3_elasticity(a,b,non):
    print("\n=== §4 弾力性 ===")
    # 内生性・慣性の検定（v0.2で追加）
    dd=sorted(non,key=lambda x:x['d'])
    xs0=[x['c'] for x in dd]; ys0=[x['cc'] for x in dd]
    dx=[xs0[i]-xs0[i-1] for i in range(1,len(xs0))]; dy=[ys0[i]-ys0[i-1] for i in range(1,len(ys0))]
    a2,_,se2,_,_,_=ols(dx,dy)
    def corr(u,v):
        mu=st.mean(u);mv=st.mean(v)
        return sum((p-mu)*(q-mv) for p,q in zip(u,v))/math.sqrt(sum((p-mu)**2 for p in u)*sum((q-mv)**2 for q in v))
    print(f"  一次差分: a={a2*1e6:.1f} (t={a2/se2:.2f}) = 水準の {a2/a:.0%}")
    print(f"  リード/ラグ: 同時{corr(xs0,ys0):+.3f} キャラ先行{corr(xs0[:-1],ys0[1:]):+.3f} 売上先行{corr(ys0[:-1],xs0[1:]):+.3f}")
    print("  → 因果の向きは識別不能。慣性ラグ仮説を排除できていない")
    for c,lab in [(1500000,'暁月ピーク'),(1200000,'黄金初動'),(853595,'直近'),(750000,'定常予測')]:
        print(f"  キャラ{c:>9,d} ({lab:8s}): ε={a*c/(b+a*c):.3f}")
    xs=[x['c'] for x in non]; ys=[x['cc'] for x in non]
    lx=[math.log(x) for x in xs]; ly=[math.log(y) for y in ys]
    e,_,se,_,_,_=ols(lx,ly)
    print(f"  log-log 独立チェック: ε={e:.3f} (se {se:.3f}) 95%CI [{e-1.96*se:.3f},{e+1.96*se:.3f}]")
    return e

def s4_backtest(a,b,pulse):
    print("\n=== §5 バックテスト（precommit: 年次CC、許容±15%） ===")
    NOM={'FY2023.3':533,'FY2024.3':473,'FY2025.3':555,'FY2026.3':410}
    # 【Phase 8で訂正】FY2023.3 は 1.146 ではなく 1.1741
    FXI={f'FY{y}.3':FX_INDEX[y] for y in (2023,2024,2025,2026)}
    d=load()
    # 四半期単位に集約してから4四半期を合計（census行を単純平均すると二重ウェイトになる）
    byq=defaultdict(list)
    for x in d: byq[(x['fy'],x['q'])].append(x)
    def annual(fy, coef_a, coef_b):
        qs=[k for k in byq if k[0]==fy]
        if len(qs)<3: return None
        pv=[]
        for k in qs:
            c=st.mean([x['c'] for x in byq[k]])
            v=coef_b+coef_a*c
            if k in LAUNCH_Q: v+=pulse       # 発売四半期にはパルスを加える
            pv.append(v)
        return st.mean(pv)*4
    print(f"  {'年度':>10s}{'実績':>7s}{'予測':>7s}{'誤差':>8s}{'判定':>6s}{'ナイーブ':>9s}")
    ok=tot=0; naive_ok=0; errs=[]; nerrs=[]
    prev=None
    for fy in ['FY2023.3','FY2024.3','FY2025.3','FY2026.3']:
        pred=annual(fy,a,b)
        if pred is None: continue
        act=cc(NOM[fy],FXI[fy]); err=pred/act-1
        tot+=1; ok+= abs(err)<=0.15; errs.append(abs(err))
        nv=prev; ns=''
        if nv is not None:
            ne=nv/act-1; naive_ok+= abs(ne)<=0.15; nerrs.append(abs(ne)); ns=f"{ne:+.1%}"
        print(f"  {fy:>10s}{act:7.0f}{pred:7.0f}{err:+8.1%}{'合格' if abs(err)<=0.15 else '不合格':>6s}{ns:>9s}")
        prev=act
    print(f"  → 差分モデル 合格 {ok}/{tot}  平均絶対誤差 {st.mean(errs):.1%}")
    if nerrs: print(f"  → ナイーブ(前年実績) 合格 {naive_ok}/{len(nerrs)}  平均絶対誤差 {st.mean(nerrs):.1%}")
    # out-of-sample: FY2022.3以前のみで学習
    tr=[x for x in d if not x['exp'] and x['fy'] not in NOM]
    if len(tr)>5:
        a2,b2,_,_,_,n2=ols([x['c'] for x in tr],[x['cc'] for x in tr])
        print(f"\n  【真のout-of-sample】FY2022.3以前のみで学習 (n={n2}): a={a2*1e6:.1f}")
        ok2=0; t2=0
        for fy in NOM:
            pred=annual(fy,a2,b2)
            if pred is None: continue
            act=cc(NOM[fy],FXI[fy]); e=pred/act-1; t2+=1; ok2+= abs(e)<=0.15
            print(f"    {fy}: {e:+.1%} {'合格' if abs(e)<=0.15 else '不合格'}")
        print(f"    → 合格 {ok2}/{t2}")
        print(f"    ※ 係数が {a*1e6:.1f} → {a2*1e6:.1f} とドリフトしている（変換係数の定数扱いへの警告）")

def s5_margin():
    print("\n=== §6 マージンバンド ===")
    rows=[r for r in csv.DictReader(open('data/mmo_financials_quarterly.csv')) if r['op_standalone_oku']]
    PRE={('FY2024.3','Q1'),('FY2024.3','Q2'),('FY2024.3','Q3'),('FY2024.3','Q4'),
         ('FY2025.3','Q1'),('FY2027.3','Q1')}
    LAUNCH={('FY2025.3','Q2')}
    bk=defaultdict(list)
    for r in rows:
        k=(r['fiscal_year'],r['quarter']); m=float(r['op_standalone_oku'])/float(r['rev_standalone_oku'])
        bk['発売四半期' if k in LAUNCH else ('発売前年' if k in PRE else 'その他')].append(m)
    for k,v in bk.items():
        print(f"  {k:8s} n={len(v)} 中央値{st.median(v):.1%} 範囲{min(v):.1%}〜{max(v):.1%}")
    print("  → 発売前年の費用先行は FY2024.3 では観測されない（38〜47%）。FY2027.3 Q1 の 28.3% のみが低い")

if __name__=='__main__':
    s1_overseas(); a,b,sd,non,pulse=s2_model(); s3_elasticity(a,b,non); s4_backtest(a,b,pulse); s5_margin()
