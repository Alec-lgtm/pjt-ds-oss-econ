import os
import requests
import matplotlib.pyplot as plt

API_KEY = os.getenv("7377c5554029f3f7d2927d4b11818d52")  # put your key in env var
PACKAGE = "requests"
PLATFORM = "pypi"

url = f"https://libraries.io/api/{PLATFORM}/{PACKAGE}"
params = {"api_key": API_KEY}
resp = requests.get(url, params=params)
resp.raise_for_status()
project = resp.json()

# Choose one variable (documented in API responses)
stars = project.get("stars", 0)

print(f"{PACKAGE} stars: {stars}")

# Visualize just this one variable
plt.bar([PACKAGE], [stars], color="skyblue")
plt.title(f"Stars for {PACKAGE} ({PLATFORM})")
plt.ylabel("Stars")
plt.show()

