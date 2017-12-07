import sqlite3 as sql
import os
import sys
from datetime import datetime

# set database location
data_dir = "/localdata/u5798145/influencemap"
db_name = "paper.db"
db_path = os.path.join(data_dir,db_name)

# get name of interest
author_name = sys.argv[1]


# open database connection
conn = sql.connect(db_path)
cur = conn.cursor()
print("{} input query: {}. Connected to {}".format(datetime.now(), author_name, db_path))

# drop existing any remaining temporary tables
table_names = ["authIDs", "publishedPapers", "citedPapers","citingPapers","reducedPAA",
				"citedPapersAuthors", "citedPaperWeights", "citingPaperWeights", "citingPapersAuthors", 
				"citedAuthorScores", "citingAuthorScores"]

for table in table_names:
	print("{} dropping {}".format(datetime.now(), table))
	q = "DROP TABLE IF EXISTS {}".format(table)
	cur.execute(q)

# get author ids and published papers
print("{} finding authorIDs associated with {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE authIDs AS SELECT authorID FROM authors WHERE authorName LIKE '{}'".format(author_name))
print("{} finding papers published by {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE publishedPapers AS SELECT paperID FROM PAA WHERE authorID IN authIDs")
print("{} dropping authID table".format(datetime.now()))
 
# get cited and citing papers
print("{} finding papers cited by {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citedPapers AS SELECT paperReferenceID as paperID FROM paperReferences WHERE paperID IN publishedPapers")
print("{} finding papers that have cited publications of {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citingPapers AS SELECT paperID FROM paperReferences WHERE paperReferenceID IN publishedPapers")

# create reduced database
cur.execute("CREATE TABLE reducedPAA AS SELECT * FROM PAA WHERE paperID IN (SELECT paperID FROM (SELECT paperID FROM publishedPapers UNION SELECT paperID FROM citedPapers) UNION SELECT paperID FROM citingPapers)")

# get cited author scores
print("{} connecting papers cited by {} to their respective authors".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citedPapersAuthors AS SELECT paperID, authorID FROM reducedPAA WHERE paperID IN citedPapers")
print("{} weighting papers cited by {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citedPaperWeights AS SELECT paperID, (CAST(1 AS float) / CAST(COUNT(authorID) AS float)) AS weightPerAuthor FROM citedPapersAuthors GROUP BY authorID")
print("{} summing weighted scores for authors cited  by {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citedAuthorScores AS SELECT authorID, CAST(SUM(weightPerAuthor) as float) AS weightedScore  FROM (citedPapersAuthors INNER JOIN citedPaperWeights) GROUP BY authorID")
print("{} dropping citedPapers and citedPaperWeights tables".format(datetime.now()))

# get citing author scores
print("{} connecting papers cited by {} to their respective authors".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citingPapersAuthors AS SELECT paperID, authorID FROM reducedPAA WHERE paperID IN citingPapers")
print("{} weighting papers that cite {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citingPaperWeights AS SELECT paperID, (CAST(1 AS float) / CAST(COUNT(authorID) AS float)) AS weightPerAuthor FROM citingPapersAuthors GROUP BY authorID")
print("{} summing weighted scores for authors that cite {}".format(datetime.now(), author_name))
cur.execute("CREATE TABLE citingAuthorScores AS SELECT authorID, CAST(SUM(weightPerAuthor) as float)  AS weightedScore FROM (citingPapersAuthors INNER JOIN citingPaperWeights) GROUP BY authorID")
print("{} dropping citingPapers, citingPaperWeights and publishedPapers tables".format(datetime.now()))

for table in table_names:
	print("{} dropping ".format(datetime.now(), table))
	q = "DROP TABLE IF EXISTS {}".format(table)
	cur.execute(q)

# close database connection
print("closing connection to database")
csr.close()
conn.close()