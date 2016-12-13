import urllib2
import urllib
import json

APItoken = '8VMzVkQIfXMbGT7WjzLQIkovB1CVw0LRGjp3H61L'

query = "citations(author:'Kormendy,John') year:2010-2015"
fields= "bibcode,aff,citation_num"

API_URL = 'http://api.adsabs.harvard.edu/v1'

def get_records(token, query_string, return_fields):
    params = {
        'q':query_string,
        'fl': return_fields
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
print data
