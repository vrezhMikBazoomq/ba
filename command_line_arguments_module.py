#######################################################################
#                                                              		  #
#    command_line_arguments_module.py                                 #
#                                                   				  #
#    By: Vrezh Mikayelyan             				                  #
#                                                				      #
#    Created: 17/01/2024    			   			                  #
#                                                                     #
#######################################################################

from datetime import datetime
import os
import argparse

class CommandLineArgs:
    '''
        @desc:
            Creates an object for arguments. 

        @args:
            id (int): NORAD ID from satnogs (https://db.satnogs.org/satellite/FNGO-2772-5931-1779-2835)
            start_date (str): The start since where to download data. Format: YYYY-MM-DDTHH:MM:SS
            end_date (str): The end date when to stop. Format: YYYY-MM-DDTHH:MM:SS
            working_dir (str): The directory where to store all data
            demod (str): Prefix of the directory where demoddata is stored
            hexpath (str): Folder name where to keep all hex data

        @methods:
            __init__(self, id, start_date, end_date):
                @desc:
                    Initializes a new CommandLineArgs instance.

            def parse_arguments():
                @desc
                    Parse command-line arguments.
            
            def get_args(): 
                @desc  
                    Creates new CommandLineArgs istance.
    '''

    def __init__ (self, id, start_date, end_date, demod, hexpath, csv, txt):
        '''
        @args:
            id (int): NORAD ID from satnogs (https://db.satnogs.org/satellite/FNGO-2772-5931-1779-2835)
            start_date (str): The start since where to download data. Format: YYYY-MM-DDTHH:MM:SS
            end_date (str): The end date when to stop. Format: YYYY-MM-DDTHH:MM:SS
            working_dir (str): The directory where to store all data
        '''
        self.id = id
        self.start_date = datetime.fromisoformat(start_date)
        self.end_date = datetime.fromisoformat(end_date)
        self.working_dir = os.path.dirname(__file__)
        self.demod = demod
        self.hexpath = hexpath
        self.csv = csv
        self.txt = txt

    def parse_arguments():
        '''
        @return:
            Object:
                object.start(datetime)
                object.end(datetime)
        '''
        parser = argparse.ArgumentParser(description="All arguments to download the data")
        parser.add_argument("-start", type = str, help="Start date of the observation")
        parser.add_argument("-end", type = str, help="End date of the observation")
        parser.add_argument("-demod", type = str, help="Dir name where binary files are stored")
        parser.add_argument("-hexpath", type = str, help="Dir name where to keep hexes")
        parser.add_argument("-csv", type = str, help="Dir name where to keep hexes")
        parser.add_argument("-txt", type = str, help="Dir name where to keep hexes")
        args = parser.parse_args()

        if not args.start:
            args.start = '1900-01-01T00:00:00'
        if not args.end:
            args.end = '1900-01-01T00:00:00'
        if not args.demod:
            args.demod = ''
        if not args.hexpath:
            args.hexpath = ''
        if not args.csv:
            args.csv = ''
        if not args.txt:
            args.txt = ''

        return args
    
    def get_args():
        '''
            @return:
                Creates and returns new Args instance.
        '''
        args = CommandLineArgs.parse_arguments()
        return CommandLineArgs(58471, args.start, args.end, args.demod, args.hexpath, args.csv, args.txt)
    

        
