import unittest
from unittest.mock import patch, mock_open
from collections import defaultdict
from src.parser import (
    load_protocol_mapping,
    parse_lookup_table,
    process_flow_log_line,
    parse_flow_logs,
    write_output,
    get_protocol_map
)
import csv
import os

PROTOCOL_MAPPING = {}

class TestParser(unittest.TestCase):
    
    @patch("builtins.open", new_callable=mock_open, read_data="Decimal,Keyword\n6,TCP\n17,UDP\n")
    def test_load_protocol_mapping(self, mock_file):
        load_protocol_mapping("protocol.csv")
        print(get_protocol_map())
        self.failureException(get_protocol_map(), {"6": "tcp", "17": "udp"})
    
    @patch("builtins.open", new_callable=mock_open, read_data="dstport,protocol,tag\n80,tcp,web\n443,tcp,secure\n")
    def test_parse_lookup_table(self, mock_file):
        lookup = parse_lookup_table("lookup.csv")
        expected_lookup = {("80", "tcp"): "web", ("443", "tcp"): "secure"}
        self.assertEqual(lookup, expected_lookup)
    
    def test_process_flow_log_line_valid(self):
        lookup_table = {("80", "tcp"): "web"}
        global PROTOCOL_MAPPING
        PROTOCOL_MAPPING = {"6": "tcp"}
        
        line = "2 1234 5678 91011 1213 1415 80 6 1617 1819 2021 2223 2425 OK"
        tag, port_protocol = process_flow_log_line(line, lookup_table)
        self.assertEqual(tag, "web")
        self.assertEqual(port_protocol, ("80", "tcp"))
    
    def test_process_flow_log_line_invalid_version(self):
        lookup_table = {}
        line = "1 1234 5678 91011 1213 1415 80 6 1617 1819 2021 2223 2425 OK"
        tag, port_protocol = process_flow_log_line(line, lookup_table)
        self.assertIsNone(tag)
        self.assertIsNone(port_protocol)
    
    def test_process_flow_log_line_nodata(self):
        lookup_table = {}
        line = "2 1234 5678 91011 1213 1415 80 6 1617 1819 2021 2223 2425 NODATA"
        tag, port_protocol = process_flow_log_line(line, lookup_table)
        self.assertIsNone(tag)
        self.assertIsNone(port_protocol)
    
    @patch("builtins.open", new_callable=mock_open, read_data="2 1234 5678 91011 1213 1415 80 6 1617 1819 2021 2223 2425 OK\n")
    def test_parse_flow_logs(self, mock_file):
        lookup_table = {("80", "tcp"): "web"}
        global PROTOCOL_MAPPING
        PROTOCOL_MAPPING = {"6": "tcp"}
        
        tag_count, port_protocol_count = parse_flow_logs("flow_log.txt", lookup_table)
        self.assertEqual(tag_count["web"], 1)
        self.assertEqual(port_protocol_count[("80", "tcp")], 1)
    
    @patch("builtins.open", new_callable=mock_open)
    def test_write_output(self, mock_file):
        tag_count = {"web": 10}
        port_protocol_count = {("80", "tcp"): 5}
        output_file = "output.csv"
        
        write_output(tag_count, port_protocol_count, output_file)
        mock_file.assert_called_with(output_file, "w", newline="")
        
if __name__ == "__main__":
    unittest.main()
