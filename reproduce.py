import typer
from typing_extensions import Annotated
from pathlib import Path
from typing import Optional, List
from src.collect import collect_repos
from src.download import download_repositories
from src.logger import Logger

# 创建logger实例
logger = Logger('reproduce')

app = typer.Typer(
    name="github-repo-classifier",
    help="A tool to fetch and classify GitHub repositories",
    add_completion=False
)

@app.command(name="collect")
def collect(
    language: Annotated[str, typer.Argument(help="Programming language to search for")],
    count: Annotated[int, typer.Argument(help="Number of repositories to fetch")],
    output_dir: Annotated[Path, typer.Option(help="Output directory for results")] = Path(".cache"),
    no_cache: Annotated[bool, typer.Option(help="Disable cache usage")] = False,
    github_token: Annotated[Optional[str], typer.Option(help="GitHub API token")] = None,
    ai_classifier: Annotated[Optional[str], typer.Option(
        help="AI classifier configuration string (format: api_url:model_name:api_key)"
    )] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Enable verbose output")] = False,
) -> None:
    """
    Collect and classify GitHub repositories based on their type.
    """
    try:
        collect_repos(
            language=language,
            count=count,
            output_dir=output_dir,
            use_cache=not no_cache,
            github_token=github_token,
            ai_classifier=ai_classifier,
            verbose=verbose
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(code=1)

@app.command(name="download")
def download(
    csv_file: Annotated[Path, typer.Argument(help="Input CSV file containing repository data")],
    output_dir: Annotated[Path, typer.Argument(help="Output directory for downloaded repositories")],
    count: Annotated[Optional[int], typer.Option(help="Maximum number of repositories to download")] = None,
    project_types: Annotated[Optional[str], typer.Option(help="Comma-separated list of project types to filter (case-insensitive)")] = None,
    do_cache: Annotated[bool, typer.Option(help="Disable cache usage")] = True,
) -> None:
    """
    Download GitHub repositories based on CSV data.
    
    Project types are case-insensitive, e.g., "Web App" and "web app" are treated the same.
    """
    try:
        # Convert project_types string to list if provided, normalize to title case
        project_type_list = None
        if project_types:
            project_type_list = [pt.strip().title() for pt in project_types.split(',')]
            logger.info(f"Filtering by project types: {', '.join(project_type_list)}")
        
        download_repositories(
            csv_file=csv_file,
            output_dir=output_dir,
            count=count,
            project_types=project_type_list,
            use_cache=do_cache
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app() 