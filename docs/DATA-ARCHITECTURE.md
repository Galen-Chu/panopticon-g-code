# Data Architecture & Inner-Axis Route C Design · 資料架構與內觀軸路線 C 設計

> Status · 狀態：Phase A/B4 已實施；Route C 的 C-1（Journal 端內觀管線）已於
> 2026-11-18 上線（Obsidian_Journal `panopticon-inner.yml`），C-2 起未實作。
> Evaluated · 評估日期：2026-11-18

---

## 1. Data Inventory · 資料盤點

| Dataset | Location · 位置 | Visibility | Retention · 保留 | Producer → Consumer |
|---|---|---|---|---|
| `data/monitor/health_*.json` | this repo (committed by CI) | **public** | daily files; compacted monthly | `outer.monitor.checker` → alerter / dashboard / correlator |
| `data/monitor/monthly_YYYYMM.ndjson` | this repo | **public** | forever (12/yr) | `outer.monitor.compact` → future trend charts |
| `data/state/alerts.json` | this repo (CI) · local | **public** (ecosystem metadata only) | rolling | alerter → tracking issue |
| `data/alerts/alerts_*.json` | local only (gitignored) | private | ad hoc | alerter (local runs) |
| `data/journal/*.json` | local only (gitignored) | **private — personal** | forever | `inner.journal.cli` → patterns / insights |
| `data/insights/*.json` | local only (gitignored) | **private — derived from journal** | forever | insights / correlator |

**隱私鐵律 Privacy rule**：journal 原始資料與一切由它衍生的洞察（insights、
correlations）**永遠不進 public repo**。Outer 軸資料（生態健康）本來就公開
（GitHub API 上的公開事實），可自由入庫。

---

## 2. Format Contracts · 格式契約

共通規則（與 Obsidian_Library 的報告契約對齊）：

- **Timestamps**: UTC ISO-8601 with offset. 日期判定一律取檔名前綴，不用
  API 回傳的 `created_at`（UTC 跨日會差一天）。
- **Idempotency 先查再寫**: same-day same-name file exists → skip, never overwrite.
- **Encoding**: UTF-8 (no BOM), LF.

### 2.1 Health report · 健康報告 (`health_YYYYMMDD_HHMMSS.json`)

```json
{ "timestamp": "...", "total_repos": 10, "healthy": 10, "issues": 0,
  "ci_failing": 2, "repos": [ { "repo": "...", "status": "healthy",
  "stars": 0, "open_issues": 0, "last_push": "...", "default_branch": "main",
  "size_kb": 0, "ci": { "status": "ok|failing", "checked_runs": 15,
  "failed_runs": 0, "threshold": 2, "last_failure": null } } ] }
```

### 2.2 Monthly rollup · 月度整併 (`monthly_YYYYMM.ndjson`)

每日報告逐行 NDJSON，依 `timestamp` 排序、去重。由 `outer.monitor.compact`
在每月 1 號產生；遲到的補檔會自動併入（self-healing）。

### 2.3 Alert state · 警報狀態 (`data/state/alerts.json`)

```json
{ "updated": "...",
  "anomalies": { "<type>:<repo>": { "type": "ci_failing", "repo": "...",
    "level": "warning", "first_seen": "...", "last_seen": "...",
    "message_en": "...", "message_zh": "..." } },
  "recently_resolved": { "<type>:<repo>": { "resolved_at": "...",
    "duration_days": 5 } } }
```

Anomaly types: `repo_unhealthy` / `ci_failing` / `high_issues` / `stale`。
Key = `<type>:<repo>`，狀態變化（new / resolved）才觸發 issue 寫入。

### 2.4 Journal entry · 日誌（現行本機格式）

```json
{ "date": "YYYY-MM-DD", "timestamp": "...",
  "prompt": { "en": "...", "zh": "..." }, "entry": "free text" }
```

---

## 3. Route C Evaluation · 路線 C 評估結論

**結論：可行，且基礎建設已存在 — 但方向要反過來。**

### 3.1 Vault 現況調查（2026-11-18）

**Obsidian_Library**（知識庫，INGEST→COMPILE→QUERY）：

