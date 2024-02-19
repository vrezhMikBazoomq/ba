import os
import csv
import re
import pandas as pd
from command_line_arguments_module import CommandLineArgs

'''
    @desc:
        Extracts all data from the beacon data to csv file.

    @methods:
        def extract_time_from_passage(passage):
            @desc:
                Extracts the time information from a given data passage.

        def extract_struct_data_from_passage(passage):
            @desc:
                Extracts structured data from a given data passage started with "Name: <datacache.dc_parser.struct_..." .

        def process_file(file_path):
            @desc:
                Processes a text file, extracting date-time and data from multiple passages.

        def process_data(directory_path):
            @desc:
                Processes all text files in a directory, extracting and formatting data.

        def write_data_to_csv(csv_rows, filename):
            @desc:
                Writes data to a CSV file, ensuring proper header and sorting by date.

        def get_directory_path(prefix):     
            @desc:
                Retrieves directories in the current working directory with a specified prefix.
 
'''

def extract_time_from_passage(passage):
    '''
        @args: 
            passage(str): Each data passage.
        @return:
            String of cleaned time.
    '''
    time_match = re.search(r'(\d+:\d+:\d+\.\d+)', passage)
    return time_match.group(1) if time_match else None

def extract_struct_data_from_passage(passage):
    '''
        @args:
            passage (str): Each data passage.
        @return:
            list: List of dictionaries containing structured data.
    '''

    struct_matches = re.finditer(
        r'Name: <datacache\.dc_parser\.struct_(.*?) object at .*?>\n(.*?)(?=\n\n|\Z)', passage, re.DOTALL)
    result_list = []

    for match in struct_matches:
        struct_name = match.group(1).strip()
        struct_data = match.group(2)
        attributes = re.findall(
            r'(\w+)\s*:\s*([\s\S]+?)(?=\n|$)', struct_data)
        struct_dict = {"Name": struct_name}
        for attr, value in attributes:
            try:
                struct_dict[attr] = str(value)
            except ValueError:
                struct_dict[attr] = str(value)

        result_list.append(struct_dict)
    return result_list

def process_file(file_path):
    '''
        @args:
            file_path (str): Path to the text file.
        @return:
            list: List of tuples containing date-time and extracted data.
    '''
    with open(file_path, 'r') as f:
        date_time = file_path.split('\\')[-1].split("_")[0]
        data = f.read()
        chunks = data.split('-------------------------------------------------------------------')
        chunks = [chunk.strip() for chunk in chunks]
        full_list = []

        for i in chunks:
            passages = re.split(r'\n\s*\n', i)
            result_list = []
            for passage in passages:
                time = extract_time_from_passage(passage)
                if time:
                    result_list.append(time)
                struct_data_list = extract_struct_data_from_passage(passage)
                result_list.extend(struct_data_list)
            full_list.append((date_time, result_list))
    return full_list

def process_data(directory_path):
    '''
        @args:
            directory_path (str): Path to the directory containing text files.
        @return:
            list: List of dictionaries containing processed data.
    '''
    csv_rows = []
    filename = directory_path
    full_list = process_file(filename)
    for date_time, sublist in full_list:
        if sublist:
            date = date_time + ' ' + sublist[0]
            for data_dict in sublist[1:]:
                if isinstance(data_dict, str):
                    continue
                row_dict = {'date': date, 'Name': data_dict['Name']}
                for key, value in data_dict.items():
                    if key != 'Name':
                        row_dict[key] = str(value)
                    csv_rows.append(row_dict)

    return csv_rows
            


def write_data_to_csv(csv_rows, filename):
    '''
        @args:
            csv_rows (list): List of dictionaries containing data.
            filename (str): Name of the CSV file to be written.
    '''
    csv_header = ['date', 'Name'] + list(set(key for row_dict in csv_rows for key in row_dict if key != 'Name'))
    csv_file_exists = os.path.exists(filename)

    with open(filename, 'w', newline='') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=csv_header)
        if not csv_file_exists or os.path.getsize(filename) == 0:
            csv_writer.writeheader()
        if csv_rows:
            csv_writer.writerows(csv_rows)
   
if __name__ == "__main__":
    args = CommandLineArgs.get_args()
    text_data = args.txt
    csv_rows = process_data(text_data)
    text_data = text_data.split('\\')[:-1]
    text_data = "\\".join(text_data)
    text_data+= '\\'
    write_data_to_csv(csv_rows, text_data+args.csv+'.csv')
