import os
import requests
from collections import defaultdict
from datetime import datetime, timedelta
import pytz

GITHUB_TOKEN = os.getenv('GH_TOKEN')
USERNAME = 'Fenohasina08'
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'}

def get_all_repos():
    url = f'https://api.github.com/users/{USERNAME}/repos?per_page=100'
    repos = []
    while url:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        repos.extend(response.json())
        url = response.links.get('next', {}).get('url')
    return repos

def get_commits_for_repo(repo_full_name, since):
    url = f'https://api.github.com/repos/{repo_full_name}/commits'
    params = {
        'author': USERNAME,
        'since': since.isoformat(),
        'per_page': 100
    }
    commits = []
    while url:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        commits.extend(response.json())
        url = response.links.get('next', {}).get('url')
        params = None
    return commits

def main():
    since_date = datetime.now(pytz.UTC) - timedelta(days=365)
    repos = get_all_repos()
    monthly_counts = defaultdict(int)

    for repo in repos:
        if repo['fork']:
            continue
        try:
            commits = get_commits_for_repo(repo['full_name'], since_date)
        except Exception as e:
            print(f"Erreur pour {repo['full_name']}: {e}")
            continue
        for commit in commits:
            if commit.get('author') and commit['author'].get('login') == USERNAME:
                date_str = commit['commit']['author']['date']
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                month_key = date.strftime('%Y-%m')
                monthly_counts[month_key] += 1

    months = []
    for i in range(11, -1, -1):
        d = datetime.now() - timedelta(days=30*i)
        month = d.strftime('%Y-%m')
        months.append(month)

    table = "| Mois | Commits |\n|------|---------|\n"
    for month in months:
        count = monthly_counts.get(month, 0)
        month_name = datetime.strptime(month, '%Y-%m').strftime('%B %Y')
        table += f"| {month_name} | {count} |\n"

    with open('README.md', 'r') as f:
        content = f.read()

    start_marker = '<!-- MONTHLY_COMMITS_START -->'
    end_marker = '<!-- MONTHLY_COMMITS_END -->'
    new_section = f"{start_marker}\n\n{table}\n{end_marker}"

    if start_marker in content and end_marker in content:
        import re
        pattern = re.escape(start_marker) + '.*?' + re.escape(end_marker)
        content = re.sub(pattern, new_section, content, flags=re.DOTALL)
    else:
        content = content.replace('# Active GitHub (par mois)', f'# Active GitHub (par mois)\n\n{new_section}')

    with open('README.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()