| Capability | Finding |
|---|---|
| Hosting | GitHub `Galen-Chu/Obsidian_Library` — **private** ✓（未認證 API 404；認證後 `private: true`） |
| Automation | GitHub Actions 已每日兩跑 `import-reports.yml`（pull 模型，冪等 + backfill 自癒） |
| Cross-repo auth | PAT pattern 已建立：repo secrets `TASK_SCHEDULE_TOKEN` / `SYNC_G_CODE_TOKEN` |
| Monthly aggregation | `compile-monthly.yml` 已存在（每月 1 號聚合 `raw/reports/` → `wiki/derived/`） |
| Conventions | 每日筆記 `YYYY-MM-DD.md`、frontmatter（`created`/`tags`/`aliases`）、wikilink、小寫連字號標籤、`templates/reflex.md`（反身思考模板，與內觀軸同源） |
| Guards | pre-commit 擋亂碼／機密／檔名契約 |

**Obsidian_Journal**（日記庫 — 個人日誌的真正源頭）：

| Capability | Finding |
|---|---|
| Hosting | GitHub `Galen-Chu/Obsidian_Journal` — **private** ✓，**內含公司工作內容**（嚴禁公開） |
| Structure | `daily/work|life|dream/` 三軌 + `weekly|monthly|yearly/` 同構；`scripts/journal.py` 建條目（冪等） |
| Sync | 本機 Windows 排程 `ObsidianJournalSync` **每日 17:00** pull--rebase→commit→push；`sync.ps1` 同步原語 |
| Cloud automation | `weekly-digest.yml`（週六 09:37 UTC+8 雲端彙整並推送）、`monthly-digest.yml` — **私有資料上雲端計算的先例已存在** |
| Write discipline | 只 append 不改寫、Session Log、先查再寫（stable key + `<!-- digest:... -->` 標記區塊） |
| AI boundary | work 軌為公司內容 → **任何第三方 API（含 Gemini）不得讀取 work 軌** |

### 3.2 關鍵推論：方向反轉 + 落點修正

原本的設想是「panopticon 的 CI 去 checkout 私有 vault」——**不可行也不該做**：

- panopticon 是 public repo。public repo 的 Actions **logs 與 artifacts 對所有人可見**，
  即使 secrets 不外洩，journal 內容與衍生洞察可能在 log 中曝光 → 違反隱私鐵律。
- `GITHUB_TOKEN` 不能跨 repo；放 PAT 進 public repo secrets 技術上可行，但計算
  結果仍會寫回 public repo → 一樣違反隱私鐵律。

第二個修正（2026-11-18 補充調查後）：內觀管線落點是 **Obsidian_Journal**，
不是原本藍圖中的 Obsidian_Library。理由：

1. **資料源頭在 Journal**——daily 條目（work/life/dream）都在 Journal repo，
   本機每日 17:00 已自動同步上 GitHub；在 Library 跑等於多一次跨私有 repo
   checkout（多一個 PAT 耦合），資料繞遠路。
2. **私有資料上雲端計算的先例就在 Journal**——`weekly-digest.yml` 已在
   Journal 的 Actions 裡讀 repo 內容、計算、推送回 repo。
3. **Library 維持知識庫角色**——若未來要把 panopticon 洞察編譯進 wiki，
   走 Library 既有的 artifact-import 模式收一條新串流即可（C-4，選配）。

**隱私邊界再加一條**：Journal 的 `daily/work/` 是公司工作內容——
**模式分析與 Gemini 只讀 `daily/life/` 與 `daily/dream/`，work 軌永遠排除**。
（工作情緒對個人覺察也是雜訊；公司內容更不可進第三方 API。）

