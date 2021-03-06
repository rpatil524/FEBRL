# =============================================================================
# AUSTRALIAN NATIONAL UNIVERSITY OPEN SOURCE LICENSE (ANUOS LICENSE)
# VERSION 1.3
#
# The contents of this file are subject to the ANUOS License Version 1.3
# (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at:
#
#   https://sourceforge.net/projects/febrl/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
# the License for the specific language governing rights and limitations
# under the License.
#
# The Original Software is: "output.py"
#
# The Initial Developer of the Original Software is:
#   Dr Peter Christen (Research School of Computer Science, The Australian
#                      National University)
#
# Copyright (C) 2002 - 2011 the Australian National University and
# others. All Rights Reserved.
#
# Contributors:
#
# Alternatively, the contents of this file may be used under the terms
# of the GNU General Public License Version 2 or later (the "GPL"), in
# which case the provisions of the GPL are applicable instead of those
# above. The GPL is available at the following URL: http://www.gnu.org/
# If you wish to allow use of your version of this file only under the
# terms of the GPL, and not to allow others to use your version of this
# file under the terms of the ANUOS License, indicate your decision by
# deleting the provisions above and replace them with the notice and
# other provisions required by the GPL. If you do not delete the
# provisions above, a recipient may use your version of this file under
# the terms of any one of the ANUOS License or the GPL.
# =============================================================================
#
# Freely extensible biomedical record linkage (Febrl) - Version 0.4.2
#
# See: http://datamining.anu.edu.au/linkage.html
#
# =============================================================================

"""Module output.py - Functions for output of linkage and deduplication.

   This module provides several functions that allow saving the linkage or
   deduplication results into files of various formats. It also contains
   various output (and input) related auxiliary functions.

   The following functions are provided:

     GenerateHistogram    Convert the summed weight vectors into a (ASCII text
                          based) histogram and return as a list of text (for
                          printing into a terminal window), and possibly write
                          into a text file.
     SaveMatchStatusFile  Save the matched record identifiers into a CVS file.
     SaveMatchDataSet     Save the original data set(s) with an additional
                          field (attribute) that contains match identifiers.

  The following auxiliary functions are also provided:

    LoadWeightVectorFile  Load a CSV file assumed to contain record identifier
                          tuples and their corresponding weight vectors as
                          written with a run() method from indexing.py
"""

# =============================================================================
# Import necessary modules (Febrl modules first, then Python standard modules)

import auxiliary
import dataset

import csv
import gzip
import logging
import math
import os

# =============================================================================


