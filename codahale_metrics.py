#!/usr/bin/env python

#####################################################
##  Parse codahale/yammer/dropwizard JSON metrics  ##
##  put the tuples into a list,                    ##
##  pickle the list and dump it into the graphite  ## 
##  pickle port                                    ##
#####################################################
import pickle
import socket
import struct
import time
import re
import sys
from base64 import b64encode
from optparse import OptionParser
import urllib.request, urllib.error, urllib.parse, http.client 
import json

socket.setdefaulttimeout(30.0)

def processResponse(data,graphiteRoot,pickleport):
    timestamp = time.time()
    output = ([])

    if options.verbose: print(data, file=sys.stderr)
    d = json.loads(data)

    try:
        # Step through JSON objects and sub objects and sub objects.
        for everyone, two in d.items():
            if type(two).__name__=='dict':
                for attr, value in list(two.items()):
                    if type(value).__name__=='dict':
                        try:
                            for left, right in list(value.items()):
                                if not ((type(right).__name__ == "float") or (type(right).__name__ == "int")): continue
                                # strip unicode stuff
                                if '.' in everyone:
                                    blah = str("%s.%s_%s_%s" % ( graphiteRoot, everyone, attr.replace(' ','_'), left.replace(' ','_')))
                                    output.append((blah, (timestamp,right)))
                                else:
                                    blah = str("%s.%s.%s_%s" % ( graphiteRoot, everyone, attr.replace(' ','_'), left.replace(' ','_')))
                                    output.append((blah, (timestamp,right)))

                        # Some 'left' objects at this level are of type unicode.
                        # So, obviously attempting to walk them like they were a dict type
                        # is going to generate some exceptions.
                        # Ignore them and move to the next one.
                        except AttributeError as uh:
                            continue
                    else:
                        #if type(value).__name__=="dict": continue
                        # strip unicode stuff
                        blah = str("%s.%s.%s" % ( graphiteRoot, everyone, attr.replace(' ','_')))
                        output.append((blah,(timestamp,value)))
            else:
                # strip unicode stuff
                blah = str("%s.%s" % ( graphiteRoot, everyone.replace(' ','_')))
                output.append((blah, (timestamp,two)))
    # probably not needed any longer
    except KeyError:
        print("Critical: Key not found: %s" % resource, file=sys.stderr)
        sys.exit(1)

    finally:
        #prepare the package for delivery!!!
        package = pickle.dumps(output, 1)
        size = struct.pack('!L', len(package))
        
        # if verbose is set write the pickle to a file for 
        #     further testing
        if options.verbose:
            fh = open('data.p', 'wb')
            pickle.dump(output, fh)
            fh.close()
        
        s = socket.socket()
        s.connect(('localhost', pickleport))
        s.sendall(size)
        s.sendall(package)
        sys.exit(0)


class HTTPSClientAuthHandler(urllib.request.HTTPSHandler):
    def __init__(self, key, cert):
        urllib.request.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert

    def https_open(self, req):
        return self.do_open(self.getConnection, req)

    def getConnection(self, host, timeout=300):
        return http.client.HTTPSConnection(host, key_file=self.key, cert_file=self.cert)

if __name__ == '__main__':
    
    parser = OptionParser()
    parser.add_option('-H', '--host', dest='host',
        help='Hostname/IP of the web server')
    parser.add_option('-p', '--port', dest='port',
        type='int', default=80,
        help='Port to connect to on the web server')
    parser.add_option('-u', '--url', dest='url',
        help='URL to retrieve data from')
    parser.add_option('-n', '--username', dest='username',
        help='Username for accessing the page')
    parser.add_option('-w', '--password', dest='password',
        help='Password for accessing the page')
    parser.add_option('-s', '--service', dest='service',
        help='Service you want to query')
    parser.add_option('-r', '--resource', dest='resource',
        help='Resource you want to query')
    parser.add_option('-q', '--query', dest='query',
        help='Object to query')
    parser.add_option('-S', '--ssl', dest='usingssl',
        action="store_true",
        help='Enable SSL for HTTP connection')
    parser.add_option('-C', '--client', dest='client',
        help='Client cert to use')
    parser.add_option('-K', '--key', dest='key',
        help='Client key to use')
    parser.add_option('-R', '--graphite-root', dest='graphiteRoot',
        help='Graphite root to store data in')
    parser.add_option('-P', '--pickle-port', dest='pickleport',
        type='int', default=2004,
        help='Pickle port to submit data to')
    parser.add_option('-v', '--verbose', dest='verbose',
        action="store_true",
        help='enable verbose output')
    options, args = parser.parse_args()

    if not options.host:
        print("Critical: You must specify the host.", file=sys.stderr)
        sys.exit(1)
    
    if not options.url:
        print("You must specify a URL.", file=sys.stderr)
        sys.exit(1)
    else:
        url = options.url


    headers = {}
    if options.username and options.password:
        authstring = ':'.join((
            options.username, options.password)).encode('base64')
        headers = {
            "Authorization": "Basic " + authstring.rstrip(),
            }

    # default to use SSL if the port is 443
    if options.usingssl or options.port == '443':
        if not options.key:
            from http.client import HTTPSConnection
            try:
                connection = HTTPSConnection(options.host, options.port)
                connection.request("GET", url, None, headers)
            except:
                print("Unable to make HTTPS connection to https://%s:%s%s" % ( options.host, options.port, url ), file=sys.stderr)
                sys.exit(1)
        else:
            import urllib.request, urllib.error, urllib.parse
            from http.client import HTTPSConnection
            opener = urllib.request.build_opener(HTTPSClientAuthHandler(options.key, options.client))
            connectString = "https://%s:%s%s" % (options.host, options.port, options.url)
            try:
                response = opener.open(connectString)
            except:
                print("Could not connect to %s" % connectString, file=sys.stderr)
                sys.exit(2)
    else:
        from http.client import HTTPConnection
        try:
            connection = HTTPConnection(options.host, options.port)
            connection.request("GET", url, None, headers)
        except Exception as e:
            print("Unable to make HTTP connection to http://%s:%s%s because: %s" % ( options.host, options.port, url, e ), file=sys.stderr)
            sys.exit(1)

    graphiteRoot = "%s.%s" % ( options.graphiteRoot, options.host )

    if options.key:
        returnCode = response.getcode()
    else:
        response = connection.getresponse()
        returnCode = response.status
    if returnCode == 200:
        processResponse(response.read(),graphiteRoot,options.pickleport)            
    elif returnCode == 401:
        print("Invalid username or password.")
        sys.exit(1)
    elif returnCode == 404:
        print("404 not found.")
        sys.exit(1)
    else:
        print("Web service error %: " % returnCode) #, (None if not response.reason else response.reason) )
        sys.exit(1)
