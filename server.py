## SAP - Send A Preview - http://sap.mdg.io
## Listen to previews of any artist over the phone
## (c) 2013 MDG Web - http://mdg.io
## Licence: GPL - see LICENCE.txt
## Author: Alexandre Passant - http://apassant.net

from twilio.rest import TwilioRestClient
from twilio.twiml import Response as TwilioResponse

import uuid

from urllib2 import urlopen
from flask import Flask, request, render_template
from json import dumps, loads

import py7digital

import config as sap
                
class SendAPreview(object):

    def preview_url(url):
        """Get final preview URL (302 redirect) to avoid exposing OAUTHKEY in the TwiML.
        This should be http://previews.7digital.com/clips/0/ID.clip.mp3, but better to get through HTTP in case it changes
        """
        return urlopen("%s&oauth_consumer_key=%s" %(url, sap.sevend_key)).geturl()

    def top_tracks(self, artist):
        """Get artist top-tracks from 7Digital"""
        ## 7D API parameters
        py7digital.COUNTRY = sap.sevend_country
        py7digital.OAUTHKEY = sap.sevend_key        
        ## Get artist + top tracks
        results = py7digital.search_artist(artist)
        if results:
            ## Save top-tracks in a {Digit:value} dict to manage TwiML <Gather> input
            artist = results.get_next_page()[0]
            top_tracks = map(lambda x: {
                'title' : x.get_title(),
                'preview' : self.preview_url(x.get_audio()),
            }, artist.get_top_tracks())
            return {
                'artist' : "%s" %(artist),
                'tracks' : dict([i+1, top_tracks[i]] for i in range(len(top_tracks)))
            }
        else:
            return False
        
    def gather(self, response, json, tid):
        """Generate a <Gather> TwiML"""
        with response.gather(numDigits=1, method="GET", timeout=10, action="/twiml/%s" %(tid)) as gather:
            for i in range(1, len(json['tracks'])+1):
                gather.say("Press %s to play %s." %(i, json['tracks'][str(i)]['title']))
        
    def twiml(self, tid, play=False):
        """Generate a TwiML, either to list tracks, or to play one"""
        ## Get JSON data to generate the TwiML
        data = open("%s/%s.json" %(sap.twiml_path, tid), 'r').read()
        json = loads(data)
        ## Twilio response
        response = TwilioResponse()
        ## If we need to play the track, create a TwiML that just <Play>
        if play:
            ## Correct digit, play + list when it's done
            if int(play) <= len(json['tracks']):
                response.play(json['tracks'][play]['preview'])
                self.gather(response, json, tid)
            ## Else, list tracks again
            else:
                response.say("Sorry! Wrong digit, please try again.")
                self.gather(response, json, tid)
        ## Otherwise, create a TwiML w/ <Gather> to get user input
        else:
            response.say("Hello! Here are a few tracks from %s" %(json['artist']))
            self.gather(response, json, tid)
        ## Render Twilio response
        return str(response)

    def sms(self, phone, artist):
        """Parse SMS and call/message user"""
        ## Setup Twilio API client
        client = TwilioRestClient(sap.twilio_account, sap.twilio_token)
        ## Get artist top tracks
        top_tracks = self.top_tracks(artist)
        ## Got tracks? Save them w/ a unique TwiML ID and call the user
        if top_tracks:
            twiml = uuid.uuid4()
            open("%s/%s.json" %(sap.twiml_path, twiml), 'w').write(dumps(top_tracks))
            url = "%s/twiml/%s" %(sap.servername, twiml)
            client.calls.create(
                to = phone,
                from_ = sap.twilio_from_,
                url = url
            )
        ## Else, send error SMS
        else:
            url = False
            client.sms.messages.create(
                to = phone, 
                from_ = sap.twilio_from_,
                body = "Ooch, we haven't found anything for %s!" %(artist)
            )
        ## Flask response, just in case
        return url

####################################################
## Flask APP
####################################################

app = Flask(__name__)

@app.route("/twiml/<tid>", methods=['GET', 'POST'])
def twiml(tid):
    """Render TwiML (list or play)"""
    assert tid
    play = request.args.get('Digits')
    return SendAPreview().twiml(tid, play)

@app.route("/sms", methods=['POST'])
def sms():
    """Parse SMS from Twilio"""
    phone = request.form.get('From')
    artist = request.form.get('Body')
    assert artist, phone
    return SendAPreview().sms(phone, artist.strip())

@app.route("/")
def index():
    """Index page"""
    return render_template('index.html')
    
if __name__ == "__main__":
    app.run(debug=True)