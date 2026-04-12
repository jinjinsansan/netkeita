import urllib.request, json
url = "https://bot.dlogicai.in/nk/api/race/20260404-%E4%B8%AD%E5%B1%B1-11/matrix"
data = json.loads(urllib.request.urlopen(url).read())
for h in data["horses"]:
    print(f"#{h['horse_number']:2d} post={h['post']} {h['horse_name']} ({h['jockey']})")
