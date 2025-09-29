import os
import requests
import matplotlib.pyplot as plt

API_KEY = os.getenv("7377c5554029f3f7d2927d4b11818d52")  # put your key in environment
PLATFORM = "pypi"
PACKAGES = ["requests", "numpy", "pandas", "scipy", "matplotlib", "flask", "django"]

stars_dict = {}

for pkg in PACKAGES:
    url = f"https://libraries.io/api/{PLATFORM}/{pkg}"
    resp = requests.get(url, params={"api_key": API_KEY})
    if resp.status_code == 200:
        project = resp.json()
        stars = project.get("stars", 0)
        stars_dict[pkg] = stars
        print(f"{pkg}: {stars} stars")
    else:
        print(f"Failed to fetch {pkg}: {resp.status_code}")

# Plot bar chart
plt.figure(figsize=(10, 6))
plt.bar(stars_dict.keys(), stars_dict.values(), color="skyblue", edgecolor="black")
plt.title("Stars for Selected PyPI Packages (Libraries.io API)")
plt.xlabel("Package")
plt.ylabel("Stars")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

