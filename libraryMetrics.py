# import (standard) Python libraries
import urllib2
import urllib
import os
import sys
import json
import re
import ConfigParser
import time
import datetime
import math
# name of the configuration file
config_file = 'config.ini'
# URL of the API
API_URL = 'http://api.adsabs.harvard.edu/v1'
# name of subdirectory for metrics data
metrics_data_dir = "metrics"
# Helper functions
# config_section_map: get a specific section from the configuration file
def config_section_map(section):
    params = {}
    options = Config.options(section)
    for option in options:
        try:
            params[option] = Config.get(section, option)
            if params[option] == -1:
                sys.stderr.write("skip: %s\n" % option)
        except:
            sys.stderr.write("exception on %s!\n" % option)
            params[option] = None
    return params

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

def get_library(token, libid):
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

# Main Engine Room
#
# First retrieve the configuration parameters
Config = ConfigParser.ConfigParser()
Config.read(config_file)
# check if the "metrics" subdirectory exists
if not os.path.exists(metrics_data_dir):
    os.mkdir(metrics_data_dir)
# What types of metrics will be retrieved from metrics endpoint
try:
    mtypes = config_section_map('Metrics')['types']
except:
    mtypes = 'basic'
# Get API token
try:
    token = config_section_map('APIauthentication')['apitoken']
except Exception, e:
    sys.stderr.write('Unable to retrieve API token: %s\n'%str(e))
    sys.exit()
# Get the project prefix (for filtering of library names)
try:
    projectID = config_section_map('ProcessingParameters')['project']
except:
    projectID = 'LIB'
# Retrieve library IDs for all relevant libraries (whose name starts with the projectID)
req = urllib2.Request("%s/biblib/libraries" % API_URL)
# and add the correct header information
req.add_header('Content-type', 'application/json')
req.add_header('Accept', 'text/plain')
req.add_header('Authorization', 'Bearer %s' % token)
# do the actual request
resp = urllib2.urlopen(req)
# and retrieve the name of the existing libraries
data = json.load(resp)['libraries']
# whose names should start with the projectID
libdata = [d for d in data if d['name'].startswith(projectID)]
# now we can start harvesting metrics
for library in libdata:
    libid = library['id']
    # retrieve the bibcodes for this library
    bibcodes = get_library(token, libid)
    # retrieve metrics for these bibcodes
    metrics_data = get_metrics(token, bibcodes, mtypes)
    # name of output file is based on the name of the library
    ofile = "%s/%s.json" % (metrics_data_dir, library['name'])
    # write the relevant data to file
    with open(ofile, 'w') as outfile:
        json.dump(metrics_data, outfile)
