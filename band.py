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

def main(wf):
  args = wf.args

  text = args[0].strip().lower()
  results = search(text)
  if len(results) == 0:
    wf.add_item(title = u'No results found.. Try with another query.')
  else:
    results = sort_results(results, text)

    # Limit to 50 results.
    results = results[0:50]

    for result in results:
      wf.add_item(title = result.title(), subtitle = result.url, arg = result.url, valid = True)

  wf.send_feedback()

if __name__ == '__main__':
  wf = Workflow3()
  sys.exit(wf.run(main))
