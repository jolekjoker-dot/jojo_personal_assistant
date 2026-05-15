"""
LongTermMemory — 长期记忆，SQLite 结构化存储 + ChromaDB 向量检索。

职责:
  1. 存储: 将记忆记录保存到 SQLite + ChromaDB
  2. 检索: 混合检索 — BM25 关键词 + 向量语义
  3. 衰减: 计算 decay_score，低分记忆跳过或淘汰
  4. 清理: purge() 永久删除低于阈值的记忆
"""

import json
import time
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.jojo.config import config
from src.jojo.memory.decay import (
    compute_decay_score, should_retrieve, should_purge,
    RETRIEVAL_THRESHOLD,
)
from src.jojo.logger import logger


@dataclass
class MemoryRecord:
    """一条长期记忆。"""
    id: str
    content: str
    importance: str = "medium"          # high / medium / low
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float | None = None
    access_count: int = 0
    decay_score: float = 1.0


class LongTermMemory:
    """
    长期记忆 — SQLite 做结构化存储，ChromaDB 做向量检索。

    每次 add() 同时写入两边。
    检索时先向量召回候选，再用 decay_score 过滤。
    """

    def __init__(self):
        self._db_path = Path(config.memory.long_term_db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # ChromaDB
        self._chroma_path = config.memory.vector_store_path
        self._chroma_client = chromadb.PersistentClient(
            path=self._chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._chroma_client.get_or_create_collection(
            name="long_term_memory",
            metadata={"hnsw:space": "cosine"},
        )

        # SQLite
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                importance TEXT DEFAULT 'medium',
                tags TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                last_accessed_at REAL,
                access_count INTEGER DEFAULT 0,
                decay_score REAL DEFAULT 1.0
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_decay
            ON memories(decay_score)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_created
            ON memories(created_at)
        """)
        self._conn.commit()

    # ========== 写入 ==========

    def add(
        self,
        content: str,
        importance: str = "medium",
        tags: list[str] | None = None,
    ) -> str:
        """添加一条长期记忆。返回 memory id。"""
        import uuid

        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = time.time()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        score = compute_decay_score(now, importance=importance)

        # SQLite
        self._conn.execute(
            """INSERT INTO memories
               (id, content, importance, tags, created_at, decay_score)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (memory_id, content, importance, tags_json, now, score),
        )
        self._conn.commit()

        # ChromaDB
        try:
            self._collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[{
                    "importance": importance,
                    "decay_score": score,
                    "created_at": now,
                }],
            )
        except Exception as e:
            logger.warning(f"ChromaDB add failed (non-fatal): {e}")

        logger.debug(f"Long-term memory added: {memory_id} (score={score:.3f})")
        return memory_id

    # ========== 检索 ==========

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = RETRIEVAL_THRESHOLD,
    ) -> list[MemoryRecord]:
        """
        混合检索:
        1. ChromaDB 向量语义召回 top_k * 2 候选
        2. SQLite 关键词匹配补充
        3. 计算当前 decay_score
        4. 按 score 排序，过滤低于阈值
        """
        results: dict[str, MemoryRecord] = {}

        # 向量检索
        try:
            chroma_results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k * 2, 20),
            )
            if chroma_results.get("ids"):
                for i, mid in enumerate(chroma_results["ids"][0]):
                    doc = chroma_results["documents"][0][i] if chroma_results.get("documents") else ""
                    results[mid] = MemoryRecord(id=mid, content=doc)
        except Exception as e:
            logger.warning(f"ChromaDB query failed: {e}")

        # 关键词回补 (SQLite LIKE)
        keywords = query.split()
        for kw in keywords[:3]:  # 最多 3 个词
            if len(kw) < 2:
                continue
            rows = self._conn.execute(
                "SELECT id, content, importance, tags, created_at, "
                "last_accessed_at, access_count, decay_score "
                "FROM memories WHERE content LIKE ? LIMIT 5",
                (f"%{kw}%",),
            ).fetchall()
            for row in rows:
                if row[0] not in results:
                    results[row[0]] = MemoryRecord(
                        id=row[0], content=row[1], importance=row[2],
                        tags=json.loads(row[3]) if row[3] else [],
                        created_at=row[4], last_accessed_at=row[5],
                        access_count=row[6], decay_score=row[7],
                    )

        # 刷新 decay_score + 过滤
        final: list[tuple[float, MemoryRecord]] = []
        now = time.time()
        for mem_id, rec in results.items():
            # 重新计算衰减分数
            rec.decay_score = compute_decay_score(
                created_at=rec.created_at,
                access_count=rec.access_count,
                importance=rec.importance,
                last_accessed_at=rec.last_accessed_at,
                now=now,
            )
            if rec.decay_score < min_score:
                continue  # 低于阈值，跳过

            # 标记被访问
            self._mark_accessed(mem_id, now)
            final.append((rec.decay_score, rec))

        # 按分数降序
        final.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in final[:top_k]]

    def _mark_accessed(self, memory_id: str, now: float) -> None:
        """标记记忆被检索命中。"""
        self._conn.execute(
            """UPDATE memories
               SET last_accessed_at = ?, access_count = access_count + 1
               WHERE id = ?""",
            (now, memory_id),
        )
        self._conn.commit()

    # ========== 维护 ==========

    def list_all(self, limit: int = 50) -> list[MemoryRecord]:
        """列出所有记忆（按衰减分数降序）。"""
        rows = self._conn.execute(
            "SELECT id, content, importance, tags, created_at, "
            "last_accessed_at, access_count, decay_score "
            "FROM memories ORDER BY decay_score DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            MemoryRecord(
                id=r[0], content=r[1], importance=r[2],
                tags=json.loads(r[3]) if r[3] else [],
                created_at=r[4], last_accessed_at=r[5],
                access_count=r[6], decay_score=r[7],
            )
            for r in rows
        ]

    def purge(self) -> int:
        """永久删除衰减分数低于阈值的记忆。返回删除数量。"""
        now = time.time()

        # 刷新所有记忆的 decay_score
        rows = self._conn.execute(
            "SELECT id, created_at, access_count, importance FROM memories"
        ).fetchall()

        to_delete: list[str] = []
        for row in rows:
            score = compute_decay_score(
                created_at=row[1],
                access_count=row[2],
                importance=row[3],
                now=now,
            )
            if should_purge(score):
                to_delete.append(row[0])

        if to_delete:
            placeholders = ",".join("?" * len(to_delete))
            self._conn.execute(
                f"DELETE FROM memories WHERE id IN ({placeholders})",
                to_delete,
            )
            self._conn.commit()

            try:
                self._collection.delete(ids=to_delete)
            except Exception:
                pass

            logger.info(f"Purged {len(to_delete)} decayed memories")

        return len(to_delete)

    def close(self) -> None:
        """关闭连接。"""
        self._conn.close()
