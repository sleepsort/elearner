#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import os
import glob

if sys.platform == "win32":
  prefix = os.path.dirname(os.path.abspath(__file__))
  sys.path.append(os.path.join(prefix, 'lib', 'python27.zip'))
  sys.path.append(os.path.join(prefix, 'lib', 'python27.zip', 'lib-tk'))
  sys.path.append(os.path.join(prefix, 'lib', 'DLLs'))

try:
  import configparser
except ImportError:
  import ConfigParser as configparser

import random
import re
from Tkinter import *
from tkMessageBox import *

USAGE= '''
  usage:
    ./dict.py [TEST_CORPUS]

    TEST_CORPUS:
      data files in data/dict (lesson01.dat as default)

    If no options are supplied and config.ini exists, it loads
    configuration from config.ini.
'''

FONT_BASE = "Fixsys"
#FONT_BASE = "DroidSansMono"

DEFAULT_FONT = "%s 15" % FONT_BASE
SUCCESS_FONT = "%s 15 bold" % FONT_BASE
FAIL_FONT = SUCCESS_FONT
INPUT_FONT = "%s 10 bold" % FONT_BASE
DEFAULT_FONT_MIDDLE = "%s 13" % FONT_BASE
DEFAULT_FONT_LARGE  = "%s 15 bold" % FONT_BASE

DEFAULT_COLOR = "black"
SUCCESS_COLOR = "black"
FAIL_COLOR    = "red"

COLUMNS = 11

class Util():
  @staticmethod
  def generate_problem(key, hide_length):
    problem = ""
    for idx, ch in enumerate(key):
      if Util.ispunct(ch):
        problem += ch
      else:
        problem += "_"
      if (idx+1) % 15 == 0:
        problem += "\n"
      else:
        if hide_length:
          problem += "_"
        else:
          problem += " "
    return problem[:-1]

  @staticmethod
  def reformat(longstr):
    if not longstr:
      return longstr
    slice = [longstr[i:i+15] for i in range(0, len(longstr), 15)]
    return "\n".join(slice)

  @staticmethod
  def ispunct(ch):
    return unicode(ch) in u' .,!?¡¿'

  @staticmethod
  def add_solution_char(problem, ch):
    text = problem.replace("_", ch, 1)
    completed = (text.find("_") == -1)
    return (text, completed)

  @staticmethod
  def del_solution_char(problem):
    text = problem
    pos = text.find("_")
    updated = (pos != 0)
    if pos == -1:
      text = text[:-1] + "_"
    elif pos != 0:
      if Util.ispunct(text[pos-2:pos-1]):
        pos -= 1 
      text = text[:pos-2] + "_" + text[pos-1:]
    return (text, updated)

  @staticmethod
  def match_str(truth, test):
    for noise in u'.,!?¡¿ \n\t':
      truth = truth.replace(noise, '')
      test = test.replace(noise, '')
    if len(truth) != len(test):
      return False
    for (x, y) in zip(truth, test):
      if x != y:
        return False
    return True
  @staticmethod
  def split(str):
    fields = re.split(r"[ ]{2,}", str.strip())
    return filter(None, fields)


class DictProcessor():
  def __init__(self, filepaths):
    self.files = filepaths
    self.pending = []
    self.filenum = -1
    self.linenum = -1

  def readline(self):
    while True:
      self.linenum += 1
      if self.linenum >= len(self.pending):
        self.filenum += 1
        if self.filenum >= len(self.files):
          return None
        try:
          data = open(self.files[self.filenum], 'rb').read().decode("utf-8")
        except IOError, message:
          print >> sys.stderr, "Dict file cound not be opened:", message
          sys.exit(1)
        self.pending = data.splitlines(0)
        if len(self.pending) <= 1 or self.pending[0].find("#DICT") == -1:
          self.linenum = len(self.pending)
          continue
        self.linenum = 1
      fields = Util.split(self.pending[self.linenum])
      if len(fields) < 2:
        print >> sys.stderr, "Bogus line? %s" % fields
        continue
      return fields

class DictItem(object):
  def __init__(self, spanish=None, chinese=None):
    self.spanish = spanish
    self.chinese = chinese

  def copy(self, other):
    self.spanish = other.spanish
    self.chinese = other.chinese

class Dict():
  dicts = {}

  @staticmethod
  def load_problem_dict(filepaths):
    processor = DictProcessor(filepaths)
    line = processor.readline()
    while line:
      spanish, chinese = [None] * 2
      spanish = line[0]
      chinese = line[1:]
      chinese = ' '.join(list(chinese))
      Dict.dicts[spanish] = DictItem(spanish, chinese)
      line = processor.readline()

