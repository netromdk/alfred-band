#!/usr/bin/python
# encoding: utf-8

import sys
from workflow import Workflow3

# Search for text and return tuples of (title, subtitle).
def search(text):
  items = []
  # TODO: Search some web API here!
  return items

def main(wf):
  args = wf.args

  items = search(args[0])
  for item in items:
    wf.add_item(item[0], item[1])

  wf.send_feedback()

if __name__ == '__main__':
  wf = Workflow3()
  sys.exit(wf.run(main))
