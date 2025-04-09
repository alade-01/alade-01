import os
import requests
import svgwrite
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file (optional but recommended)
load_dotenv()

USERNAME = "alade-01"
TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_URL = f"https://api.github.com/users/{USERNAME}"

HEADERS = {
    "Authorization": f"token {TOKEN}"
}

# --------------- API Utilities ---------------

def get_user_details():
    try:
        response = requests.get(GITHUB_API_URL, headers=HEADERS)
        response.raise_for_status()
        user_data = response.json()
        return {
            "followers": user_data["followers"],
            "following": user_data["following"],
            "public_repos": user_data["public_repos"],
            "public_gists": user_data["public_gists"],
            "bio": user_data.get("bio", "No bio available"),
            "avatar_url": user_data["avatar_url"]
        }
    except requests.RequestException as e:
        print(f"Error fetching user details: {e}")
        return {}

def get_repositories():
    repos_url = f"https://api.github.com/users/{USERNAME}/repos"
    repos = []
    try:
        while repos_url:
            response = requests.get(repos_url, headers=HEADERS)
            response.raise_for_status()
            repos.extend(response.json())
            repos_url = response.links.get('next', {}).get('url')
    except requests.RequestException as e:
        print(f"Error fetching repositories: {e}")
        return []

    return repos

def get_repo_commits(repo_name):
    commits_url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits"
    total_commits = 0
    try:
        while commits_url:
            response = requests.get(commits_url, headers=HEADERS)
            response.raise_for_status()
            commits = response.json()
            total_commits += len(commits)
            commits_url = response.links.get('next', {}).get('url')
    except requests.RequestException as e:
        print(f"Error fetching commits for {repo_name}: {e}")
    return total_commits

def get_lines_of_code(repo_name):
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/languages"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return sum(response.json().values())
    except requests.RequestException:
        return 0

# --------------- Visualization Utilities ---------------

def download_image(url):
    try:
        img_response = requests.get(url)
        img = Image.open(BytesIO(img_response.content))
        return img
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def generate_svg(user_data, stats):
    img = download_image(user_data['avatar_url'])
    if img:
        img.save("avatar.png")

    dwg = svgwrite.Drawing("github_profile.svg", profile="tiny", size=("600px", "400px"))
    dwg.add(dwg.rect(insert=(0, 0), size=("600px", "400px"), fill="#f4f4f4"))

    dwg.add(dwg.image("avatar.png", insert=(20, 20), size=("100px", "100px")))
    dwg.add(dwg.text("GitHub Profile", insert=(140, 30), font_size="20", fill="black"))

    y = 70
    spacing = 30

    lines = [
        f"Followers: {user_data['followers']}",
        f"Following: {user_data['following']}",
        f"Public Repos: {user_data['public_repos']}",
        f"Public Gists: {user_data['public_gists']}",
        f"Total Commits: {stats['total_commits']}",
        f"Total Stars: {stats['total_stars']}",
        f"Lines of Code: {stats['total_lines']}",
        f"Bio: {user_data['bio']}"
    ]

    for line in lines:
        dwg.add(dwg.text(line, insert=(140, y), font_size="14", fill="black"))
        y += spacing

    dwg.save()

def update_readme(followers, following, public_repos, public_gists, bio, total_commits, total_stars, total_lines_of_code):
    start_tag = "<!--STATS-START-->"
    end_tag = "<!--STATS-END-->"

    # Markdown block to inject
    stats_md = f"""{start_tag}

### 🧠 GitHub Profile Summary

- **👥 Followers:** {followers}
- **🔄 Following:** {following}
- **📁 Public Repositories:** {public_repos}
- **📝 Public Gists:** {public_gists}
- **💬 Bio:** {bio or "No bio available"}
- **🧮 Total Commits:** {total_commits}
- **⭐ Stars Earned:** {total_stars}
- **📊 Lines of Code:** {total_lines_of_code}

![Profile SVG](github_profile.svg)

{end_tag}"""

    # Read, replace, write
    with open("README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    if start_tag in readme and end_tag in readme:
        new_readme = readme.split(start_tag)[0] + stats_md + readme.split(end_tag)[1]
    else:
        # Append if tags not found
        new_readme = readme.strip() + "\n\n" + stats_md

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_readme)


# --------------- Main Orchestration ---------------

def main():
    if not TOKEN:
        print("Error: GitHub token not found. Set GITHUB_TOKEN in environment.")
        return

    user_data = get_user_details()
    if not user_data:
        return

    repos = get_repositories()
    total_commits = sum(get_repo_commits(repo["name"]) for repo in repos)
    total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    total_lines = sum(get_lines_of_code(repo["name"]) for repo in repos)

    stats = {
        "total_commits": total_commits,
        "total_stars": total_stars,
        "total_lines": total_lines
    }

    print(f"\nGitHub Stats for {USERNAME}:")
    for key, value in {**user_data, **stats}.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    generate_svg(user_data, stats)

    update_readme(
        user_data["followers"],
        user_data["following"],
        user_data["public_repos"],
        user_data["public_gists"],
        user_data["bio"],
        stats["total_commits"],
        stats["total_stars"],
        stats["total_lines"]
    )


if __name__ == "__main__":
    main()