class Logger(object):
  def __init__(self):
    self.id = os.getpid()
    self.filename = 'log/dict.%d.tmp' % (self.id);
    self.file = open(self.filename, 'w', 0)
    print >> self.file, "#LOG <flag> <key>"
    self.done = self.cleanup(self.filename)

  def cleanup(self, exclude):
    oldlogs = glob.glob("log/dict.*.tmp")
    for i, item in enumerate(oldlogs):
      oldlogs[i] = item.replace('\\', '/')
    oldlogs = set(oldlogs)
    oldlogs.remove(exclude)
    done = set()
    for name in oldlogs:
      data = open(name, 'rb').read().decode("utf-8")
      records = data.splitlines(0)
      if not records or records[0].find('#LOG') == -1:
        print >> sys.stderr,"%s isn't a valid log file, ignored!" % name
      else:
        for line in records[1:]:
          line = line.strip()
          print >> self.file, line.encode('utf-8')
          fields = Util.split(line)
          if fields[0] == '1':  # ignore passed items
            done.add(fields[1])
      os.remove(name)
    return done

  def write(self, flag, key):
    info = "%s   %s" % (flag, key)
    print >> self.file, info.encode('utf-8')

  def merge(self):
    if self.file:
      self.file.close()
    collect = {}
    try:
      file = open('log/dict.dat', 'rb')
      if file.readline().find('#LOG') == -1:
        print >> sys.stderr, "Previous log file invalid"
        file.close()
      else:
        for line in file:
          line = Util.split(line)
          passed, failed, key = int(line[0]), int(line[1]), line[2]
          if key not in collect:
            collect[key] = [passed, failed]
          else:
            collect[key][0] += passed
            collect[key][1] += failed
        file.close()
    except IOError, message:
      print >> sys.stderr, "File could not be opened:", message
    newdata = open(self.filename, 'r')
    newdata.readline()
    for record in newdata:
      fields = Util.split(record)
      flag, key = int(fields[0]), fields[1]
      if key not in collect:
        collect[key] = [0, 0]
      if flag == 0:
        collect[key][1] += 1
      else:
        collect[key][0] += 1
    newdata.close()
    file = open('log/dict.dat', 'w', 0)
    print >> file, "#LOG <pass> <fail> <key>"

    for key in sorted(collect.iterkeys()):
      val = collect[key]
      info = "%3d %3d   %s" % (val[0], val[1], key)
      print >> file, info
    file.close()
    os.remove(self.filename)


class Runner(object):
  def __init__(self):
    self.hide_length = False
    self.pended = set(Dict.dicts.keys())
    self.failed = set()
    self.key  = None
    self.totalpass = 0
    self.totalfail = 0
    self.logger = Logger()
    self.pended = self.pended - self.logger.done

  def next(self):
    if not self.pended and self.failed:
      self.pended = self.failed
      self.failed = set()
    totalpass = self.totalpass
    total = totalpass + len(self.failed) + len(self.pended)
    if self.pended:
      key = random.sample(self.pended, 1)[0]
      item = Dict.dicts[key]
      self.key = key
      return totalpass, total, Util.generate_problem(key, self.hide_length), item.chinese
    self.logger.merge()
    return totalpass, total, None, None

  def test(self, input):
    key, item = self.key, Dict.dicts[self.key]
    try:
      print item.spanish, 
    except UnicodeEncodeError, message:
      print "----",
    try:
      print item.chinese,
    except UnicodeEncodeError, message:
      print "----",
    print "{%s}" % input
    success = Util.match_str(key, input)
    if success:
      self.totalpass += 1
      self.logger.write(1, key)
    else:
      self.totalfail += 1
      self.failed.add(key)
      self.logger.write(0, key)
    self.pended.remove(key)
    item = DictItem()
    item.copy(Dict.dicts[key])
    item.spanish = Util.reformat(item.spanish)
    item.chinese = Util.reformat(item.chinese)
    return item, success

  def stats(self):
    return self.totalpass, self.totalfail

