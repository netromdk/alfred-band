#!/usr/bin/python
# encoding: utf-8

from __future__ import unicode_literals

import os
import sys

from multiprocessing import Process, Queue
from HTMLParser import HTMLParser
from workflow import Workflow3, web, ICON_INFO, ICON_WEB, ICON_NOTE, ICON_SYNC
from workflow.notify import notify

class Result:
  def __init__(self, band, url = None, genre = None, country = None, icon = None, icon_type = None):
    self.band = band
    self.url = url
    self.genre = genre
    self.country = country
    self.icon = icon
    self.icon_type = icon_type

  def title(self):
    subtexts = []
    if self.genre:
      subtexts.append(self.genre)
    if self.country:
      subtexts.append(self.country)
    subtext = ' ({})'.format(", ".join(subtexts)) if len(subtexts) > 0 else ""
    return '{}{}'.format(self.band, subtext)

  def add_to_workflow(self, wf):
    url = '' if self.url is None else self.url
    wf.add_item(title = self.title(), subtitle = url, arg = self.url,
                valid = not self.url is None, icon = self.icon, icontype = self.icon_type)

  def __eq__(self, other):
    return (self.band == other.band) and \
      (self.url == other.url) and \
      (self.genre == other.genre) and \
      (self.country == other.country) and \
      (self.icon == other.icon) and \
      (self.icon_type == other.icon_type)

  def __hash__(self):
    return hash((self.band, self.url, self.genre, self.country, self.icon, self.icon_type))

class LinkParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self.text = None
    self.url = None

  def handle_starttag(self, tag, attrs):
    for attr in attrs:
      if attr[0] == 'href':
        self.url = attr[1]

  def handle_data(self, data):
    if not self.text:
      self.text = data

# Parses "<a href=URL>TEXT</a>" into (TEXT, URL).
def parse_link(link):
  parser = LinkParser()
  parser.feed(link)
  return (parser.text, parser.url)

def search_metal_archives(queue, text, field = 'name'):
  results = []

  r = web.get('https://www.metal-archives.com/search/ajax-band-search/',
              {'field': field, 'query': text})
  r.raise_for_status()
  data = r.json()

  if 'error' in data:
    error = data['error']
    if len(error) > 0:
      notify('Band search error!', error)
      return

  if not 'aaData' in data:
    return

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

  queue.put(results)

def levdist(a, b):
  if not a and b:
    return len(b)
  if not b and a:
    return len(a)
  if not a and not b:
    raise Exception("You have to supply two non-empty strings!")

  a = " "+a;
  m = len(a)
  b = " "+b;
  n = len(b)

  # matrix with m+1 rows and n+1 columns
  d = {}
  for i in range(m): d[i, 0] = i
  for j in range(n): d[0, j] = j

  for j in range(1, n):
    for i in range(1, m):
      if a[i] == b[j]:
        d[i, j] = d[i-1, j-1]
      else:
        d[i, j] = min(d[i-1,   j] + 1,
                      d[  i, j-1] + 1,
                      d[i-1, j-1] + 1)

  return d[m-1, n-1]

# Sort results so that the ones with the least edit distance to the input text are first! It also
# checks if input text is contained in only one of them.
def sort_results(results, text):
  text = text.strip().lower()
  def lt(x, y):
    x = x.band.strip().lower()
    y = y.band.strip().lower()
    if text in x and not text in y:
      return -1
    if not text in x and text in y:
      return 1
    return levdist(x, text) < levdist(y, text)
  return sorted(results, cmp = lt)

def workflow_file_path(local_path):
  return os.path.join(os.path.dirname(os.path.abspath(__file__)), local_path)

def make_allmusic_query_result(text):
  return Result('Search AllMusic for "{}"'.format(text),
                'https://www.allmusic.com/search/all/{}'.format(text), icon = ICON_WEB)

def make_wikipedia_query_result(text):
  return Result('Search Wikipedia for "{}"'.format(text),
                'https://en.wikipedia.org/w/index.php?search={}'.format(text + ' (band)'),
                icon = ICON_WEB)

# Concurrently search for text and return a sorted list of instances of Result.
def search(text):
  # TODO: Search other sites later..

  queue = Queue()

  procs = (Process(target = search_metal_archives, args = (queue, text, 'name')),
           Process(target = search_metal_archives, args = (queue, text, 'genre')))

  # Retrieve information.
  for proc in procs: proc.start()

  # Wait for all threads to complete.
  for proc in procs: proc.join()

  results = []
  while not queue.empty():
    results += queue.get_nowait()

  results = set(results) # Remove duplicates.
  return sort_results(results, text)[0:50]

def main(wf):
  if wf.update_available:
    wf.add_item('New version available',
                'Action this item to install the update',
                autocomplete = 'workflow:update', icon = ICON_SYNC)

  args = wf.args
  text = args[0].strip().lower()

  # Cache results for one minute keyed to the search text.
  results = wf.cached_data(text, lambda: search(text), max_age = 60)

  if len(results) == 0:
    wf.add_item(title = 'No results found.. Try with another query.', icon = ICON_NOTE)

  for result in results:
    result.add_to_workflow(wf)

  # Add alternative searches.
  make_allmusic_query_result(text).add_to_workflow(wf)
  make_wikipedia_query_result(text).add_to_workflow(wf)

  wf.send_feedback()

if __name__ == '__main__':
  wf = Workflow3(update_settings = {'github_slug': 'netromdk/alfred-band', 'frequency': 7})
  sys.exit(wf.run(main))
