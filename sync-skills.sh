#!/bin/sh
# sync-skills.sh — 正典 .agents/skills/ を Claude Code 用 .claude/skills/ へミラーする。
#
# Zed と Codex は .agents/skills/ を直接読むため、このスクリプトは Claude Code 専用。
# .claude/skills/ は派生物なのでコミットしない（.gitignore 済み）。

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC="$SCRIPT_DIR/.agents/skills"
DST="$SCRIPT_DIR/.claude/skills"

mkdir -p "$DST"
rm -rf "$DST"/*
cp -R "$SRC"/. "$DST"/

echo "同期しました: $SRC -> $DST"