class ELearner(Frame):
  def __init__(self, dict_files):
    """Create and grid several components into the frame"""
    Frame.__init__(self)

    Dict.load_problem_dict(dict_files)

    self.dict_files = dict_files

    self.runner = Runner()

    # text variables that might be updated in real time
    self.active_text = {"input" : StringVar(),
                        "counter" : StringVar(),
                        "spanish" : StringVar(),
                        "chinese" : StringVar()}

    # widgets that might change style in real time
    self.active_widgets = {"input" : None,
                           "spanish" : None,
                           "chinese" : None }
   
    self.init_widgets()

    self.lock = False
    # TODO: when dict is empty, without this we have problem
    # quit the program properly
    self.after(50, self.next)

  def init_widgets(self):
    self.bind_all("<Escape>", self.del_char)
    self.pack(expand = NO, fill = BOTH)
    self.master.title("Español Learning")
    self.master.geometry("350x160")
    self.master.rowconfigure(0, weight = 1)
    self.master.columnconfigure(0, weight = 1)
    self.grid(sticky = W+E+N+S)

    self.row = 0
    spanish_pane = Label(self)
    spanish_pane["textvariable"] = self.active_text["spanish"]
    spanish_pane["height"] = 2
    spanish_pane["font"] = DEFAULT_FONT_LARGE
    pad_pane = Label(self)
    pad_pane["text"] = ""
    pad_pane["width"] = 2
    pad_pane.grid(row = self.row, rowspan = 2, column = 0, columnspan = 1)
    spanish_pane.grid(row = self.row, rowspan = 2, column = 1, columnspan = COLUMNS - 2, sticky = W+E+N+S)
    self.active_widgets["spanish"] = spanish_pane
    self.row += 2;

    chinese_pane = Label(self)
    chinese_pane["textvariable"] = self.active_text["chinese"]
    chinese_pane["height"] = 2
    chinese_pane["font"] = DEFAULT_FONT_MIDDLE
    chinese_pane.grid(row = self.row, rowspan = 2, columnspan = COLUMNS, sticky = W+E+N+S)
    self.active_widgets["chinese"] = chinese_pane
    self.row += 2;

    counter_pane = Label(self)
    counter_pane["textvariable"] = self.active_text["counter"]

    input_pane = Entry(self, font = INPUT_FONT)
    input_pane["textvariable"] = self.active_text["input"]
    input_pane.grid(row = self.row, column = 1, columnspan = COLUMNS - 2, sticky = W+E+N+S)
    input_pane.focus_set()
    input_pane.bind("<Return>", self.test)
    confirm_button = Button(self)
    confirm_button["text"] = "ok"
    confirm_button["width"] = 1
    confirm_button.bind("<ButtonRelease>", self.test)
    confirm_button.grid(row = self.row + 1, column = COLUMNS - 2, columnspan = 1, sticky = W+E+N+S)
    counter_pane.grid(row = self.row + 1, columnspan = 3, column = 1, sticky = W+E+N+S)
    self.row = self.row + 2;

    self.active_widgets["input"] = input_pane

    self.rowconfigure(self.row, weight = 1)
    for i in range(0, COLUMNS):
      self.columnconfigure(i, weight = 1)

  def test(self, event):
    if self.lock:
      return
    self.lock = True
    item, success = self.runner.test(self.active_text["input"].get())
    spanish = item.spanish
    self.active_text["spanish"].set(spanish)
    if success:
      self.active_widgets["spanish"]["foreground"] = SUCCESS_COLOR
      self.active_widgets["spanish"]["font"] = SUCCESS_FONT
      self.active_widgets["input"]["state"] = 'disabled'
      self.after(800, self.next)
    else:
      self.active_widgets["spanish"]["foreground"] = FAIL_COLOR
      self.active_widgets["spanish"]["font"] = FAIL_FONT
      self.active_widgets["input"]["state"] = 'disabled'
      self.after(4000, self.next)

  def add_char(self, event):
    if not self.lock:
      ch = event.widget["text"]
      text = self.active_text["spanish"].get()
      text, complete = Util.add_solution_char(text, ch)
      self.active_text["spanish"].set(text)
      if complete:
        newtext = text.replace(' ', '')
        self.active_text["input"].set(newtext)
        self.test(event)

  def del_char(self, event):
    if not self.lock:
      text = self.active_text["spanish"].get()
      text, update = Util.del_solution_char(text)
      self.active_text["spanish"].set(text)

  def next(self):
    self.lock = False
    passed, total, hint, problem = self.runner.next()
    if problem:
      self.active_text["spanish"].set(hint)
      self.active_text["chinese"].set(problem)
      self.active_text["counter"].set("%d / %d" % (passed, total))
      self.active_text["input"].set("")
      self.active_widgets["spanish"]["foreground"] = DEFAULT_COLOR
      self.active_widgets["spanish"]["font"] = DEFAULT_FONT
      self.active_widgets["input"]["state"] = 'normal'
    else:
      passed, failed = self.runner.stats()
      info = "Well done!\n\n"
      info += "Result:\n"
      info += "  pass: %d  fail: %d\n" % (passed, failed)
      showinfo("Message", info)
      self.quit()

def main(dict_files):
  ELearner(dict_files).mainloop()

def load_config():
  config = configparser.ConfigParser()
  config.read('config.ini')
  test_dir  = config.get('dict', 'testdir').split('|')
  test_file = config.get('dict', 'testfile').split('|')
  dict_files = []
  for dir in test_dir:
    dir = dir.strip()
    for file in test_file:
      file = file.strip()
      dict_files += glob.glob("%s/%s" % (dir, file))
  return dict_files

if __name__ == "__main__":
  os.chdir(os.path.dirname(os.path.abspath(__file__)))

  argv = sys.argv[1:]

  files = []
  for x in argv:
    files.append(x)

  config = False
  try:
    dict_files = load_config()
    config = True
  except Exception, e:
    print >> sys.stderr, "load config error:", e 

  if files or not config:
    # default options 
    # (when no config file exists, and no arguments)
    dict_files = ['data/dict/lesson01.dat']
    if files:
      dict_files = files

  main(dict_files)