def GenerateHistogram(w_vec_dict, bin_width, file_name=None, match_sets=None):
    """Print and/or save a histogram of the weight vectors stored in the given
       dictionary, and according to the match sets (if given).

       The histogram is rotated 90 degrees clockwise, i.e. up to down instead of
       left to right.

       This function sums up the number of weight vectors with a matching weight
       in a given bin (according to the given bin width).

       If given, the match sets must be a tuple containing three sets, the first
       being a set with matches, the second with non-matches, and the third with
       possible matches, as generated by classifiers in the classification.py
       Febrl module.

       For each bin, the number of weight vectors in this bin is printed as well,
       and if the match sets are given the number of matches, non-matches and
       possible matches in this bin.

       If a file name is given, the output will be written into this text file.

       This function returns a list of containing the histogram as text strings.
    """

    MAX_HISTO_WIDTH = 80  # maximum width in characters

    auxiliary.check_is_dictionary("w_vec_dict", w_vec_dict)
    auxiliary.check_is_number("bin_width", bin_width)
    auxiliary.check_is_positive("bin_width", bin_width)
    if file_name != None:
        auxiliary.check_is_string("file_name", file_name)
    if match_sets != None:
        auxiliary.check_is_tuple("match_sets", match_sets)
        if len(match_sets) != 3:
            logging.exception("Match sets must be a tuple containing three sets.")
            raise Exception
        auxiliary.check_is_set("match_sets[0]", match_sets[0])
        auxiliary.check_is_set("match_sets[1]", match_sets[1])
        auxiliary.check_is_set("match_sets[2]", match_sets[2])
        if len(w_vec_dict) != (
            len(match_sets[0]) + len(match_sets[1]) + len(match_sets[2])
        ):
            logging.exception(
                "Lengths of weight vector dictionary differs from"
                + "summed lengths of match sets."
            )
            raise Exception

    # Check if weight vector dictionary is empty, if so return empty list
    #
    if w_vec_dict == {}:
        logging.warn(
            "Empty weight vector dictionary given for histogram " + "generation"
        )
        return []

    # Get a random vector dictionary element to get dimensionality of vectors
    #
    (rec_id_tuple, w_vec) = w_vec_dict.popitem()
    v_dim = len(w_vec)
    w_vec_dict[rec_id_tuple] = w_vec  # Put back in

    histo_dict = {}  # A combined histogram dictionary

    if match_sets != None:  #  Also matches, non-matches and possible matches
        match_histo_dict = {}
        non_match_histo_dict = {}
        poss_match_histo_dict = {}

    max_bin_w_count = -1  # Maximal count for one binned weight entry

    # Loop over weight vectors - - - - - - - - - - - - - - - - - - - - - - - - -
    #
    for (rec_id_tuple, w_vec) in w_vec_dict.items():

        w_sum = sum(w_vec)  # Sum all weight vector elements
        binned_w = w_sum - (w_sum % bin_width)

        binned_w_count = histo_dict.get(binned_w, 0) + 1  # Increase count by one
        histo_dict[binned_w] = binned_w_count

        if binned_w_count > max_bin_w_count:  # Check if this is new maximum count
            max_bin_w_count = binned_w_count

        if match_sets != None:
            if rec_id_tuple in match_sets[0]:
                binned_w_count = match_histo_dict.get(binned_w, 0) + 1
                match_histo_dict[binned_w] = binned_w_count
            elif rec_id_tuple in match_sets[1]:
                binned_w_count = non_match_histo_dict.get(binned_w, 0) + 1
                non_match_histo_dict[binned_w] = binned_w_count
            else:  # A possible match
                binned_w_count = poss_match_histo_dict.get(binned_w, 0) + 1
                poss_match_histo_dict[binned_w] = binned_w_count

    # Sort histogram according to X axis values - - - - - - - - - - - - - - - - -
    #
    x_vals = list(histo_dict.keys())
    x_vals.sort()

    assert sum(histo_dict.values()) == len(w_vec_dict)

    if match_sets == None:  # Can use 68 characters for histogram
        scale_factor_y = float(MAX_HISTO_WIDTH - 19) / max_bin_w_count
    elif len(poss_match_histo_dict) == 0:  # No possible matches
        scale_factor_y = float(MAX_HISTO_WIDTH - 30) / max_bin_w_count
    else:  # All three set non-empty
        scale_factor_y = float(MAX_HISTO_WIDTH - 41) / max_bin_w_count

    # Generate the histogram as a list of strings - - - - - - - - - - - - - - - -
    #
    histo_list = []
    histo_list.append("Weight histogram:")
    histo_list.append("-----------------")

    if match_sets == None:
        histo_list.append("  Counts  | w_sum |")
        histo_list.append("-------------------")
    elif len(poss_match_histo_dict) == 0:  # No possible matches
        histo_list.append("       Counts        |")
        histo_list.append("  Match   | Non-Match| w_sum |")
        histo_list.append("------------------------------")
    else:
        histo_list.append("              Counts            |")
        histo_list.append("  Match   | Non-Match|Poss-Match| w_sum |")
        histo_list.append("-----------------------------------------")
    for x_val in x_vals:
        this_count = histo_dict[x_val]

        if match_sets == None:
            line_str = "%9d | %5.2f |" % (this_count, x_val)
        elif len(poss_match_histo_dict) == 0:  # No possible matches
            this_match_count = match_histo_dict.get(x_val, 0)
            this_non_match_count = non_match_histo_dict.get(x_val, 0)

            line_str = "%9d |%9d | %5.2f |" % (
                this_match_count,
                this_non_match_count,
                x_val,
            )
        else:
            this_match_count = match_histo_dict.get(x_val, 0)
            this_non_match_count = non_match_histo_dict.get(x_val, 0)
            this_poss_match_count = poss_match_histo_dict.get(x_val, 0)

            line_str = "%9d |%9d |%9d | %5.2f |" % (
                this_match_count,
                this_non_match_count,
                this_poss_match_count,
                x_val,
            )

        line_str += "*" * int(this_count * scale_factor_y)
        histo_list.append(line_str)

    histo_list.append("")

    # If a file name is given open it for writing - - - - - - - - - - - - - - - -
    #
    if file_name != None:
        try:
            f = open(file_name, "w")
        except:
            logging.exception('Cannot open file "%s" for writing' % (str(file_name)))
            raise IOError

        for line in histo_list:
            f.write(line + os.linesep)

        f.close()
        logging.info("Histogram written to file: %s" % (file_name))

    if match_sets != None:
        print(list(match_histo_dict.items()))
        print(list(non_match_histo_dict.items()))

    return histo_list


