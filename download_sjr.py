import urllib.request

url = 'https://www.scimagojr.com/journalrank.php?out=xls'
headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request(url, headers=headers)
print("Downloading SCImago CSV...")
try:
    with urllib.request.urlopen(req) as response:
        with open('data/scimagojr.csv', 'wb') as out_file:
            out_file.write(response.read())
    print("Downloaded successfully!")
except Exception as e:
    print(f"Error: {e}")
