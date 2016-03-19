"""
This program is used to cluster logs based on their similarity.
The similarity between two logs is measured based the editing distance between.
The basic unit of a log is not a character but a token.

[1] Wikibooks: Algorithm Implementation/Strings/Levenshtein distance - Python:
https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python

[2] Fast implementation of the edit distance (Levenshtein distance) - C++:
https://github.com/aflc/editdistance

[3] The dateutil module provides powerful extensions to the standard datetime
module, available in Python.
https://github.com/dateutil/dateutil

The method 'levenshteinNumPy(source, target)' implemented here is very slower
than the package 'editdistance', since the source code of 'editdistance' is
written in C++. However, if we would like to modify the levenshtein algorithm
by adding weights to different token classes 'levenshteinNumPy(source, target)'
is easier to change the code.

Author: Chang Liu (fluency03)
Data: 2016-03-11
"""


import editdistance
from dateutil.parser import parse as timeparser
# from numbers import Number
import numpy as np
import re
# import sys
import socket
import time


class LogTemplateExtractor(object):
    """
    A log template extractor.

    Attributes:
        logfile: a string, the source log file name/path.
        template_file: a string, the output file for storing log templates.
        cluster_file: a string, the output file for storing clustered logs.
        seqfile: a string, the output file for storing log sequences.
        delimiter_kept: regex, delimiters for dividing a log into tokens.
        distance_threshold: a float, two logs with editing distance less than
            this distance_threshold are considered to be similar. Default: 0.1
        ignored_chars: an integer, how many chars are ignored from the beginning
            of a log (because of the time-stamp, server-name, etc.) Default: 21
    """
    def __init__(self, logfile):
        """
        Inits LogTemplateExtractor class.
        """
        self.logfile = logfile
        self.template_file = "/home/cliu/Documents/SC-1/output"
        self.cluster_file = "/home/cliu/Documents/SC-1/console"
        self.seqfile = "/home/cliu/Documents/SC-1/sequence"

        # self.delimiter = r'[\s,:()\[\]=|/\\{}\'\"<>]+'  # ,:()[]=|/\{}'"<>
        self.delimiter_kept = r'([\s,:()\[\]=|/\\{}\'\"<>]+)'

        self.distance_threshold = 0.1

        self.ignored_chars = 21

    def set_logfile(self, logfile):
        """
        Set the source log file (name/path) which is going to be analyzed.
        """
        self.logfile = logfile

    def set_delimiter(self, delimiter):
        """
        Set the delimiters (in regular expression)
        for dividing one log into tokens.
        """
        self.delimiter_kept = delimiter

    def set_distance_threshold(self, distance_threshold):
        """
        Set the distance threshold 0 ~ 1 used for creating new cluster.
        The less the threshold is, the more similar two logs have to be
        if they want to be clustered together.
        """
        self.logfile = distance_threshold

    def set_ignored_chars(self, ignored_chars):
        """
        Set the ignored chars at the beginning of each log.
        """
        self.ignored_chars = ignored_chars

    def levenshtein_numpy(self, source, target):
        """
        Dynamic Programming algorithm, with the added optimization that only
        the last two rows of the dynamic programming matrix are needed for
        the computation. Vectorized version using NumPy.
        """
        if len(source) < len(target):
            return self.levenshtein_numpy(target, source)

        # So now we have len(source) >= len(target).
        if len(target) == 0:
            return len(source)

        # We call tuple() to force strings to be used as sequences
        # ('c', 'a', 't', 's') - numpy uses them as values by default.
        source = np.array(tuple(source))
        target = np.array(tuple(target))

        # We use a dynamic programming algorithm, but with the
        # added optimization that we only need the last two rows
        # of the matrix.
        previous_row = np.arange(target.size + 1)
        for one_source in source:
            # Insertion (target grows longer than source):
            current_row = previous_row + 1

            # Substitution or matching:
            # Target and source items are aligned, and either
            # are different (cost of 1), or are the same (cost of 0).
            current_row[1:] = np.minimum(current_row[1:],
                                         np.add(previous_row[:-1],
                                                target != one_source))

            # Deletion (target grows shorter than source):
            current_row[1:] = np.minimum(current_row[1:],
                                         current_row[0:-1] + 1)

            previous_row = current_row

        return float(previous_row[-1]) / float(max(len(source), len(target)))

    @classmethod
    def is_timestamp(cls, string):
        """
        Check whether input str is with time format like: Feb 11 05:22:51 .
        """
        try:
            time.strptime(string, '%b %d %H:%M:%S ')
            return True
        except ValueError:
            return False

    @classmethod
    def is_time(cls, string):
        """
        Check whether this is a time string.
        It supports most of the time format, more than is_timestamp()
        """
        try:
            timeparser(string)
            return True
        except ValueError:
            return False

    @classmethod
    def is_ipv4(cls, address):
        """
        Check whether this is a velid ipv4 address
        """
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except socket.error:
                return False
            return address.count('.') == 3
        except socket.error:  # not a valid address
            return False

        return True

    @classmethod
    def is_ipv6(cls, address):
        """
        Check whether this is a velid ipv6 address
        """
        try:
            socket.inet_pton(socket.AF_INET6, address)
        except socket.error:  # not a valid address
            return False
        return True


    def is_ip_address(self, address):
        """
        Check whether this is a valid ip address (ipv4 or ipv6)
        """
        return self.is_ipv4(address) or self.is_ipv6(address)

    @classmethod
    def is_pci_address(cls, address):
        """
        Check whether this is a PCI address, like 0000:00:00.0
        """
        pci_addr_pattern = r'(0000):([\da-fA-F]{2}):([\da-fA-F]{2}).(\d)'

        return re.search(pci_addr_pattern, address) is not None

    @classmethod
    def is_number(cls, number):
        """
        Check whether this is a number (int, long, float, hex)
        """
        try:
            float(number)  # for int, long, float
        except ValueError:
            try:
                int(number, 16) # for possible hex
            except ValueError:
                return False

        return True

    @classmethod
    def contain_hex(cls, string):
        """
        Check whether it contains hex values
        """
        hex_pattern = r'0x[\da-fA-F]+'

        return re.search(hex_pattern, string) is not None


    # @classmethod
    def to_wildcard(self, tokens):
        """
        Replace number tokens, hex (0x...) tokens, ip addresses and
        pci addresses by wildcard symbol * .
        """
        # hex_pattern = r'0x[\da-fA-F]+'

        for i in range(0, len(tokens)):
            token = tokens[i]
            if (self.is_number(token) or
                    self.contain_hex(token) or
                    self.is_ip_address(token) or
                    self.is_pci_address(token)):
                tokens[i] = '*'

        return tokens

    def min_distance(self, added_line, one_cluster_dict):
        """
        Calculate the minimal distance between the log and all the sub-clusters
            from previous pre-partitioned cluster.
        Return the minimal distance and its index (key for cluster).
        """
        # dictionary of the distance between this log and
        # each of its compared clusters
        distance = {}

        len_line = len(added_line)

        for cluster_num in one_cluster_dict:
            cluster = one_cluster_dict[cluster_num]

            # the first log of this cluster represents this cluster
            cluster_line = cluster[0]
            len_cluster = len(cluster_line)

            # if the length difference is already beyond the distance threshold
            # there is no need to calculate the editing distance, and
            # the distance ratio will be set to 1
            if (abs(len_cluster - len_line) / min(len_line, len_cluster) <
                    self. distance_threshold):
                dis_ratio = (
                    float(editdistance.eval(cluster_line, added_line)) /
                    float(min(len(added_line), len(cluster_line))))
            else:
                dis_ratio = float(1)

            distance[cluster_num] = dis_ratio

        # find the minimal distance and its key value
        mini = min(distance.iteritems(), key=lambda x: x[1])

        return mini[1], mini[0]

    def partition_by_command(self):
        """
        First partition the original logs based on their command type and the
        length of each log because:
        1. Dramatically reduce the computational time, especially plenty of
            time spent on levenshtein distance.
        2. Naturally, we should cluster logs starting with different command
            names into different clusters.
        3. The logs within one cluster sharing same length will make the next
            template extraction step easier.
        """
        # dictionary of the partitions divided based on
        # the tuple of command type and log length
        command_cluster = {}

        # pattern for extracting the command.
        # the command token could contain English letters, '-', '_' and '.'
        # example: rsyslogd, CMW, ERIC-RDA-Merged-Campaign,
        # mmas_syslog_control_setup.sh, etc.
        pattern = re.compile(r'([\w\-\_\./]+)([\[:])(.*)')

        # keep track of the the number of each log
        current_num = 0

        with open(self.logfile) as in_file:
            # read the first line
            added_line = in_file.readline()
            current_num = current_num + 1

            # the real first line is the first log appearing with time-stamp
            while not self.is_timestamp(added_line[:16]):
                added_line = in_file.readline()
                current_num = current_num + 1

            # read th following lines
            for line in in_file:
                current_num = current_num + 1

                # if the current line is not with time-stamp, it will be
                # added together to its previous logs until the the previous
                # nearest log with time-stamp
                if not self.is_time(line[:16]):
                    added_line = added_line.rstrip() + ' | ' + line
                    continue
                else:
                    # extract command
                    command = re.match(pattern, added_line[21:]).group(1)
                    # tokenize the log message
                    line_tokens = [t for t in
                                   re.split(self.delimiter_kept,
                                            added_line[self.ignored_chars:])
                                   if t is not '']
                    # convert numbers, hexs, ip address, pci address to *
                    line_tokens = self.to_wildcard(line_tokens)
                    # get the length of this token list
                    length = len(line_tokens)

                    # if this cluster (command, length) existing,
                    # append current log into its cluster;
                    # if not, create a new cluster, key is (command, length),
                    # initial value is [current log]
                    command_cluster.setdefault(
                        (command, length), [line_tokens]).append(line_tokens)

                    added_line = line

            # Add the last line
            command = re.match(pattern, added_line[21:]).group(1)
            line_tokens = self.to_wildcard(
                re.split(self.delimiter_kept, added_line[self.ignored_chars:]))
            length = len(line_tokens)

            command_cluster.setdefault((command, length),
                                       [line_tokens]).append(line_tokens)

        return command_cluster

    def log_clustering(self, print_clusters=False):
        """
        Similarity checks and clustering after partitioning based on command.
        """
        # clusters based on command and log length
        command_cluster = self.partition_by_command()

        # dictionary of the log clusters
        cluster_dict = {}
        # keep track of the log cluster number
        cluster_num = 0

        for i in command_cluster:
            one_cluster_dict = {}
            for line in command_cluster[i]:
                if not one_cluster_dict:
                    one_cluster_dict[cluster_num] = [line]
                    cluster_num += 1
                else:
                    # get the minimal distance ratio and its index key
                    min_dis, min_key = self.min_distance(line, one_cluster_dict)

                    # if minimal distance ratio is less than the threshold,
                    # add this log into the cluster according to the index key;
                    # otherwise, create a new cluster
                    if min_dis < self.distance_threshold:
                        one_cluster_dict[min_key].append(line)
                    else:
                        one_cluster_dict[cluster_num] = [line]
                        cluster_num += 1

            # put all new clusters into the dictionary
            cluster_dict.update(one_cluster_dict)

        # print the clusters
        if print_clusters:
            with open(self.cluster_file, 'w') as cluster_file:
                for i in cluster_dict:
                    cluster_file.write(str(i) + '\n')
                    for item in cluster_dict[i]:
                        cluster_file.write(''.join(item).rstrip() + '\n')

        print "Number of clusters: %d" %len(cluster_dict)

        return cluster_dict

    @classmethod
    def log_template(cls, cluster):
        """
        Collect the unique tokens at each position of a log within a cluster.
        Update the positions where >1 unique tokens by wildcard *.
        Generate the template representation for this cluster.
        """
        # the first log represent this cluster
        one_line_tokens = cluster[0]
        # get the length
        len_line = len(one_line_tokens)

        # a list of dictionaries represents at each of the token position
        # how many different tokens there are, and what are they
        token_collection = []

        for item in cluster:
            for i in range(0, len_line):
                token = item[i]
                if len(token_collection) > i:
                    token_collection[i].setdefault(token)
                else:
                    token_collection.append({token: None})

        # cardinality = []
        # for i in range(0, len_line):
            # cardinality.append(str(len(token_collection[i])))

        # for positions sharing more than one unique token,
        # regard them as variables and convert them into *
        for i in range(0, len_line):
            if len(token_collection[i]) is not 1:
                one_line_tokens[i] = '*'

        return ''.join(one_line_tokens).rstrip() + '\n'

    def discover_template(self, print_clusters=False, print_templates=False):
        """
        Abstract the template representation from each of the clusters.
        """
        cluster_dict = self.log_clustering(print_clusters=print_clusters)
        template_dict = {}

        # get each of the tempalte representations into the template_dict
        for i in cluster_dict:
            template_dict.setdefault(i, self.log_template(cluster_dict[i]))

        # print the template representations
        if print_templates:
            with open(self.template_file, 'w') as template_file:
                for i in template_dict:
                    template_file.write(str(i) + '\n')
                    for item in template_dict[i]:
                        template_file.write(item)

        print "Number of tempaltes: %d" %len(template_dict)

        return template_dict


    def generate_sequence(self, new_logfile, print_sequence=True,
                          print_clusters=False, print_templates=False):
        """
        Generate the log sequence based on previous generated templates and
        new input log files
        """
        template_dict = self.discover_template(print_clusters=True,
                                               print_templates=True)

        # print the template representations
        with open(new_logfile, 'r') as seq_file:
            with open(self.seqfile, 'w') as seq_file:
                pass











def main():
    """
    Main function
    """

    print "\nStart...\n"

    start_time = time.time()
    logfile = "/home/cliu/Documents/SC-1/messages.1"
    extractor = LogTemplateExtractor(logfile)
    # extractor.log_clustering_slow()
    # extractor.partition_by_command()
    # extractor.log_clustering()
    # extractor.discover_template(print_clusters=True, print_templates=True)
    stop_time = time.time()

    print "\n--- %s seconds ---\n" % (stop_time - start_time)

    print "\nStop...\n"



    # ---------------------------- For debugging ---------------------------- #



    # ---------------------------- For debugging ---------------------------- #


if __name__ == "__main__":
    # sys.stdout = open(console, 'w')
    main()
