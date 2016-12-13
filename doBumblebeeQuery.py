import urllib2
import urllib
import json

APItoken = 'TOKEN'

query = "author:'Kormendy,John' year:2000-2005"
fields= "bibcode, title, author, citation_count"

API_URL = 'http://api.adsabs.harvard.edu/v1'

def get_records(token, query_string, return_fields):
    params = {
        'q':query_string,
        'fl': return_fields,
        'rows': 10000
    }
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

data = get_records(APItoken, query, fields)

for item in data:
    print item
