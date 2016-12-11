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
# name of the configuration file
config_file = 'config.ini'
# URL of the API
API_URL = 'http://api.adsabs.harvard.edu/v1'
# maximum number of records for one records submission to a library
max_recs = 500
# Helper functions
# chunks: functions to split a list up into a list of (smaller) lists
def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

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
def get_records(config, author_data, orcid):
    # Establish the data required to do the query
    # Query parameters:
    try:
        params = config_section_map('QueryParameters')
    except Exception, e:
        sys.stderr.write('Unable to retrieve query parameters: %s\n'%str(e))
        sys.exit()
    if orcid and author_data['orcid'] != 'NA':
        aq = ' orcid:%s' % author_data['orcid']
    else:
        aq = ' author:"%s"' % author_data['name']
    # Augment or set the query
    if params.has_key('q'):
        params['q'] += aq
    else:
        params['q'] = aq.strip()
    # If a start year was specified, add this to the query string
    if author_data['startyear'].isdigit():
        now = datetime.datetime.now()
        params['q'] += ' year:%s-%s'% (author_data['startyear'].strip(), str(now.year + 1))
    # The API token:
    try:
        token = config_section_map('APIauthentication')['apitoken']
    except Exception, e:
        sys.stderr.write('Unable to retrieve API token: %s\n'%str(e))
        sys.exit()
    # URL-encode the parameters
    qparams = urllib.urlencode(params)
    # set up the request
    req = urllib2.Request("%s/search/query?%s" % (API_URL, qparams))
    # and add the correct header information
    req.add_header('Content-type', 'application/json')
    req.add_header('Accept', 'text/plain')
    req.add_header('Authorization', 'Bearer %s' % token)
    # do the actual request
    resp = urllib2.urlopen(req)
    # and retrieve the data to work with
    data = json.load(resp)['response']['docs']
    
    return data

# add_to_libary: add records to the specified library (will be created if it doesn't exist)
def add_to_library(token, author_data, records, libid=None):
    # Select the correct endpoint based on whether library exists
    if not libid:
        libURL = "%s/biblib/libraries" % API_URL
    else:
        libURL = "%s/biblib/documents/%s" % (API_URL, libid)
    # 
    bibcodes = [d['bibcode'] for d in records]
    # Split the list up in a list of lists of maximally "max_recs" records
    biblists = list(chunks(bibcodes, max_recs))
    # Create the library with the first list of bibcodes (may be the only)
    first_batch = biblists.pop(0)
    params = {
        'name': author_data['library'],
        'description': 'Publications for %s' % author_data['name'],
        'public': False,
        'action': 'add',
        'bibcode': first_batch
    }
    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain',
        'Authorization': 'Bearer %s' % token
    }
    req = urllib2.Request(libURL, json.dumps(params), headers)
    resp = urllib2.urlopen(req)
    # If there are any lists of bibcodes left, add these to the library as well
    if len(biblists) > 0:
        for biblist in biblists:
            params = {
                'name': author_data['library'],
                'description': 'Publications for %s' % author_data['name'],
                'public': False,
                'action': 'add',
                'bibcode': biblist
            }
            req = urllib2.Request(libURL, json.dumps(params), headers)
            resp = urllib2.urlopen(req)
    
# update_library: if no ADS library exists, it will be created and populated with the records retrieved.
#                     if the ADS library exists, it will be updated or recreated (see configuration parameter)
def update_library(config, author_data, records):
    # The API token:
    try:
        token = config_section_map('APIauthentication')['apitoken']
    except Exception, e:
        sys.stderr.write('Unable to retrieve API token: %s\n'%str(e))
        sys.exit()
    # Do we update existing libraries
    try:
        update = Config.getboolean("ADSLibrarySettings", "update")
    except:
        update = False
    # First check if the library exists
    req = urllib2.Request("%s/biblib/libraries" % API_URL)
    # and add the correct header information
    req.add_header('Content-type', 'application/json')
    req.add_header('Accept', 'text/plain')
    req.add_header('Authorization', 'Bearer %s' % token)
    # do the actual request
    resp = urllib2.urlopen(req)
    # and retrieve the name of the existing libraries
    data = json.load(resp)['libraries']
    try:
        library_exists = True
        libdata = [d for d in data if d['name'] == author_data['library']][0]
    except:
        library_exists = False
    if not library_exists:
        sys.stderr.write('Creating new ADS library %s...\n'%author_data['library'])
        res = add_to_library(token, author_data, records)
    elif not update:
        sys.stderr.write('Recreating ADS library %s...\n'%author_data['library'])
        sys.stderr.write('Deleting existing version...\n')
        req = urllib2.Request("%s/biblib/documents/%s" % (API_URL, libdata['id']))
        req.get_method = lambda: 'DELETE'
        req.add_header('Content-type', 'application/json')
        req.add_header('Accept', 'text/plain')
        req.add_header('Authorization', 'Bearer %s' % token)
        resp = urllib2.urlopen(req)
        sys.stderr.write('Creating new version...\n')
        res = add_to_library(token, author_data, records)
    else:
        sys.stderr.write('Updating ADS library %s...\n'%author_data['library'])
        res = add_to_library(token, author_data, records, libid=libdata['id'])
        
    
# Main Engine Room
#
# First retrieve the configuration parameters
Config = ConfigParser.ConfigParser()
Config.read(config_file)
# Get project prefix ID to add to library names for easy retrieval
# later to calculate metrics
try:
    projectID = config_section_map('ProcessingParameters')['project']
except:
    projectID = 'LIB'
# Now we should have all necessary information to start working
# Retrieve all input author data
author_file = config_section_map('InputFileLocations')['authors']
author_data = []
library_names = []
if os.path.exists(author_file):
    with open(author_file) as fh:
        for entry in fh:
            if entry.startswith('#'):
                continue
            author = prefix = syear = orcid = 'NA'
            try:
                adata = entry.strip().split(';')
            except ValueError:
                continue
            if len(adata) < 2:
                continue
            # these entries are always defined
            author = adata[0]
            prefix = adata[1]
            # get start year if given
            try:
                syear = adata[2]
            except:
                pass
            # get ORCID if giveh
            try:
                orcid = adata[3]
            except:
                pass
            # Construct the name for the ADS Library for this author
            libname = "%s_%s_%s" % (projectID, prefix, ''.join(e for e in author if e.isalnum()))
            # Check if we already have a library with this name, in oder to avoid name collision
            if libname in library_names:
                datestring = str(int(time.time()))
                libname = "%s_%s" % (libname, datestring)
            library_names.append(libname)
            # Add a new entry to the listb with input author data
            author_data.append({'name': author, 'library': libname, 'orcid': orcid, 'startyear': syear})
# Do we use ORCiD if present
try:
    use_orcid = Config.getboolean("ProcessingParameters", "orcid")
except:
    use_orcid = False

# Now we can start processing the authors
for entry in author_data:
    # Retrieve records for this author
    records = get_records(Config, entry, use_orcid)
    # Now we are ready to either update and existing library or (re)create a library
    res = update_library(Config, entry, records)
