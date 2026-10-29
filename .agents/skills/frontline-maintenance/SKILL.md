---
name: frontline-maintenance
description: FF14 フロントライン早見表（frontline/）の値台帳を、パッチや HotFix の後に調査・検証・更新し、ページを作り直すときに使う。調査方法、等級と出典の扱い、更新手順、検査を定める。
---

# フロントライン早見表の保守

FF14 フロントラインの早見表（ルール別5ページ＋今日のルールを出すトップページ）を保守する手順。
ページは**値台帳（Markdown の表）だけ**から生成する。保守とは、台帳を現行パッチに合わせ続けることである。

## 使う場面

- 新しいパッチや HotFix が出たとき（特に PvP・フロントラインの変更があるとき）
- ユーザーが確認用ページで書き出した判定（`frontline-review-日付.json`）を渡したとき、または台帳の「採否」列に ○／× を、「コメント」列に訂正を直接書いたとき
- ゲーム内確認の結果が [ゲーム内確認リスト](../../../frontline/data/ingame-checks.md) に記入されたとき

## ファイルの地図

| パス | 役割 |
|---|---|
| `frontline/data/ledger/<rule>.md` | 値台帳（正典）。rule は common / secure / seize / shatter / naadam / triumph |
| `frontline/data/sources.md` | 出典台帳。値台帳の「出典」列の ID を引く |
| `frontline/data/ingame-checks.md` | ゲーム内でしか確かめられない値の確認手順と結果 |
| `frontline/data/official/<出典ID>.md` | 公式（スクウェア・エニックス）の原文抜粋。© SQUARE ENIX |
| `frontline/tools/ledger.py` | 台帳の検証（`validate`）と JSON 出力（`export-json`） |
| `frontline/tools/check_official.py` | 公式の行の原文抜粋が、公式ページに今も載っているかを照合する（パッチ後に最初に回す） |
| `frontline/tools/review_page.py` | ユーザーが ○×・コメントを付ける確認用ページを台帳から作る |
| `frontline/tools/apply_review.py` | 確認用ページで書き出した判定（JSON）を台帳の「採否」「コメント」に取り込む |
| `frontline/data/README.md` | ユーザー向けの台帳の見方（○×・コメントの付け方） |
| `frontline/data/retired.md` | 旧値の登録簿。値を訂正・撤回したら1行足す（公開ページに残っていないことを検査する） |
| `frontline/data/judgments.md` | 判定の記録（ユーザーが ○／× を付けたときの値）。`apply_review.py` が書く。公式でない ○ の行は、値がこれと違うと validate が止まる |
| `frontline/tools/build.py` | 台帳から公開ページを生成する（○ の行しか使えない。× や空欄の行を参照すると止まる） |
| `frontline/tools/pages.py` | ルール別のページの中身（どの行をどのカードに出すか）。数を書かない |
| `frontline/assets/` | 見た目（`site.css`）、自作のアイコン（`icons.svg`）、公式サイトの画像（`img/`、出どころは `img/SOURCES.tsv`） |
| `frontline/index.html` ほか | 生成物（トップ＝今日のルール、`<rule>/`、`jobs/`、`sources/`）。手で直さない |
| `frontline/README.md` | 公開向けの説明（使い方・データの方針・間違いの知らせ方・権利）。各ページの下の「このサイトについて」からリンクする。素材や方針を変えたら直す |
| `tests/frontline/` | 自動検査（数字の出どころ・× の行と旧値の不在・変異テスト・表示領域ごとのスクロールなしと文字の下限・今日のルール） |
| `reports/20261027_1/plan.md` | 設計の経緯（目的、ゴール、決定事項） |
| `reports/20261027_1/ledger-build/` | 初回（2026-10-27〜28）の台帳作成の記録（作成役・検証役の出力、手作業の修正 `manual-edits.json`） |

モック（`reports/20261027_1/mock/`）は捨て前提の試作で、保守の対象ではない。

## よく使うコマンド

```sh
python frontline/tools/ledger.py validate                       # 台帳の検査（エラー 0 になるまで直す）
python -I frontline/tools/check_official.py                     # 公式の行の原文照合（不一致 0 を確認）
python -I frontline/tools/check_official.py --rule seize        # ルールを絞って照合
python frontline/tools/ledger.py set-display <ID> <表示文>        # ページに出す短い言い方を書き直す（値を変えたあと）
python frontline/tools/build.py                                 # 公開ページを作り直す
python frontline/tools/build.py --check                         # 生成物が台帳と合っているかだけ確かめる
python -m pytest tests/frontline                                # 自動検査（ブラウザの検査は Chrome か Edge が要る）
python frontline/tools/review_page.py                           # 確認用ページを作る（reports/20261027_1/review/index.html）
python frontline/tools/apply_review.py <判定.json> --dry-run      # 判定の取り込みを試す（台帳は変えない）
python frontline/tools/apply_review.py <判定.json>                # 判定を台帳の「採否」「コメント」に取り込む
```

