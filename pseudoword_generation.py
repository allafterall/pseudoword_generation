#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse

from csv import reader, writer
from collections import defaultdict
from random import randint


class LexiconEntry:
  def __init__(self, pos, ipm):
    self.pos = pos
    self.ipm = ipm
  

def ReadLexicon(lexicon_filename):
  lexicon = defaultdict(LexiconEntry)
  with open(lexicon_filename) as lexicon_file:
    lexicon_reader = reader(lexicon_file, delimiter="\t") 
    skip_header = True
    for line in lexicon_reader:
      if skip_header:
        skip_header = False
        continue
      word = line[0].decode('utf-8').lower().encode('utf-8')
      if word.find('-') != -1:
        continue
      if word in lexicon:
        continue
      pos = line[1]
      ipm = float(line[2])
      lexicon[word] = LexiconEntry(pos, ipm)
  return lexicon


def GenerateModel(lexicon, vowels,args):
  model = defaultdict(dict)
  count = 0
  for word in lexicon:
    if args.pos and lexicon[word].pos != args.pos:
      continue
    count += 1
    syllables = GetSyllables(word, vowels)
    dimension = str(len(syllables))
    ipm = lexicon[word].ipm
    if args.dont_use_ipm:
      ipm = 1
    if args.v:
      print word, ":", (" - ".join(syllables)).encode('utf-8')
    syllables.insert(0, "[BEG]")
    for i in range(1, len(syllables)):
      prev_syllable = syllables[i - 1]
      if args.use_finale_only:
        prev_syllable = GetFinale(prev_syllable, vowels)
      length = dimension
      if args.use_any_length and i != len(syllables) - 1:
        length = ""
      key = prev_syllable + "_" + str(i - 1) + "_" + length
      if not syllables[i] in model[key]:
        model[key][syllables[i]] = ipm
      else:
        model[key][syllables[i]] += ipm
  print "Used", count, "words to generate model"
  return model


def GetSyllables(word, vowels):
  syllables = []
  current_syllable = ""
  for letter in word.decode('utf-8'):
    current_syllable += letter
    if letter in vowels:
      syllables.append(current_syllable)
      current_syllable = ""
  if (len(syllables) == 0) :
    syllables.append(current_syllable)
  else:
    syllables[len(syllables) - 1] += current_syllable
  for i in range(1,len(syllables)):
    if (len(syllables[i]) > 2 and
        syllables[i][0] not in vowels and
        syllables[i][1] not in vowels):
      syllables[i - 1] += syllables[i][0]
      syllables[i] = syllables[i][1:]
    if syllables[i][0] == u"ь":
      syllables[i - 1] += syllables[i][0]
      syllables[i] = syllables[i][1:]
  return syllables
  # This could be used if we want to generate words letter-by-letter,
  # not syllable-by-syllable
  # TODO: make this configurable by flags
  #ret = []
  #for letter in word.decode('utf-8'):
  #  ret.append(letter)
  #return ret

def GetFinale(syllable, vowels):
  if syllable == "[BEG]":
    return ""
   
  res = ""
  for i in range(len(syllable)):
    if syllable[len(syllable) - i - 1] in vowels:
      return res
    else:
      res = syllable[len(syllable) - i - 1] + res
  print "Error in [",syllable,"] finale detection!"


def GeneratePseudoword(model, length, lexicon, vowels, args):
  count = 0
  while count < args.max_tries:
    count += 1
    current_syllable = "[BEG]"
    pos = 0
    pseudoword = ""
    while pos < length:
      prev_syllable = current_syllable
      if args.use_finale_only:
        prev_syllable = GetFinale(prev_syllable, vowels)
      len_key = str(length)
      if args.use_any_length and pos != length - 1:
        len_key = ""
      key = prev_syllable + "_" + str(pos) + "_" + len_key
      if not key in model:
        print "Cannot generate pseudoword"
        return ""
      bigrams = sorted(model[key].items(), key=lambda x: x[1], reverse=True)
      right_bound = min(len(bigrams) - 1, len(bigrams) * args.u / 100)
      index = randint(0, right_bound)
      if args.v:
        for i in range(0, right_bound):
          print ("Candidate:", bigrams[i][0].encode('utf-8'),
                 key.encode('utf-8'), bigrams[i][1])
      current_syllable = bigrams[index][0]
      if args.v:
        print "Selected syllable:",current_syllable.encode('utf-8') 
      pseudoword += current_syllable
      pos += 1
    # Only generate words that are not currently in lexicon
    if not pseudoword.encode('utf-8') in lexicon:
      return pseudoword
    elif args.v:
      print ("Generated pseudoword", pseudoword.encode('utf-8'),
             "which is already in the lexicon!")
  print ("All generated", args.max_tries, "pseudowords are "
         "in the lexicon already, aborting")
  return ""

      
def main():
  parser = argparse.ArgumentParser(description='Generate Pseudowords')
  parser.add_argument('--lexicon', default="freqrnc2011.csv",
                      help='Path to file with lexicon')
  parser.add_argument('--pos', help='Generate pseudoword only for given part of speech')
  parser.add_argument('--use_finale_only',action="store_true",
                       help='Use only finale of previous syllable when building the model')
  parser.add_argument('--use_any_length',action="store_true",
                       help='Don\'t take into account length of the word when generating'
                       ' pseudoword')
  parser.add_argument('-n', dest='n', type=int, default=10,
                       help='How much pseudowords to generate')
  parser.add_argument('-s', dest='s', type=int, default=6,
                       help='Number of syllables in each pseudoword')
  parser.add_argument('-u', dest='u', type=int, default=20,
                       help='Percent of top candidates to select syllable from')
  parser.add_argument('--dont_use_ipm', action="store_true",
                       help='Don\'t take into account IPM for words from dictionary')
  parser.add_argument('--output', help='File to output resulting pseudowords')
  parser.add_argument('--max_tries', type=int, default=500,
                       help='Maximum number of tries to generate pseudoword not from'
                       ' the lexicon')
  parser.add_argument('-v', action="store_true",
                       help='Verbose output')
  args = parser.parse_args()

  vowels = [u'а', u'у', u'е', u'ё', u'и', u'о', u'у', u'ы', u'э', u'ю', u'я']
  
  lexicon = ReadLexicon(args.lexicon)
  print "Dictionary size: ", len(lexicon)

  model = GenerateModel(lexicon, vowels, args)
  
  print "Generating", args.n, "pseudowords with", args.s, "syllables"
  if args.output:
    with open(args.output, "w") as res_file:
      for i in range(0,args.n):
        res_file.write(GeneratePseudoword(model, args.s, lexicon, vowels, args).encode('utf-8') + "\n")
  else:
    for i in range(0,args.n):
      print "\t", GeneratePseudoword(model, args.s, lexicon, vowels, args)


if __name__ == '__main__':
    main()
