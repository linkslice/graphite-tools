#!/bin/env python


from optparse import OptionParser
import sys
import os
import pickle





def main():
    parser = OptionParser()
    parser.add_option('-f', '--file', dest='filename',
        default='data.p',
        help='location of data.p or other pickle.')
    options, args = parser.parse_args()


    data = pickle.load(open(options.filename))

    i = 0
    while i < len(data):
        print(("%s %s %s") % (data[i][0], data[i][1][1], data[i][1][0]))
        i = i + 1 

if __name__ == '__main__':
    main()
