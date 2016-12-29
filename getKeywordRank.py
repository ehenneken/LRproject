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
    status = resp.getcode()
    if status != 200:
        sys.stderr.write('')
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

def get_citations(token, bibcodes):
    citations = []
    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain',
        'Authorization': 'Bearer %s' % token
    }
    keywords = []
    biblists = list(chunks(bibcodes, 50))
    for biblist in biblists:
        params = {
            'q': 'bibcode:(%s)' % " OR ".join(biblist),
            'fl': 'citation',
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
        citations += list(itertools.chain(*[d['citation'] for d in data if d.has_key('citation')]))
    return citations
# get_records: query the API and retrieve records
def get_keyword_rank(token, cits, frequency):
    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain',
        'Authorization': 'Bearer %s' % token
    }
    bibcodes = cits.keys()
    keywords = []
    all_keywords = []
    biblists = list(chunks(bibcodes, 50))
    for biblist in biblists:
        params = {
            'q': 'bibcode:(%s)' % " OR ".join(biblist),
            'fl': 'bibcode,keyword_facet',
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
        keywords += list(itertools.chain(*[list(set(d['keyword_facet'])) for d in data if d.has_key('keyword_facet')]))
        all_keywords += list(itertools.chain(*[list(set(d['keyword_facet']))*cits[d['bibcode']] for d in data if d.has_key('keyword_facet')]))
    d = defaultdict(int)
    for k in keywords:
        d[k] += 1
    dd= defaultdict(int)
    for k in all_keywords:
        dd[k] += 1
    sorted_d = sorted(d.items(), key=operator.itemgetter(1), reverse=True)
    sorted_dd= sorted(dd.items(), key=operator.itemgetter(1), reverse=True)
    first = [e for e in sorted_d if e[1] <= frequency][0]
    first_all = [e for e in sorted_dd if e[1] <= frequency][0]
    index = sorted_d.index(first)
    index_all = sorted_dd.index(first_all)
        # return the data retrieved
    return (first[0],index,first_all[0],index_all)

libraries = open(library_file).read().strip().split('\n')
print "Library | Rank (freq = %s)| Keyword" % frequency
for library in libraries:
    citfreq = defaultdict(int)
    try:
        bibcodes = get_library(APItoken, library)
    except NoSuchLibrary:
        print "%s | %s | %s | %s | %s" % (library, 9999, 9999, 9999, 9999)
        continue
    except urllib2.HTTPError, e:
        sys.stderr.write('Error retrieving bibcodes from ADS library "%s": %s\n' % (library, str(e)))
        continue
    try:
        citations = get_citations(APItoken, bibcodes)
        for c in citations:
            citfreq[c] += 1
        keyword, rank, kw_all, rank_all = get_keyword_rank(APItoken, citfreq, frequency)
        print "%s | %s | %s | %s | %s" % (library, rank, keyword, rank_all, kw_all) 
    except urllib2.HTTPError, e:
        sys.stderr.write('Error retrieving citations for ADS library "%s": %s\n' % (library, str(e)))
        


