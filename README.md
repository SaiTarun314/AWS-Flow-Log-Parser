# AWS-Flow-Log-Parser

## Description

This application parses files containing AWS Flow Log Data and maps each row to a single or multiple tags based on a user defined lookup table. The lookup table is a CSV file with 3 columns - dstport(Destination Port), Protocol and Tag. 

The output file consists of 2 parts:
1. Count of matches for each tag

2. Count of matches for each port/protocol combination 

## Assumptions

1. **AWS Log Version**  - We assume that the version of the Flow Logs is fixed and set to be **2**.

2. **Flow Log Format** - The program currently accepts a log record as valid if it has 14 fields. Any missing fields or wrong data will be skipped during processing.

3. **Output for Port/Protocol Combination** - We have assumed that the output of the port/protocol combination is to be recorded whose entry was present in the lookup table and no other combination. 

4. **Supported Protocols** - We are using all the IP Protocol definitions which version 2 of AWS Flow Logs support. We achieve this by loading the data from **protocol.csv** file which is downloaded from iana.org 

5. **Case Insensitive** - All the protocols loaded from the iana IP dataset and the lookup table have formatted to **lower case** in order to avoid skipping data points. 

6. **File Sizes** - The Flow logs files have been assumed to be of **maximum size 10 MB**. Although, the application has been tested on **800K flow log entires** equivalent to **100MB** of data with a running time of about 1 second.

## Running the application

### Prerequisites

- Python 3.x is installed on your system.
- No additional external libraries are required, only built-in Python libraries like `csv`, `os`, `concurrent`, `argparse`, `typing`, `logging`, and `collections`.


1. **Setup on Local**:

- Clone or download the project with git.
```
git clone https://github.com/SaiTarun314/AWS-Flow-Log-Parser.git
```
2. **Input Files**

- Create/Place your AWS Flow Log files/files in /data or any other folder (Use flow_log_1.txt as sample input)
- Create/Place your lookup.csv file in /data or any other folder(Use lookup.csv as sample input)

3. **Run the application with arguments**

- Navigate to the `src/` directory and run the `parser.py` file:

```
python3 parser.py --lookup ../data/lookup.csv --logs ../data/flow_log_1.txt ../data/flow_log_2.txt --output ../output/
```

4. **Output**
- After the parser application runs succesfully, the output will be written to a file in the output location provided in as an argument to run the application.
- The output file will contain two sections:
    1. **Tag Counts**
    2. **Port/Protocol Combination Counts(Tagged only)**

### Sample Output
```
Tag Counts
Tag,Count
Untagged,8
sv_P2,1
sv_P1,2
email,3

Tagged Port/Protocol Combination Counts
Port,Protocol,Count
443,tcp,1
23,tcp,1
25,tcp,1
110,tcp,1
993,tcp,1
143,tcp,1
```
## Testing

To ensure the correctness of the flow log processor, a suite of unit tests has been implemented using the `unittest` framework. These tests validate the core functionalities of the script, including:

- **Loading Protocol Mappings:** Ensures that protocol mappings from the CSV file are correctly read and stored.
- **Parsing Lookup Table:** Confirms that the lookup table is properly loaded and validated.
- **Processing Flow Log Entries:** Checks that valid entries are parsed correctly and handles malformed or unsupported entries properly.
- **Handling Edge Cases:** Includes tests for scenarios such as unsupported versions, missing protocols, and log statuses (`NODATA`, `SKIPDATA`).
- **Generating Output Files:** Verifies that processed data is correctly written to an output CSV file.

### Running the Tests
To execute the tests, run the following command in the project directory:

```sh
python -m unittest discover
```

This will automatically discover and run all test cases in the `tests` directory or within the script.

## Parallel Processing
The program supports parallel processing using the ThreadPoolExecutor to speed up processing of multiple flow log files. By default, it uses 4 worker threads, but this can be adjusted if needed.

