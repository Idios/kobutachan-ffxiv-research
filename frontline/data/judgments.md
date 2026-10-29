# 判定の記録

ユーザーが ○／× を付けたときの値。公式でない行（外部・実測・未確認）は、採否が ○ でも、
今の値がここの「判定時の値」と違えば `python frontline/tools/ledger.py validate` がエラーにする
（値だけを直して、ユーザーが見ていない値を公開しないため）。値を直したら採否を空欄に戻し、確認用ページで判定し直してもらう。
取り込み（`frontline/tools/apply_review.py`）がこの表を書き足す。手で書き換えない。

| ID | 採否 | 判定時の値 | 判定日 | 判定のもと |
|---|---|---|---|---|
| COM-META-NEXT-EXPANSION | ○ | 2027-01 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| COM-LBB-NIN | ○ | 90 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| COM-LBB-DNC | ○ | 90 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-COUNT | ○ | 9 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-TICK | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-1 | ○ | 2 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-2 | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-3 | ○ | 6 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-4 | ○ | 10 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-5 | ○ | 12 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-6 | ○ | 14 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-7 | ○ | 18 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-8 | ○ | 20 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-RATE-9 | ○ | 22 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-CAPTURE-BONUS | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-FLAG-CAPTURE-TIME | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-SHEER-WILL-MULT | ○ | 1.5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-DRONE-COUNT | ○ | 18 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-DRONE-ALPHA-RATE | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-CMDR-PTS-UNIT | ○ | 予兆1か所の受け止めごとに24 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-CMDR-SPLIT | × | 24を受け止めた部隊の数で等分（1部隊24／2部隊12ずつ／3部隊8ずつ） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-CMDR-SPOTS | ○ | 18 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-NODE-PTS-UNIT | ○ | HPが0になるたびに150（全快5回＋撃破で最大6回） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-BH-DRONE | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-BH-ALPHA | ○ | 8 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-BH-CMDR | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-BH-NODE | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-FIRST | ○ | 40 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-DUR-DRONE | × | 50 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-DUR-CMDR | × | 70 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-DUR-NODE | × | 120 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-GAP-AFTER-CMDR | × | 175 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-GAP-AFTER-DRONE | × | 110〜130 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-GAP-AFTER-NODE | × | 150〜210 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-ORDER | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-HUD | ○ | 中央のモンスターの出現状況は専用UIで確認できる | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-HUD-NEXT | ○ | 次の出現までの残り時間（と次の種類）が表示される | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-PANEL-COUNT | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-PANEL-ONEWAY | ○ | 外周から中央への一方通行 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-PANEL-INVULN | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-KO-GAIN | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-KO-LOSS | ○ | -5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-B-TOTAL | ○ | 80 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-A-TOTAL | ○ | 120 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-S-TOTAL | ○ | 160 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-B-TICK | ○ | 2 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-A-TICK | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-S-TICK | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-TICK-SEC | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-TOME-NEUTRAL-DRAIN | ○ | 減らない | 2026-10-28 | ユーザーのコメントによる訂正（確認用ページ 2026-10-28。round2_edits.py） |
| SEI-TOME-STACK | ○ | 各リスの加算の合計（上乗せなし） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-SPAWN-FIRST-TIME | ○ | 19:30 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-SPAWN-FIRST-COUNT | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-SPAWN-REFILL-SEC | ○ | 15 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-CAP-1 | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-CAP-2 | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-CAP-SWITCH | ○ | 10:00 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-OCC-LOCKOUT-SEC | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-OCC-CAST-SEC | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-OCC-INTERRUPT | ○ | キャスト中に攻撃を受けると中断する | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-OCC-CAPTURE-BONUS | ○ | 0 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-RANK-PROB | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-RANK-NO-B-LATE | ○ | 起動しない（AとSだけ） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-RANK-MAP-SYMBOL | ○ | B＝三角形（△）／A＝ひし形（◇。四角形とも呼ぶ）／S＝五角形（⬠） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEI-RANK-COLOR | ○ | B＝青／A＝赤（頂上に赤い球）／S＝黄（頂上に細い突起） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-DEATH-LOSS | ○ | -8 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-MAP-STATES | ○ | 表示なし（破壊直後）→ 黒い影（再出現済み・停止中）→ 縁取り／光る影（予告。30秒後に起動）→ 氷のアイコン（起動中・攻撃できる） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-L-SPOTS | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-L-FIRST-WARN | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-L-REACT | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-S-DATA | ○ | 50 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-S-SPOTS | ○ | 15 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-S-FIRST-ACTIVE | ○ | 12:30 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SHA-S-REACT-RULE | ○ | 小が1個壊れるたびに、その420秒後に、黒い影が出ている地点の中から抽選で1か所に予告が出て、30秒後に起動する（2巡目は一斉ではなく順次） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-OVOO-B-TOTAL | ○ | 50 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-OVOO-A-TOTAL | ○ | 100 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-OVOO-S-TOTAL | ○ | 200 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-OVOO-B-TICK | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-OVOO-A-TICK | ○ | 10 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-OVOO-S-TICK | ○ | 20 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-OVOO-TICK-SEC | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CLAIM-DURATION | ○ | 30 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-WARN-MAPGAUGE | ○ | マップの記号の枠線がゲージになり、満ちると有効。契約済みの土地は部隊の紋章入り、未契約は枠だけ | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-SPAWN-FIRST | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-WARN-SEC | ○ | 30 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-SPAWN-REFILL | ○ | 契約が終わって待機に戻ると、別の地点の待機中の土地が予告状態になる | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-REFILL-DELAY | × | 0 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CAP-SWITCH-1 | ○ | 15 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CAP-SWITCH-2 | ○ | 10 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CAP-SWITCH-3 | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CAP-1 | ○ | 6 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CAP-2 | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CAP-3 | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CAP-4 | ○ | 2 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-NOREPEAT | ○ | 直前に契約が終わった地点には、続けて出ない | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-SITES | ○ | 13 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-RANK-PROB | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-RANK-SYMBOL | ○ | B＝青い三角形／A＝赤いひし形／S＝黄（金）色の五角形 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-RANK-MAPICON | ○ | 上空と同じ形（B三角形・Aひし形・S五角形） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| NAA-CLAIM-GUARDIAN | ○ | オブジェクトにアクセス中の味方には、ナイトのガーディアンの肩代わりが働かない（契約を実行中の味方をかばえない） | 2026-10-29 | ユーザーの指示（会話。公式の記載を採用） |
| NAA-CLAIM-CAST | ○ | 4 | 2026-10-28 | ユーザーのコメントによる訂正（確認用ページ 2026-10-28。round2_edits.py） |
| NAA-CLAIM-MULTI | ○ | 人数を増やしても契約は速くならない | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-KO-GAIN | ○ | 8 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-KO-LOSS | ○ | -8 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SPAWN-OPEN-COUNT | ○ | 6 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SPAWN-OPEN-SEC | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-ACTIVATING-SEC | ○ | 30 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SPAWN-REFILL | ○ | 制圧状態が終わって無効に戻ると、別の地点の無効な目標地が移行状態になる | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-REFILL-DELAY | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CAP-SWITCH-1 | ○ | 15 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CAP-SWITCH-2 | ○ | 10 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CAP-SWITCH-3 | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CAP-1 | ○ | 6 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CAP-2 | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CAP-3 | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CAP-4 | ○ | 2 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SPAWN-SITES | ○ | 15 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SPAWN-NOREPEAT | × | 制圧が終わった地点は、しばらく次の出現の候補から外れる | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-RANK-PROB | × | 不明 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-RANK-SHAPE | ○ | B＝青い三角形／A＝赤いひし形／S＝金色の五角形 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-OBJ-B-TOTAL | ○ | 50 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-OBJ-A-TOTAL | ○ | 100 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-OBJ-S-TOTAL | ○ | 200 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-OBJ-B-TICK | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-OBJ-A-TICK | ○ | 10 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-OBJ-S-TICK | ○ | 20 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-OBJ-TICK-SEC | × | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CLAIM-DURATION | ○ | 30 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-B | ○ | 3 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-A | ○ | 4 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-S | ○ | 5 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-SEC | ○ | 8 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-CONTEST | ○ | 他部隊のプレイヤーがサークル内にいる間は、占拠が進まない | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-RESET | ○ | 確定する前にサークルが無人になると、進みは最初に戻る | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-KEEP | ○ | 確定した後はサークルを離れてよい（次のサークルへ移れる） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-CIRCLE-OVERWRITE | ○ | 目標地の制圧が確定するまでは、他部隊が占拠したサークルを塗り替えられる | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-WX-ORDER | × | 変化なし → 雪 → 変化なし → オーロラ → 変化なし（各1回。順番は固定） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-WX-SNOW-START | ○ | 16〜15 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-WX-SNOW-SEC | ○ | 300 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-WX-AURORA-START | ○ | 10〜9 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-WX-AURORA-SEC | ○ | 150 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SNOW-STATUE-CENTER | ○ | 雪の間は、中央の盆地の三叉路が大きな雪像でふさがれ、遠回りが要る | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SNOW-STATUE-WARN | ○ | 雪像が出る場所に赤い範囲が出る。中にいるとダメージを受ける | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SNOW-BARRIER-PCT | ○ | 50 | 2026-10-28 | ユーザーのコメントによる訂正（確認用ページ 2026-10-28。round2_edits.py） |
| TRI-SNOW-BARRIER-SEC | ○ | 30 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SNOW-BARRIER-REFRESH | ○ | 効果中に受け直すと上書きされる（時間が戻る） | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-SNOW-BLESS-INTERVAL | ○ | 10 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-AURORA-NO-B | ○ | オーロラ中はランクBが出ず、AかSだけが出る | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-AURORA-LB-RATE | ○ | 2 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| TRI-AURORA-LB-STACK | ○ | 順位によるLB補正や、吟遊詩人のLB「英雄のファンタジア」と重なって効く | 2026-10-28 | ユーザーのコメントによる訂正（確認用ページ 2026-10-28。round2_edits.py） |
| TRI-START-FIXED | ○ | 部隊（グランドカンパニー）ごとに出撃地点が固定 | 2026-10-28 | 確認用ページ（frontline-review-2026-10-28.json） |
| SEC-EVT-FIRST-KIND | ○ | 邀撃システムか邀撃ドローン（邀撃コマンダーは最初に出ない） | 2026-10-28 | ユーザーのコメント（SEC-EVT-FIRST に付けたもの。確認用ページ 2026-10-28）から作った行 |
| COM-ROT-ANCHOR | ○ | 2026-04-29 | 2026-10-28 | ユーザーのゲーム内確認（IG-ROT-TODAY。10/27・10/28 のルール） |
| COM-MATCH-TIMEOUT | ○ | 残り0:00の時点のスコアの多い順に1〜3位が決まり、最も多い部隊の勝利 | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| COM-MATCH-DRAW | ○ | 2部隊以上が同時に目標値へ達すると引き分け | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| SEI-OCC-PERSIST | ○ | 続く（その場に残らなくてよい） | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| SHA-ICE-BH | ○ | 乗る | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| NAA-WARN-NOTICE | ○ | 予告が始まると、お知らせのメッセージが出る | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| NAA-CLAIM-LOOK | ○ | 柱に、部隊の紋章入りの旗が掲げられる（公式ガイドの画像は黒渦団の紋章の旗） | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| TRI-CIRCLE-DEFEND | ○ | 自部隊のプレイヤーが中にいる間は、そのサークルを他部隊は取れない（自部隊の色なら塗り替えられず、白なら占拠されない） | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| TRI-SNOW-BLESS-TIMING | ○ | 範囲の中の円がゆっくり満ちていき、満ちたときに範囲の中にいるプレイヤーに付く（入ってすぐには付かない） | 2026-10-29 | 確認用ページ（frontline-review-2026-10-29.json） |
| SEC-BH-ALPHA-WHO | ○ | 最も多くのダメージを与えたパーティのメンバー全員 | 2026-10-29 | ユーザーの指摘（会話。α もドローンと同じく最多ダメのパーティ） |
