from urllib2 import urlopen, Request

import config as sas

import sys, getopt

def help(status=0):
    """Display help message and exit"""
    print 'test.py -f <from_phone_number> -b <message_body>'
    sys.exit(status)
    
def main(argv):
    """Parse input and call SAP SMS endpoint"""
    if not len(argv):
        help(2)
    try:
        opts, args = getopt.getopt(argv,"f:b:",["from=","body="])
    except getopt.GetoptError:
        help(2)
    ## Set Twilio parameters From and Body
    for opt, arg in opts:
        if opt == '-h':
            help()
        elif opt in ("-f", "--from"):
            from_ = arg
        elif opt in ("-b", "--body"):
            body = arg
    ## Send query to SAP SMS endpoint
    print 'Sending message ...'
    urlopen(Request("%s/sms" %(sas.servername), "From=%s&Body=%s" %(from_, body)))
    print '... Message sent'

if __name__ == "__main__":
    main(sys.argv[1:])