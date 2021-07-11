package org.rubigdata

import org.apache.spark.sql.SparkSession
import org.apache.hadoop.io.NullWritable
import de.l3s.concatgz.io.warc.{WarcGzInputFormat,WarcWritable}
import de.l3s.concatgz.data.WarcRecord
import org.apache.commons.lang3.StringUtils
import org.apache.spark.SparkContext

object Top2000ChordCount {
  def main(args: Array[String]) {
    val spark = SparkSession.builder.appName("Top2000ChordCount").getOrCreate()

    val ugwarcs = spark.read.json("hdfs:///user/s1009854/ugwarcs2019.json")
    val outputrdd = spark.sparkContext.parallelize(ugwarcs.take(ugwarcs.count().toInt).map(w => getMostFrequentChords(w, spark)).flatMap(l => l)).reduceByKey(_ + _).sortBy(- _._2)

    println("\n########## OUTPUT ##########")
    println("The fifty most used chords in the Top 2000 of 2019 are:")
    outputrdd.take(50).foreach(println)
    println("########## OUTPUT ##########\n")

    spark.stop()
  }

  def getMostFrequentChords(input: org.apache.spark.sql.Row, spark: org.apache.spark.sql.SparkSession) : List[(String, Float)] = {
    val aws = s"s3://commoncrawl/"

    val warcfile = input.get(1).toString

    val artist = input.get(0).toString

    val tracktitleraw = input.get(4).toString
    val tracktitle = formatTrackTitle(tracktitleraw)

    val warcs = spark.sparkContext.newAPIHadoopFile(
                        aws+warcfile,
                        classOf[WarcGzInputFormat],
                        classOf[NullWritable],
                        classOf[WarcWritable]
                )

    val wb = warcs.
            map{ wr => wr._2.getRecord() }.
            filter{ _.getHeader().getUrl() != null}.
            filter{ _.getHeader().getUrl().contains("ultimate-guitar")}.
            filter{ _.getHeader().getUrl().contains(tracktitle)}.
            filter{ _.getHeader().getUrl().contains("chords")}.
            map{ wr => wr.getHttpStringBody()}.
            filter{ _.length > 0 }

    if (wb.count() == 0) {
        return List()
    } else {
        val ugHTML = wb.take(1)(0)

        val regex = """\[ch\]([^\\\s]+)\[\/ch\]""".r

        val results = (regex findAllIn ugHTML).matchData.map(_ group 1).toList
        val chordsgrouped = results.groupBy(identity).transform((k,v) => (k,v.size)).values.toList.sortBy(- _._2)
        val chordsordered = chordsgrouped.zipWithIndex.map{case((c,n),i) => (c,1f/(i+1))}
        
        return chordsordered
    }

    
  }

  def formatTrackTitle(tracktitle: String) : String = {
    tracktitle.toLowerCase()
                .replace("Part I", "Part 1")
                .replace(" & ","-")
                .replace(". ","-")
                .replace(" ","-")
                .replace(",","")
                .replace("\'","")
                .replace("(","")
                .replace(")","")
                .replace(".","-")
                .replace("/",".")
                .replace("!","")
  }
}