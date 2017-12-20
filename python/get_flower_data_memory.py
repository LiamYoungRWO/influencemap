import sqlite3
import os
import sys
from datetime import datetime
from mkAff import getAuthor
from export_citations_author import construct_cite_db
from entity_type import *

# Limit number of query
BATCH_SIZE = 999 # MAX=999

# database location
db_dir = "/localdata/u5642715/influenceMapOut"

# output directory
dir_out = "/localdata/u5642715/influenceMapOut/out"

def ids_dict(pdict):
    res = dict()
    for key in pdict.keys():
        res[key] = True
    return res

def get_papers(pdict):
    values = list()
    for key in pdict.keys():
        values += pdict[key]
    return values

def self_dict(pdict):
    res = dict()
    for key in pdict.keys():
        res[key] = True
    return res

'''
def coauthors_dict(conn, pdict, my_etype, fdict=dict()):
    e_id = pdict.keys()
    paper_ids = get_papers(pdict)
    coauth_dict = fdict

    cur = conn.cursor()

    for paper in paper_ids:
        query = 'SELECT {} FROM paper_info WHERE paper_id = ?'.format(my_etype.get_keyn())
        
        cur.execute(query, (paper, ))

        e_list = list()
        filter_flag = False

        for line in cur.fetchall():
            key, = line
            e_list.append(key)
            if key in e_id:
                filter_flag = True

        for val in e_list:
            coauth_dict[val] = True

    cur.close()
    return coauth_dict
'''

def get_weight(etype, qline, ref_count):
    if etype == Entity.AUTH:
        auth_id, auth_count = qline
        if not auth_id == '':
            return [(auth_id, (1 / auth_count) * (1 / ref_count), etype.keyn[0])]

    res = list()
    for idx, key in enumerate(etype.keyn):
        e_id = qline[idx]
        if not e_id == '':
            res.append((e_id, 1 / ref_count, key))
    return res

def gen_score(conn, etype, plist, iddict, fdict=dict(), selfcite=False):
    res = dict()
    id_to_name = dict([(tname, dict()) for tname in etype.keyn])

    # split papers into chunks
    total_prog = 0
    total = len(plist)
    # paper_chunks = [plist[x:x+BATCH_SIZE] for x in range(0, total, BATCH_SIZE)]

    cur = conn.cursor()

    for paper, ref_count in plist:
        # query plan for this
        output_scheme = ",".join(etype.scheme)
        #targets = ','.join(['?'] * len(chunk))
        query = 'SELECT {} FROM paper_info WHERE paper_id = ?'.format(output_scheme)

        cur.execute(query, (paper, ))

        qlines = list()
        self_cite = False

        # iterate through query results
        for line in cur.fetchall():
            # iterate over different table types
            for wline in get_weight(etype, line, ref_count):
                e_id, weight, tkey = wline
                # check if self cite
                if not selfcite and iddict.get(e_id, False):
                    self_cite = True
                    break

                # If id is in the filter map, don't add
                if not fdict.get(e_id, False):
                    qlines.append((e_id, weight, tkey))

            # If self_cite break out of outer loop
            if self_cite:
                break

        if self_cite:
            continue

        # Add scores
        for e_id, weight, tkey in qlines:
            # check ids_to_name dictionary
            try:
                e_name = id_to_name[tkey][e_id]
            except KeyError:
                id_query = 'SELECT * FROM {} WHERE {} = ? LIMIT 1'.format(etype.edict[tkey], tkey)
                cur.execute(id_query, (e_id, ))
                name = cur.fetchone()[1]
                e_name = ' '.join(name.split())

                id_to_name[tkey][e_id] = e_name

            # Add to score
            try:
                res[e_name] += weight
            except KeyError:
                res[e_name] = weight

        # progression
        # total_prog += 1
        # print('{} finish query of paper chunk, total prog {:.2f}%'.format(datetime.now(), total_prog/total * 100))

    cur.close()

    # return dict results
    return res

if __name__ == "__main__":

    # input
    name = sys.argv[1]

    # get paper ids associated with input name
    print('{} start get associated papers to input name {}'.format(datetime.now(), name))
    _, id_2_paper_id = getAuthor(name)
    print('{} finish get associated papers to input name {}'.format(datetime.now(), name))

    associated_papers = get_papers(id_2_paper_id)
    my_ids = ids_dict(id_2_paper_id)

    # sqlite connection
    db_path = os.path.join(db_dir, 'paper_info.db')
    conn = sqlite3.connect(db_path)

    db_path2 = os.path.join(db_dir, 'paper_ref.db')
    conn2 = sqlite3.connect(db_path2)

    # filter ref papers
    print('{} start filter paper references'.format(datetime.now()))
    citing_papers, cited_papers = construct_cite_db(conn2, associated_papers)
    print('{} finish filter paper references'.format(datetime.now()))

    # Generate a self filter dictionary
    filter_dict = self_dict(id_2_paper_id)

    # Add coauthors to filter
    # filter_dict = coauthors_dict(conn, id_2_paper_id, Entity.AUTH, filter_dict)

    # Generate associated author scores for citing and cited
    citing_records = gen_score(conn, Entity.CONF, citing_papers, my_ids, fdict=filter_dict)
    cited_records = gen_score(conn, Entity.CONF, cited_papers, my_ids, fdict=filter_dict)

    # Print to file (Do we really need this?
    with open(os.path.join(dir_out, 'authors_citing.txt'), 'w') as fh:
        for key in citing_records.keys():
            fh.write("{}\t{}\n".format(key, citing_records[key]))

    with open(os.path.join(dir_out, 'authors_cited.txt'), 'w') as fh:
        for key in cited_records.keys():
            fh.write("{}\t{}\n".format(key, cited_records[key]))

    conn.close()
