import json
import csv
import time
import urllib.request
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from classifier import classify_description_heuristic, classify_description_ai, CLASSIFIER_NAMES
from .logger import Logger
from .config import Config

# GitHub API配置
_HEADERS = {
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'Dataset-PHPRepos'
}

# 创建logger实例
logger = Logger('collect')

def _create_progress() -> Progress:
    """创建进度显示器"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        TextColumn("[bold]{task.fields[status]}"),
        expand=True
    )

def _load_cache(url: str) -> Optional[Dict]:
    """从缓存加载响应数据"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_file = Config.GITHUB_INTER_DIR / f"{url_hash}.json"
    if not cache_file.exists():
        return None
        
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            cache_days = 7 
            if time.time() - cache_data['timestamp'] < cache_days * 24 * 3600:
                logger.debug(f"Using cached data for {url}")
                return cache_data['data']
    except Exception as e:
        logger.debug(f"Failed to load cache for {url}: {e}")
    return None

def _save_cache(url: str, data: Dict) -> None:
    """保存响应数据到缓存"""
    try:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_file = Config.GITHUB_INTER_DIR / f"{url_hash}.json"
        cache_data = {
            'timestamp': time.time(),
            'url': url,
            'data': data
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
            logger.debug(f"Saved cache for {url}", path=str(cache_file))
    except Exception as e:
        logger.debug(f"Failed to save cache for {url}: {e}")

def _handle_rate_limit(response: urllib.error.HTTPError) -> int:
    """处理API速率限制"""
    try:
        headers = dict(response.headers)
        reset_time = int(headers.get('X-RateLimit-Reset', '0'))
        remaining = headers.get('X-RateLimit-Remaining', '0')
        limit = headers.get('X-RateLimit-Limit', '60')
        
        if reset_time:
            current_time = int(time.time())
            wait_time = max(reset_time - current_time + 1, 60)
            
            # 剩余配额不到10%时增加等待时间
            if int(remaining) < int(limit) * 0.1:
                wait_time += 30
                
            logger.warning(
                f"Rate limit reached",
                extra_info={
                    'Remaining': f"{remaining}/{limit}",
                    'Wait Time': f"{wait_time} seconds"
                }
            )
            return wait_time
            
    except Exception as e:
        logger.error(f"Failed to handle rate limit: {e}")
        
    return 3600  # 出错时默认等待1小时

def _make_request(url: str, token: Optional[str] = None) -> Optional[Dict]:
    """发送GitHub API请求"""
    headers = _HEADERS.copy()
    if token:
        headers['Authorization'] = f'Bearer {token}'
        
    # 检查缓存
    cached_data = _load_cache(url)
    if cached_data is not None:
        return cached_data

    # 重试设置
    retry_attempts = 0
    max_retries = 5
    base_delay = 2
    
    while retry_attempts < max_retries:
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request) as response:
                data = json.loads(response.read().decode('utf-8'))
                _save_cache(url, data)
                return data
                
        except urllib.error.HTTPError as e:
            if e.code in {403, 429}:  # 速率限制
                wait_time = _handle_rate_limit(e)
                time.sleep(wait_time)
                continue
                
            elif e.code in {500, 502, 503, 504}:  # 服务器错误
                retry_attempts += 1
                delay = base_delay * (2 ** retry_attempts)
                logger.warning(f"Server error (HTTP {e.code}), retrying in {delay} seconds...")
                time.sleep(delay)
                
            else:
                logger.error(f"HTTP error {e.code} for {url}")
                return None
                
        except Exception as e:
            retry_attempts += 1
            delay = base_delay * (2 ** retry_attempts)
            logger.warning(f"Request failed, retrying in {delay} seconds: {e}")
            time.sleep(delay)
            
    logger.error(f"Max retries reached for {url}")
    return None

def get_top_repos(language: str, count: int, token: Optional[str] = None) -> List[Dict]:
    """获取指定语言的热门仓库"""
    repos = []
    page = 1
    per_page = min(100, count)  # GitHub API每页最多100条记录
    
    logger.start_process(f"Fetching top {count} {language} repositories")
    
    with _create_progress() as progress:
        task = progress.add_task(
            f"[cyan]Fetching repositories",
            total=count,
            status="Starting..."
        )
        
        while len(repos) < count:
            url = f"https://api.github.com/search/repositories?q=language:{language}&sort=stars&order=desc&page={page}&per_page={per_page}"
            data = _make_request(url, token)
            
            if not data or 'items' not in data:
                logger.warning("No more repositories available")
                break
                
            items = data['items']
            if not items:
                break
                
            for item in items:
                if len(repos) >= count:
                    break
                    
                repo_info = {
                    'repo_uname': item['full_name'],
                    'commit_hash': item.get('default_branch', ''),
                    'description': item.get('description', ''),
                    'topics': item.get('topics', []),
                    'size': item.get('size', 0),
                    'stars': item.get('stargazers_count', 0)
                }
                repos.append(repo_info)
                progress.update(task, completed=len(repos), status=f"Found {len(repos)} repositories")
                
            page += 1
            
        progress.update(task, completed=len(repos), status="[green]Completed")
    
    logger.success(f"Found {len(repos)} repositories")
    return repos

