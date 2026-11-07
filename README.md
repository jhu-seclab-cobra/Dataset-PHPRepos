# PHPRepos

> PHP + Repos: the web applications among the 1000 most-starred PHP repositories on GitHub.

250 popular PHP web applications on GitHub, each with the source code of a fixed commit.

## Install

```bash
git clone https://github.com/jhu-seclab-cobra/Dataset-PHPRepos.git
```

The clone is about 3.5 GB: the compressed source archives of all 250 datapoints.

## Usage

Extract the source code of the datapoints you need (Python 3.12 or later, no third-party packages):

```bash
python tools/extract.py                                 # every repository
python tools/extract.py --top 50                        # the 50 most-starred
python tools/extract.py pterodactyl_panel humhub_humhub # named repositories
```

Each archive is checked against the sha256 values in its `meta.json` and extracted to `repos/<owner>_<repo>/codes/`, which Git ignores. An existing `codes/` is kept unless `--force` is given.

## Dataset

250 repositories classified as `Web App` among the 1000 PHP repositories with the most GitHub stars in March 2025, each at the head commit of its default branch at that time. Their star ranks run from 1 to 1000.

How the repositories were selected: [docs/collection.md](docs/collection.md).

## Format

```
repos.csv                                  one row per datapoint, in rank order
repos/<owner>_<repo>/meta.json             datapoint metadata
repos/<owner>_<repo>/source/source.tar.xz  source archive (cut into source.tar.xz.000, .001, ... above 48 MiB)
repos/<owner>_<repo>/codes/                extracted source (created by tools/extract.py)
```

`repos.csv` columns: `github_repo`, `commit`, `project_type`, `rank`.

`meta.json` fields:

| Field | Meaning |
|---|---|
| `github_repo`, `github_url` | Repository |
| `commit` | Head commit of the default branch at collection time; the archive holds its tree |
| `project_type` | Repository type (`Web App` for every datapoint) |
| `rank` | Position among the 1000 most-starred PHP repositories, 1 being the most starred |
| `snapshot_origin` | Where the commit was fetched from: `github_url`, or a fork holding the same commit when the repository is no longer on GitHub |
| `source_package` | Archive size and sha256, each part's path, size and sha256, and the command, Git and xz versions that produced the archive |

```json
{
  "github_repo": "pterodactyl/panel",
  "github_url": "https://github.com/pterodactyl/panel",
  "commit": "871ef0c56412b71ca43602759ee0caff68e32fdf",
  "project_type": "Web App",
  "rank": 148,
  "snapshot_origin": "https://github.com/pterodactyl/panel",
  "source_package": {
    "archive_size": 1705728,
    "archive_sha256": "4e2118263b9fbb1f8e3806f16f6f09507eca4f48f5ae658072640b1763df5525",
    "parts": [
      {
        "path": "source/source.tar.xz",
        "size": 1705728,
        "sha256": "4e2118263b9fbb1f8e3806f16f6f09507eca4f48f5ae658072640b1763df5525"
      }
    ],
    "generation_command": "...",
    "git_version": "git version 2.50.1 (Apple Git-155)",
    "xz_version": "xz (XZ Utils) 5.8.4"
  }
}
```

## Citation

```bibtex
@inproceedings{xu_cobra_2026,
  title = {{CoBrA}: Context-, Branch-sensitive Static Analysis for Detecting Taint-style Vulnerabilities in {PHP} Web Applications},
  author = {Xu, Yichao and Kang, Mingqing and Thimmaiah, Neil and Gjomemo, Rigel and Venkatakrishnan, V. N. and Cao, Yinzhi},
  booktitle = {Proceedings of the IEEE/ACM 48th International Conference on Software Engineering (ICSE)},
  publisher = {ACM},
  pages = {1943--1954},
  year = {2026},
  doi = {10.1145/3744916.3773195}
}
```

## License

[GPL-2.0](LICENSE). The archived source code keeps the license of its own repository.