照合で「不一致」が出たら、公式ページの記述が変わった可能性がある。抜粋を取り直し、値が変わっていれば更新手順（references/update-procedure.md）に進む。

## 守ること

1. **値は台帳にだけ書く。** ページ、テンプレート、スクリプトに数値を手で書かない。1分あたりや合計などの派生値は、生成時に台帳から計算する（リポジトリの AGENTS.md 規約1）。
2. **公式以外の値は、ユーザーの ○ がなければページに出さない。** 公式の値は誤りがない前提で、原文照合が済めば ○ にしてよい。
3. **等級は4つだけ。**
   - 公式: 公式ガイド、パッチノート、ジョブガイド、HotFix 告知など、スクウェア・エニックスの公表値
   - 外部: 公式ではないが、現行期の互いに独立した2系統以上の資料で一致する値
   - 実測: ユーザーがゲーム内で確認した値（確認日とパッチを残す）
   - 未確認: 上のどれでもない値（1系統だけ、食い違い、古い資料のみ）
4. **現行確認を必ず更新する。** 書式は「7.57 ✔公式」「7.5期 △外部2系統」「？外部1系統」など。パッチが変わったら、確かめた行だけを新しいパッチ番号にする。確かめていない行の番号を上げない。
5. **第三者の文章を写さない。** 外部資料は URL・日付・要約だけを残す。公式の文は短い抜粋を保存してよい（非商用・© SQUARE ENIX 表記が条件）。
6. **外部ツールとデータ抽出を使わない。** ACT・Dalamud・オーバーレイ由来の情報や、クライアントから抜き出したデータ（XIVAPI の CSV など）は、出典にも裏付けにも使わない。ゲーム内ヘルプの文は、ユーザーのゲーム内確認で置き換える。
7. **撤回・訂正は全ファイルに伝える。** 値を変えたら、旧値がページや他の台帳に残っていないかを検査する（analysis-integrity スキルの不在検査）。
8. **収束を主張しない。** 報告では、何を確かめ、何を確かめていないかを書く。
9. **表示文は値を言い換えるだけ。** ページの短い言い方（台帳の「## 表示文」）に、値にない事実や数を足さない。値を変えたら表示文も見直す（`set-display`）。
10. **文字の下限と1画面を守る。** 文字は画面上で24px以上（ユーザーの指示「文字は倍でいい」）、どのページもスクロールなしで1画面。行を足すときは、何かを削るか短くして `tests/frontline` を通す。
11. **公式でない値を直したら、採否を空欄に戻す。** 外部・実測・未確認の行は、ユーザーが ○ を付けたときの値が判定の記録（`frontline/data/judgments.md`）にあり、値だけを直すと validate が止まる。空欄に戻して確認用ページで判定し直してもらう（ユーザーが見ていない値を公開しない）。
12. **長さと時刻を書き分ける。** 時刻は残り時間（20:00→0:00）だけを「分:秒」で書く。長さ・待ち時間は「N秒」「N分」（続く長さは「N秒間」、待ち時間は「N秒後」）。
13. **数には何の数かが分かる単位を付ける。** 得点は「戦術値」「情報値」「戦略値」、時間あたりは「40/分」「2/3秒毎」、1体・1か所あたりは「戦術値/体」など（2026-10-29 ユーザーの指示「ぱっと見なんの数字か分からない」）。
14. **等級はページに出さない。** 等級は台帳にだけ残す（2026-10-29 ユーザーの指示。`build.py` の `SHOW_GRADES = False`）。ページの下の「© SQUARE ENIX」は著作物利用条件 3-1 で必要なので消さない。権利・出典の説明は `frontline/README.md` に書く。
15. **ゲームの用語は公式の日本語の表記で書く。** 通称（「リス」「氷」「枯れる」など）は使わない。名前は「アイスドトームリス」（「アイスドーム」ではない）、ランクは「ランクB」の語順。同じページに正式名があれば「土地」「目標地」のような自然な省略はよい。狭い列見出しの「与ダメ」「被ダメ」「LB」は略のまま。「撃破」「被撃破」はユーザーの指定（公式サイトの文はプレイヤーに「ノックアウト」を使う）。点検の記録は `reports/20261027_1/ledger-build/terms/`。

## 手順書

- 調査のしかた: [references/research-method.md](references/research-method.md)
- パッチ後の更新手順: [references/update-procedure.md](references/update-procedure.md)

## 検証（完了を報告する前に）

- [ ] `python frontline/tools/ledger.py validate` がエラー 0
- [ ] 変えた行の「現行確認」「最終変更」「出典」が更新されている
- [ ] 公式の行には原文抜粋があり、`frontline/data/official/` に保存されている
- [ ] 旧値を `frontline/data/retired.md` に足し、`python -m pytest tests/frontline` が通る（旧値の不在・スクロールなし・文字の下限）
- [ ] `python frontline/tools/build.py` で作り直し、`--check` が「生成物は最新」
- [ ] 変えた行の一覧をユーザーに示し、○／× をもらった