def get_default_branch_commit(repo: str, token: Optional[str] = None) -> Optional[str]:
    """获取仓库默认分支的最新commit hash"""
    url = f"https://api.github.com/repos/{repo}/commits"
    data = _make_request(url, token)
    
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]['sha']
    
    return None

def get_repo_info(repo: str, token: Optional[str] = None) -> Optional[Dict]:
    """获取仓库信息"""
    if not repo:
        return None
        
    url = f"https://api.github.com/repos/{repo}"
    return _make_request(url, token)

def get_repo_readme(repo: str) -> str:
    """获取仓库的README内容"""
    readme_content = ''
    
    # 尝试master分支
    readme_url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
    try:
        request = urllib.request.Request(readme_url, headers=_HEADERS)
        with urllib.request.urlopen(request) as response:
            readme_content = response.read().decode('utf-8')[:200] + "..."
            return readme_content
    except Exception as e:
        logger.debug(f"Failed to get README from master branch: {e}")
    
    # 尝试main分支
    try:
        readme_url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
        request = urllib.request.Request(readme_url, headers=_HEADERS)
        with urllib.request.urlopen(request) as response:
            readme_content = response.read().decode('utf-8')[:200]
            return readme_content
    except Exception as e:
        logger.debug(f"Failed to get README from main branch: {e}")
    
    return readme_content

def get_highest_probability_type(results: Dict[str, float]) -> Tuple[Optional[str], float]:
    """从概率字典中获取最高概率的类型"""
    if not results:
        return None, 0.0
    project_type, confidence = max(results.items(), key=lambda x: x[1])
    return project_type, confidence

