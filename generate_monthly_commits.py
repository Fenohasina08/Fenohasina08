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
    page = 1
    while url:
        print(f"  Récupération page {page} pour {repo_full_name}")
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        print(f"  {len(data)} commits dans cette page")
        commits.extend(data)
        url = response.links.get('next', {}).get('url')
        params = None
        page += 1
    return commits

def main():
    print("=== DÉBUT DU SCRIPT ===")
    print(f"Token présent: {'oui' if GITHUB_TOKEN else 'non'}")

    start_date = datetime(2000, 1, 1, tzinfo=pytz.UTC)
    print(f"Date de début: {start_date}")

    try:
        repos = get_all_repos()
        print(f"Nombre total de dépôts trouvés: {len(repos)}")
    except Exception as e:
        print(f"Erreur lors de la récupération des dépôts: {e}")
        return

    commits_par_annee_mois = defaultdict(lambda: defaultdict(int))
    total_commits = 0

    for repo in repos:
        repo_name = repo['name']
        if repo['fork']:
            print(f"Dépôt {repo_name} est un fork, ignoré")
            continue
        print(f"\n--- Traitement du dépôt: {repo_name} ---")
        try:
            commits = get_commits_for_repo(repo['full_name'], start_date)
            print(f"Total commits récupérés pour {repo_name}: {len(commits)}")
        except Exception as e:
            print(f"Erreur pour {repo_name}: {e}")
            continue

        for commit in commits:
            # Vérification de l'auteur
            author = commit.get('author')
            if author and author.get('login') == USERNAME:
                date_str = commit['commit']['author']['date']
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                annee = date.year
                mois = date.month
                commits_par_annee_mois[annee][mois] += 1
                total_commits += 1
            else:
                # Afficher quelques exemples de commits ignorés (pour debug)
                if len(commits) < 10:  # Limite pour ne pas surcharger
                    sha = commit.get('sha', 'inconnu')
                    author_login = author.get('login') if author else 'None'
                    print(f"  Commit ignoré {sha}: auteur={author_login}")

    print(f"\n=== RÉSULTATS ===")
    print(f"Total des commits comptés: {total_commits}")

    # Vérification croisée avec le tableau
    somme_tableau = 0
    for an in commits_par_annee_mois:
        for mois in commits_par_annee_mois[an]:
            somme_tableau += commits_par_annee_mois[an][mois]
    print(f"Somme du tableau (commits par mois): {somme_tableau}")

    # Construction du tableau (inchangée)
    annee_courante = datetime.now().year
    mois_courant = datetime.now().month
    annees = list(range(2024, annee_courante + 1))

    mois_fr = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

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

    # Lecture et mise à jour du README
    try:
        with open('README.md', 'r') as f:
            content = f.read()
        print("README.md lu avec succès")
    except Exception as e:
        print(f"Erreur lecture README: {e}")
        return

    # Mise à jour du tableau
    start_marker = '<!-- MONTHLY_COMMITS_START -->'
    end_marker = '<!-- MONTHLY_COMMITS_END -->'
    new_section = f"{start_marker}\n\n{table}\n\n{end_marker}"

    if start_marker in content and end_marker in content:
        import re
        pattern = re.escape(start_marker) + '.*?' + re.escape(end_marker)
        content = re.sub(pattern, new_section, content, flags=re.DOTALL)
        print("Section tableau remplacée")
    else:
        print("Marqueurs du tableau non trouvés, ajout...")
        content = content.replace('# Active GitHub (par mois)', f'# Active GitHub (par mois)\n\n{new_section}')

    # Mise à jour du total
    total_marker_start = '<!-- TOTAL_CONTRIBUTIONS_START -->'
    total_marker_end = '<!-- TOTAL_CONTRIBUTIONS_END -->'
    total_line = f"{total_marker_start}\n\n**Total des commits : {total_commits}**\n\n{total_marker_end}"

    if total_marker_start in content and total_marker_end in content:
        pattern_total = re.escape(total_marker_start) + '.*?' + re.escape(total_marker_end)
        content = re.sub(pattern_total, total_line, content, flags=re.DOTALL)
        print("Section total remplacée")
    else:
        print("Marqueurs du total non trouvés, ajout...")
        content = content.replace('# 🔥 Streak de contributions', f'# 🔥 Streak de contributions\n\n{total_line}')

    try:
        with open('README.md', 'w') as f:
            f.write(content)
        print("README.md écrit avec succès")
    except Exception as e:
        print(f"Erreur écriture README: {e}")
        return

    print(f"TOTAL_COMMITS={total_commits}")
    print("=== FIN DU SCRIPT ===")

if __name__ == '__main__':
    main()