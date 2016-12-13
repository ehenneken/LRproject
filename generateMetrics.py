import urllib2
import urllib
import sys
import json
import math


APItoken = 'TOKEN'

library_file = 'libraries.txt'

metrics_types = 'basic,citations,indicators'

API_URL = 'http://api.adsabs.harvard.edu/v1'

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
        sys.stderr.write('Cannot find library %s!\n' % libname)
        sys.exit()
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
def get_metrics(token, bibcodes, metrics_types):
    # Define the parameters used by the metrics service
    params = {
        'bibcodes': bibcodes,
        'types': metrics_types.split(',')
    }
    # Set the correct header information
    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain',
        'Authorization': 'Bearer %s' % token
    }
    # Fire off the query
    req = urllib2.Request("%s/metrics" % API_URL, json.dumps(params), headers)
    resp = urllib2.urlopen(req)
    # and retrieve the data to work with
    data = json.load(resp)
    # return the data retrieved
    return data

libraries = open(library_file).read().strip().split('\n')
print "Library | Total citations | Normalized citations | Hirsch | Tori"
for library in libraries:
    bibcodes = get_library(APItoken, library)
    metrics_data = get_metrics(APItoken, bibcodes, metrics_types)
    print "%s | %s | %s | %s | %s" % (library, metrics_data['citation stats']['total number of citations'], 
                                          metrics_data['citation stats']['normalized number of citations'],
                                          metrics_data['indicators']['h'],
                                          metrics_data['indicators']['tori'])
    


