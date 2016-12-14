import urllib2
import urllib
import sys
import json
import math
import itertools
import operator
from collections import defaultdict


APItoken = 'TOKEN'

frequency = 100

library_file = 'libraries.txt'

metrics_types = 'basic,citations,indicators'

API_URL = 'http://api.adsabs.harvard.edu/v1'

class NoSuchLibrary(Exception):
    pass

def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

def get_library(token, libname):
    req = urllib2.Request("%s/biblib/libraries" % API_URL)
    req.add_header('Content-type', 'application/json')
    req.add_header('Accept', 'text/plain')
    req.add_header('Authorization', 'Bearer %s' % token)
    # do the actual request
    resp = urllib2.urlopen(req)
    data = json.load(resp)['libraries']
    try:
        libdata = [d for d in data if d['name'] == libname][0]
    except:
        raise NoSuchLibrary 
    libid = libdata['id']
    # Retrieve the contents of the library specified
    # rows: the number of records to retrieve per call
    rows = 25
    start = 0
    req = urllib2.Request("%s/biblib/libraries/%s?start=%s&rows=25&fl=bibcode" % (API_URL, libid, start))
    # and add the correct header information
    req.add_header('Content-type', 'application/json')
    req.add_header('Accept', 'text/plain')
    req.add_header('Authorization', 'Bearer %s' % token)
    # do the actual request
    resp = urllib2.urlopen(req)
    data = json.load(resp)
    num_documents = data['metadata']['num_documents']
    documents = data['documents']
    num_paginates = int(math.ceil((num_documents) / (1.0*rows)))
    # Update the start position with the number of records we have retrieved so far
    start += rows
    # Start retrieving the remainder of the contents
    for i in range(num_paginates):
        req = urllib2.Request("%s/biblib/libraries/%s?start=%s&rows=25&fl=bibcode" % (API_URL, libid, start))
        # and add the correct header information
        req.add_header('Content-type', 'application/json')
        req.add_header('Accept', 'text/plain')
        req.add_header('Authorization', 'Bearer %s' % token)
        # do the actual request
        resp = urllib2.urlopen(req)
        data = json.load(resp)
        # Add the bibcodes from this batch to the collection
        documents.extend(data['documents'])
        # Update the start position for the next batch
        start += rows

    return documents

# get_records: query the API and retrieve records
def get_keyword_rank(token, bibcodes, frequency):
    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain',
        'Authorization': 'Bearer %s' % token
    }
    keywords = []
    biblists = list(chunks(bibcodes, 50))
    for biblist in biblists:
        params = {
            'q': 'citations(bibcode:(%s))' % " OR ".join(biblist),
            'fl': 'keyword_facet',
            'rows': 10000
        }
        # Fire off the query
        qparams = urllib.urlencode(params)
        req = urllib2.Request("%s/search/query?%s" % (API_URL, qparams))
        req.add_header('Content-type', 'application/json')
        req.add_header('Accept', 'text/plain')
        req.add_header('Authorization', 'Bearer %s' % token)
        resp = urllib2.urlopen(req)
        # and retrieve the data to work with
        data = json.load(resp)['response']['docs']
        keywords += list(itertools.chain(*[d['keyword_facet'] for d in data if d.has_key('keyword_facet')]))
    d = defaultdict(int)
    for k in keywords:
        d[k] += 1
    sorted_d = sorted(d.items(), key=operator.itemgetter(1), reverse=True)
    first = [e for e in sorted_d if e[1] <= 100][0]
    index = sorted_d.index(first)
        # return the data retrieved
    return (first[0],index)

libraries = open(library_file).read().strip().split('\n')
print "Library | Rank (freq = %s)| Keyword" % frequency
for library in libraries:
    try:
        bibcodes = get_library(APItoken, library)
        keyword, rank = get_keyword_rank(APItoken, bibcodes, frequency)
        print "%s | %s | %s" % (library, rank, keyword) 
    except NoSuchLibrary:
        print "%s | %s | %s" % (library, 9999, 9999)


