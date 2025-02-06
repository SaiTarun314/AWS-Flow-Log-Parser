import csv
import logging
import os
from collections import defaultdict
import argparse
from typing import Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging settings
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

EXPECTED_HEADERS = ["dstport", "protocol", "tag"]
PROTOCOL_MAPPING = {}

def load_protocol_mapping(protocol_file: str):
    """Loads the protocol mapping from a CSV file."""
    global PROTOCOL_MAPPING
    PROTOCOL_MAPPING.clear()
    
    try:
        with open(protocol_file, "r") as file:
            reader = csv.DictReader(file)
            required_headers = {"Decimal", "Keyword"}
            
            if not required_headers.issubset(reader.fieldnames or {}):
                raise ValueError(f"Invalid headers in {protocol_file}. Expected: {required_headers}")
            
            for row in reader:
                decimal = row["Decimal"].strip()
                keyword = row["Keyword"].strip().lower()
                if decimal.isdigit():
                    PROTOCOL_MAPPING[decimal] = keyword
                else:
                    logging.warning(f"Skipping invalid entry: {row}")
            
            if not PROTOCOL_MAPPING:
                raise ValueError("No valid protocol mappings found.")
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error loading protocol mapping: {e}")
        raise

def get_protocol_map() -> Dict[str, str] :
    """Returns the value of the Protocol Map"""
    return PROTOCOL_MAPPING
    
def parse_lookup_table(lookup_file: str) -> Dict[Tuple[str, str], str]:
    """Parses lookup table from a CSV file."""
    lookup = {}
    try:
        with open(lookup_file, "r") as file:
            reader = csv.DictReader(file)
            
            if reader.fieldnames != EXPECTED_HEADERS:
                raise ValueError(f"Invalid headers in {lookup_file}. Expected: {EXPECTED_HEADERS}")
            
            for row in reader:
                lookup[(row["dstport"], row["protocol"].lower())] = row["tag"]
            
            if not lookup:
                raise ValueError("Lookup table is empty.")
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error parsing lookup table: {e}")
        raise
    
    return lookup

def process_flow_log_line(line: str, lookup_table: Dict[Tuple[str, str], str]) -> Tuple[str, Tuple[str, str]]:
    """Processes a single line from the flow log."""
    parts = line.strip().split()
    if len(parts) != 14:
        logging.warning(f"Malformed line skipped: {line.strip()}")
        return None, None

    dstport, protocol_num, version, status = parts[6], parts[7], parts[0], parts[-1]
    protocol = PROTOCOL_MAPPING.get(protocol_num)

    if version != "2":
        logging.warning(f"Skipping unsupported version {version}: {line.strip()}")
        return None, None
    
    # Skipping when log-status field in flow logs is set to NODATA or SKIPDATA according to AWS Guides
    if status in {"NODATA", "SKIPDATA"}:
        logging.info(f"Skipping line with status {status}: {line.strip()}")
        return None, None
    
    if not protocol:
        logging.warning(f"Unknown protocol {protocol_num} in line: {line.strip()}")
        return None, None
    
    tag = lookup_table.get((dstport, protocol), "Untagged")
    return (tag, None) if tag == "Untagged" else (tag, (dstport, protocol))

def parse_flow_logs(flow_log_file: str, lookup_table: Dict[Tuple[str, str], str]) -> Tuple[Dict[str, int], Dict[Tuple[str, str], int]]:
    """Parses a flow log file and counts occurrences of tags and port/protocol pairs."""
    tag_count, port_protocol_count = defaultdict(int), defaultdict(int)
    
    try:
        with open(flow_log_file, "r") as file:
            for line in file:
                tag, port_protocol = process_flow_log_line(line, lookup_table)
                if tag:
                    tag_count[tag] += 1
                if port_protocol:
                    port_protocol_count[port_protocol] += 1
            
            if not tag_count:
                raise ValueError("No valid flow log entries found.")
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Error parsing flow log: {e}")
        raise
    
    return tag_count, port_protocol_count

def write_output(tag_count: Dict[str, int], port_protocol_count: Dict[Tuple[str, str], int], output_file: str):
    """Writes tag and port/protocol counts to an output CSV file."""
    try:
        with open(output_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Tag Counts"])
            writer.writerow(["Tag", "Count"])
            writer.writerows(tag_count.items())
            
            if port_protocol_count:
                writer.writerow([])
                writer.writerow(["Tagged Port/Protocol Combination Counts"])
                writer.writerow(["Port", "Protocol", "Count"])
                writer.writerows([(port, protocol, count) for (port, protocol), count in port_protocol_count.items()])
    except Exception as e:
        logging.error(f"Failed to write output file: {e}")
        raise

def process_single_file(flow_log_file: str, lookup_table: Dict[Tuple[str, str], str], output_dir: str):
    """Processes a single flow log file and writes output."""
    logging.info(f"Processing {flow_log_file}...")
    try:
        tag_count, port_protocol_count = parse_flow_logs(flow_log_file, lookup_table)
        output_file = os.path.join(output_dir, f"{os.path.basename(flow_log_file)}_output.csv")
        write_output(tag_count, port_protocol_count, output_file)
        logging.info(f"Completed: {flow_log_file}. Output: {output_file}")
    except Exception as e:
        logging.error(f"Error processing {flow_log_file}: {e}")

def process_multiple_files(flow_log_files: List[str], lookup_file: str, output_dir: str, max_workers: int = 4):
    """Processes multiple flow log files in parallel."""
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        lookup_table = parse_lookup_table(lookup_file)
    except Exception as e:
        logging.error(f"Lookup table parsing failed: {e}")
        return
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_file, file, lookup_table, output_dir): file for file in flow_log_files}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error processing file: {e}")

def main():

    parser = argparse.ArgumentParser(description="Process flow log files.")
    parser.add_argument("--lookup", required=True, help="Path to the lookup CSV file.")
    parser.add_argument("--logs", nargs='+', required=True, help="List of flow log file paths.")
    parser.add_argument("--output", required=True, help="Directory for output CSV files.")
    
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    protocol_file = os.path.join(base_dir, "../data/protocol.csv")
    lookup_file = args.lookup
    output_dir = args.output
    
    load_protocol_mapping(protocol_file)
    flow_log_files = args.logs
    
    if not flow_log_files:
        logging.error("No flow log files found.")
        return
    
    process_multiple_files(flow_log_files, lookup_file, output_dir)

if __name__ == "__main__":
    main()
