# -*- coding: utf-8 -*-

import re

from pycurl import FOLLOWLOCATION

from module.plugins.internal.SimpleHoster import SimpleHoster, create_getInfo


class QuickshareCz(SimpleHoster):
    __name__    = "QuickshareCz"
    __type__    = "hoster"
    __version__ = "0.56"

    __pattern__ = r'http://(?:[^/]*\.)?quickshare\.cz/stahnout-soubor/.+'
    __config__  = [("use_premium", "bool", "Use premium account if available", True)]

    __description__ = """Quickshare.cz hoster plugin"""
    __license__     = "GPLv3"
    __authors__     = [("zoidberg", "zoidberg@mujmail.cz")]


    NAME_PATTERN = r'<th width="145px">Název:</th>\s*<td style="word-wrap:break-word;">(?P<N>[^<]+)</td>'
    SIZE_PATTERN = r'<th>Velikost:</th>\s*<td>(?P<S>[\d.,]+) (?P<U>[\w^_]+)</td>'
    OFFLINE_PATTERN = r'<script type="text/javascript">location\.href=\'/chyba\';</script>'


    def process(self, pyfile):
        self.html = self.load(pyfile.url, decode=True)
        self.getFileInfo()

        # parse js variables
        self.jsvars = dict((x, y.strip("'")) for x, y in re.findall(r"var (\w+) = ([\d.]+|'.+?')", self.html))
        self.logDebug(self.jsvars)
        pyfile.name = self.jsvars['ID3']

        # determine download type - free or premium
        if self.premium:
            if 'UU_prihlasen' in self.jsvars:
                if self.jsvars['UU_prihlasen'] == '0':
                    self.logWarning(_("User not logged in"))
                    self.relogin(self.user)
                    self.retry()
                elif float(self.jsvars['UU_kredit']) < float(self.jsvars['kredit_odecet']):
                    self.logWarning(_("Not enough credit left"))
                    self.premium = False

        if self.premium:
            self.handlePremium(pyfile)
        else:
            self.handleFree(pyfile)

        if self.checkDownload({"error": re.compile(r"\AChyba!")}, max_size=100):
            self.fail(_("File not m or plugin defect"))


    def handleFree(self, pyfile):
        # get download url
        download_url = '%s/download.php' % self.jsvars['server']
        data = dict((x, self.jsvars[x]) for x in self.jsvars if x in ("ID1", "ID2", "ID3", "ID4"))
        self.logDebug("FREE URL1:" + download_url, data)

        self.req.http.c.setopt(FOLLOWLOCATION, 0)
        self.load(download_url, post=data)
        self.header = self.req.http.header
        self.req.http.c.setopt(FOLLOWLOCATION, 1)

        m = re.search(r'Location\s*:\s*(.+)', self.header, re.I)
        if m is None:
            self.fail(_("File not found"))

        self.link = m.group(1).rstrip()  #@TODO: Remove .rstrip() in 0.4.10
        self.logDebug("FREE URL2:" + self.link)

        # check errors
        m = re.search(r'/chyba/(\d+)', self.link)
        if m:
            if m.group(1) == '1':
                self.retry(60, 2 * 60, "This IP is already downloading")
            elif m.group(1) == '2':
                self.retry(60, 60, "No free slots available")
            else:
                self.fail(_("Error %d") % m.group(1))


    def handlePremium(self, pyfile):
        download_url = '%s/download_premium.php' % self.jsvars['server']
        data = dict((x, self.jsvars[x]) for x in self.jsvars if x in ("ID1", "ID2", "ID4", "ID5"))
        self.download(download_url, get=data)


getInfo = create_getInfo(QuickshareCz)
