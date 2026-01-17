# 公式Skills（agent-contracts 利用者向け）

これらの skills は、**`agent-contracts` で実際のAIエージェントを作る人**向けに設計されています。
このリポジトリの API / 例 / 設計方針に合わせた、実務寄りのワークフローとガードレールを含みます。

## Skill Packs

- `docs/skills/official/agent-contracts-app-builder/`（全体設計/立ち上げ）
- `docs/skills/official/agent-contracts-backend-runtime/`（API/SSE ランタイム）
- `docs/skills/official/agent-contracts-routing-tuning/`（ルーティング設計/デバッグ）
- `docs/skills/official/agent-contracts-interactive-flow/`（複数ターンQ/A）
- `docs/skills/official/agent-contracts-tool-use-rag/`（services/tools/RAG）
- `docs/skills/official/agent-contracts-contracts-ci/`（CI 検証/diff/可視化）

## 使い方

利用しているエージェントツールに合わせて、ファイルを読み取り場所へコピーします：

- Codex Skills: skills ディレクトリへコピーし、各パックの `SKILL.md` を使う
- その他のエージェント（Claude Code 等）: プロジェクトの指示ファイル（例: `CLAUDE.md`）へ内容をコピーし、参照先の docs/examples も近くに置く

## 言語

各パックには以下が含まれます：

- `SKILL.md`（English）
- `SKILL.ja.md`（日本語）

多くの skill システムは「エントリーファイルが1つ」「skill名がユニーク」を要求します。
コピーする際は、どちらか一方の言語を選んで使ってください（必要なら `SKILL.md` にリネーム）。

