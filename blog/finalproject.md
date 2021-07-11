# Introduction
During the the past months of making assignments I began understanding more and more about Spark and HDFS, mostly through experience. It was time to put this to the test with an interesting project to work on. 

For the project, the objective was to do something with web archive (WARC) data from CommonCrawl. I imagined that if I had something fun to work on with interesting output, this would give me a good drive to finish the project quickly. Over the past couple of months I have been getting a lot into music making and musical composition, so I thought, why not do something interesting with music data?

## The plan
The idea that came to mind is to analyse the chords used in the Top 2000. I could use the Top 2000 as a reference of commonly-appreciated music, then check what chords are used in each song using the website [ultimate-guitar.com](https://www.ultimate-guitar.com). As a guitarist, I know that whenever you look for chords of a song by typing "<songname\> chords" into a search engine, this website will very likely be the first result. It has a catalog of over a million songs and the chords themselves seemed to be easy enough to extract from the website at first sight, more on that later. 

It became clear that there were three parts to this project for me: getting the WARC data, analysing it locally and running the full program on the cluster.

1. [Getting the WARCs](#getting-the-warcs)
2. [Extracting chords](#extracting-chords)
3. [Combining the data and running on the cluster](#combining-the-data-and-running-on-the-cluster)

* [Results](#results)
	* [Most used chords](#most-used-chords)
	* [Most used consecutive chord sequences](#most-used-consecutive-chord-sequences)
* [Conclusion](#conclusion)

# Getting the WARCs
The title of this section already tells something I did not fully expect when starting with the process, this being that WARCs is plural. At the start, I expected that each website would have its own WARC in the CommonCrawl, with each webpage from that website in the same WARC. After querying the CommonCrawl Index (CC-INDEX) for ```ultimate-guitar.com```, 8 WARCs appeared. I downloaded each one to see which chord sheets were in which one, but to my surprise, they all had only the ultimate-guitar.com homepage in them, plus maybe one or two other webpages from this website. It was clear that querying the CC-INDEX for the homepage would only give WARCs with the homepage. The first worries for this project started to settle when querying for ```ultimate-guitar.com/*```: this, to my surprise, returned tens of thousands of WARCs, implying that this website (and probably any website) was completely fragmented over numerous WARC files. To add to this, I noticed that the individual CommonCrawls do not have overlap (I think), so the crawls only contain webpages that have been added (or changed?) after the previous crawl. Since I needed to get the data from specific URLs, this implies I need to collect specific WARC files. This was the first hurdle, but nothing that a Python script could not fix.

## The next step
After trying some queries on the CC-INDEX search engine, I found a way to semi-consistently collect WARC files for specific songs. Each chord page on ultimate-guitar.com is on the subdomain ```tabs``` and querying for ```tabs.ultimate-guitar.com/<artist>/*``` returns all ultimate-guitar.com webpages that were relevant to that artist on the crawl queried. Each chord webpage has ```<title>-chords``` in the URL, so this was useful too. It is important to note that the ```<artist>``` and ```<title>``` only consist of lowercase letters a-z and dashes in between words. ```Simon & Garfunkel``` hence becomes ```simon-garfunkel```. Something else I noticed is that ultimate-guitar.com had started to use the tabs subdomain somewhere around 2015, this will be useful later in the process.

Getting the Top 2000 data was not hard at all, [nporadio2.nl/top2000](https://www.nporadio2.nl/top2000) had all Top 2000s archived and downloadable as .xlsx. Using an online converter I converted these .xlsx files to my preferred format: .csv. The file can be found in ```csv/TOP-2000-1999.csv``` I chose to go with the first iteration of the Top 2000, from 1999. Using the ```csv``` library, I was able to easily iterate over the rows in the CSV file. Using the ```json``` and ```requests``` libraries, I first loaded a JSON of all CC indices that was available on the CC-INDEX website. I iterated over each row of the Top 2000 CSV, which had the columns ```Rank```, ```Artiest```, ```Titel``` and ```Jaar```. Using a couple of ```.replace()```  calls, I converted the artist and song title fields to something that could occur in a ultimate-guitar.com URL. Then, starting at the latest CC, I iterated over each crawl in reverse chronological order for each crawl that had at least one result for ```tabs.ultimate-guitar.com/*```, which turned out to be the first fifty crawls. For each of the crawls I queried for ```tabs.ultimate-guitar.com/<artist>/*```, then, using a greedy approach, I added the first WARC entry that had ```<title>-chords``` in the URL to the list to return. The result would be output as a JSON file. This first iteration can be found in [py/getwarcs.py](https://www.github.com/rubigdata/cc-2020-wlambooy/blob/master/py/getwarcs.py).

I took a break from the project by letting this script run for around 36 hours, after which it had gone over the first 1337 songs in the Top 2000. The script was extremely slow due to massive latency issues. There were quite a few songs that could not be found at all and some that were parsed incorrectly (I forgot to replace the '&' the first time). For each of these songs it went ahead waited for fifty responses anyway (non-parallel) which look a long time. After this first run I got the WARC file with the ultimate-guitar chords for around 280 songs. I noticed that each result came from one of the first seven CCs queried, so this would make for a massive speedup for the next iteration of the script. Before starting with the next part of the project, I quickly edited the script to include some fixes for the ```artist``` and ```title``` conversion and queried only the first seven CC indices. This iteration ([py/getmorewarcs.py](https://www.github.com/rubigdata/cc-2020-wlambooy/blob/master/py/getmorewarcs.py)) took around three hours to finish the complete Top 2000, after which it yielded an additional 108 results, bringing the total amount of results to 382. The resulting JSON can be seen in [json/ugwarcs1999.json](https://www.github.com/rubigdata/cc-2020-wlambooy/blob/master/json/ugwarcs1999.json).

# Extracting chords
This part when relatively smooth. I first downloaded a WARC from the list that I had collected and put it on the Docker container. Using Zeppelin locally though Docker with the WARC for Spark II notebook (I originally used the first WARC for Spark notebook but this gave me some issues in the end), I loaded the WARC file and listed its contents by filtering the URLs on containing "ultimate-guitar", "chords" and the song title parsed in the same way as in the Python script. For the WARCs I tested, it seemed to be consistent to just take the HTML of the first element in the resulting array and continue with that. 

In the image below you can see an example of how a chords webpage looks like, this one displays the [chords for Bohemian Rhapsody by Queen](https://tabs.ultimate-guitar.com/tab/queen/bohemian-rhapsody-chords-40606)

<img src="imgs/ugqueen.png" width="450"/>

Extracting the chords looks easy enough since each chord looks to be wrapped in some HTML stuff. Upon closer inspection of the HTML, each chord is wrapped in ```[ch]<chord>[/ch]```. This is not actual HTML syntax but rather something for the website templater. Because of this, I had not much use for JSoup to extract HTML elements and rather I had to parse the HTML using a regular expression. Using [regex101.com](https://www.regex101.com), I was able to create a nice regular expression in a whiff: 
```scala
val regex = """\[ch\]([^\\\s]+)\[\/ch\]""".r
```
With the help of StackOverflow, I could use this regular expression to generate the list of chords used:
<img src="imgs/ugchordso1.png"/>
I then applied some functional transformations to group the chords and sort the resulting list to have the most occurring chord first:
<img src="imgs/ugchordso2.png"/>

That looks good, I think I am almost done!

# Combining the data and running on the cluster
When I thought I was almost done after the previous part, I did not realise that the most time-consuming and frankly the most frustrating part was still ahead of me. While I will not go into detail with the numerous errors that occurred in the process of getting a program running correctly on the cluster, it should be noted that I definitely did not get everything running in one go. I started off rather well however, I converted my Zeppelin code to a Spark job that would give the four most used chords in Bohemian Rhapsody which returned the expected answer on the second go, to my surprise.

## Combining the data
Before I could move on to create a job running over multiple WARCs, I needed to find a way to combine the data that was gathered. My primary objective with the chord data analysis was to output the most used chords in the Top 2000. To make the output from ```chordsgrouped``` combinable, I needed to assign relative values to the chords depending on how often they occur in the chart. I considered a few solutions, for example I could could give each chord the value ```no_of_times_used/max_no_of_times_used``` where ```max_no_of_times_used``` is the amount of times the most frequent occurring chord occurred. Upon inspection of arbitrary chord charts, I noticed that some charts charted a part of the song twice, with more detail the second time. This was mostly for parts that occurred multiple time throughout the song, so often occurring chords would occur more often. To prevent an imbalance following from this, I decided to simply assign each chord 1 divided by the index of the chord in the sorted list + 1:
<img src="imgs/ugchordso3.png"/>

This would now be the output of the mapper, the reduce operation will simply consist of adding the values together per key.

## Creating a Spark Job and running on the cluster
I now needed to compress the code snippets I had in Zeppelin to a single Spark Job running over all the data I had collected. Using Sparks JSON reader, I was able to create a RDD from the ```ugwarcs1999.json``` file I created earlier. Using the Map-Reduce design pattern, I created a mapper function ```getMostFrequentChords``` that takes a RDD row as input and outputs a list of key-value pairs. The output of running this mapper function on the input RDD was then flatMapped so a new RDD could be made. This enabled me to use the reduceByKey function, which reduces the mapped input using the different chords as keys. 

I first tested this job with the first four entries of the JSON (```take(4)```) which executed well on the cluster. When scaling up to the full RDD however (stop using ```take()```), I got continuous errors with each new attempt, so I took the following escape approach, which worked fine:
```scala
ugwarcs.take(ugwarcs.count().toInt)
```
Running a job on the cluster was pretty straightforward, I just needed to ```hdfs dfs -put``` the input JSON on the cluster and I was set. The last hurdle that arose when submitting my job to the cluster is that it returned a NullPointerException after a minute. Apparently some WARCs I collected did have an entry with the URL that should be contained in it, however this entry did not have any content so the HTML array would have length 0 and taking the first element of this array would fail. For my first proper run, I included some debug output with the ranks of each song for which this occurred. The final output for this run was the twenty most used chords in the Top 2000. The outlog can be found in [out/outlog20_99.txt](https://www.github.com/rubigdata/cc-2020-wlambooy/blob/master/out/outlog20_99.txt). Apparently this NullPointerException would have occurred for 11 songs so this was not a big deal since the other 371 songs were processed correctly. For the second run of my job, I removed the debug output and output the fifty most used chords. The value assigned to each chord is the result of adding the mapper outputs for that chord for each song (```reduceByKey(_ + _)```), note that this value is relative to the cardinality of the input set. The job used to create the output can be found in [scala/clusterjob50-1999.scala](https://www.github.com/rubigdata/cc-2020-wlambooy/blob/master/scala/clusterjob50-1999.scala). Its output can be found [here](https://www.github.com/rubigdata/cc-2020-wlambooy/blob/master/out/outlog50_99.txt).

# Results

## Most used chords
I edited the WARC collector script to collect song from the 2019 iteration of the Top 2000, this time it collected 657 songs in 4.5 hours, so almost double the amount of songs I collected for the 1999 iteration. The output can be seen on the right side in the table below.

----

*This table contains the most used chords for the Top 2000 of 1999 and 2019 separately. The values assigned to the chords for are relative per year since the input set sizes differ.*

| Rank | 1999 (Chord,Value)     | 2019 (Chord,Value)     |
|------|------------------------|------------------------|
| 1    | (**G**,91.76782)       | (**G**,180.51779)      |
| 2    | (**C**,86.98074)       | (**C**,156.6589)       |
| 3    | (**D**,82.46628)       | (**D**,140.5357)       |
| 4    | (**A**,63.903236)      | (**A**,106.72741)      |
| 5    | (**E**,54.852364)      | (**F**,92.9258)        |
| 6    | (**F**,51.36029)       | (**Em**,90.34632)      |
| 7    | (**Em**,37.20516)      | (**Am**,75.17919)      |
| 8    | (**Am**,33.29219)      | (**E**,73.62939)       |
| 9    | (**B**,23.326736)      | (**Dm**,37.824093)     |
| 10   | (**Dm**,20.07482)      | (**Bm**,28.822659)     |
| 11   | (**Bm**,18.050669)     | (**Bb**,27.8132)       |
| 12   | (**Bb**,16.533905)     | (**B**,26.872005)      |
| 13   | (**F#**,13.226496)     | (**F#m**,18.90599)     |
| 14   | (**F#m**,12.385719)    | (**Gm**,16.449133)     |
| 15   | (**D7**,11.991313)     | (**Am7**,13.738431)    |
| 16   | (**E7**,10.993721)     | (**F#**,13.506865)     |
| 17   | (**A7**,10.654926)     | (**Eb**,13.252374)     |
| 18   | (**Am7**,9.677315)     | (**D7**,11.747337)     |
| 19   | (**Bm7**,9.140049)     | (**Em7**,11.709919)    |
| 20   | (**Gm**,9.116614)      | (**A7**,11.560539)     |
| 21   | (**G7**,8.763174)      | (**E7**,10.437331)     |
| 22   | (**C7**,8.174505)      | (**C#m**,10.236774)    |
| 23   | (**Cm**,7.96508)       | (**Ab**,9.844742)      |
| 24   | (**B7**,7.7129908)     | (**Cadd9**,9.603373)   |
| 25   | (**Eb**,7.1548705)     | (**B7**,9.176017)      |
| 26   | (**Dm7**,6.120718)     | (**Cm**,8.929133)      |
| 27   | (**Em7**,5.507609)     | (**Fm**,7.805945)      |
| 28   | (**C#m**,5.4589343)    | (**G/B**,7.2224813)    |
| 29   | (**Cmaj7**,4.530143)   | (**Cmaj7**,7.220691)   |
| 30   | (**G#**,4.525)         | (**Bm7**,6.641637)     |
| 31   | (**G/B**,4.118513)     | (**G7**,6.602749)      |
| 32   | (**Ab**,3.7859151)     | (**C7**,6.5293036)     |
| 33   | (**Gm7**,3.6625886)    | (**G5**,6.028384)      |
| 34   | (**Fmaj7**,3.5617425)  | (**C#**,5.548621)      |
| 35   | (**C#m7**,3.3340006)   | (**D/F#**,5.5166235)   |
| 36   | (**C#**,3.123528)      | (**Fmaj7**,5.1724567)  |
| 37   | (**G#m**,3.0001915)    | (**Dm7**,5.149885)     |
| 38   | (**Fm**,2.8316665)     | (**Dsus2**,4.920076)   |
| 39   | (**Fm7**,2.7958333)    | (**Dsus4**,4.912119)   |
| 40   | (**Db**,2.7693498)     | (**D5**,4.8745255)     |
| 41   | (**Cm7**,2.7420254)    | (**G#m**,4.790799)     |
| 42   | (**F#m7**,2.676838)    | (**A5**,4.4034276)     |
| 43   | (**Dmaj7**,2.572619)   | (**Asus4**,4.1252236)  |
| 44   | (**G/D**,2.2050068)    | (**C/G**,4.11792)      |
| 45   | (**Asus2**,2.083247)   | (**C/E**,3.8650107)    |
| 46   | (**G6**,1.8488636)     | (**A7sus4**,3.7537715) |
| 47   | (**Bbm**,1.8398694)    | (**C#m7**,3.6675324)   |
| 48   | (**Asus4**,1.8352544)  | (**D#**,3.5957603)     |
| 49   | (**D#m**,1.7704545)    | (**Amaj7**,3.5383117)  |
| 50   | (**C/E**,1.7261214)    | (**Asus2**,3.261515)   |

-----

## Most used consecutive chord sequences
For another experiment, I eagerly wanted to try if I could extract the most used consecutive sequences of chords in the Top 2000. This output would give very useful insight into which chords sound good after some other chord. For my input, I chose to use the Top 2000 of 2019 dataset since I had more data for this iteration of the Top 2000. With slight changes to the getChordCounts mapper function, I was able to transform it to output consecutive chord sequences of length 2, with relative values assigned to them based on their occurrence count in the song. I did this by changing the ```chordsgrouped``` value. The full Scala code for this Spark job can be found in [scala/clusterjobSeq2019.scala](https://www.github.com/rubigdata/cc-2020-wlambooy/blob/master/scala/clusterjobSeq2019.scala).
```scala
val chordseqgrouped = (results.grouped(2) ++ results.drop(1).grouped(2)).toList
                                .filter(_.size == 2).filter(_.toSet.size > 1)
                                .groupBy(identity).transform((k,v) => (k,v.size))
                                .values.toList.sortBy(- _._2)
``` 
The final run that succeeded in giving output took a whopping 13 and a half hours, the raw output can be found [here](https://github.com/rubigdata/cc-2020-wlambooy/blob/master/out/seqoutlog_19.txt).

----

*This table contains the most used consecutive chord sequences of lenght 2 for the Top 2000 of 2019 together with their relative values (higher = more common).*

| Rank | Chord Sequence | Value |
|------|:-----------:|-----------|
| 1    | C → G       | 64.09691  |
| 2    | G → D       | 53.729744 |
| 3    | G → C       | 48.07283  |
| 4    | D → A       | 39.891014 |
| 5    | D → G       | 39.32843  |
| 6    | Em → C      | 30.315874 |
| 7    | F → C       | 29.888504 |
| 8    | A → E       | 28.245712 |
| 9    | C → D       | 26.245422 |
| 10   | C → F       | 25.650906 |
| 11   | F → G       | 25.62784  |
| 12   | Am → F      | 24.79731  |
| 13   | A → D       | 20.156832 |
| 14   | G → Am      | 19.016378 |
| 15   | E → A       | 17.083902 |
| 16   | D → C       | 16.796745 |
| 17   | C → Em      | 16.416103 |
| 18   | D → Em      | 16.048216 |
| 19   | G → Em      | 15.995105 |
| 20   | Am → G      | 15.986654 |
| 21   | Em → D      | 14.894712 |
| 22   | G → F       | 14.822518 |
| 23   | C → Am      | 14.606403 |
| 24   | Am → C      | 13.895739 |
| 25   | Em → G      | 13.856773 |
| 26   | G → A       | 13.628114 |
| 27   | Am → Em     | 11.702563 |
| 28   | E → B       | 10.238043 |
| 29   | E → D       | 10.183832 |
| 30   | Em → Am     | 9.9678335 |
| 31   | D7 → G      | 9.028028  |
| 32   | D → E       | 8.862451  |
| 33   | A → G       | 8.835319  |
| 34   | A → Bm      | 8.602225  |
| 35   | C → Bb      | 8.441133  |
| 36   | Bb → F      | 7.956235  |
| 37   | Dm → C      | 7.777381  |
| 38   | Bm → A      | 7.6790595 |
| 39   | B7 → Em     | 7.5901227 |
| 40   | B → E       | 7.1928973 |
| 41   | F → Bb      | 6.772066  |
| 42   | Em → A      | 6.4933896 |
| 43   | Dm → F      | 6.44967   |
| 44   | Bm → G      | 6.3353367 |
| 45   | F → Am      | 5.963629  |
| 46   | Dm → G      | 5.8024883 |
| 47   | Em → F      | 5.752368  |
| 48   | C#m → A     | 5.6409087 |
| 49   | D → Am      | 5.511447  |
| 50   | D → Bm      | 5.4955974 |
| 51   | F → Dm      | 5.4845905 |
| 52   | B → A       | 5.3693266 |
| 53   | Bb → C      | 5.302263  |
| 54   | C → Dm      | 5.1585283 |
| 55   | A → Em      | 4.7227483 |
| 56   | E → G       | 4.3338113 |
| 57   | E → F#m     | 4.1778107 |
| 58   | Dm → Am     | 4.138019  |
| 59   | A → F#m     | 4.131686  |
| 60   | F#m → E     | 4.1164684 |
| 61   | A → C       | 4.1114106 |
| 62   | G → Bm      | 4.099782  |
| 63   | A → B       | 4.0809484 |
| 64   | A7 → D      | 3.993377  |
| 65   | D → F       | 3.9128911 |
| 66   | F#m → D     | 3.885835  |
| 67   | G7 → C      | 3.7990706 |
| 68   | Cm → Ab     | 3.79259   |
| 69   | Bm → E      | 3.7790575 |
| 70   | Bb → Eb     | 3.7753477 |
| 71   | F → Eb      | 3.712745  |
| 72   | F#m → A     | 3.5411398 |
| 73   | Esus4 →   E | 3.4984426 |
| 74   | G → Cadd9   | 3.390482  |
| 75   | Am → Dm     | 3.3644698 |
| 76   | B → Em      | 3.3089685 |
| 77   | G → Dm      | 3.28208   |
| 78   | C → A       | 3.256203  |
| 79   | Bb → Gm     | 3.245777  |
| 80   | G → E       | 3.2398012 |
| 81   | Bm → F#m    | 3.2143793 |
| 82   | Cadd9 →   G | 3.2106836 |
| 83   | Bm → D      | 3.208025  |
| 84   | Bb → A      | 3.1879425 |
| 85   | C → G/B     | 3.187698  |
| 86   | A → Dm      | 3.1730938 |
| 87   | Em7 → C     | 3.0949702 |
| 88   | G → D/F#    | 3.03002   |
| 89   | B → C#m     | 3.0239754 |
| 90   | Ab → Bb     | 3.0163069 |
| 91   | C → C7      | 2.9913168 |
| 92   | F → D       | 2.97371   |
| 93   | Dm → Gm     | 2.9616015 |
| 94   | Eb → Bb     | 2.9447858 |
| 95   | G → Em7     | 2.9093072 |
| 96   | Gm → C      | 2.8777957 |
| 97   | C → C/B     | 2.8713236 |
| 98   | B → F#      | 2.8444443 |
| 99   | Gm → Bb     | 2.8349674 |
| 100  | C → Am7     | 2.775204  |

-----

# Conclusion
The process of arriving at the results was a lengthy one and one certainly not without hurdles. I have been working day in - day out on this project for a week straight (apart from the data collection day) to finish the project as quickly as possible since I have a trip to France planned. When I first got the idea for my project I thought of lots of interesting analysis ideas, some of which would be useful for my own musical development. I am very content that I was able to get the most used consecutive chord sequences, but if I had more time I would have liked to take this a step further. Not only would I like to know the most used consecutive chords sequences of length N > 2, I would have liked to try and abstract away from the musical scale the song was written in and output the most frequent occurring consecutive sequences of [scale degrees](https://en.wikipedia.org/wiki/Roman_numeral_analysis). This could be done by with a dataset of chords and keys, matching each song to the key that matches the best with the notes used in the song. Unfortunately I do not have enough time for that at the moment, perhaps when I am back in the Netherlands at the end of the month I try a bit more with the data I gathered (although the cluster will probably be down by then).

In the end I thought the project was fun to work on when you know what you are doing. I started off with the project by just trying things until it worked and for the most part that went alright, although I got stuck after a while and finally decided to properly read the assignment. I then realised there was a lot of information there that I found out on my own, so I suppose reading the assignment first would have saved me some time. 

[Back to top]()