# -----------------------------------------------------------------------------


def SaveMatchStatusFile(w_vec_dict, match_set, file_name):
    """Save the matched record identifiers into a CVS file.

       This function saves the record identifiers of all record pairs that are in
       the given match set into a CSV file with four columns:
       - First record identifier
       - Second record identifier
       - Summed matching weight from the corresponding weight vector
       - A unique match identifier (generated in the same way as the ones in the
         function SaveMatchDataSet below).
    """

    auxiliary.check_is_dictionary("w_vec_dict", w_vec_dict)
    auxiliary.check_is_set("match_set", match_set)
    auxiliary.check_is_string("file_name", file_name)

    match_rec_id_list = list(match_set)  # Make a list so it can be sorted
    match_rec_id_list.sort()

    if len(match_set) > 0:
        num_digit = max(1, int(math.ceil(math.log(len(match_set), 10))))
    else:
        num_digit = 1
    mid_count = 1  # Counter for match identifiers

    # Try to open the file for writing
    #
    try:
        f = open(file_name, "w")
    except:
        logging.exception('Cannot open file "%s" for writing' % (str(file_name)))
        raise IOError

    for rec_id_tuple in match_rec_id_list:
        w_vec = w_vec_dict[rec_id_tuple]
        w_sum = sum(w_vec)

        mid_count_str = "%s" % (mid_count)
        this_mid = "mid%s" % (mid_count_str.zfill(num_digit))

        rec_id1 = rec_id_tuple[0]
        rec_id2 = rec_id_tuple[1]

        f.write("%s,%s,%f,%s" % (rec_id1, rec_id2, w_sum, this_mid) + os.linesep)

        mid_count += 1

    f.close()


# -----------------------------------------------------------------------------


