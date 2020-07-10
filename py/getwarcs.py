import csv, json, requests

cclist = json.loads(open("../json/cclist.json").read())

result = []

top2000csv = csv.DictReader(open("../csv/TOP-2000-1999.csv"))

try:
	for row in top2000csv:
		artist = row['artiest']
		track = row['titel']

		artist = artist.lower().replace(' ','-').replace(',','').replace('\'','').replace('(','').replace(')','').replace('.','-').replace('/','.')
		track = track.lower().replace(' ','-').replace(',','').replace('\'','').replace('(','').replace(')','').replace('.','-').replace('/','.')
		track += "-chords"

		print("Looking for {} by {}...\n".format(track, artist))

		foundtrack = False
		for i in range(50):#len(cclist)):
			print("Checking {}...".format(cclist[i]['id']))
			
			response = None
			while response == None:
				response = requests.get(cclist[i]["cdx-api"]+'?url=tabs.ultimate-guitar.com%2Ftab%2F' + artist + '%2F*&output=json')
				
				if response.status_code not in [200,404]:
					response = None
		
			found = False
			if response.status_code == 200:
				
				respjson = json.loads('['+response.text.replace('\n',',',response.text.count('{')-1)+']')
				
				for j in range(len(respjson)):
					if track in respjson[j]['url']:
						
						print("\nFound in {}:\nURL: {}\nWARC: {}".format(cclist[i]['id'],respjson[j]['url'],respjson[j]['filename']))
						
						result.append(dict({"artist":row["artiest"],"title":row["titel"],"rank":row["1999"],"year":row["jaar"],"id": cclist[i]['id'],"url":respjson[j]['url'],"filename":respjson[j]['filename']}))
						
						found = True
						foundtrack = True
						break
			if found:
				break

		if not foundtrack:		
			print("Not found")
		print('\n')
except KeyboardInterrupt:
	pass
finally:
	output = open("../json/foundwarcs.json", "w")
	output.write(json.dumps(result))
	print("Written to ../json/foundwarcs.json")
