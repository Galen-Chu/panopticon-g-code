# Data Architecture & Inner-Axis Route C Design · 資料架構與內觀軸路線 C 設計

> Status · 狀態：Phase A/B4 已實施；Route C 為評估結論與設計藍圖，尚未實作。
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

### 3.1 Obsidian_Library 現況調查（2026-11-18）

| Capability | Finding |
|---|---|
| Hosting | GitHub `Galen-Chu/Obsidian_Library` — **private** ✓（未認證 API 404；認證後 `private: true`） |
| Automation | GitHub Actions 已每日兩跑 `import-reports.yml`（pull 模型，冪等 + backfill 自癒） |
| Cross-repo auth | PAT pattern 已建立：repo secrets `TASK_SCHEDULE_TOKEN` / `SYNC_G_CODE_TOKEN` |
| Monthly aggregation | `compile-monthly.yml` 已存在（每月 1 號聚合 `raw/reports/` → `wiki/derived/`） |
| Conventions | 每日筆記 `YYYY-MM-DD.md`、frontmatter（`created`/`tags`/`aliases`）、wikilink、小寫連字號標籤、`templates/reflex.md`（反身思考模板，與內觀軸同源） |
| Guards | pre-commit 擋亂碼／機密／檔名契約 |

### 3.2 關鍵推論：方向反轉

原本的設想是「panopticon 的 CI 去 checkout 私有 vault」——**不可行也不該做**：

- panopticon 是 public repo。public repo 的 Actions **logs 與 artifacts 對所有人可見**，
  即使 secrets 不外洩，journal 內容與衍生洞察可能在 log 中曝光 → 違反隱私鐵律。
- `GITHUB_TOKEN` 不能跨 repo；放 PAT 進 public repo secrets 技術上可行，但計算
  結果仍會寫回 public repo → 一樣違反隱私鐵律。

**正確方向（pull 模型，與 vault 既有管線同構）**：內觀軸的計算搬進
**Obsidian_Library 的私有 Actions** 執行。私有端可以自由讀取公開端
（panopticon 的 outer 資料本來就 public），反向不行——所以跨軸 correlation
（需要同時讀 journal + 生態健康）**只屬於私有端**。

```
┌─ public ─────────────────────┐      ┌─ private: Obsidian_Library ──────┐
│ panopticon-g-code            │      │                                  │
│  daily.yml: outer monitor    │      │  panopticon-inner.yml (新):      │
│   → health_*.json committed  │─────▶│   1. checkout self (journal)     │
│   → alerts / state           │ read │   2. checkout panopticon (code   │
│                              │ only │      + public health archive)    │
│ 本 repo 提供: outer 資料 +    │      │   3. inner.patterns → insights   │
│ inner 模組程式碼（公有程式、  │      │   4. 跨軸 correlation             │
│ 私有資料）                    │      │   5. 寫入 wiki/panopticon/ +     │
└──────────────────────────────┘      │      guard + commit              │
                                      └──────────────────────────────────┘
```

### 3.3 Vault-side data design · vault 端資料設計

遵循 vault 既有慣例（wikilink、frontmatter、MD+JSON 孿生檔）：

- **Journal 儲存**：`notes/journal/YYYY-MM-DD.md`（人工書寫，Obsidian 原生）
  - frontmatter：`created: YYYY-MM-DD`、`tags: [journal, panopticon-reflection]`
  - 機器可讀側車 `notes/journal/YYYY-MM-DD.json`（對齊 `raw/reports/` 的
    MD+JSON 契約），欄位相容 §2.4（`date`/`entry`/`prompt`）
- **產出位置**：`wiki/panopticon/insight-YYYY-MM-DD.md`（每日洞察）、
  `wiki/panopticon/correlation-YYYY-MM-DD.md`（跨軸相關）、
  `wiki/panopticon/weekly-YYYY-Www.md`（週回顧，Phase C）
  - frontmatter：`tags: [panopticon, insight]` 等；內文雙語、wikilink 連回
    當日 journal note 與 panopticon repo
- **Secrets**：`GEMINI_API_KEY` 設在 vault repo secrets（panopticon 端的
  之後可撤除）

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
| C-0（本次） | 本文件 + Phase A/B 落地 | alert 狀態化、月度 rollup、自我監看已上線 |
| C-1 | vault 端 `panopticon-inner.yml`：checkout 兩個 repo → patterns/insights → 寫 `wiki/panopticon/` | 需先把既有本機 journal 遷入 `notes/journal/`（MD+JSON） |
| C-2 | `inner.journal.cli` 增加 vault 匯出（`--vault <path>` 產生 MD+JSON 孿生檔） | 本機書寫習慣不變 |
| C-3 | 跨軸 correlation 移入 vault 管線；panopticon daily.yml 移除 inner 步驟與 `GEMINI_API_KEY` | CI 誠實化為純 outer 軸 |
| C-4（optional） | dashboard 趨勢圖：讀 `monthly_*.ndjson` 畫歷史線 | 資產已在 repo 累積 |

Migration note · 遷移注意：alert 狀態化上線後，舊制每日開的 8 張 issue
（#14–#21）不會被新系統管理（無 label），需手動關閉一次。