def SaveMatchDataSet(
    match_set,
    dataset1,
    id_field1,
    new_dataset_name1,
    dataset2=None,
    id_field2=None,
    new_dataset_name2=None,
):
    """Save the original data set(s) with an additional field (attribute) that
       contains match identifiers.

       This functions creates unique match identifiers (one for each matched pair
       of record identifiers in the given match set), and inserts them into a new
       attribute (field) of a data set(s) which will be written.

       If the record identifier field is not one of the fields in the input data
       set, then additionally such a field will be added to the output data set
       (with the name of the record identifier from the input data set).

       Currently the output data set(s) to be written will be CSV type data sets.

       Match identifiers as or the form 'mid00001', 'mid0002', etc. with the
       number of digits depending upon the total number of matches in the match
       set. If a record is involved in several matches, then the match
       identifiers will be separated by a semi-colon (;).

       Only one new data set will be created for deduplication, and two new data
       sets for linkage.

       For a deduplication, it is assumed that the second data set is set to
       None.
    """

    auxiliary.check_is_set("match_set", match_set)
    auxiliary.check_is_not_none("dataset1", dataset1)
    auxiliary.check_is_string("id_field1", id_field1)
    auxiliary.check_is_string("new_dataset_name1", new_dataset_name1)

    if dataset2 != None:  # A linkage, check second set of parameters
        auxiliary.check_is_not_none("dataset2", dataset2)
        auxiliary.check_is_string("id_field2", id_field2)
        auxiliary.check_is_string("new_dataset_name2", new_dataset_name2)
        do_link = True
    else:
        do_link = False

    match_rec_id_list = list(match_set)  # Make a list so it can be sorted
    match_rec_id_list.sort()

    if len(match_set) > 0:
        num_digit = max(1, int(math.ceil(math.log(len(match_set), 10))))
    else:
        num_digit = 1
    mid_count = 1  # Counter for match identifiers

    # Generate a dictionary with record identifiers as keys and lists of match
    # identifiers as values
    #
    match_id_dict1 = {}  # For first data set
    match_id_dict2 = {}  # For second data set, not required for deduplication

    for rec_id_tuple in match_rec_id_list:
        rec_id1, rec_id2 = rec_id_tuple

        mid_count_str = "%s" % (mid_count)
        this_mid = "mid%s" % (mid_count_str.zfill(num_digit))

        rec_id1_mid_list = match_id_dict1.get(rec_id1, [])
        rec_id1_mid_list.append(this_mid)
        match_id_dict1[rec_id1] = rec_id1_mid_list

        if do_link == True:  # Do the same for second data set
            rec_id2_mid_list = match_id_dict2.get(rec_id2, [])
            rec_id2_mid_list.append(this_mid)
            match_id_dict2[rec_id2] = rec_id2_mid_list

        else:  # Same dicionary for deduplication
            rec_id2_mid_list = match_id_dict1.get(rec_id2, [])
            rec_id2_mid_list.append(this_mid)
            match_id_dict1[rec_id2] = rec_id2_mid_list

        mid_count += 1

    # Now initialise new data set(s) for output based on input data set(s) - - -

    # First need to generate field list from input data set
    #
    if dataset1.dataset_type == "CSV":
        new_dataset1_field_list = dataset1.field_list[:]  # Make a copy of list
        last_col_index = new_dataset1_field_list[-1][1] + 1

    elif dataset1.dataset_type == "COL":
        new_dataset1_field_list = []
        col_index = 0
        for (field, col_width) in dataset1.field_list:
            new_dataset1_field_list.append((field, col_index))
            col_index += 1
        last_col_index = col_index

    # Check if the record identifier is not a normal input field (in which case
    # it has to be written into the output data set as well)
    #
    rec_ident_name = dataset1.rec_ident

    add_rec_ident = True
    for (field_name, field_data) in dataset1.field_list:
        if field_name == rec_ident_name:
            add_rec_ident = False
            break

    if add_rec_ident == True:  # Put record identifier into first column
        new_dataset1_field_list.append((rec_ident_name, last_col_index))
        last_col_index += 1

    # Append match id field
    #
    new_dataset1_field_list.append((id_field1, last_col_index))

    new_dataset1_description = dataset1.description + " with match identifiers"

    new_dataset1 = dataset.DataSetCSV(
        description=new_dataset1_description,
        access_mode="write",
        rec_ident=dataset1.rec_ident,
        header_line=True,
        write_header=True,
        strip_fields=dataset1.strip_fields,
        miss_val=dataset1.miss_val,
        field_list=new_dataset1_field_list,
        delimiter=dataset1.delimiter,
        file_name=new_dataset_name1,
    )

    # Read all records, add match identifiers and write into new data set
    #
    for (rec_id, rec_list) in dataset1.readall():
        if add_rec_ident == True:  # Add record identifier
            rec_list.append(rec_id)

        mid_list = match_id_dict1.get(rec_id, [])
        mid_str = ";".join(mid_list)
        rec_list.append(mid_str)
        new_dataset1.write({rec_id: rec_list})

    new_dataset1.finalise()

    if do_link == True:  # Second data set for linkage only - - - - - - - - - -

        if dataset2.dataset_type == "CSV":
            new_dataset2_field_list = dataset2.field_list[:]  # Make a copy of list
            last_col_index = new_dataset2_field_list[-1][1] + 1

        elif dataset2.dataset_type == "COL":
            new_dataset2_field_list = []
            col_index = 0
            for (field, col_width) in dataset2.field_list:
                new_dataset2_field_list.append((field, col_index))
                col_index += 1
            last_col_index = col_index

        # Check if the record identifier is not an normal input field (in which
        # case it has to be written into the output data set as well)
        #
        rec_ident_name = dataset2.rec_ident

        add_rec_ident = True
        for (field_name, field_data) in dataset2.field_list:
            if field_name == rec_ident_name:
                add_rec_ident = False
                break

        if add_rec_ident == True:  # Put record identifier into first column
            new_dataset2_field_list.append((rec_ident_name, last_col_index))
            last_col_index += 1

        # Append match id field
        #
        new_dataset2_field_list.append((id_field2, last_col_index))

        new_dataset2_description = dataset2.description + " with match identifiers"

        new_dataset2 = dataset.DataSetCSV(
            description=new_dataset2_description,
            access_mode="write",
            rec_ident=dataset2.rec_ident,
            header_line=True,
            write_header=True,
            strip_fields=dataset2.strip_fields,
            miss_val=dataset2.miss_val,
            field_list=new_dataset2_field_list,
            file_name=new_dataset_name2,
        )

        # Read all records, add match identifiers and write into new data set
        #
        for (rec_id, rec_list) in dataset2.readall():

            if add_rec_ident == True:  # Add record identifier
                rec_list.append(rec_id)

            mid_list = match_id_dict2.get(rec_id, [])
            mid_str = ";".join(mid_list)
            rec_list.append(mid_str)
            new_dataset2.write({rec_id: rec_list})

        new_dataset2.finalise()


