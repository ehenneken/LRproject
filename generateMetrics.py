import urllib2
import urllib
import sys
import json
import math


APItoken = 'TOKEN'

library_file = 'libraries.txt'

metrics_types = 'basic,citations,indicators'

API_URL = 'http://api.adsabs.harvard.edu/v1'

class NoSuchLibrary(Exception):
    pass

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
print "Library | Number of papers | Normalized paper count | Total number of reads | Reads current year | Total number of downloads | Downloads current year | Total citations | Normalized citations | Refereed citations | Median citations | Average citations | Hirsch | Tori | i10 | i100 | READ10 | m | g"
for library in libraries:
    try:
        bibcodes = get_library(APItoken, library)
        metrics_data = get_metrics(APItoken, bibcodes, metrics_types)
        print "%s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s" % (library, 
                                          metrics_data['basic stats']['number of papers'], 
                                          metrics_data['basic stats']['normalized paper count'], 
                                          metrics_data['basic stats']['total number of reads'], 
                                          metrics_data['basic stats']['recent number of reads'], 
                                          metrics_data['basic stats']['total number of downloads'],
                                          metrics_data['basic stats']['recent number of downloads'],
                                          metrics_data['citation stats']['total number of citations'], 
                                          metrics_data['citation stats']['normalized number of citations'],
                                          metrics_data['citation stats']['total number of refereed citations'],
                                          metrics_data['citation stats']['median number of citations'],
                                          metrics_data['citation stats']['average number of citations'],
                                          metrics_data['indicators']['h'],
                                          metrics_data['indicators']['tori'],
                                          metrics_data['indicators']['i10'],
                                          metrics_data['indicators']['i100'],
                                          metrics_data['indicators']['read10'],
                                          metrics_data['indicators']['m'],
                                          metrics_data['indicators']['g'])
    except NoSuchLibrary:
        print "%s | %s | %s | %s | %s" % (library, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999, 9999)


