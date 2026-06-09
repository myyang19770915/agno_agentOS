"""
data/generate_100_docs.py — 隨機生成 100 筆測試文件並寫入 PostgreSQL + Qdrant
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.ingest import ingest_documents, init_postgres_table
from app.core.database import postgres_db
from app.core.vector_db import vector_db

BRANCHES = ["Taipei", "Taichung", "Kaohsiung", "Tainan", "HQ"]
CATEGORIES = ["finance", "risk", "hr", "strategy", "security", "operations", "marketing", "tech"]
DATES = [f"2026-{m:02d}-{d:02d}" for m in range(1, 4) for d in (5, 10, 15, 20, 25)]

# ---- 文件模板池 ----
TEMPLATES = [
    # finance
    ("{branch}分公司 {quarter} 營收報告",
     "{branch}分公司 2026 年{quarter}營收為 NT${amount:,}，{trend}。主要{reason}。"),
    ("{branch}分公司 {quarter} 成本分析",
     "{branch}分公司 2026 年{quarter}總營運成本為 NT${cost:,}，其中人事成本佔 {pct}%，{detail}。"),
    ("{branch}分公司應收帳款報告",
     "{branch}分公司截至 {date} 應收帳款餘額為 NT${amount:,}，逾期 30 天以上的帳款佔 {pct}%，{action}。"),
    # risk
    ("{branch}分公司風險評估報告",
     "{branch}分公司已識別 {count} 項主要風險，包括{risk_types}。建議{mitigation}。"),
    ("{branch}分公司資安事件報告",
     "{branch}分公司本月偵測到 {count} 起資安事件，其中 {high} 起為高風險等級，{response}。"),
    # hr
    ("{branch}分公司人力資源季報",
     "{branch}分公司目前共有 {headcount} 名員工，本季新進 {new} 人、離職 {left} 人，離職率 {turnover}%。{plan}"),
    ("{branch}分公司員工培訓計畫",
     "{branch}分公司 {quarter} 規劃 {courses} 門課程，涵蓋{topics}。預計培訓 {trained} 人次。"),
    # strategy
    ("全公司{initiative}策略規劃",
     "公司計畫在 {timeline} 完成{initiative}，預計投入 NT${budget:,}，{scope}。"),
    ("{branch}分公司數位轉型進度",
     "{branch}分公司{initiative}專案目前進度 {progress}%，已完成{milestones}，下一階段將{next_phase}。"),
    # security
    ("{branch}分公司資安稽核報告",
     "{branch}分公司完成 {quarter} 資安稽核，發現 {findings} 項缺失，其中 {critical} 項為重大缺失，{remediation}。"),
    ("全公司零信任架構部署進度",
     "零信任架構部署進度：{progress}% 完成。{component}已上線，下一步將{next_step}。"),
    # operations
    ("{branch}分公司營運效率報告",
     "{branch}分公司 {quarter} 客戶服務回應時間平均 {response_time} 分鐘，客戶滿意度 {satisfaction}%，{improvement}。"),
    ("{branch}分公司供應鏈報告",
     "{branch}分公司現有 {suppliers} 家供應商，本季準時交貨率 {delivery_rate}%，{supply_action}。"),
    # marketing
    ("{branch}分公司行銷活動報告",
     "{branch}分公司 {quarter} 舉辦 {events} 場行銷活動，觸及 {reach:,} 人次，轉換率 {conversion}%。{highlight}"),
    ("{branch}分公司品牌調查報告",
     "{branch}區域品牌知名度調查結果：知名度 {awareness}%，好感度 {preference}%，{insight}。"),
    # tech
    ("{branch}分公司 IT 基礎設施報告",
     "{branch}分公司主要系統可用率 {uptime}%，本季完成 {upgrades} 項基礎設施升級，{tech_detail}。"),
    ("AI 模型{model_topic}進展報告",
     "公司 {model_topic} 最新進展：{model_metric}，已在{deployment}環境部署，{model_plan}。"),
    ("{branch}分公司資料品質報告",
     "{branch}分公司資料品質評估：完整性 {completeness}%、準確性 {accuracy}%、時效性 {timeliness}%。{dq_action}"),
]

# ---- 隨機內容填充 ----
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
TRENDS = [
    "較去年同期成長 15%", "較去年同期成長 8%", "較去年同期下降 5%",
    "與去年同期持平", "較上季成長 12%", "較上季下降 3%",
]
REASONS = [
    "貢獻來自企業客戶的大型專案", "來自新產品線的營收突破", "受到原物料成本上漲影響",
    "因新客戶合約簽訂帶動", "因為季節性需求增加", "受匯率波動影響",
]
RISK_TYPES = [
    "供應商交期延遲與合約違約", "資安威脅與資料外洩風險", "法規遵循與個資保護風險",
    "市場競爭加劇與客戶流失", "匯率波動與財務風險",
]
MITIGATIONS = [
    "啟動備用供應商計畫並加強監控", "強化員工資安意識培訓", "委請外部顧問進行合規審查",
    "加速產品差異化策略", "建立避險機制以降低匯率影響",
]
INITIATIVES = [
    "AI 導入", "雲端遷移", "ERP 升級", "客服自動化", "資料中台建設",
    "DevOps 轉型", "行動應用開發", "IoT 感測器部署",
]
TOPICS = [
    "AI/ML、雲端架構、專案管理", "資安合規、資料治理", "領導力、溝通技巧",
    "Python 程式設計、資料分析", "產品設計思維、敏捷開發",
]
TECH_DETAILS = [
    "包括伺服器記憶體擴充與網路設備更新", "完成 Kubernetes 叢集遷移",
    "導入 CI/CD 流水線與自動化測試", "升級資料庫至 PostgreSQL 16",
    "部署 Prometheus + Grafana 監控平台",
]
MODEL_TOPICS = [
    "RAG 系統優化", "Embedding 模型微調", "文件分類模型", "意圖辨識模型",
    "知識圖譜建構", "語音轉文字系統",
]


def _fill_template(template_pair, branch, date) -> dict:
    title_tpl, content_tpl = template_pair
    quarter = random.choice(QUARTERS)
    params = dict(
        branch=branch, quarter=quarter, date=date,
        amount=random.randint(3_000_000, 50_000_000),
        cost=random.randint(1_000_000, 20_000_000),
        budget=random.randint(5_000_000, 100_000_000),
        pct=random.randint(10, 65),
        count=random.randint(2, 15),
        high=random.randint(1, 5),
        headcount=random.randint(20, 200),
        new=random.randint(2, 20),
        left=random.randint(1, 10),
        turnover=round(random.uniform(2, 15), 1),
        courses=random.randint(3, 15),
        trained=random.randint(30, 200),
        progress=random.randint(20, 95),
        findings=random.randint(2, 12),
        critical=random.randint(0, 3),
        suppliers=random.randint(15, 80),
        delivery_rate=random.randint(85, 99),
        events=random.randint(2, 10),
        reach=random.randint(5_000, 100_000),
        conversion=round(random.uniform(1.5, 12.0), 1),
        awareness=random.randint(40, 90),
        preference=random.randint(30, 80),
        uptime=round(random.uniform(99.0, 99.99), 2),
        upgrades=random.randint(2, 10),
        completeness=random.randint(85, 99),
        accuracy=random.randint(90, 99),
        timeliness=random.randint(80, 98),
        response_time=random.randint(5, 45),
        satisfaction=random.randint(70, 98),
        trend=random.choice(TRENDS),
        reason=random.choice(REASONS),
        detail="預計下季透過流程優化降低 10%",
        action="已啟動催收流程並加強信用審核",
        risk_types=random.choice(RISK_TYPES),
        mitigation=random.choice(MITIGATIONS),
        response="已啟動事件應變程序並完成修補",
        plan="預計 Q2 招募 AI 工程師 5 名",
        topics=random.choice(TOPICS),
        initiative=random.choice(INITIATIVES),
        timeline="2026 年底前",
        scope="涵蓋全公司五大分支機構",
        milestones="需求分析與系統架構設計",
        next_phase="進入開發與測試階段",
        component="MFA 多因子認證模組",
        next_step="部署微分段網路策略",
        remediation="已建立改善計畫並排定時程",
        improvement="較上季提升 5 個百分點",
        supply_action="已新增 2 家備援供應商",
        highlight="其中線上研討會效果最佳",
        insight="年輕族群好感度較高，建議加強社群經營",
        tech_detail=random.choice(TECH_DETAILS),
        model_topic=random.choice(MODEL_TOPICS),
        model_metric="準確率達 92%、F1-Score 0.89",
        deployment="staging",
        model_plan="預計下月推進至 production",
        dq_action="已建立自動化資料品質監控流程",
    )
    title = title_tpl.format(**params)
    content = content_tpl.format(**params)
    category = _infer_category(template_pair)
    return dict(title=title, content=content, branch=branch, category=category, date=date)


def _infer_category(template_pair) -> str:
    title_tpl = template_pair[0].lower()
    if "營收" in title_tpl or "成本" in title_tpl or "應收" in title_tpl:
        return "finance"
    if "風險" in title_tpl or "資安事件" in title_tpl:
        return "risk"
    if "人力" in title_tpl or "培訓" in title_tpl or "員工" in title_tpl:
        return "hr"
    if "策略" in title_tpl or "轉型" in title_tpl:
        return "strategy"
    if "稽核" in title_tpl or "零信任" in title_tpl:
        return "security"
    if "營運" in title_tpl or "供應鏈" in title_tpl:
        return "operations"
    if "行銷" in title_tpl or "品牌" in title_tpl:
        return "marketing"
    if "it" in title_tpl or "ai" in title_tpl or "資料品質" in title_tpl:
        return "tech"
    return "general"


def generate_100_docs():
    random.seed(42)
    docs = []
    for i in range(100):
        branch = random.choice(BRANCHES)
        date = random.choice(DATES)
        tpl = random.choice(TEMPLATES)
        doc = _fill_template(tpl, branch, date)
        docs.append(doc)
    return docs


def main():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    docs = generate_100_docs()
    logger.info("Generated %d random documents", len(docs))

    # 顯示分佈統計
    from collections import Counter
    branch_counts = Counter(d["branch"] for d in docs)
    cat_counts = Counter(d["category"] for d in docs)
    logger.info("Branch distribution: %s", dict(branch_counts))
    logger.info("Category distribution: %s", dict(cat_counts))

    # 寫入 PG + Qdrant
    count = ingest_documents(docs)
    logger.info("=== Done: %d documents ingested ===", count)

    # 驗證
    pg_rows = postgres_db.execute_query("SELECT COUNT(*) AS cnt FROM documents")
    qd_count = vector_db.count()
    logger.info("Postgres: %s rows | Qdrant: %d points", pg_rows[0]["cnt"], qd_count)


if __name__ == "__main__":
    main()