def _parse_aicg_api(api_str: Optional[str]) -> Optional[Dict]:
    """
    解析AICG API字符串
    
    Args:
        api_str: API配置字符串 (格式: api_url:model_name:api_key)
        
    Returns:
        Optional[Dict]: API配置字典
    """
    if not api_str:
        return None
        
    try:
        parts = api_str.split(':')
        if len(parts) != 3:
            logger.warning(f"Invalid AICG API format: {api_str}")
            return None
            
        api_url, model_name, api_key = parts
        
        # 验证API URL格式
        if not api_url.startswith(('http://', 'https://')):
            api_url = f"https://{api_url}"
            
        return {
            'api_url': api_url,
            'model_name': model_name,
            'api_key': api_key
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse AICG API string: {e}")
        return None

def classify_repository_with_cache(repo: str, use_ai: bool = False, api_config: Optional[Dict] = None) -> str:
    """
    使用缓存机制的仓库分类函数
    
    Args:
        repo: 仓库名称 (格式: owner/repo)
        use_ai: 是否使用AI分类
        api_config: AI API配置 (包含 api_url, model_name, api_key)
    
    Returns:
        str: 项目类型
    """
    if not repo:
        return "Unknown"
    
    repo_url = f"https://github.com/{repo}"
    
    try:
        # 获取仓库信息
        repo_info = get_repo_info(repo)
        if not repo_info:
            logger.debug(f"Failed to get repository info for {repo}")
            return "Unknown"
        
        # 获取description和readme
        description = str(repo_info.get('description', '')).replace('\n', ' ')
        readme_content = str(get_repo_readme(repo)).replace('\n', ' ')
        
        # 组合项目描述
        project_desc = f"Repository: {repo_url};\nDescription: {description}\nReadme: {readme_content}"
        if use_ai and api_config:
            # 检查AI分类缓存
            cache_key = hashlib.md5(f"{repo}:{api_config['model_name']}:{project_desc}".encode()).hexdigest()
            cache_file = Config.AI_CLASS_INTER_DIR / f"{cache_key}.json"
            
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        if time.time() - cache_data['timestamp'] < 30 * 24 * 3600:  # 30天缓存
                            logger.debug(f"Using cached AI classification for {repo}")
                            return cache_data['project_type']
                except Exception as e:
                    logger.debug(f"Error loading AI classification cache: {e}")
            
            # 执行AI分类
            try:
                results = classify_description_ai(
                    project_desc,
                    classifier=CLASSIFIER_NAMES.PHP,
                    api_url=api_config['api_url'],
                    api_key=api_config['api_key'],
                    model_name=api_config['model_name']
                )
                if results:
                    project_type, confidence = get_highest_probability_type(results)
                    if project_type and confidence > 0.5:  # 只接受置信度大于0.5的结果
                        # 保存到缓存
                        try:
                            cache_data = {
                                'timestamp': time.time(),
                                'repo': repo,
                                'model_name': api_config['model_name'],
                                'project_type': project_type,
                                'confidence': confidence,
                                'description': project_desc,
                                'probabilities': results
                            }
                            with open(cache_file, 'w', encoding='utf-8') as f:
                                json.dump(cache_data, f, indent=2)
                                logger.debug(f"Saved AI classification cache for {repo}", path=str(cache_file))
                        except Exception as e:
                            logger.debug(f"Error saving AI classification cache: {e}")
                        return project_type
            except Exception as e:
                logger.debug(f"AI classification failed: {e}")

        # 使用启发式分类
        results = classify_description_heuristic(project_desc, classifier=CLASSIFIER_NAMES.PHP)
        if results:
            project_type, confidence = get_highest_probability_type(results)
            if project_type and confidence > 0.3:  # 启发式方法使用较低的置信度阈值
                return project_type
        
    except Exception as e:
        logger.debug(f"Classification failed for {repo}: {e}")
    
    return "Unknown"

def _check_existing_cache(language: str, count: int) -> Optional[Path]:
    """
    检查是否存在匹配的缓存文件
    
    Args:
        language: 编程语言
        count: 仓库数量
        
    Returns:
        Optional[Path]: 如果找到匹配的缓存文件则返回路径，否则返回None
    """
    cache_file = Config.CACHE_DIR / f"{language}_repos_{count}.csv"
    if cache_file.exists():
        return cache_file
    return None

def collect_repos(
    language: str,
    count: int,
    output_dir: Path,
    use_cache: bool = True,
    github_token: Optional[str] = None,
    ai_classifier: Optional[str] = None,
    verbose: bool = False
) -> None:
    """
    收集并分类指定语言的GitHub仓库
    
    Args:
        language: 编程语言
        count: 要获取的仓库数量
        output_dir: 输出文件保存目录
        use_cache: 是否使用缓存数据
        github_token: GitHub API token，用于提高API限制
        ai_classifier: AI分类器配置字符串 (格式: api_url:model_name:api_key)
        verbose: 是否输出详细日志
    """
    # 设置logger的verbose模式
    logger.verbose = verbose
    
    # 确保输出目录存在
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 准备输出文件路径
    output_file = output_dir / f"{language}_repos_{count}.csv"
    
    # 检查是否存在缓存结果
    if use_cache:
        cached_file = _check_existing_cache(language, count)
        if cached_file:
            logger.operation('cache', f"Found existing results", path=str(cached_file))
            logger.operation('cache', f"Copying to output directory", path=str(output_file))
            shutil.copy2(cached_file, output_file)
            logger.success(f"Reused existing results", path=str(output_file))
            return
    
    # 配置中间数据缓存
    if not use_cache:
        logger.operation('clean', "Clearing intermediate data directories")
        shutil.rmtree(Config.GITHUB_INTER_DIR, ignore_errors=True)
        shutil.rmtree(Config.AI_CLASS_INTER_DIR, ignore_errors=True)
        Config.GITHUB_INTER_DIR.mkdir(parents=True, exist_ok=True)
        Config.AI_CLASS_INTER_DIR.mkdir(parents=True, exist_ok=True)
    
    # 准备AI配置
    use_ai = False
    api_config = None
    if ai_classifier:
        api_config = _parse_aicg_api(ai_classifier)
        if api_config:
            use_ai = True
            logger.success("AI classification enabled")
        else:
            logger.warning("Invalid AI classifier configuration, falling back to heuristic classification")
    
    # 输出配置信息
    logger.info("Configuration", extra_info={
        'Language': language,
        'Target Count': count,
        'Output File': str(output_file),
        'Cache Enabled': use_cache,
        'GitHub Token': 'Provided' if github_token else 'Not provided',
        'Classification': 'AI' if use_ai else 'Heuristic'
    })
    
    # 获取仓库列表
    repos = get_top_repos(language, count, github_token)
    
    logger.step(f"Classifying {len(repos)} repositories")
    results = []
    
    with _create_progress() as progress:
        task = progress.add_task(
            "[cyan]Classifying repositories",
            total=len(repos),
            status="Starting..."
        )
        
        for repo in repos:
            # 获取最新commit hash
            commit_hash = get_default_branch_commit(repo['repo_uname'], github_token)
            if commit_hash:
                repo['commit_hash'] = commit_hash
            
            # 分类项目
            project_type = classify_repository_with_cache(
                repo['repo_uname'],
                use_ai=use_ai,
                api_config=api_config
            )
            
            results.append({
                'repo_uname': repo['repo_uname'],
                'commit_hash': repo['commit_hash'],
                'project_type': project_type
            })
            
            progress.update(task, advance=1, status=f"Processed {repo['repo_uname']}")
    
    # 写入CSV文件
    logger.operation('cache', f"Writing results to CSV file", path=str(output_file))
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['repo_uname', 'commit_hash', 'project_type'])
        writer.writeheader()
        writer.writerows(results)
    
    # 保存一份到缓存目录
    cache_file = Config.CACHE_DIR / f"{language}_repos_{count}.csv"
    logger.operation('cache', f"Saving results to cache", path=str(cache_file))
    shutil.copy2(output_file, cache_file)
    
    logger.success(f"Collection completed", path=str(output_file))
    
    # 输出统计信息
    if verbose:
        type_stats = {}
        for result in results:
            proj_type = result['project_type']
            type_stats[proj_type] = type_stats.get(proj_type, 0) + 1
        
        logger.info("Classification Statistics", extra_info=type_stats)
