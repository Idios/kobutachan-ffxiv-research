#!/usr/bin/env python3
"""Phase 4 の全計算を再現する。使い方: python3 scripts/phase4_calc.py"""
import csv, math, statistics as st, random
from datetime import date
from collections import defaultdict

def D(s):
    y,m,d=map(int,s.split('-')); return date(y,m,d)
LAUNCH=[('4.x',D('2017-06-20')),('5.x',D('2019-07-02')),('6.x',D('2021-12-07')),
        ('7.x',D('2024-07-02')),('8.x',D('2027-01-01'))]
# 2026-07-20 同日ペア（Lv70超→Lv80超）から得たカテゴリ別の定義変更効果
STEP={'new':5/8,'ret':28/31,'cont':61/63,'total':95/102}
REGIDX={'Lv36以上':0,'Lv60超':1,'Lv70超':2,'Lv80超':3}
CEN=[r for r in csv.DictReader(open('data/census_normalized.csv'))]

def gen_of(d):
    for j,(g,L) in enumerate(LAUNCH[:-1]):
        if L<=d<LAUNCH[j+1][1]: return g,L,LAUNCH[j+1][1]
    return None,None,None

def lstsq(X,Y):
    k=len(X[0]); n=len(X)
    A=[[sum(X[i][a]*X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    B=[sum(X[i][a]*Y[i] for i in range(n)) for a in range(k)]
    M=[A[i][:]+[B[i]] for i in range(k)]
    for i in range(k):
        p=max(range(i,k),key=lambda r:abs(M[r][i])); M[i],M[p]=M[p],M[i]
        for r in range(k):
            if r!=i:
                f=M[r][i]/M[i][i]
                for c in range(i,k+1): M[r][c]-=f*M[i][c]
    beta=[M[i][k]/M[i][i] for i in range(k)]
    res=[Y[i]-sum(X[i][j]*beta[j] for j in range(k)) for i in range(n)]
    s2=sum(r*r for r in res)/(n-k)
    inv=[[1.0 if i==j else 0.0 for j in range(k)] for i in range(k)]
    M=[A[i][:]+inv[i] for i in range(k)]
    for i in range(k):
        p=max(range(i,k),key=lambda r:abs(M[r][i])); M[i],M[p]=M[p],M[i]
        dd=M[i][i]
        for c in range(2*k): M[i][c]/=dd
        for r in range(k):
            if r!=i:
                f=M[r][i]
                for c in range(2*k): M[r][c]-=f*M[i][c]
    se=[math.sqrt(s2*M[i][k+i]) for i in range(k)]
    tss=sum((y-st.mean(Y))**2 for y in Y)
    return beta,se,n,1-sum(r*r for r in res)/tss

def s1_generation_curves(step=-0.069):
    print("=== §1 世代別 山→谷カーブ（自世代ピーク基準・位相正規化） ===")
    eff={'Lv36以上':1.0,'Lv60超':1+step,'Lv70超':(1+step)**2,'Lv80超':(1+step)**2*(1-0.069)}
    cur={}
    for r in CEN:
        if not r['normalized_64d']: continue
        g,L,E=gen_of(D(r['date']))
        if not g: continue
        cur.setdefault(g,[]).append(((D(r['date'])-L).days/(E-L).days,
                                     float(r['normalized_64d'])/eff[r['regime']]))
    def interp(pts,x):
        pts=sorted(pts)
        for i in range(len(pts)-1):
            if pts[i][0]<=x<=pts[i+1][0]:
                (x0,y0),(x1,y1)=pts[i],pts[i+1]; return y0+(y1-y0)*(x-x0)/(x1-x0)
    print(f"{'位相':>6s} " + " ".join(f"{g:>7s}" for g in ['4.x','5.x','6.x','7.x']))
    norm={g:max(v for p,v in cur[g] if p<=0.25) for g in cur}
    for x in [0.2,0.3,0.4,0.5,0.6,0.7,0.8]:
        out=[]
        for g in ['4.x','5.x','6.x','7.x']:
            v=interp(cur[g],x); out.append(f"{v/norm[g]:7.3f}" if v else "     — ")
        print(f"{x:6.2f} "+" ".join(out))

def s2_within_trend():
    print("\n=== §2 世代内トレンド log(水準)~位相 ===")
    eff={'Lv36以上':1.0,'Lv60超':0.931,'Lv70超':0.931**2,'Lv80超':0.931**3}
    print(f"{'世代':>5s}{'n':>4s}{'総アクティブ':>13s}{'t':>7s}{'継続':>11s}{'t':>7s}")
    for g in ['4.x','5.x','6.x','7.x']:
        A=[];B=[]
        for r in CEN:
            gg,L,E=gen_of(D(r['date']))
            if gg!=g: continue
            ph=(D(r['date'])-L).days/(E-L).days
            if r['normalized_64d']: A.append((ph,math.log(float(r['normalized_64d'])/eff[r['regime']])))
            if r['continuing_dual_adj_64d']: B.append((ph,math.log(float(r['continuing_dual_adj_64d'])/eff[r['regime']])))
        b1,s1,n1,_=lstsq([[1,p] for p,_ in A],[y for _,y in A])
        b2,s2,n2,_=lstsq([[1,p] for p,_ in B],[y for _,y in B])
        print(f"{g:>5s}{n1:>4d}{math.exp(b1[1])-1:>12.1%}{b1[1]/s1[1]:>7.2f}{math.exp(b2[1])-1:>10.1%}{b2[1]/s2[1]:>7.2f}")

def s3_flows(step_map,label):
    def cum(cat,i):
        f=1.0
        for s in range(i): f*= STEP[cat] if s==2 else step_map[cat]
        return f
    agg=defaultdict(lambda:[[],[],[]])
    for r in CEN:
        if not r['new_scaled']: continue
        g,_,_=gen_of(D(r['date']))
        if not g: continue
        i=REGIDX[r['regime']]; k=64/float(r['window_days'])
        agg[g][0].append(float(r['new_scaled'])*k/cum('new',i))
        agg[g][1].append(float(r['returning_scaled'])*k/cum('ret',i))
        agg[g][2].append(float(r['continuing_scaled'])/cum('cont',i))
    print(f"\n--- {label} ---")
    print(f"{'世代':>5s}{'新規(64d)':>12s}{'復帰(64d)':>12s}{'継続':>11s}{'新規/継続':>10s}{'対6.x':>8s}")
    m={g:(st.mean(v[0]),st.mean(v[1]),st.mean(v[2])) for g,v in agg.items()}
    base=m['6.x'][0]
    for g in ['4.x','5.x','6.x','7.x']:
        n,rr,c=m[g]; print(f"{g:>5s}{n:12,.0f}{rr:12,.0f}{c:11,.0f}{n/c:10.3f}{n/base:8.2f}")

def s4_retention():
    print("\n=== §4 再捕捉率モデル log(継続_t/総数_{t-1}) ~ log(窓長)+世代ダミー ===")
    byd={r['date']:r for r in CEN}; X=[];Y=[];gens=['4.x','5.x','6.x','7.x']
    for r in CEN:
        if not r['continuing_scaled'] or not r['prev_date']: continue
        p=byd.get(r['prev_date'])
        if not p or r['regime']!=p['regime']: continue
        g,_,_=gen_of(D(r['date']))
        if not g: continue
        X.append([1.0,math.log(float(r['window_days']))]+[1.0 if g==x else 0.0 for x in gens[1:]])
        Y.append(math.log(float(r['continuing_scaled'])/float(p['raw_total'])))
    b,se,n,r2=lstsq(X,Y)
    for nm,bb,ss in zip(['切片','log(窓長)','5.x','6.x','7.x'],b,se):
        print(f"  {nm:10s} {bb:+.4f} se={ss:.4f} t={bb/ss:+.2f}")
    print(f"  n={n}  窓長64日換算の再捕捉率:")
    for i,g in enumerate(gens):
        print(f"    {g}: {math.exp(b[0]+b[1]*math.log(64)+(b[1+i] if i else 0)):.3f}")
    return math.exp(b[0]+b[1]*math.log(64)+b[4])

def s5_steadystate(rho):
    print(f"\n=== §5 ストック・フロー定常モデル（ρ={rho:.3f}） ===")
    I=[]
    for r in CEN:
        if not r['new_scaled'] or D(r['date'])<D('2024-07-02'): continue
        k=64/float(r['window_days'])
        I.append((float(r['new_scaled'])+float(r['returning_scaled']))*k)
    cur=853595
    for lab,sl in [('7.x全体',I),('直近5回',I[-5:]),('直近3回',I[-3:])]:
        m=st.mean(sl); print(f"  {lab:8s} 平均流入 {m:8,.0f} → 定常 S*={m/(1-rho):9,.0f}  現在比 {m/(1-rho)/cur-1:+6.1%}")
    m=st.mean(I[-5:]); s=cur
    print("  収束経路:", end="")
    for step in range(1,18):
        s=rho*s+m
        if step in (3,6,9,12,17): print(f" +{step*64/365.25:.1f}年={s:,.0f}", end="")
    print()
    print("  ρ感度:", "  ".join(f"ρ={r_:.3f}→{m/(1-r_):,.0f}" for r_ in [0.653,0.701,0.745,0.78]))

if __name__=='__main__':
    s1_generation_curves(); s2_within_trend()
    for sm,lab in [({'new':1.0,'ret':1.0,'cont':1.0},'A: 未測定2回=効果ゼロ'),
                   ({'new':STEP['new'],'ret':STEP['ret'],'cont':STEP['cont']},'B: 未測定2回=実測と同じ'),
                   ({'new':(1+STEP['new'])/2,'ret':(1+STEP['ret'])/2,'cont':(1+STEP['cont'])/2},'C: 実測の半分')]:
        s3_flows(sm,lab)
    rho=s4_retention(); s5_steadystate(rho)
