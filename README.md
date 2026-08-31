# kobutachan-ffxiv-research

FFXIV 事業・人口の3年予測に関する分析リポジトリ。詳細は [`20260830_1/`](20260830_1/) を参照。

## エージェントスキル

複数ツール（Zed / Claude Code / Codex）で共有するスキルを `.agents/skills/` に置いている。

- `analysis-integrity` — 複数文書にまたがる分析の整合性
- `forecast-with-audit` — 監査つき予測

Zed と Codex は `.agents/skills/` を直接読む。Claude Code は `.claude/skills/` を読むため、以下で同期する:

```sh
./sync-skills.sh
```

常に効かせる共通ルールは [`AGENTS.md`](AGENTS.md) に記載している。
