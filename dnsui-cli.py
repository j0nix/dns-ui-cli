#!/usr/bin/env python
import cmd
import re
import sys
import requests
import json
import getpass
import yaml
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class dnsuiAPI():


    # New strategy. Add actions to a list, use command commit that takes an comment as input. We then can track changes related to tickets.

    url = 'https://localhost'
    api = '/api/v2/zones/'
    baseurl = ""

    #add_tmpl = str('{ "actions": [ { "action": "%s","name": "%s","type": "A","ttl": "1H","comment": "","records": [{"content": "%s","enabled": true}]}],"comment": "%s@dns-ui-cli"}')
    #del_tmpl = str('')

    add_tmpl=str('{ "action": "%s","name": "%s", "type": "A","ttl": "1H","comment": "%s","records": [ { "content": "%s", "enabled": true }]}')
    delete_tmpl = str('{"action": "delete","name": "%s","type": "A"}')
    actions_tmpl = str('{ "actions": [%s],"comment": "%s"}')

    validName = re.compile("^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]+[a-zA-Z0-9]))+$")
    validIpV4 = re.compile("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")

    zones = []
    commits = []
    usr = ''
    pwd = ''

    SSL_VERIFY = False

    def __init__(self,usr,pwd):
    
        try:
            with open(".dns-ui-cli.yml", 'r') as ymlfile:
                cfg = yaml.load(ymlfile)
        except:
            pass

        if cfg:

            try:
                if cfg['dns-ui']['url']:
                    self.url = cfg['dns-ui']['url']
            except:
                pass

            try:
                if cfg['dns-ui']['api']:
                    self.api = cfg['dns-ui']['api']
            except:
                pass
        
        # Set baseurl
        self.baseurl = "{}{}".format(self.url,self.api)
       
        try:
            r = requests.get(self.baseurl, auth=(usr, pwd), verify=self.SSL_VERIFY)
            self.usr = usr
            self.pwd = pwd
            zones = r.json()
            for zone in zones:
                self.zones.append(zone['name'])

        except requests.exceptions.ConnectionError:
            print "CONNECTION ERROR: Failed to connect to '{}'".format(self.baseurl)

        except:

            if r:
                if r.status_code == 401:
                    print "UNAUTHORIZED ACCESS to {}".format(self.baseurl)
                else:
                    print "Failed to get data from %s [%s, %s] " % (self.baseurl, r.status_code,r.request.headers)

            else:
                print "ERROR:".format(sys.exc_info())


    def get_template(self):
        return self.template

    def batch_records(self,filename):
        # read from file to batch add records
        pass

    def commit(self,zone,comment):

	data = self.actions_tmpl % (",".join(self.commits),comment)

	data = json.loads(data)

        if not zone.endswith('.'):
		zone = "{}.".format(zone)

	# start a session
	sess = requests.Session()
        sess.auth = (self.usr,self.pwd)

	# Add that record
	patch = sess.patch(url=self.baseurl+zone, data=json.dumps(data),verify=False)

	# Success ?
	if patch.status_code == 200:
	    return "SUCCESS adding to {}".format(zone)
	else:
            return "FAIL adding to {} => [data]: {} [http-code]: {} [http-headers]: {}".format(zone,json.dumps(data),patch.status_code,patch.request.headers)

    def add_record(self,name,ipaddr):

	valid = self.validName.match(name);

        if not valid:
	    return "Not a valid hostname '%s'" % name

        valid = self.validIpV4.match(ipaddr);

        if not valid:
            return "Not a valid ipaddress '%s'" % ipaddr

	action = self.add_tmpl % ("add",name,self.usr,ipaddr)

        self.commits.append(action)

        return "{} {} added".format(name,ipaddr)


class dnsuiCMD(cmd.Cmd):

    zone = "?"
    intro = "::Simple dnsui-cli by j0nix::"
    prompt = '[ZONE {}]: '.format(zone)

    dnsui = None

    def preloop(self):

        try:
            with open(".dns-ui-cli.yml", 'r') as ymlfile:
                cfg = yaml.load(ymlfile)
            
            if cfg['autologin']:
                usr = cfg['autologin']
                print "Autologin set in conf file, login as user {}".format(usr)

            # TODO: Add ask for pwd input and store crypted password in a file called
            # something like .dns-ui-cli.<usr>.pwd, then we can automagic login
            # ..for now, ask for password

        except:
            usr = raw_input("Username: ")

        pwd = getpass.getpass('Password: ')

        self.dnsui = dnsuiAPI(usr,pwd)

        if self.dnsui == None:
            print "Failed initiate communication with dns-ui, bailing out!"
            exit(1)
        
        if len(self.dnsui.zones) == 0:
            print "Found 0 zones !?, bailing out!"
            exit(1)

    def emptyline(self):
        pass


    def do_add(self, record):

        if self.zone in self.dnsui.zones:
            temp = record.split()
            print self.dnsui.add_record(temp[0],temp[1])
        else:
            print 'Missing zone, you MUST set zone'
            self.help_zone()

    def do_commit(self,comment):
        
        if self.zone in self.dnsui.zones:
            if len(self.dnsui.commits) > 0:
                print self.dnsui.commit(self.zone,comment)
            else:
                print "nothing to commit?"
        else:
            print 'Missing zone, you MUST set zone'
            self.help_zone()

    def do_zone(self, zone):

        if zone:
            self.zone = zone
            self.prompt = "[ZONE {}]: ".format(self.zone)
            print "using zone", self.zone
        else:
            self.help_zone()


    def complete_zone(self, text, line, begidx, endidx):

        if not text:
            completions = self.dnsui.zones[:]
        else:
            completions = [ f for f in self.dnsui.zones if f.startswith(text)]

        return completions

    def help_zone(self):

        print "\nSYNTAX: zone [zone]"
        print "\nZones:"
        for zone in self.dnsui.zones:
            print "\t{}".format(zone)
        print "\n Ex.\n\tzone int.comhem.com\n"

    def do_exit(self, line):
        return True

    def help_exit(self):
        print "exit"

    def do_EOF(self, line):
        return True
    
    def help_EOF(self):
        print "ctrl+d to exit"

if __name__ == '__main__':
    dnsuiCMD().cmdloop()
