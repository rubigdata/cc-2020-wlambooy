import json, requests

cclist = json.loads(open("../json/cclist.json").read())

artist = "Dire Straits"
track = "Sultans Of Swing"

artist = artist.lower().replace(' ','-').replace(',','').replace('\'','').replace('(','').replace(')','')
track = track.lower().replace(' ','-').replace(',','').replace('\'','').replace('(','').replace(')','')
track += "-chords"

print("Looking for {} by {}...\n".format(track, artist))

for i in range(len(cclist)):
	print("Checking {}...".format(cclist[i]['id']))
	response = None
	while response == None:
		response = requests.get(cclist[i]["cdx-api"]+'?url=tabs.ultimate-guitar.com%2Ftab%2F' + artist + '%2F*&output=json')
		if response.status_code not in [200,404]:
			response = None
	respjson = json.loads('['+response.text.replace('\n',',',response.text.count('{')-1)+']')
			
	if not 'error' in respjson[0]:
		for j in range(len(respjson)):
			if track in respjson[j]['url']:
				print("\nFound in {}:\nURL: {}\nWARC: {}".format(cclist[i]['id'],respjson[j]['url'],respjson[j]['filename']))
				exit()
print("Not found")