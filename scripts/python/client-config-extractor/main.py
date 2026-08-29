#!/usr/bin/env python3
from network.fetcher.resource_fetcher import ResourceFetcher
from extractor.config_extractor import ClientConfigExtractor
from parser.client_config_parser import ClientConfigParser


def main():
    resource_fetcher = ResourceFetcher()
    resource_fetcher.process_regions()

    client_config_extractor = ClientConfigExtractor()
    client_config_extractor.process_regions()

    client_config_parser = ClientConfigParser()
    client_config_parser.process_regions()


if __name__ == "__main__":
    main()
