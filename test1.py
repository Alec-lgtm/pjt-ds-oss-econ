import os
import requests
import matplotlib.pyplot as plt

API_KEY = os.getenv("7377c5554029f3f7d2927d4b11818d52")  # set this in your shell
PLATFORM = "pypi"
PACKAGES = ["requests", "numpy", "pandas", "scipy", "matplotlib", "flask", "django"]

stars_list = []

for pkg in PACKAGES:
    url = f"https://libraries.io/api/{PLATFORM}/{pkg}"
    resp = requests.get(url, params={"api_key": API_KEY})
    if resp.status_code == 200:
        project = resp.json()
        stars = project.get("stars", 0)
        stars_list.append(stars)
        print(f"{pkg}: {stars} stars")
    else:
        print(f"Failed to fetch {pkg}: {resp.status_code}")

# Plot histogram of stars across projects
plt.hist(stars_list, bins=5, color="skyblue", edgecolor="black")
plt.title("Distribution of Stars for Selected PyPI Projects")
plt.xlabel("Stars")
plt.ylabel("Number of Projects")
plt.show()

