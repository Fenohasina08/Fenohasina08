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

def get_total_contributions_graphql():
    """Récupère le nombre total de contributions (commits, issues, PR, etc.) depuis le début via GraphQL."""
    query = """
    {
      user(login: "%s") {
        contributionsCollection(from: "2008-01-01T00:00:00Z", to: "%s") {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """ % (USERNAME, datetime.now(pytz.UTC).isoformat().replace('+00:00', 'Z'))

    response = requests.post(
        'https://api.github.com/graphql',
        headers=HEADERS,
        json={'query': query}
    )
    if response.status_code == 200:
        data = response.json()
        try:
            return data['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions']
        except (KeyError, TypeError):
            print("Erreur lors du parsing de la réponse GraphQL")
            return None
    else:
        print(f"Erreur GraphQL: {response.status_code}")
        return None

def main():
    # Récupérer le total des contributions (tous types) via GraphQL
    total_contributions = get_total_contributions_graphql()
    if total_contributions is None:
        # Fallback sur le calcul des commits (REST) si GraphQL échoue
        total_contributions = 0
        # (on va le recalculer plus tard, mais pour l'instant on laisse 0)
        print("Fallback sur le calcul des commits REST")

    # Date de début très ancienne pour couvrir tous les commits (2000-01-01)
    start_date = datetime(2000, 1, 1, tzinfo=pytz.UTC)
    repos = get_all_repos()
    
    # Pour les mois
    commits_par_annee_mois = defaultdict(lambda: defaultdict(int))
    total_commits = 0  # pour le fallback éventuel

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
                total_commits += 1

    # Si GraphQL a échoué, on utilise total_commits comme fallback
    if total_contributions is None:
        total_contributions = total_commits

    # Années à afficher (de 2024 à l'année en cours)
    annee_courante = datetime.now().year
    mois_courant = datetime.now().month
    annees = list(range(2024, annee_courante + 1))

    mois_fr = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    # Construction du tableau mensuel
    header = "| Mois | " + " | ".join(str(a) for a in annees) + " |"
    separator = "|" + "---|" * (len(annees) + 1)
    lignes = [header, separator]

    for mois_num in range(1, 13):
        ligne = f"| {mois_fr[mois_num-1]} |"
        for an in annees:
            if an == annee_courante and mois_num > mois_courant:
                cellule = "_"
            else:
                count = commits_par_annee_mois[an].get(mois_num, 0)
                cellule = str(count)
            ligne += f" {cellule} |"
        lignes.append(ligne)

    table = "\n".join(lignes)

    # Lire le README actuel
    with open('README.md', 'r') as f:
        content = f.read()

    # Insérer le tableau mensuel entre les marqueurs existants
    start_marker = '<!-- MONTHLY_COMMITS_START -->'
    end_marker = '<!-- MONTHLY_COMMITS_END -->'
    new_section = f"{start_marker}\n\n{table}\n\n{end_marker}"

    if start_marker in content and end_marker in content:
        import re
        pattern = re.escape(start_marker) + '.*?' + re.escape(end_marker)
        content = re.sub(pattern, new_section, content, flags=re.DOTALL)
    else:
        content = content.replace('# Active GitHub (par mois)', f'# Active GitHub (par mois)\n\n{new_section}')

    # Insérer le total des contributions (GraphQL) dans la section streak
    total_marker_start = '<!-- TOTAL_CONTRIBUTIONS_START -->'
    total_marker_end = '<!-- TOTAL_CONTRIBUTIONS_END -->'
    total_line = f"{total_marker_start}\n\n**Total de toutes les contributions (commits, issues, PR, etc.) : {total_contributions}**\n\n{total_marker_end}"

    if total_marker_start in content and total_marker_end in content:
        pattern_total = re.escape(total_marker_start) + '.*?' + re.escape(total_marker_end)
        content = re.sub(pattern_total, total_line, content, flags=re.DOTALL)
    else:
        # On ajoute la ligne après la section "🔥 Streak de contributions"
        content = content.replace('# 🔥 Streak de contributions', f'# 🔥 Streak de contributions\n\n{total_line}')

    with open('README.md', 'w') as f:
        f.write(content)

    # Pour le message de commit automatique
    print(f"TOTAL_COMMITS={total_contributions}")

if __name__ == '__main__':
    main()