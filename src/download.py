"""
Download functionality for GitHub Repository Dataset Collection Tool.
"""

from pathlib import Path
from typing import Optional, List
import requests
import zipfile
import shutil
import csv
import json
from collections import Counter
from rich.table import Table
from rich import box
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from .logger import Logger

# 创建logger实例
logger = Logger('download')

def download_repositories(
    csv_file: Path,
    output_dir: Path,
    count: Optional[int] = None,
    project_types: Optional[List[str]] = None,
    use_cache: bool = True
) -> bool:
    """
    Download GitHub repository archives based on CSV entries with filtering options.
    
    Args:
        csv_file: Path to the CSV file containing repository data
        output_dir: Directory to store downloaded and extracted repositories
        count: Optional number of repositories to download (None means no limit)
        project_types: Optional list of project types to filter
        use_cache: Whether to use cached downloads
    """
    try:
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create cache directory if using cache
        inter_dir = Path('.inter/downloads')
        if use_cache:
            inter_dir.mkdir(parents=True, exist_ok=True)
        elif inter_dir.exists():
            logger.operation('clean', "Clearing download cache directory")
            shutil.rmtree(inter_dir)
            inter_dir.mkdir(parents=True)
        
        # Read and filter CSV entries
        filtered_entries = []
        console = Console()
        console.print("[cyan]Reading and filtering CSV entries...[/cyan]")
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize project type to title case for comparison
                row_project_type = row['project_type'].strip().title()
                
                # Apply project type filter
                if project_types and row_project_type not in project_types:
                    continue
                
                # Store normalized project type
                row['project_type'] = row_project_type
                filtered_entries.append(row)
                
                # Apply count limit if both count and project_types are specified
                if count is not None and project_types is not None and len(filtered_entries) >= count:
                    break
        
        # Apply count limit if only count is specified (no project type filter)
        if count is not None and project_types is None and len(filtered_entries) > count:
            filtered_entries = filtered_entries[:count]
        
        if not filtered_entries:
            logger.warning("No entries match the specified filters")
            return False
        
        # Format filter conditions for display
        filter_info = []
        if project_types:
            filter_info.append(f"Project Types: {', '.join(project_types)}")
        if count is not None:
            filter_info.append(f"Max Count: {count}")
            
        # Display found entries with filter information
        console.print(f"[green]Found {len(filtered_entries)} matching entries[/green]" + 
                    (f" with filters:\n" + "\n".join(f"[yellow]•[/yellow] {info}" for info in filter_info) if filter_info else ""))
        console.print()
        
        # Process filtered entries with progress bar
        success_count = 0
        successful_entries = []  # Store successful entries for statistics
        
        # Create progress bar
        progress = Progress(
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TextColumn("•"),
            TextColumn("[progress.description]{task.description}"),
        )
        
        with progress:
            # Add main task
            task = progress.add_task(
                "",  # Empty initial description
                total=len(filtered_entries)
            )
            
            for entry in filtered_entries:
                repo_name = entry['repo_uname']
                commit = entry['commit_hash']
                project_type = entry['project_type']
                
                # Update progress description
                repo_short_name = repo_name.split('/')[-1]
                progress.update(task, description=f"[cyan]{project_type}/{repo_short_name}")
                
                try:
                    # Create archive URL
                    archive_url = f"https://github.com/{repo_name}/archive/{commit}.zip"
                    
                    # Create cache key using accountname_reponame_commit前七位 format
                    account_name, repo_name = repo_name.split('/')
                    cache_key = f"{repo_name.replace('/', '_')}_{commit}"
                    cache_path = inter_dir / f"{cache_key}.zip"
                    
                    if use_cache and cache_path.exists():
                        logger.debug(f"Using cached download for {repo_name}")
                        temp_zip = cache_path
                    else:
                        # Download zip file
                        response = requests.get(archive_url, stream=True)
                        response.raise_for_status()
                        
                        # Save to cache if enabled
                        temp_zip = cache_path if use_cache else output_dir / f"{cache_key}_temp.zip"
                        with open(temp_zip, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                    
                    # Extract zip file
                    with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                        # Get the name of the root directory in the zip
                        root_dir = zip_ref.namelist()[0].split('/')[0]
                        zip_ref.extractall(output_dir)
                    
                    # Move repository to its final location using the new naming format
                    repo_name = f"{account_name}_{repo_name}_{commit[:7]}"
                    extracted_path = output_dir / root_dir
                    final_path = output_dir / project_type / repo_name
                    
                    # Create project type directory if it doesn't exist
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Remove existing directory if it exists
                    if final_path.exists():
                        shutil.rmtree(final_path)
                    
                    # Move repository to its final location
                    extracted_path.rename(final_path)
                    
                    # Create metadata file
                    metadata = {
                        'repo_name': repo_name,
                        'commit_hash': commit,
                        'project_type': project_type,
                        'account_name': account_name
                    }
                    
                    with open(final_path / '.repo_meta.json', 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2)
                    
                    # Clean up if not using cache
                    if not use_cache and temp_zip.exists():
                        temp_zip.unlink()
                    
                    # If successful, store the entry
                    successful_entries.append(entry)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {repo_name}: {str(e)}")
                
                # Advance progress bar
                progress.advance(task)
        
        # Generate statistics after download
        console = Console()
        
        # Collect statistics
        stats = {
            'total_repos': len(successful_entries),
            'project_types': Counter(entry['project_type'] for entry in successful_entries)
        }
        
        # Create summary tables
        console.print("\n[bold cyan]Download Summary[/bold cyan]")
        
        # Main statistics table
        main_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        main_table.add_column("Metric", style="cyan")
        main_table.add_column("Value", justify="right")
        
        main_table.add_row(
            "Total Repositories Downloaded",
            str(stats['total_repos'])
        )
        main_table.add_row(
            "Project Types",
            str(len(stats['project_types']))
        )
        
        console.print(main_table)
        console.print()
        
        # Project types distribution
        if stats['project_types']:
            console.print("[bold cyan]Project Type Distribution[/bold cyan]")
            proj_table = Table(box=box.SIMPLE, show_header=True)
            proj_table.add_column("Project Type", style="bold")
            proj_table.add_column("Repository Count", justify="right")
            proj_table.add_column("Percentage", justify="right")
            
            for proj_type, count in stats['project_types'].most_common():
                percentage = (count / stats['total_repos']) * 100
                proj_table.add_row(
                    proj_type,
                    str(count),
                    f"{percentage:.1f}%"
                )
            
            console.print(proj_table)
        
        logger.operation('end', "Download process completed", extra_info={
            'total': len(filtered_entries),
            'successful': success_count,
            'failed': len(filtered_entries) - success_count
        })
        
        return True
        
    except Exception as e:
        logger.error(f"Download operation failed: {str(e)}")
        return False 