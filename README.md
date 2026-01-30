# GitHub Language Rankings

The purpose of this project is to generate a “most used languages” breakdown for a GitHub user by aggregating the languages reported across their public repositories and rendering the result as a chart PNG file (`visualization.png`).

This repository is intentionally self-contained: the code avoids requiring external links or relying on self-hosted servers.

## What it does

- Fetches a user’s repositories from the GitHub API
- For each repo, fetches its language byte counts (`languages_url`)
- Sums language usage across all repos
- Produces a “top languages + Other” chart and saves it to `visualization.png`

## Requirements

The GitHub `workflow.yml` file manages the necessary requirements. If run outside GitHub, this project requires: 
- Python 3
- Python packages:
    - `requests`
    - `matplotlib`

## Configuration

1. Fork the repository
2. Add a raw content URL pointed at the visualization.png file to any GitHub README.md, e.g., `![Alt Text](https://raw.githubusercontent.com/<username>/<repository>/<branch>/visualization.png)`

That's it!

Note: The script reads configuration information from the following environment variables:

- `GITHUB_USER` - the GitHub username to analyze
- `GITHUB_TOKEN` - the GitHub API token required to make requests