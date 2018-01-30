#!/usr/bin/python
# encoding: utf-8

import sys
from HTMLParser import HTMLParser
from workflow import Workflow3, web
from workflow.notify import notify

class Result:
  def __init__(self, band, url, genre = None, country = None):
    self.band = band
    self.url = url
    self.genre = genre
    self.country = country

  def title(self):
    subtexts = []
    if self.genre:
      subtexts.append(self.genre)
    if self.country:
      subtexts.append(self.country)
    subtext = u' ({})'.format(", ".join(subtexts)) if len(subtexts) > 0 else ""
    return u'{}{}'.format(self.band, subtext)

class LinkParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.text = None
    self.url = None

  def handle_starttag(self, tag, attrs):
    for attr in attrs:
      if attr[0] == u'href':
        self.url = attr[1]

  def handle_data(self, data):
    if not self.text:
      self.text = data

# Parses "<a href=URL>TEXT</a>" into (TEXT, URL).
def parse_link(link):
  parser = LinkParser()
  parser.feed(link)
  return (parser.text, parser.url)

def search_metal_archives(text):
  results = []
  data = web.get('https://www.metal-archives.com/search/ajax-band-search/?field=name&query={}'
                 .format(text)).json()
  if 'error' in data:
    error = data['error']
    if len(error) > 0:
      notify(u'Band search error!', error)
      return results

  if not 'aaData' in data:
    return results

  # Each result is on the following form:
  # ["<a href=\"https://www.metal-archives.com/bands/BAND/NUMBER\">BAND</a>  <!-- LOAD TIME -->" ,
  #  "GENRE",
  #  "COUNTRY"]
  for res in data['aaData']:
    if len(res) < 3:
      continue

    (link, genre, country) = res
    (band, url) = parse_link(link)
    if not band or not url:
      continue

    results.append(Result(band, url, genre, country))

  return results

# Search for text and return instances of Result.
def search(text):
  # TODO: Search other sites later..
  return search_metal_archives(text)

def main(wf):
  args = wf.args

  results = search(args[0])
  if len(results) == 0:
    wf.add_item(title = u'No results found.. Try with another query.')
  else:
    for result in results:
      wf.add_item(title = result.title(), subtitle = result.url, arg = result.url, valid = True)

  wf.send_feedback()

if __name__ == '__main__':
  wf = Workflow3()
  sys.exit(wf.run(main))
