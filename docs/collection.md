# How PHPRepos Was Collected

This page records how the 250 datapoints in `repos.csv` were selected. The selection is fixed: using the dataset needs only `repos.csv` and `repos/`, not a rerun of the collection.

The collection tool (`reproduce.py` and `src/`) is kept at tag [`WebApp_top1000_03.05`](https://github.com/jhu-seclab-cobra/Dataset-PHPRepos/tree/WebApp_top1000_03.05), together with its full output `.cache/php_repos_1000.csv`. Rerunning it does not reproduce the dataset, because the star ranking, the head commits and the classifier inputs are live GitHub data.

## Steps

1. **Popular PHP repositories.** The GitHub search API (`q=language:php&sort=stars&order=desc`) returned the 1000 PHP repositories with the most stars, in March 2025. A datapoint's `rank` is its position in that list, 1 being the most starred.
2. **Snapshot commit.** For each repository, the latest commit of its default branch at collection time is the datapoint's `commit`.
3. **Project type.** The repository's GitHub description and the first 200 characters of its `README.md` are classified by [`repo_classifier`](https://pypi.org/project/repo-classifier/), with a language model when one is configured and with its keyword heuristic otherwise. The run did not record which of the two produced each type.
4. **Selection.** Keep the repositories whose project type is `Web App`. This leaves 250 of the 1000.

| Project type | Repositories in the top 1000 |
|---|---|
| Library | 376 |
| Web App | 250 |
| Framework Plugin | 236 |
| Framework | 68 |
| CLI App | 55 |
| Framework Theme | 12 |
| PHP-SRC | 2 |
| Unknown | 1 |

## Snapshot Archives

Each `repos/<owner>_<repo>/source/` holds `git archive --format=tar <commit> | xz -T1 -6`, cut into 48 MiB parts when larger: exactly the files of the commit's tree, including any macOS metadata files (`.DS_Store`, `__MACOSX/`) the repository itself committed. The exact command, Git and xz versions, and the sha256 of the archive and of every part are in the datapoint's `meta.json` under `source_package`.

The commit is fetched from `snapshot_origin`, which is `github_url` for 248 datapoints. vanilla/vanilla and swagkarna/Rafel-Rat are no longer on GitHub; their commits are fetched from the forks [prosembler/vanilla](https://github.com/prosembler/vanilla) and [tech-samarth/Rafel-Rat](https://github.com/tech-samarth/Rafel-Rat). Since a commit id is the hash of its content, the tree is the same.

Two properties of `git archive` matter when reproducing an archive:

- **Attribute patterns are matched case-sensitively** (`-c core.ignorecase=false`). Otherwise Git on a case-insensitive file system lets a `.gitattributes` line such as `CHANGELOG.md export-ignore` also drop `changelog.md`, which the repository's own GitHub archive keeps.
- **`export-subst` placeholders expand from the fetching repository.** After the depth-1 fetch the command prescribes, kanboard's `%d` in `app/constants.php` expands to ` (grafted)`; GitHub's own archive expands it to an empty string.

Every extracted archive was compared file by file with the snapshots the collection tool had extracted from GitHub zip archives of the same commits. Apart from kanboard's `app/constants.php` above, file contents are identical. The remaining differences are defects of those older snapshots, not of the archives:

- **Symbolic links** (19 datapoints): the zip extraction stored each symbolic link as a regular file. The archives keep them as symbolic links.
- **Non-ASCII file names** (18 datapoints): the zip extraction decoded UTF-8 names as CP437, so `strängé` became `stra╠ênge╠ü`. The archives keep the original UTF-8 names.
- **Paths differing only in case** (8 datapoints, such as sqli-labs's `Less-24/Logged-in.php` and `Less-24/logged-in.php`): on a case-insensitive file system one path overwrote the other. The archives hold both; extracting them on such a file system loses one again.
- **AppleDouble files** (2 datapoints): committed `._*` files that the zip extraction merged into macOS metadata. The archives keep them as files.
- **Local files** (luolongfei/freenom): a `.DS_Store` that the old snapshot gained on disk and the commit does not contain.
