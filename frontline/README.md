# FF14 フロントライン早見表

FINAL FANTASY XIV の PvP「フロントライン」の数値を、ルールごとに1画面（フルHD・スクロールなし）にまとめた早見表です。トップページには、その日のルールが出ます。

- ページ: <https://idios.github.io/kobutachan-ffxiv-research/frontline/>
- 個人が作っている非公式のファンサイトです。スクウェア・エニックスとは関係ありません。
- 非商用です。広告・寄付の募集・スポンサーのリンクは置いていません。

## 使い方

- トップページは今日のルールです（日本時間の日付で決まります）。日付が変わったら、再読み込みすると切り替わります。
- 右上のタブで、ほかのルール・ジョブ補正の一覧・出典の一覧に移れます。
- 右下の「ジョブ補正」で自分のジョブのアイコンを押すと、そのジョブの補正値がすぐ下に出ます（3つまで。選んだジョブはこのブラウザに記憶されます）。

## データについて

- ページの数値は、すべて値台帳（[data/](data/)）から自動で作っています。ページに手で書いた数字はありません。
- 基本は公式の情報（公式サイトのプレイガイド・パッチノートなど）です。公式に書かれていない値は、ゲーム内で確かめた値か、独立した複数の資料が一致した値を、管理者が確認してから載せています。
- 値ごとの根拠（公式・ゲーム内で確認・外部の資料・計算）と出典は台帳に記録しています。見やすさを優先して、ページには出していません。出典の URL と確認日は、各ページの「出典」から見られます。
- どのパッチの時点のデータかは各ページ右上の「データ … 時点」に、確認した日付はページの下に出ています。パッチで値が変わることがあります。

## 間違いを見つけたら

[GitHub の Issues](https://github.com/Idios/kobutachan-ffxiv-research/issues) で知らせてください。確かめて直します。

どのページのどの値か、正しいと思う値と、その根拠（公式ページの URL や、ゲーム内で見た状況）があると助かります。

## 権利について

FINAL FANTASY XIV に関する画像・文章・情報の権利は、スクウェア・エニックスにあります。

© SQUARE ENIX

- スクウェア・エニックスの「[ファイナルファンタジーXIV 著作物利用条件](https://support.jp.square-enix.com/rule.php?id=5381&la=0&tag=authc)」（2026年10月14日改訂版で確認）に従って使っています。
  - 非商用で使っています。
  - 各ページの下に「© SQUARE ENIX」を表記しています（条件の 3-1 で、ページごとに1か所の表記が求められています）。
  - 日本のプレイヤー向けに、日本語で作っています。
  - スクウェア・エニックスから依頼があれば、すぐに掲載をやめます。
- 使っている公式の素材:
  - 画像: ルールの見出しの画像、ジョブ・ロールのアイコン、リミットブレイクのアイコン、戦意高揚のアイコン。いずれも公式サイトの画像です（取得元の一覧は [assets/img/SOURCES.tsv](assets/img/SOURCES.tsv)）。
  - 文章・情報: 公式サイトのプレイガイド・パッチノートなど（値の根拠にした原文の抜粋は [data/official/](data/official/)）。
- ランクの図形、中央の中立モンスター・アイスドトームリス・天候の絵は、自作の簡単な図です（[assets/icons.svg](assets/icons.svg)）。
- ゲームのクライアントから抜き出したデータ・画像や、外部ツール（ACT・Dalamud など）で得た情報は使っていません。
- ほかのファンの資料（wiki・Lodestone の日記など）は、数値を確かめるために出典つきで参照しただけです。文章や表は写していません。
- このリポジトリの MIT ライセンス（[LICENSE](../LICENSE)）は、作者が書いたコード（ページを作るツールなど）に適用されます。スクウェア・エニックスの著作物と、ほかの方の著作物には及びません。

## 作り方・保守（開発者向け）

- 台帳の見方・確認のしかた・ページの作り方・検査: [data/README.md](data/README.md)
- パッチ後の更新手順: [.agents/skills/frontline-maintenance/](../.agents/skills/frontline-maintenance/)

## 言語（Languages）

日本語・English・Deutsch・Français で見られます（`/frontline/ja/`・`/en/`・`/de/`・`/fr/`）。入口の `/frontline/` は、ブラウザの言語の版を開きます（対応していない言語なら英語）。各ページの下の JA / EN / DE / FR で切り替えると、その言語を記憶します。英語・ドイツ語・フランス語の文は自動翻訳で、ゲームの用語だけは各言語の公式サイトの表記を使っています。

---

## About this site (English)

A one-screen-per-mode cheat sheet for FINAL FANTASY XIV Frontline (PvP). The top page shows today's mode.

- Pages: <https://idios.github.io/kobutachan-ffxiv-research/frontline/> (日本語: `/frontline/ja/`, English: `/frontline/en/`, Deutsch: `/frontline/de/`, Français: `/frontline/fr/`)
- An unofficial, non-commercial fan site by an individual player. Not affiliated with Square Enix. No ads, donations or sponsorship.
- Languages: the entry page `/frontline/` opens the version matching your browser language (English if unsupported). Switching with JA / EN / DE / FR at the bottom of each page is remembered in your browser.
- Translations of the English, German and French pages are machine-made. Game terms (maps, modes, jobs, Limit Breaks, objects) are copied from each language's official Lodestone guides and job guides.
- All values are generated from a value ledger ([data/](data/)), mostly from official sources; other values are shown only after the maintainer checked them. Sources: the "Sources" page.
- Found a mistake? Please open a [GitHub Issue](https://github.com/Idios/kobutachan-ffxiv-research/issues) (any language).

### Rights

Images, text and information about FINAL FANTASY XIV belong to Square Enix.

© SQUARE ENIX

- Used under Square Enix's materials usage policies for FINAL FANTASY XIV ([Japan](https://support.jp.square-enix.com/rule.php?id=5381&la=0&tag=authc); North America and Europe versions effective October 14, 2026), non-commercially, with "© SQUARE ENIX" on every page. Material will be removed promptly on request from Square Enix.
- Official materials used: mode header images, job/role icons, the Limit Break icon and Battle High icons from the official site (list: [assets/img/SOURCES.tsv](assets/img/SOURCES.tsv)); text and information from the official guides and patch notes. Rank shapes and illustrations of monsters, tomeliths and weather are simple self-made drawings ([assets/icons.svg](assets/icons.svg)).
- No datamined client data and no third-party tools (ACT, Dalamud, …) are used. Fan resources were consulted only to check values, with citations; their text is not copied.
- The repository's MIT license covers only the author's code, not Square Enix's or anyone else's material.
