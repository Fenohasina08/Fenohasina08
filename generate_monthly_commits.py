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
    # Commits depuis le 1er janvier 2024
    start_date = datetime(2024, 1, 1, tzinfo=pytz.UTC)
    repos = get_all_repos()
    
    # Dictionnaire : commits[année][mois] = nombre
    commits_par_annee_mois = defaultdict(lambda: defaultdict(int))

    for repo in repos:
        if repo['fork']:
            continue
        try:
            commits = get_commits_for_repo(repo['full_name'], start_date)
        except Exception as e:
            print(f"Erreur pour {repo['full_name']}: {e}")
            continue
        for commit in commits:
            if commit.get('author') and commit['author'].get('login') == USERNAME:
                date_str = commit['commit']['author']['date']
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                annee = date.year
                mois = date.month
                commits_par_annee_mois[annee][mois] += 1

    # Années à afficher (de 2024 à l'année en cours)
    annee_courante = datetime.now().year
    annees = list(range(2024, annee_courante + 1))

    mois_fr = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    # Construction du tableau
    header = "| Mois | " + " | ".join(str(a) for a in annees) + " |"
    separator = "|" + "---|" * (len(annees) + 1)
    lignes = [header, separator]

    for mois_num in range(1, 13):
        ligne = f"| {mois_fr[mois_num-1]} |"
        for an in annees:
            count = commits_par_annee_mois[an].get(mois_num, 0)
            ligne += f" {count} |"
        lignes.append(ligne)

    table = "\n".join(lignes)

    # Mise à jour du README
    with open('README.md', 'r') as f:
        content = f.read()

    start_marker = '<!-- MONTHLY_COMMITS_START -->'
    end_marker = '<!-- MONTHLY_COMMITS_END -->'
    new_section = f"{start_marker}\n\n{table}\n\n{end_marker}"

    if start_marker in content and end_marker in content:
        import re
        pattern = re.escape(start_marker) + '.*?' + re.escape(end_marker)
        content = re.sub(pattern, new_section, content, flags=re.DOTALL)
    else:
        # Si les marqueurs ne sont pas trouvés, on les ajoute
        content = content.replace('# Active GitHub (par mois)', f'# Active GitHub (par mois)\n\n{new_section}')

    with open('README.md', 'w') as f:
        f.write(content)

    # Pour le message de commit automatique
    total = sum(sum(mois.values()) for mois in commits_par_annee_mois.values())
    print(f"TOTAL_COMMITS={total}")

if __name__ == '__main__':
    main()