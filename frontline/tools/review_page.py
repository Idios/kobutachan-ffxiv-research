"""値台帳の確認用ページ（○×とコメントを付ける画面）を生成する。

Markdown の表に直接書き込む代わりに、ブラウザで1行ずつ ○／× とコメントを付けられるようにする。
判定はブラウザ（localStorage）に自動で保存され、「判定を書き出す」で JSON ファイルにできる。
書き出した JSON は apply_review.py で台帳へ取り込む。

使い方:
    python frontline/tools/review_page.py [--out PATH] [--only-pending]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger

REPO = ledger.ROOT.parent
DEFAULT_OUT = REPO / "reports" / "20261027_1" / "review" / "index.html"

PAGE = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>値台帳の確認（○×）</title>
<style>
:root { color-scheme: dark; --page:#0d0d0d; --s1:#1a1a19; --s2:#222220; --s3:#2c2c2a; --line:#383835;
  --t1:#f0efec; --t2:#c3c2b7; --t3:#898781; --ok:#0ca30c; --ng:#d03b3b; --warn:#fab219; --accent:#3987e5;
  --font: system-ui, -apple-system, "Segoe UI", "Yu Gothic UI", "Meiryo UI", sans-serif; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--t1); font-family: var(--font); font-size: 15px; }
header { position: sticky; top: 0; z-index: 5; background: #111110; border-bottom: 1px solid var(--line); padding: 10px 18px; display: grid; gap: 8px; }
h1 { font-size: 18px; margin: 0; display: flex; align-items: center; gap: 14px; }
h1 .prog { font-size: 14px; color: var(--t2); font-weight: 400; }
.bar { height: 6px; background: var(--s3); border-radius: 3px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--ok); }
.ctl { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.ctl button, .ctl label, .ctl input[type=search] { font: inherit; font-size: 13px; color: var(--t1); background: var(--s2); border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; }
.ctl button.on { background: var(--accent); border-color: var(--accent); }
.ctl input[type=search] { width: 220px; }
.ctl .sp { flex: 1; }
.ctl .primary { background: #1f6f2a; border-color: #1f6f2a; font-weight: 700; }
main { padding: 14px 18px 60px; display: grid; gap: 10px; max-width: 1400px; margin: 0 auto; }
.card { background: var(--s1); border: 1px solid var(--line); border-left: 5px solid var(--s3); border-radius: 10px; padding: 10px 14px; display: grid; grid-template-columns: 1fr 300px; gap: 10px 18px; }
.card.v-ok { border-left-color: var(--ok); }
.card.v-ng { border-left-color: var(--ng); }
.top { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 12px; }
.id { font-family: ui-monospace, Consolas, monospace; font-size: 12px; color: var(--t3); }
.lbl { font-weight: 700; }
.val { font-size: 20px; font-weight: 700; }
.val small { font-size: 13px; color: var(--t2); font-weight: 400; margin-left: 3px; }
.cond { color: var(--t2); font-size: 13px; margin-top: 2px; }
.disp { color: #a6c8f0; font-size: 13px; margin-top: 2px; }
.tag { font-size: 12px; padding: 1px 8px; border-radius: 999px; background: var(--s3); color: var(--t2); white-space: nowrap; }
.tag.g-公式 { background: #26364d; color: #cde2fb; }
.tag.g-外部 { background: #3a3a2a; color: #f0e3b0; }
.tag.g-未確認 { background: #4a3510; color: #ffd98a; }
.tag.g-実測 { background: #173d1b; color: #a6f0ad; }
.chk { font-size: 12px; color: var(--t3); }
details { margin-top: 6px; font-size: 13px; color: var(--t2); }
details summary { cursor: pointer; color: var(--t3); }
details .q { border-left: 3px solid #26364d; padding: 4px 8px; margin: 6px 0; color: var(--t1); background: #161b22; }
details ul { margin: 4px 0 0 18px; padding: 0; }
details a { color: #86b6ef; }
.act { display: grid; gap: 6px; align-content: start; }
.btns { display: flex; gap: 6px; }
.btns button { flex: 1; font: inherit; font-size: 20px; font-weight: 700; padding: 6px 0; border-radius: 8px; border: 1px solid var(--line); background: var(--s2); color: var(--t2); cursor: pointer; }
.btns button.ok.on { background: var(--ok); border-color: var(--ok); color: #fff; }
.btns button.ng.on { background: var(--ng); border-color: var(--ng); color: #fff; }
.btns button.clr { flex: 0 0 52px; font-size: 12px; }
.act textarea { font: inherit; font-size: 13px; color: var(--t1); background: var(--s2); border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; min-height: 38px; resize: vertical; }
.empty { color: var(--t3); padding: 30px; text-align: center; }
.help { font-size: 12px; color: var(--t3); }
</style></head>
<body>
<header>
  <h1>値台帳の確認 <span class="prog" id="prog"></span></h1>
  <div class="bar"><i id="barfill" style="width:0"></i></div>
  <div class="ctl" id="rules"></div>
  <div class="ctl">
    <label><input type="checkbox" id="pending" checked> 未判定だけ</label>
    <span id="grades"></span>
    <input type="search" id="q" placeholder="項目・値・表示・ID で検索">
    <span class="sp"></span>
    <button id="import">判定を読み込む</button><input type="file" id="file" accept="application/json" hidden>
    <button id="export" class="primary">判定を書き出す</button>
  </div>
  <div class="help">○＝採用、×＝不採用。値を直したいときはコメントに書く（例: 正しくは -8）。判定はこのブラウザに自動で保存される。終わったら「判定を書き出す」で JSON を保存し、Claude に渡す。公式の値は既定で ○。</div>
</header>
<main id="list"></main>
<script>
var DATA = __DATA__;
var KEY = 'fl-review-v1';
var saved = JSON.parse(localStorage.getItem(KEY) || '{}');
var state = {};
DATA.rows.forEach(function (r) {
  // 保存した判定は、判定したときの値が今の台帳の値と同じときだけ使う（値が変わった行は判定し直す）
  var s = saved[r.id];
  state[r.id] = (s && s.value === r.value) ? s : { verdict: r.verdict || '', comment: r.comment || '', value: r.value };
});
var RULES = DATA.rules, cur = 'all', grades = { '公式': true, '外部': true, '実測': true, '未確認': true };
function save() { localStorage.setItem(KEY, JSON.stringify(state)); }
function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
function changed(id) { var r = DATA.byId[id], s = state[id]; return s.verdict !== (r.verdict || '') || s.comment !== (r.comment || ''); }
function progress() {
  var total = DATA.rows.length, done = 0;
  DATA.rows.forEach(function (r) { if (state[r.id].verdict) done++; });
  document.getElementById('prog').textContent = '判定済み ' + done + ' / ' + total + '（未判定 ' + (total - done) + '）';
  document.getElementById('barfill').style.width = (100 * done / total) + '%';
}
function srcHtml(ids) {
  return '<ul>' + ids.map(function (id) {
    var s = DATA.sources[id] || {};
    var name = s['名称'] || id, url = s['URL'] || '';
    var link = /^https?:/.test(url) ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(name) + '</a>' : esc(name);
    return '<li><span class="id">' + esc(id) + '</span> ' + link + ' <span class="chk">' + esc([s['公開・更新'], s['対象パッチ'], s['系統']].filter(Boolean).join(' ・ ')) + '</span></li>';
  }).join('') + '</ul>';
}
function card(r) {
  var s = state[r.id];
  var el = document.createElement('div');
  el.className = 'card' + (s.verdict === '○' ? ' v-ok' : s.verdict === '×' ? ' v-ng' : '');
  el.innerHTML =
    '<div><div class="top"><span class="id">' + esc(r.id) + '</span><span class="tag">' + esc(RULES[r.rule]) + '</span>' +
    '<span class="tag">' + esc(r.group) + '</span><span class="tag g-' + esc(r.grade) + '">' + esc(r.grade) + '</span>' +
    '<span class="chk">現行確認: ' + esc(r.current_check) + ' ・ 最終変更: ' + esc(r.last_changed) + '</span></div>' +
    '<div class="top" style="margin-top:4px"><span class="lbl">' + esc(r.label) + '</span><span class="val">' + esc(r.value) + '<small>' + esc(r.unit === 'テキスト' ? '' : r.unit) + '</small></span></div>' +
    (r.condition ? '<div class="cond">' + esc(r.condition) + '</div>' : '') +
    (r.display ? '<div class="disp">ページでの表示: ' + esc(r.display) + '</div>' : '') +
    '<details><summary>根拠と出典（' + r.sources.length + '件）</summary>' +
    (r.quote ? '<div class="q">' + esc(r.quote) + '</div>' : '') +
    (r.notes ? '<div>' + esc(r.notes) + '</div>' : '') + srcHtml(r.sources) + '</details></div>' +
    '<div class="act"><div class="btns"><button class="ok' + (s.verdict === '○' ? ' on' : '') + '">○</button>' +
    '<button class="ng' + (s.verdict === '×' ? ' on' : '') + '">×</button><button class="clr">取消</button></div>' +
    '<textarea placeholder="コメント（訂正など）">' + esc(s.comment) + '</textarea></div>';
  var btn = el.querySelectorAll('.btns button');
  function set(v) { s.verdict = v; save(); progress(); el.className = 'card' + (v === '○' ? ' v-ok' : v === '×' ? ' v-ng' : '');
    btn[0].classList.toggle('on', v === '○'); btn[1].classList.toggle('on', v === '×'); }
  btn[0].onclick = function () { set(s.verdict === '○' ? '' : '○'); };
  btn[1].onclick = function () { set(s.verdict === '×' ? '' : '×'); };
  btn[2].onclick = function () { set(''); };
  el.querySelector('textarea').oninput = function (e) { s.comment = e.target.value; save(); };
  return el;
}
function render() {
  var list = document.getElementById('list'), q = document.getElementById('q').value.trim().toLowerCase();
  var onlyPending = document.getElementById('pending').checked;
  list.innerHTML = '';
  var shown = DATA.rows.filter(function (r) {
    if (cur !== 'all' && r.rule !== cur) return false;
    if (!grades[r.grade]) return false;
    if (onlyPending && state[r.id].verdict) return false;
    if (q && (r.id + ' ' + r.label + ' ' + r.value + ' ' + r.group + ' ' + (r.display || '')).toLowerCase().indexOf(q) < 0) return false;
    return true;
  });
  shown.forEach(function (r) { list.appendChild(card(r)); });
  if (!shown.length) list.innerHTML = '<div class="empty">該当する行はない</div>';
}
var rb = document.getElementById('rules');
[['all', 'すべて']].concat(Object.keys(RULES).map(function (k) { return [k, RULES[k]]; })).forEach(function (p) {
  var b = document.createElement('button'); b.textContent = p[1]; b.dataset.rule = p[0];
  if (p[0] === cur) b.classList.add('on');
  b.onclick = function () { cur = p[0]; rb.querySelectorAll('button').forEach(function (x) { x.classList.toggle('on', x === b); }); render(); };
  rb.appendChild(b);
});
var gb = document.getElementById('grades');
Object.keys(grades).forEach(function (g) {
  var l = document.createElement('label'); l.innerHTML = '<input type="checkbox" checked> ' + g;
  l.querySelector('input').onchange = function (e) { grades[g] = e.target.checked; render(); };
  gb.appendChild(l);
});
document.getElementById('pending').onchange = render;
document.getElementById('q').oninput = render;
document.getElementById('export').onclick = function () {
  var out = { ledger_generated: DATA.generated, decisions: {} };
  DATA.rows.forEach(function (r) { if (changed(r.id)) out.decisions[r.id] = { verdict: state[r.id].verdict, comment: state[r.id].comment, value: r.value }; });
  var blob = new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' });
  var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'frontline-review-' + new Date().toISOString().slice(0, 10) + '.json'; a.click();
};
document.getElementById('import').onclick = function () { document.getElementById('file').click(); };
document.getElementById('file').onchange = function (e) {
  var f = e.target.files[0]; if (!f) return;
  f.text().then(function (t) {
    var d = JSON.parse(t).decisions || {};
    Object.keys(d).forEach(function (id) { var r = DATA.byId[id]; if (r && (!d[id].value || d[id].value === r.value)) state[id] = { verdict: d[id].verdict || '', comment: d[id].comment || '', value: r.value }; });
    save(); progress(); render();
  });
};
DATA.byId = {}; DATA.rows.forEach(function (r) { DATA.byId[r.id] = r; });
progress(); render();
</script></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    ledgers, sources, errors = ledger.load_all()
    if errors:
        for e in errors:
            print("エラー:", e)
        return 1
    rows = [asdict(r) for led in ledgers for r in led.rows]
    stamp = max(p.stat().st_mtime_ns for p in ledger.LEDGER_DIR.glob("*.md"))
    data = {
        "generated": str(stamp),
        "rules": {k: v[1] for k, v in ledger.RULES.items()},
        "rows": rows,
        "sources": sources,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.replace("__DATA__", payload), encoding="utf-8")
    pending = sum(1 for r in rows if not r["verdict"])
    print(f"wrote {out}（{len(rows)} 行、未判定 {pending} 行）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