```
┌─ public ─────────────────────┐      ┌─ private: Obsidian_Journal ──────┐
│ panopticon-g-code            │      │  panopticon-inner.yml (新):      │
│  daily.yml: outer monitor    │      │   1. checkout self (life/dream)  │
│   → health_*.json committed  │─────▶│   2. checkout panopticon (程式碼 │
│   → alerts / state           │ read │      + 公開健康資料)              │
│                              │ only │   3. patterns → insights (Gemini) │
│ 本 repo 提供: outer 資料 +    │      │   4. 跨軸 correlation             │
│ inner 模組程式碼（公有程式、  │      │   5. 寫入 panopticon/ 資料夾      │
│ 私有資料）                    │      │      （先查再寫、帶標記區塊）      │
└──────────────────────────────┘      └──────────────────────────────────┘
        ┌─ private: Obsidian_Library（角色不變）────────────────┐
        │ 未來 (C-4 選配): 以既有 import-reports 模式收一條      │
        │ panopticon 串流，編譯進 wiki/                          │
        └────────────────────────────────────────────────────────┘
```

排程設計：Journal 本機同步 17:00（UTC+8）→ 內觀管線 **10:23 UTC（18:23 台北）**
——當日條目已同步、當日 outer 報告（09:23 台北）已 commit，兩軸資料都到齊。

### 3.3 Journal-side data design · Journal 端資料設計

遵循 Obsidian_Journal 既有架構（`<periodicity>/<track>/`，先週期後軌道；
只 append、先查再寫、標記區塊）：

- **輸入（不新增檔案）**：直接讀 `daily/life/YYYY-MM-DD.md` 與
  `daily/dream/dream_YYYY-MM-DD.md`（dream 帶檔名前綴）的條目內文；
  管線內的轉接器把 MD 轉成 analyzer 的輸入格式（in-memory，不寫側車檔
  ——日記是人的領域，機器不回寫）。work 軌永遠排除（§3.2 隱私邊界）。
- **產出位置**：`daily/panopticon/`——daily 第四軌（觀察者軌），對齊
  vault 架構與 dream_ 前綴慣例；frontmatter 用條目格式（type/date/tags）
  - `daily/panopticon/panopticon_YYYY-MM-DD.md`（每日洞察，雙語）
  - 週/月層級（`weekly/panopticon/`、C-2 跨軸相關等）後續依同構擴展
  - 週/月彙整不受影響：vault 腳本明確列舉 work/life/dream，不 glob
  - 寫入紀律沿用 vault 慣例：同日同名已存在即跳過（冪等）
- **Secrets**：`GEMINI_API_KEY` 設在 Obsidian_Journal repo secrets
  （panopticon 端的於 C-3 撤除）

### 3.4 Rejected alternatives · 已否決的替代方案

| Option | Verdict |
|---|---|
| (a) 維持現狀：CI 內觀步驟永遠 no-op | 零成本但雙軸自動化名存實亡 |
| (b) 全本機化（Task Scheduler） | 可作為過渡；機器沒開就斷，跨軍 correlation 無法自動跑 |
| panopticon CI + PAT checkout vault | **否決**：public repo 的 logs/artifacts 可見，隱私鐵律違反 |
| journal 直接 commit 進 panopticon | **否決**：public repo = 公開個資 |

---

## 4. Rollout Plan · 分階段實施

| Phase | Scope | Notes |
|---|---|---|
| C-0（done） | 本文件 + Phase A/B 落地 | alert 狀態化、月度 rollup、自我監看已上線 |
| C-1（done） | **Obsidian_Journal** 建 `panopticon-inner.yml`：checkout 兩 repo → 讀 daily/life+dream → patterns → insights → 寫 `panopticon/` | 2026-11-18 上線（commit `09a94c9`）；`GEMINI_API_KEY` 已設於 Journal repo；排程 10:23 UTC |
| C-2 | 跨軸 correlation 移入 Journal 管線（讀 panopticon 公開健康資料）；panopticon daily.yml 移除 inner 步驟與 `GEMINI_API_KEY` | panopticon CI 誠實化為純 outer 軸 |
| C-3（optional） | Obsidian_Library 以既有 import-reports 模式收一條 panopticon 洞察串流，編譯進 wiki/ | 走 Library 既有 PAT pattern |
| C-4（optional） | dashboard 趨勢圖：讀 `monthly_*.ndjson` 畫歷史線 | 資產已在 repo 累積 |

Migration note · 遷移記錄：舊制每日開的 8 張 alert issue（#14–#21）已於
2026-11-18 全數關閉並註記；新追蹤 issue 由下一次 daily cycle 自動建立。
