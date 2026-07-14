# 🐛⚡ Bug-Zapper & Chill

<div align="center">

[繁體中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

</div>

<div align="center">

<img src="./profile-hud.svg" alt="Bug-Zapper & Chill hardware HUD dashboard" width="850" />

**私の GitHub アクティビティをリアルタイムに反映する、サイバーパンクなブラック＆ゴールドのハードウェアコンソール**
*(上の画像がまだ表示されない場合は、[HUD Updater](.github/workflows/hud-updater.yml) がまだ一度も実行されていません)*

</div>

---

## これは何？

`Bug-Zapper & Chill` は完全オリジナルの GitHub プロフィール用ダイナミックダッシュボードプロジェクトです。毎日自動的に：

1. GitHub GraphQL API v4 経由で過去 365 日分の Contribution Calendar 統計を取得します。
2. 純粋な Python の文字列フォーマットのみで（matplotlib / Pillow などの描画ライブラリは**一切使用せず**）、ネイティブな SVG を手作業で組み立てます。
3. `profile-hud.svg` を生成し、左右 2 つのハードウェアコアコンポーネントを描画します：

| コンポーネント | 説明 |
|---|---|
| 🧪 **オーバーヒート液冷ループシステム** | CPU ウォーターブロックに接続された矩形ループ型リザーバー。冷却液の液面、上昇する気泡アニメーション、PUMP SPEED / COOLANT TEMP / SYS PRESSURE の数値は、その日のコミット数に応じて動的に変化します（`24°C [STANDBY]` ～ `84°C [OVERCLOCK]`）。 |
| ⚡ **EM バグ捕獲防衛タワー** | 稲妻を放つ円錐形の防衛タワー。毎日あなたのコミット数から「今日撃破したバグの数」を計算し、もがき苦しむ黄色いバグと `NullPointer` 例外を電撃で撃ち抜きます。 |

この画像は毎日 [GitHub Actions](.github/workflows/hud-updater.yml) によって自動的に再生成され、`main` ブランチにコミットされます。手動でのメンテナンスは一切不要です。

---

## プロジェクト構成

```
Bug-Zapper-Chill/
├── generate_hud.py                 # コア：データ取得 + SVG 手動組み立て
├── profile-hud.svg                 # 自動生成される出力（workflow が毎日上書き）
├── .github/workflows/hud-updater.yml   # 毎日のスケジュール自動化ワークフロー
└── README.md
```

---

## 自分のプロフィールで使う方法

1. **Personal Access Token (classic) を作成**します。最低でも `read:user` 権限が必要です（対象リポジトリがプライベートの場合は `repo` 権限も追加してください）。
2. 本リポジトリの **Settings → Secrets and variables → Actions** で、`GH_PAT` という名前のリポジトリシークレットを新規作成し、先ほどのトークンを貼り付けます。
3. （任意）別のユーザーを監視したい場合は、workflow 内の `HUD_USERNAME` 環境変数を変更してください（デフォルトは `MikeYC-Wang`）。
4. **Actions → HUD Updater → Run workflow** を一度手動実行し、`profile-hud.svg` が正しく生成・コミットされることを確認してください。
5. その後は毎日 UTC 16:00（台北時間 0:00）に自動的に更新されます。

自分の個人プロフィール README（`<username>/<username>` リポジトリ）にこの画像を埋め込むには、本リポジトリが生成する raw SVG を直接参照してください：

```markdown
![Bug-Zapper & Chill HUD](https://raw.githubusercontent.com/MikeYC-Wang/Bug-Zapper-Chill/main/profile-hud.svg)
```

---

## ローカルでのテスト

```bash
pip install requests
set GH_PAT=ghp_xxxxxxxxxxxxxxxxxxxx      # PowerShell: $env:GH_PAT="ghp_xxx"
set HUD_USERNAME=MikeYC-Wang
python generate_hud.py
```

成功すると、プロジェクトのルートディレクトリに `profile-hud.svg` が生成されます。

---

## 技術的なポイント

- **描画ライブラリ依存ゼロ**：ループ配管、発光フィルター、グラデーション、稲妻のジグザグ線など、すべての視覚要素はネイティブな `<svg>` タグ文字列の手組みで作られており、ラスター画像やサードパーティの描画ライブラリは一切使用していません。
- **動的に連動するデータ**：冷却システムと防衛タワーの数値はすべて「今日のコミット数」からリアルタイムに計算されており、ハードコードされた静的な値ではありません。
- **失敗は失敗として扱う、偽装はしない**：データ取得に失敗した場合、スクリプトは即座に非ゼロの終了コードで終了し、偽のデータで誤解を招く HUD を生成することはありません。

---

<div align="center">

**ENGINEER: MikeYC-Wang** · SYSTEM STATUS: ONLINE

</div>
