# 專案架構與企業適用性分析報告

## 1. 專案架構總覽 (Context Layer Architecture)

目前這是一個**大語言模型 (LLM) 的語意與情境層 (Semantic & Context Layer) 雛型**，專案的核心目標在於「在將問題丟給 LLM 之前，先根據使用者的身分、權限以及商業名詞 (Business Terms) 來獲取正確的背景脈絡與資料」。

主要的模組劃分如下：
* **[context_pipeline.py](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_pipeline.py)（主流程）**：負責接收 User Query 與 User ID，串接各個模組，最後產出完整的 Prompt。
* **[context_resolver.py](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_resolver.py)（情境解析）**：根據傳入的 User ID 以及 Query，讀取本地的 JSON 檔案 (`context_data`)，以此決定當前使用者的權限 (Access Context)、使用偏好 (User Context)，以及查詢中涉及到的商業名詞定義 (Domain Context)。
* **[prompt_builder.py](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/prompt_builder.py)（提示詞生成）**：將解析出來的情境 (Context) 與查詢到的資料 (Data Result) 進行組裝，生成最終給 LLM 的系統提示詞 (System Prompt)。
* **`adapters/`（資料源適配器）**：負責向外部系統（如 CRM、ERP、Case System）發送請求並獲取資料。目前是 Mock 實作。
* **`context_data/`（靜態情境資料庫）**：利用 JSON 檔案存放商業名詞定義 ([terms/](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_resolver.py#35-43))、權限規則 ([resolver_heuristics.json](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_data/resolver_heuristics.json)) 及使用者資料 (`users/`)。


## 2. 此架構是否符合「企業實際所需」？

目前的設計確實抓到了企業應用 AI 的核心痛點（權限控管、商業名詞對齊、防護機制），但在**擴充性**與**自動化**上，距離實際企業級上線 (Enterprise-grade) 還有需要調整的空間。

### 🌟 符合企業需求的優點
1. **名詞定義解耦 (Semantic Layer)**：
   企業存在許多同名異義詞（例如 Sales 認為的 Active Customer 和 Marketing 的定義可能不同）。把 `Customer`、`Case` 單獨抽成 JSON 去定義其 scope, active_rule，這完全符合企業資料治理 (Data Governance) 的需求。
2. **權限與資料隔離 (Access Control & Compliance)**：
   有實作出權限檢查機制（如 `finance_access_flag` 檢查與 `warnings` 攔截）。企業痛點是怕 LLM 把不該講的機密（如財務報表、不屬於該部門的資料）洩漏出來，此架構在 Prompt 生成前先掛載存取限制 (Access Context)，這是正確的企業防護方向。
3. **適配器模式 (Adapter Pattern)**：
   把對外部系統的呼叫抽象成 `adapters`，未來如果要實接真實的 Salesforce (CRM) 或 SAP (ERP)，只需要重新實作 Adapter 即可，不會動到主邏輯。

### ⚠️ 需要改進的企業級痛點 (Limitations)
1. **路由與工具呼叫不夠動態 (Hardcoded Routing)**：
   這是目前最大的致命傷。在 [context_pipeline.py](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_pipeline.py) 中，使用的是硬編碼的 `If-Else`（如 `if has_customer and has_case:`）來決定呼叫哪些 Adapters。
   * **企業現實**：企業問題千變萬化，不可能用 if-else 窮舉所有情境。
   * **建議方向**：應該引入 **Tool Calling (或 Function Calling) 的 Agent 機制**，讓 LLM 自己根據使用者的問題來決定要呼叫什麼 Adapter，Pipeline 只負責權限管控與注入規則。
2. **資料獲取是同步阻塞的 (Synchronous Fetching)**：
   目前獲取各個 adapter 資料是 `[adapter.fetch(...) for adapter in adapters]`，這在真實環境中會帶來嚴重的效能問題（等待多個外部 API 回應）。
   * **建議方向**：實作非同步 (Asynchronous) 請求機制如 `asyncio.gather` 或導入平行處理。
3. **靜態 JSON 管理不便 (Static Context Data)**：
   目前使用者的角色、商業術語都是寫死在 JSON。
   * **企業現實**：在幾千人的企業裡，User Context 應該要整合企業的 Active Directory (AD) 或 SSO 系統獲取；同時，Terms 定義應該從資料目錄 (Data Catalog，如 Collibra 或 Alation) 動態拉取或定期同步。
4. **缺少 LLM 的防幻覺與事實查核 (Fact-Checking)**：
   目前的 [prompt_builder.py](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/prompt_builder.py) 只用純文字把規則組裝上去，期待 LLM 乖乖遵守（例如：`不要捏造...`）。但在企業嚴謹場景，這樣仍不夠。最好在後段加上一層獨立的 Validator (Output Guardrails) 來確保 LLM 回答的數字與 data result 完全一致。

## 3. 總結建議
目前的 `Context Layer` 結構作為概念驗證 (PoC) 非常優秀，完美展示了「**AI Semantic Routing**」的核心理念——用業務語言引導 LLM。

但若要推廣到實際業務環境中，建議下一步可以將 [context_pipeline.py](file:///d:/my_note/_300-A%E4%B8%BB%E9%A1%8C/Agent/context-layer-docs-2026-03-31/tools/context_pipeline.py) 中的寫死邏輯拆除，改用 `LangChain` 或 `LlamaIndex` 搭配 **Agent 工具調用 (Tool Calling)**，並將情境層 (`context_resolver`) 封裝成 Agent 可以自動調用的知識庫或攔截器 (Interceptor)。
