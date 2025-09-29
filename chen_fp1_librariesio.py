import librariesio
import matplotlib.pyplot as plt

# Replace with your Libraries.io API key
API_KEY = "7377c5554029f3f7d2927d4b11818d52"

# Create a client
client = librariesio.Client(API_KEY)

# Example: fetch project data for the "requests" library from PyPI
project = client.project("pypi", "requests")

# Extract some interesting variables
repo_name = project.get("repository_url", "Unknown")
stars = project.get("stars", 0)
forks = project.get("forks", 0)
subscribers = project.get("subscribers", 0)

print(f"Repo: {repo_name}")
print(f"Stars: {stars}, Forks: {forks}, Subscribers: {subscribers}")

# Visualization (bar chart)
labels = ["Stars", "Forks", "Subscribers"]
values = [stars, forks, subscribers]

plt.bar(labels, values, color=["#4caf50", "#2196f3", "#ff9800"])
plt.title("GitHub Stats for 'requests' (from Libraries.io API)")
plt.ylabel("Count")
plt.show()

