import sqlite3
import math
import itertools
import os
import csv
from datetime import datetime 
from sqlite3 import Error

chunk_limit = 999

"""
scheme as a list of strings in order

will delete and remake the specified table if it already exists
"""
def construct_table(conn, name, scheme, override=False, primary=[]):
    try:
        cur = conn.cursor()

        # check if override option is True
        if override:
            print('{} removing table {}'.format(datetime.now(), name))
            cur.execute('DROP TABLE IF EXISTS {};'.format(name))
            print('{} removed table {}'.format(datetime.now(), name))

        if primary:
            scheme.append('PRIMARY KEY ({})'.format(",".join(primary)))

        print('{} creating table {}'.format(datetime.now(), name))
        cur.execute('CREATE TABLE IF NOT EXISTS {} ({});'.format(name, ",".join(scheme)))
        print('{} created table {}'.format(datetime.now(), name))
    except Error as e:
        print(e)

def remove_outer_quotes(string):
    if string.startswith in quotes and stringendswith in quotes and string.startswith == stringendswith:
        return string[1:-1]
    return string

def gen_chunks(reader, chunk_size, idx):
    chunk = []
    for i, line in enumerate(reader):
        if (i % chunk_size == 0 and i > 0):
            yield chunk
            del chunk[:]
        chunk.append([line[i] for i in idx])
    yield(chunk)

def do_insert(cur, chunk, name, colname):
    num_cols = len(colname)
    vals = list(map(lambda line : '({})'.format(','.join(line)), chunk))
    num_ins = len(vals)
    # ins_string = ','.join(['({})'.format(','.join((['?'] * num_cols)))] * num_ins)
    ins_string = ','.join(['({})'.format(','.join((['?'] * num_cols)))] * num_ins)
    # print(list(itertools.chain.from_iterable((chunk))))

    cur.execute('INSERT INTO {} ({}) VALUES {};'.format(name, ",".join(colname), ins_string), list(itertools.chain.from_iterable((chunk))))


"""
Imports data from f into the table given by name

dataidx is a list of int which specify to columns in the data which correspond
to colname in order. First column is col 0
"""
def import_to_table(conn, name, f, colname, dataidx, delim='\t', rmquotes=False, fmap=id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(name))
        if not cur.fetchone:
            raise Exception("Table {} does not exist".format(name))

        # Import table data from file f
        print("{} starting reading data from {}".format(datetime.now(), f))
        data = csv.reader(open(f, 'r'), delimiter=delim)
        print("{} finish reading data from {}".format(datetime.now(), f))

        chunk_size = math.floor(chunk_limit / len(colname))
        chunk_count = 0

        for chunk in gen_chunks(data, chunk_size, dataidx):
            chunk_count += 1

            #print("{} begin preprocessing for chunk {}".format(datetime.now(), chunk_count))

            if rmquotes:
                chunk = list(map(lambda line : list(map(remove_outer_quotes, line)), chunk))

            chunk = list(map(lambda line : list(map(fmap, line)), chunk))
            chunk = list(map(lambda line : list(map(lambda s : str(s), line)), chunk))
            #print("{} finish preprocessing for chunk {}".format(datetime.now(), chunk_count))

            #print("{} begin transaction for chunk {}".format(datetime.now(), chunk_count))
            cur.execute('BEGIN TRANSACTION')

            # cur.executemany('INSERT INTO {} ({}) VALUES (?, ?);'.format(name, ",".join(colname)), chunk)
            do_insert(cur, chunk, name, colname)

            cur.execute('COMMIT')
            if chunk_count % 1e4 == 0:
                print("{} finished transaction for chunk {}".format(datetime.now(), chunk_count))

    except Error as e:
        print(e)
