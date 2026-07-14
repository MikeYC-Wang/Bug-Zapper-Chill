# 🐛⚡ Bug-Zapper & Chill

<div align="center">

<img src="./profile-hud.svg" alt="Bug-Zapper & Chill hardware HUD dashboard" width="850" />

**一個會即時反映我 GitHub 活動的賽博朋克黑金硬體控制台**
*(如果上面的圖還沒出現，代表 [HUD Updater](.github/workflows/hud-updater.yml) 尚未跑過第一次)*

</div>

---

## 這是什麼？

`Bug-Zapper & Chill` 是一個完全原創的 GitHub Profile 動態數據面板專案。它會每天自動：

1. 透過 GitHub GraphQL API v4 撈取過去 365 天的 Contribution Calendar 矩陣。
2. 用純 Python 字串格式化（**沒有** matplotlib / Pillow 等繪圖庫）手工拼接原生 SVG。
3. 產生一張 `profile-hud.svg`，畫出三大硬體核心組件：

| 組件 | 說明 |
|---|---|
| 🧊 **中央 3D 晶片矩陣** | 把 52 週 × 7 天的 Commit 紀錄以等角投影 (isometric projection) 繪製成立體晶片方塊陣列，Commit 越多、晶片越高、顏色越接近發光琥珀金。 |
| 🧪 **過熱液態冷卻循環系統** | 模擬一顆連接 CPU 水冷頭的儲液冷卻循環，液面高度與溫度會隨著今日 Commit 數量動態變化（`24°C [STANDBY]` ~ `84°C [OVERCLOCK]`）。 |
| ⚡ **Bug 誘捕電磁防禦塔** | 一座會發射閃電的特斯拉線圈塔，每天用你的 Commit 數量計算出「今日消滅的 Bug 數量」，順便電爆一隻 `NullPointerException`。 |

整個畫面每天由 [GitHub Actions](.github/workflows/hud-updater.yml) 自動重新產生並提交回 `main`，不需要手動維護。

---

## 專案結構

```
Bug-Zapper-Chill/
├── generate_hud.py                 # 核心：抓資料 + 手工拼接 SVG
├── profile-hud.svg                 # 自動產生的輸出（由 workflow 每日覆寫）
├── .github/workflows/hud-updater.yml   # 每日排程自動化工作流
└── README.md
```

---

## 如何在自己的 Profile 套用

1. **建立一組 Personal Access Token (classic)**，至少需要 `read:user` 權限（若倉庫為私有可另加 `repo`）。
2. 到本倉庫 **Settings → Secrets and variables → Actions**，新增一個名為 `GH_PAT` 的 Repository secret，貼上剛剛的 Token。
3. （選用）若要監控其他使用者，可在 workflow 中調整 `HUD_USERNAME` 環境變數，預設為 `MikeYC-Wang`。
4. 手動觸發一次 **Actions → HUD Updater → Run workflow**，確認 `profile-hud.svg` 有被正確產生並提交。
5. 之後每天 UTC 16:00（台灣時間 00:00）都會自動重新整理。

若要在自己的個人 Profile README（`<username>/<username>` 倉庫）嵌入這張圖，可直接引用本倉庫產生的 raw SVG：

```markdown
![Bug-Zapper & Chill HUD](https://raw.githubusercontent.com/MikeYC-Wang/Bug-Zapper-Chill/main/profile-hud.svg)
```

---

## 本機測試

```bash
pip install requests
set GH_PAT=ghp_xxxxxxxxxxxxxxxxxxxx      # PowerShell: $env:GH_PAT="ghp_xxx"
set HUD_USERNAME=MikeYC-Wang
python generate_hud.py
```

執行成功後會在專案根目錄產生 `profile-hud.svg`。

---

## 技術重點

- **零繪圖依賴**：所有視覺元素（等角投影方塊、發光濾鏡、漸層、閃電折線）都是原生 `<svg>` 標籤字串拼接，沒有任何點陣圖或第三方繪圈函式庫。
- **等角投影公式**：
  $$x_{iso} = (x - y)\cos(30°) + offset_x$$
  $$y_{iso} = (x + y)\sin(30°) - z + offset_y$$
  每個晶片方塊由頂面 / 左側面 / 右側面三個 `<polygon>` 以不同明暗係數組成立體光影。
- **失敗即失敗，不造假**：資料撈取失敗時腳本會直接以非零狀態碼結束，不會用假資料生成誤導性的 HUD。

---

<div align="center">

**ENGINEER: MikeYC-Wang** · SYSTEM STATUS: ONLINE

</div>
