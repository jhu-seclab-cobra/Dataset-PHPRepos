from pathlib import Path
from dataclasses import dataclass

@dataclass
class Config:
    # 中间数据目录配置
    INTER_DIR = Path('.inter')
    GITHUB_INTER_DIR = INTER_DIR / 'github_responses'
    AI_CLASS_INTER_DIR = INTER_DIR / 'ai_classifications'
    
    # 确保中间数据目录存在
    INTER_DIR.mkdir(exist_ok=True)
    GITHUB_INTER_DIR.mkdir(parents=True, exist_ok=True)
    AI_CLASS_INTER_DIR.mkdir(parents=True, exist_ok=True)
    
    # 缓存输出目录配置
    CACHE_DIR = Path('.cache')    
    # 确保缓存输出目录存在
    CACHE_DIR.mkdir(exist_ok=True)

    