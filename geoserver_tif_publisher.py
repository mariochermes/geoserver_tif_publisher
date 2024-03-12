import os
import re
import sys
import json
import requests

class GeoServerClient():
    def __init__(self, config):
        self.config = config

    # Use base authenticatication  to perform any request in the GeoServer REST
    def authenticate(self):
        return requests.auth.HTTPBasicAuth(self.username, self.password)
    
    # Function to send a POST request to GeoServer
    def send_post_request(self, url, json_data):
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, auth=self.authenticate(), headers=headers, json=json_data)
        return response

    # Function to send a PUT request to GeoServer
    def send_put_request(self, url, json_data):
        headers = {"Content-Type": "application/json"}
        response = requests.put(url, auth=self.authenticate(), headers=headers, json=json_data)
        return response
    
    # Function to create a coverage store
def create_coverage_store(self, workspace, coverage_store, file_path):
    url = f"{self.base_url}workspaces/{self.workspace}/coveragestores"
    
    file_path = file_path.replace("\\", "/").replace("/./mapbiomas/", "/data/mapbiomas/mapbiomas/")
    
    # Prepare the request body
    request_data = {
        "coverageStore": {
            "name": coverage_store,
            "description":coverage_store,
            "type": "GeoTIFF",
            "workspace": self.workspace,
            "enabled": True,
            "url": file_path
        }
    }

    response = self.send_post_request(url, request_data)
    
    if response.status_code == 201:
        print(f"Coverage store '{coverage_store}' created successfully.")
    else:
        print(f"Failed to create coverage store '{coverage_store}'.")
        print(response.text)

# Function to publish a layer from a coverage store
def publish_layer(self, workspace, coverage_store, coverage_name):
    url = f"{self.base_url}workspaces/{self.workspace}/coveragestores/{coverage_store}/coverages"
    
    # Prepare the request body
    request_data = {
        "coverage": {
            "defaultInterpolationMethod": "nearest neighbor",
            "description": f"{coverage_name} layer",
            "enabled": True,
            "interpolationMethods": {
                "string": [
                    "nearest neighbor",
                    "bilinear",
                    "bicubic"
                ]
            },
            "keywords": {
                "string": [
                    coverage_store,
                    "WCS",
                    "GeoTIFF",
                    "type\\@language=fr\\;\\@vocabulary=test\\;"
                ]
            },
            "name": coverage_name,
            "namespace": {
                "href": f"{self.base_url}/workspaces/SIGALERTA/coveragestores/{coverage_store}/{coverage_name}",
                "name": coverage_name
            },
            "requestSRS": {
                "string": [
                    "EPSG:4326"
                ]
            },
            "responseSRS": {
                "string": [
                    "EPSG:4326"
                ]
            },
            "srs": "EPSG:4326",
            "store": {
                "@class": "coverageStore",
                "href": f"{self.base_url}/workspaces/SIGALERTA/coveragestores/{coverage_store}.json",
                "name": f"{workspace}:{coverage_store}"
            },
            "title": coverage_name
        }
    }

    response = self.send_post_request(url, request_data)
    
    if response.status_code == 201:
        print(f"Layer '{coverage_name}' published successfully.")
    else:
        print(f"Failed to publish layer '{coverage_name}'.")
        print(response.text)
        
def add_default_style(self, workspace, coverage_name, style):
    url = f"{self.base_url}layers/{workspace}:{coverage_name}"
    
    request_data = {
        "layer": {
            "name": coverage_name,
            "defaultStyle": {
                "name": f"{workspace}:{style}"
            }
        }
    }
    
    response = self.send_put_request(url, request_data)
    
    if response.status_code == 200:
        print(f"Default style {style} set succesfully")
    else:
        print(f"Failed to set the default style: '{style}'.")
        print(response.text)

class PublishManager():    
    def __init__(self, client):
        self.client = client

    def publish_single_layer(self, tiff_file_path):
        coverage_store = os.path.splitext(os.path.basename(tiff_file_path))[0].lower()
        layer_name = coverage_store.replace("_tiled", "")

        self.client.create_coverage_store(coverage_store, f"file:./data/{tiff_file_path}")
        # Publish layer
        self.client.publish_layer(self.client.config["workspace_name"], f"{coverage_store}", f"{layer_name}")
        # Add the default style for the layer
        self.client.add_default_style(self.client.config["workspace_name"], f"{layer_name}", "mapbiomas_legend")

    def publish_multiple_layers(self, base_directory):
        for root, dirs, files in os.walk(base_directory):
            for file in files:
                if file.endswith(".tif"):
                    tiff_file_path = os.path.join(root, file)
                    self.publish_single_layer(tiff_file_path)

    def publish_filtered_layers(self, base_directory, regex):
        pattern = re.compile(regex)
        for root, dirs, files in os.walk(base_directory):
            for file in files:
                if file.endswith(".tif") and pattern.search(file):
                    tiff_file_path = os.path.join(root, file)
                    self.publish_single_layer(tiff_file_path)
                
def load_config_from_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def main(config_file, *args):
    config = load_config_from_file(config_file)
    client = GeoServerClient(config)
    publisher = PublishManager(client)

    if "single_layer" in args:
        layer_path = args[args.index("single_layer") + 1]
        publisher.publish_single_layer(client, layer_path)
    elif "multiple_layers" in args:
        base_directory = args[args.index("multiple_layers") + 1]
        publisher.publish_multiple_layers(client, base_directory)
    elif "filtered_layers" in args:
        base_directory = args[args.index("filtered_layers") + 1]
        regex = args[args.index("filtered_layers") + 2]
        publisher.publish_filtered_layers(client, base_directory, regex)
    else:
        print("Invalid option. Use one of the following:")
        print(" - single_layer <layer_path>")
        print(" - multiple_layers <base_directory>")
        print(" - filtered_layers <base_directory> <regex>")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <config_file> <option> <args>")
        sys.exit(1)

    config_file = sys.argv[1]
    option = sys.argv[2]
    args = sys.argv[3:]

    main(config_file, option, *args)