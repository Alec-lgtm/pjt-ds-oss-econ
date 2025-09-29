import pandas as pd

url = 'http://flossdata.syr.edu/data/apache/git/all-authors-by-commits-2012-08.csv'

df = pd.read_csv(url)

print(df.head())
