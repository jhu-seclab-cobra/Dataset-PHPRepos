# Dataset PHPRepos

## 1. Overview

This dataset is specifically curated for evaluating PHP security analysis tools on zero-day vulnerability detection. It comprises source codes of 141 GitHub repositories for PHP Web applications, classified by their project types. The repositories are selected based on their popularity (star count) and classified using both heuristic and AI-based methods.

### 1.1 Dataset Purpose

- **Security Tool Evaluation**: The dataset is designed to assess the effectiveness of PHP security analysis tools in detecting potential zero-day vulnerabilities.
- **Real-world Applications**: By including popular PHP repositories, it provides realistic test cases that reflect actual development practices.
- **Diverse Project Types**: The variety of project types helps evaluate tool performance across different application contexts.

### 1.2 Collection Information

- **Collection Date**: February 2025
- **Selection Criteria**: Top starred PHP repositories on GitHub
- **Repository Count**: 100 most popular repositories
- **Version Control**: Each repository is preserved at a specific commit to ensure reproducibility

### 1.3 Collection Methodology

| Step | Process | Description |
|------|---------|-------------|
| 1 | Repository Selection | Fetch top 500 starred PHP repositories from GitHub |
| 2 | Project Classification | Classify repositories using heuristic or AI methods |
| 3 | Data Organization | Organize repositories by their project types |
| 4 | Metadata Storage | Store repository information and classification results |
| 5 | Download Web App repos | Download codes of all web app type repo in the 500 repos |  

### 1.4 Project Types

The repositories are classified into the following main categories:

| Project Type | Description | Example Projects |
|-------------|-------------|------------------|
| Framework | PHP frameworks and libraries | Laravel, Symfony |
| Web App | Web applications and CMS | WordPress, Drupal |
| Tool | Development tools and utilities | Composer, PHPUnit |
| API | API services and implementations | API platforms |
| Template | Website templates and themes | HTML/PHP templates |

## 2. Dataset Structure

### 2.1 Directory Organization

```
output/
├── Framework/
│   ├── laravel/
│   │   └── .repo_meta.json
│   └── symfony/
│       └── .repo_meta.json
├── Web App/
│   ├── wordpress/
│   │   └── .repo_meta.json
│   └── drupal/
│       └── .repo_meta.json
└── Tool/
    └── composer/
        └── .repo_meta.json
```

### 2.2 Metadata Format

Each repository contains a `.repo_meta.json` file with the following information:
```json
{
    "repo_name": "owner/repository",
    "commit_hash": "commit_identifier",
    "project_type": "Framework"
}
```

## 3. Download

### OPTION-1: Download Pre-collected Dataset

You can find the pre-collected dataset in the [releases page](https://github.com/YichaoXu/Dataset-PHPRepos/releases).

### OPTION-2: Download Using Python Script

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Download repositories:
```bash
python reproduce.py download \
    .cache/php_repos_500.csv \
    ./REPOs \
    --project-types "Web App"
```

Parameters:
- `php_repos_500.csv`: Input file containing repository data
- `./REPOs`: Output directory for downloaded repositories
- `--project-types`: Filter by project types (optional)

The repositories will be organized by project type in the output directory.

## 4. Update Dataset Collection

If you want to update the dataset with the latest repositories, you can use the collect command:

1. Collect new repository data:
```bash
python reproduce.py collect php 100 \
    --output-dir .cache \
    --github-token YOUR_GITHUB_TOKEN \
    --ai-classifier "api_url:model_name:api_key" \
    --verbose
```

Parameters:
- `php`: Target programming language
- `100`: Number of top repositories to collect
- `--output-dir`: Directory to store the collected data
- `--github-token`: GitHub API token for higher rate limits (recommended)
- `--ai-classifier`: AI service configuration for better classification (If none, use keywords based statistic algorithm)
- `--verbose`: Show detailed progress information

The command will:
1. Fetch the top 100 PHP repositories from GitHub
2. Classify each repository using AI (if configured) or heuristic methods
3. Save the results to `.cache/php_repos_100.csv`
4. This CSV file can then be used with the download command

Example workflow to update and download:
```bash
# 1. Collect new repository data
python reproduce.py collect php 100 \
    --output-dir .cache \
    --github-token YOUR_GITHUB_TOKEN

# 2. Download the updated repositories
python reproduce.py download \
    .cache/php_repos_100.csv \
    ./output \
    --project-types "Framework,Web App"
```

### Important Notes
- Repository availability depends on GitHub's accessibility
- Some repositories might be renamed or removed after collection
- For consistency, we recommend using the pre-collected dataset from releases
- The download process respects GitHub's rate limits

## Contact

For questions or issues, please contact the project maintainer.