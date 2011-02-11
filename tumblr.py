#!/usr/bin/env python
import feedparser
from haikufinder import LineSyllablizer, Nope, TooShort, first_word_comma, HaikuFinder
import itertools
import math
import os
import re
import simplejson
import subprocess
import sys
import time
from urllib import urlencode
import urllib2
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

config = simplejson.load(open('config.json'))
data_file = 'tumblr-data.json'

class SubtitleHaikuFinder(HaikuFinder):
    def __init__(self, lines, unknown_word_handler=None):
        self.lines = lines
        self.unknown_word_handler = unknown_word_handler
    
    def find_haikus(self):
        haikus = []
        count = len(self.lines)
        for i in xrange(count):
            offset = 0
            line = ""
            while i + offset < count:
                new_line = self.get_element_text(self.lines[i + offset])
                if not new_line:
                    break
                # Remove #s from start and end of lyrics
                new_line = re.sub(r'(^#\s*)|(\s+#$)', '', new_line)
                # Only start of sentences
                if offset == 0 and (new_line[0].upper() != new_line[0]
                                    or re.match(r'[^A-Za-z]', new_line[0])):
                    break
                # Ignore sounds
                if new_line == new_line.upper():
                    break
                line = "%s %s" % (line, new_line)
                line = line.strip()
                # Ensure we have complete sentences
                if line[-1] not in ('.', '!', '?'):
                    offset += 1
                    continue
                try:
                    haikus.append({
                        'haiku': LineSyllablizer(line).find_haiku(),
                        'subtitle': self.lines[i],
                    })
                    break
                except (Nope, TooShort):
                    break
        return haikus
    
    def get_element_text(self, e):
        s = []
        if e.text:
            s.append(e.text.strip())
        for child in e:
            s.append(self.get_element_text(child))
        if e.tail:
            s.append(e.tail.strip())
        return ' '.join(s)


class SubtitleHaikuCrawler(object):
    all_channels = [
        'bbc_one',
        'bbc_two',
        'bbc_three',
        'bbc_four',
        'cbbc',
        'cbeebies',
        'bbc_news24',
        'bbc_parliament',
    ]

    def __init__(self, crawled_pids, channels=None):
        self.crawled_pids = crawled_pids
        self.channels = channels or self.all_channels
    
    def find_haikus(self):
        haikus = []
        for channel in self.channels:
            print 'Getting feed for %s...' % channel
            d = feedparser.parse('http://feeds.bbc.co.uk/iplayer/%s/list' 
                                 % channel)
            for entry in d.entries:
                pid = entry.id.split(':')[-1]
                if pid in self.crawled_pids:
                    continue
                etree = self.download_subtitles(pid)
                if etree is None:
                    self.crawled_pids.append(pid)
                    continue
                entry_haikus = SubtitleHaikuFinder(etree[1][0]).find_haikus()
                for d in entry_haikus:
                    d['pid'] = pid
                    d['entry'] = entry
                haikus.extend(entry_haikus)
                time.sleep(1)
        return haikus

    def download_subtitles(self, pid):
        """
        Returns an etree of the subtitles for a given pid.
        """
        print 'Downloading subtitles for %s...' % pid
        process = subprocess.Popen(
            ['ruby', 'download_subtitles.rb', pid],
            stdout=subprocess.PIPE
        )
        xml = process.communicate()[0]
        # Skip if there are no subtitles
        if process.wait() != 0:
            return None
        try:
            return ElementTree.fromstring(xml)
        except ExpatError:
            return None


class TumblrHaikuPoster(object):
    def __init__(self, crawled_pids=None):
        self.crawled_pids = crawled_pids or []

    def run(self):
        crawler = SubtitleHaikuCrawler(self.crawled_pids)
        for haiku in crawler.find_haikus():
            print 'Posting haiku from %s...' % haiku['pid']
            begin = self.timecode_to_seconds(haiku['subtitle'].get('begin'))
            req = urllib2.Request('http://www.tumblr.com/api/write', urlencode({
                'email': config['email'],
                'password': config['password'],
                'type': 'quote',
                'quote': '\n'.join(haiku['haiku']).encode('utf-8'),
                'source': '<a href="%s?t=%sm%ss">%s</a>' % (
                    haiku['entry'].link,
                    int(math.floor(begin / 60)),
                    int(begin % 60),
                    haiku['entry'].title.split(':')[0].encode('utf-8')
                ),
                'state': 'draft',
            }))
            try:
                urllib2.urlopen(req)
            except urllib2.HTTPError, e:
                if e.code != 201:
                    print >>sys.stderr, e.fp.read()
                    raise
            if haiku['pid'] not in self.crawled_pids:
                self.crawled_pids.append(haiku['pid'])

    def timecode_to_seconds(self, tc):
        bits = [float(b) for b in tc.split(':')]
        return bits[0] * 60 * 60 + bits[1] * 60 + bits[2]


def main():
    if os.path.exists(data_file):
        data = simplejson.load(open(data_file))
    else:
        data = {}
    poster = TumblrHaikuPoster(data.get('crawled_pids'))
    try:
        poster.run()
    except:
        raise
    finally:
        data['crawled_pids'] = poster.crawled_pids
        simplejson.dump(data, open(data_file, 'w'))

if __name__ == '__main__':
    main()


