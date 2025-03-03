import typer
from typing_extensions import Annotated
from pathlib import Path
from typing import Optional
from src.collect import collect_repos
from src.logger import Logger

# 创建logger实例
logger = Logger('reproduce')

app = typer.Typer(
    name="github-repo-classifier",
    help="A tool to fetch and classify GitHub repositories",
    add_completion=False
)

@app.command()
def main(
    language: Annotated[str, typer.Argument(help="Programming language to search for")],
    count: Annotated[int, typer.Argument(help="Number of repositories to fetch")],
    output_dir: Annotated[Path, typer.Argument(help="Output directory for results")],
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Disable cache usage")] = False,
    github_token: Annotated[Optional[str], typer.Option("--github-token", help="GitHub API token")] = None,
    ai_classifier: Annotated[Optional[str], typer.Option(
        "--ai-classifier",
        help="AI classifier configuration string (format: api_url:model_name:api_key)"
    )] = None,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Enable verbose output")] = False,
) -> None:
    """
    Fetch and classify GitHub repositories based on their type.
    
    This tool will fetch the top repositories for a given programming language,
    classify them using either heuristic or AI-based methods, and save the results
    to a CSV file.
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

if __name__ == "__main__":
    app() 