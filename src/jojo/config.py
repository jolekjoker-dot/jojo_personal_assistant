"""
配置管理 — 从 YAML 文件和环境变量加载配置。
"""

import os
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """LLM 配置"""
    default_model: str = "openai/gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096


class MemoryConfig(BaseModel):
    """记忆系统配置"""
    working_max_messages: int = 20
    short_term_ttl_seconds: int = 3600
    long_term_db_path: str = "data/memory.db"
    vector_store_path: str = "data/chroma"


class AgentConfig(BaseModel):
    """Agent 默认配置"""
    max_iterations: int = 10
    verbose: bool = False
    workspace_root: str = "."          # 工作目录根，工具只能访问此目录
    allowed_dirs: list[str] = ["data", "output"]  # 额外白名单目录


class SchedulerConfig(BaseModel):
    """定时任务配置"""
    db_path: str = "data/scheduler.db"
    max_retries: int = 3


class OrchestratorConfig(BaseModel):
    """Orchestrator 配置 — 多 Agent 协作"""
    classifier_model: str = "deepseek/deepseek-chat"
    flash_model: str = "deepseek/deepseek-chat"
    pro_model: str = "deepseek/deepseek-chat"


class Config(BaseModel):
    """全局配置"""
    project_name: str = "jojo"
    version: str = "0.1.0"
    log_level: str = "INFO"
    log_file: str = "data/jojo.log"
    llm: LLMConfig = LLMConfig()
    memory: MemoryConfig = MemoryConfig()
    agent: AgentConfig = AgentConfig()
    orchestrator: OrchestratorConfig = OrchestratorConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    skills_dir: str = "skills"
    mcp_config_path: str = "configs/mcp_servers.yaml"

    @property
    def openai_api_key(self) -> str | None:
        return os.environ.get("OPENAI_API_KEY")

    @property
    def anthropic_api_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY")

    @property
    def deepseek_api_key(self) -> str | None:
        return os.environ.get("DEEPSEEK_API_KEY")


def _load_yaml_config(config_path: str) -> dict:
    """从 YAML 文件加载配置，文件不存在则返回空字典。"""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_config(config_path: str = "config.yaml") -> Config:
    """
    加载全局配置（单例，缓存）。

    优先级: 环境变量 > YAML 文件 > 默认值
    """
    # 加载 .env 文件
    load_dotenv(".env", override=False)

    # 加载 YAML 配置
    yaml_data = _load_yaml_config(config_path)

    # 合并：YAML 的值覆盖默认值
    merged = Config()

    if "llm" in yaml_data:
        for k, v in yaml_data["llm"].items():
            if hasattr(merged.llm, k):
                setattr(merged.llm, k, v)

    if "memory" in yaml_data:
        for k, v in yaml_data["memory"].items():
            if hasattr(merged.memory, k):
                setattr(merged.memory, k, v)

    if "agent" in yaml_data:
        for k, v in yaml_data["agent"].items():
            if hasattr(merged.agent, k):
                setattr(merged.agent, k, v)

    if "orchestrator" in yaml_data:
        for k, v in yaml_data["orchestrator"].items():
            if hasattr(merged.orchestrator, k):
                setattr(merged.orchestrator, k, v)

    if "scheduler" in yaml_data:
        for k, v in yaml_data["scheduler"].items():
            if hasattr(merged.scheduler, k):
                setattr(merged.scheduler, k, v)

    for field in ["project_name", "version", "log_level", "log_file",
                  "skills_dir", "mcp_config_path"]:
        if field in yaml_data:
            setattr(merged, field, yaml_data[field])

    return merged


# 全局单例
config = load_config()