# =============================================================================


def LoadWeightVectorFile(file_name):
    """Function to load a weight vector dictionary from a file, assumed to be of
       type CSV (comma separated values), with the first line being a header line
       containing the field comparison names.

       Such files were normally written withhin the run() method of index
       implementations, see the Febrl module indexing.py.

       The first two columns in each line are assumed to be the two record
       identifiers which (together as a tuple) will become the keys in the weight
       vector dictionary that is returned.

       The function first checks if a gzipped version of the file is available
       (with file ending '.gz' or '.GZ').

       This function returns a list with the field comparison names and a weight
       vector dictionary.
    """

    auxiliary.check_is_string("file_name", file_name)

    if file_name[-3:] not in [".gz", ".GZ"]:  # Check for gzipped versions
        if os.access(file_name + ".gz", os.F_OK) == True:
            file_name = file_name + ".gz"
        elif os.access(file_name + ".GZ", os.F_OK) == True:
            file_name = file_name + ".GZ"

    if (file_name.endswith(".gz")) or (file_name.endswith(".GZ")):
        try:
            in_file = gzip.open(file_name)  # Open gzipped file
        except:
            logging.exception(
                'Cannot open gzipped CSV file "%s" for reading' % (file_name)
            )
            raise IOError

    else:  # Open normal file for reading
        try:  # Try to open the file in read mode
            in_file = open(file_name)
        except:
            logging.exception('Cannot open CSV file "%s" for reading' % (file_name))
            raise IOError

    # Initialise the CSV parser - - - - - - - - - - - - - - - - - - - - - - -
    #
    csv_parser = csv.reader(in_file)

    header_line = next(csv_parser)  # Read header line

    # Generate field names list
    #
    field_names_list = header_line[2:]  # Remove record identifier names

    weight_vec_dict = {}  # Fill weight vector dictionary with data from file

    for line in csv_parser:
        rec_id_tuple = (line[0], line[1])

        if rec_id_tuple in weight_vec_dict:  # Check for unique record ids
            logging.warn(
                "Record identifier tuple %s already in weight vector "
                % (str(rec_id_tuple))
                + "dictionary"
            )

        w_vec = []

        for w in line[2:]:
            w_vec.append(float(w))

        weight_vec_dict[rec_id_tuple] = w_vec

    in_file.close()

    return [field_names_list, weight_vec_dict]


# =============================================================================
