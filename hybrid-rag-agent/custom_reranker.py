from typing import Any, Dict, List, Optional, Tuple
from agno.knowledge.document import Document
from agno.knowledge.reranker.base import Reranker
from agno.utils.log import logger
import requests
from pydantic import BaseModel # 雖然 VLLMCrossEncoder 被移除，但 BaseModel 可能仍用於 SelfDefineReranker 的屬性定義，先保留

class SelfDefineReranker(Reranker):
    base_url: str = "http://192.168.37.71:30807"
    """vLLM 服務的基礎 URL"""
    model_name: str = "BAAI/bge-reranker-v2-m3"
    """模型名稱"""
    truncate_prompt_tokens: int = 2000
    """截斷提示詞的 token 數量"""
    timeout: int = 30
    """請求超時時間（秒）"""
    top_n: Optional[int] = None

    # 移除 client 屬性，因為不再需要 VLLMCrossEncoder 實例

    def _rerank(self, query: str, documents: List[Document]) -> List[Document]:
        # Validate input documents and top_n
        if not documents:
            return []

        top_n = self.top_n
        if top_n and not (0 < top_n):
            logger.warning(f"top_n should be a positive integer, got {self.top_n}, setting top_n to None")
            top_n = None

        # Prepare text pairs for the cross-encoder
        text_pairs = [(query, doc.content) for doc in documents]
        
        if not text_pairs:
            return []

        # 準備批次請求數據 (直接整合 VLLMCrossEncoder 的 score 邏輯)
        text_1_list = [pair[0] for pair in text_pairs]
        text_2_list = [pair[1] for pair in text_pairs]
          
        payload = {
            "model": self.model_name,
            "text_1": text_1_list,
            "text_2": text_2_list,
            "truncate_prompt_tokens": self.truncate_prompt_tokens,
            "additional_data": "",
            "priority": 0,
            "additionalProp1": {}
        }
          
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        
        scores: List[float] = []
        try:
            response = requests.post(
                f"{self.base_url}/score",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
              
            # 解析 vLLM API 回應格式
            result = response.json()
              
            if "data" in result and isinstance(result["data"], list):
                scores_data = sorted(result["data"], key=lambda x: x.get("index", 0))
                scores = [item.get("score", 0.0) for item in scores_data]
            else:
                logger.error(f"Unexpected API response format: {result}")
                scores = [0.0] * len(text_pairs)
                  
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling vLLM rerank API: {e}")
            scores = [0.0] * len(text_pairs)

        if len(scores) != len(documents):
            logger.error("Number of scores returned by API does not match number of documents. Returning original documents.")
            return documents # Return original documents on error

        compressed_docs: list[Document] = []
        for i, doc in enumerate(documents):
            doc.reranking_score = scores[i]
            compressed_docs.append(doc)

        # Order by relevance score
        compressed_docs.sort(
            key=lambda x: x.reranking_score if x.reranking_score is not None else float("-inf"),
            reverse=True,
        )

        # Limit to top_n if specified
        if top_n:
            compressed_docs = compressed_docs[:top_n]

        return compressed_docs

    def rerank(self, query: str, documents: List[Document]) -> List[Document]:
        try:
            return self._rerank(query=query, documents=documents)
        except Exception as e:
            logger.error(f"Error reranking documents: {e}. Returning original documents")
            return documents
