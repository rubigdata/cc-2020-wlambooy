import csv, json, requests

cclist = json.loads(open("../json/cclist.json").read())

foundwarcs = json.loads(open("../json/ugwarcs1999.json").read())

result = []

top2000csv = csv.DictReader(open("../csv/TOP-2000-2019.csv"))

try:
	for row in top2000csv:
		artistraw = row['ARTIEST']
		trackraw = row['TITEL']
		rank = row['NR.']
		year = row['JAAR']
		ccid = ""
		ccurl = ""
		ccfilename = ""

		alreadyfound = False
		for foundwarc in foundwarcs:
			if trackraw == foundwarc['title'] and artistraw == foundwarc['artist']:
				ccid = foundwarc['id']
				ccurl = foundwarc['url']
				ccfilename = foundwarc['filename']
				alreadyfound = True
				break
		if alreadyfound:
			result.append(dict({"artist":artistraw,"title":trackraw,"rank":rank,"year":year,"id": ccid,"url":ccurl,"filename":ccfilename}))
			print("Already found, skipping")
			print("\n")
			continue

		artist = artistraw.lower().replace(" & ", '-').replace(". ",'-').replace(' ','-').replace(',','').replace('\'','').replace('(','').replace(')','').replace('.','-').replace('/','.').replace('!','')
		track = trackraw.lower().replace("Part I", "Part 1").replace(" & ", '-').replace(". ",'-').replace(' ','-').replace(',','').replace('\'','').replace('(','').replace(')','').replace('.','-').replace('/','.').replace('!','')
		track += "-chords"

		print("Looking for {} by {}...\n".format(track, artist))

		foundtrack = False
		for i in range(7):#len(cclist)):
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
						
						result.append(dict({"artist":artistraw,"title":trackraw,"rank":rank,"year":year,"id": cclist[i]['id'],"url":respjson[j]['url'],"filename":respjson[j]['filename']}))
						
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
	output = open("../json/foundwarcs2019.json", "w")
	output.write(json.dumps(result, indent=4))
	print("Written to ../json/foundwarcs2019.json")
