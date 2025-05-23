import os
import json
from datetime import datetime, timedelta
import requests
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session

templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
static_dir = os.path.join(os.path.dirname(__file__), 'static')

if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
    os.makedirs(os.path.join(templates_dir, 'dashboard'))
    os.makedirs(os.path.join(templates_dir, 'node'))

if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    os.makedirs(os.path.join(static_dir, 'css'))
    os.makedirs(os.path.join(static_dir, 'js'))

app = Flask(__name__, 
           template_folder=templates_dir,
           static_folder=static_dir)
app.secret_key = 'mysterium-node-dashboard-secret-key'
NODES_FILE = 'nodes.json'

if not os.path.exists(NODES_FILE):
    with open(NODES_FILE, 'w') as f:
        json.dump([], f)

# Helper functions for node data
def get_nodes():
    try:
        with open(NODES_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_nodes(nodes):
    with open(NODES_FILE, 'w') as f:
        json.dump(nodes, f, default=str)

def get_node_by_id(node_id):
    nodes = get_nodes()
    for node in nodes:
        if node.get('id') == node_id:
            return node
    return None

# Add a helper function to check if a node name already exists
def node_name_exists(name):
    nodes = get_nodes()
    return any(node.get('name') == name for node in nodes)

def get_lowest_available_id(nodes):
    """Find the lowest available ID that can be used for a new node"""
    used_ids = set(node.get('id', 0) for node in nodes)
    id = 1
    while id in used_ids:
        id += 1
    return id

# Node API service
class NodeAPI:
    def __init__(self, ip, port, token=None):
        self.base_url = f"http://{ip}:{port}/tequilapi"
        self.token = token
        self.headers = {'Accept': 'application/json'}
        if token:
            self.headers['Authorization'] = f'Bearer {token}'
    
    # Authentication method to get token
    def authenticate(self, password):
        import requests
        url = f"{self.base_url}/auth/authenticate"
        data = {'username': 'myst', 'password': password}
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            token = response.json().get('token')
            self.token = token
            self.headers['Authorization'] = f'Bearer {token}'
            return token
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")
    
    # Health check method
    def health_check(self):
        import requests
        try:
            response = requests.get(f"{self.base_url}/healthcheck", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Health check failed: {str(e)}")
    
    # Session stats method
    def session_stats(self):
        import requests
        try:
            response = requests.get(f"{self.base_url}/sessions/stats-aggregated", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get session stats: {str(e)}")
    
    # Session stats daily method
    def session_stats_daily(self, query=None):
        import requests
        try:
            response = requests.get(f"{self.base_url}/sessions/stats-daily", headers=self.headers, params=query)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get daily session stats: {str(e)}")
    
    # Sessions list method
    def sessions(self, query=None):
        import requests
        try:
            response = requests.get(f"{self.base_url}/sessions", headers=self.headers, params=query)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get sessions: {str(e)}")
    
    # Identity list method
    def identity_list(self):
        import requests
        try:
            response = requests.get(f"{self.base_url}/identities", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get identities: {str(e)}")
    
    # Service list method
    def service_list(self):
        import requests
        try:
            response = requests.get(f"{self.base_url}/services", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get services: {str(e)}")
    
    # Start service method
    def start_service(self, request):
        import requests
        try:
            print(f"Starting service with request: {request}")
            # Send the complete request object to the API
            response = requests.post(
                f"{self.base_url}/services", 
                json=request, 
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Service start error details: {str(e)}")
            raise Exception(f"Failed to start service: {str(e)}")

    # Stop service method
    def stop_service(self, service_id):
        import requests
        try:
            response = requests.delete(f"{self.base_url}/services/{service_id}", headers=self.headers)
            response.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to stop service: {str(e)}")
    
    # Connection statistics method for active sessions
    def connection_statistics(self):
        import requests
        try:
            response = requests.get(f"{self.base_url}/connection/statistics", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get connection statistics: {str(e)}")
            # Return empty stats instead of raising error
            return {"bytesReceived": 0, "bytesSent": 0, "duration": 0, "tokensSpent": 0}
    
    # Get individual session data
    def session_by_id(self, session_id):
        import requests
        try:
            response = requests.get(f"{self.base_url}/sessions/{session_id}", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get session by ID: {str(e)}")
            return None
    
    # Add NAT detection method
    def nat_status(self):
        import requests
        try:
            nat_info = {}
            
            # Try the nat/type endpoint first since it seems more reliable
            try:
                response = requests.get(f"{self.base_url}/nat/type", headers=self.headers)
                if response.status_code == 200:
                    nat_type_info = response.json()
                    if nat_type_info:
                        print("NAT type obtained from /nat/type endpoint")
                        
                        # Use type information from this endpoint
                        if 'type' in nat_type_info:
                            nat_info['type'] = nat_type_info['type']
                        
                        # Add any other relevant fields
                        for key in ['status', 'error']:
                            if key in nat_type_info:
                                nat_info[key] = nat_type_info[key]
                else:
                    print(f"The /nat/type endpoint returned status code {response.status_code}")
            except Exception as e:
                print(f"Failed to get NAT type from nat/type endpoint: {str(e)}")
            
            # If we have NAT info, add a status if it's missing
            if nat_info and 'type' in nat_info and 'status' not in nat_info:
                nat_info['status'] = 'finished'  # Assume it's finished if we have a type
            
            # If we have any NAT info, return it
            if nat_info:
                return nat_info
                
            # As a fallback, try to determine NAT from proposal
            try:
                response = requests.get(f"{self.base_url}/proposals", headers=self.headers)
                response.raise_for_status()
                proposals = response.json()
                
                if proposals and len(proposals) > 0:
                    # NAT info can sometimes be found in the proposal
                    nat_type = proposals[0].get('nat_compatibility')
                    if nat_type:
                        print(f"NAT information extracted from proposals: {nat_type}")
                        return {
                            'type': nat_type,
                            'status': 'finished'
                        }
            except Exception as e:
                print(f"Failed to get NAT info from proposals: {str(e)}")
                
            # As another fallback, create a basic NAT status
            return {
                'type': 'unknown',
                'status': 'unavailable'
            }
        except Exception as e:
            print(f"All NAT detection methods failed: {str(e)}")
            return {
                'type': 'unknown',
                'status': 'error'
            }

    # Add monitoring status method
    def node_monitoring_status(self):
        import requests
        try:
            response = requests.get(f"{self.base_url}/node/monitoring-status", headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"The /node/monitoring-status endpoint returned status code {response.status_code}")
                return None
        except Exception as e:
            print(f"Failed to get node monitoring status: {str(e)}")
            return None

# Routes
@app.route('/')
def index():
    nodes = get_nodes()
    return render_template('dashboard/index.html', title='Dashboard', nodes=nodes)

@app.route('/add_node', methods=['GET', 'POST'])
def add_node():
    if request.method == 'POST':
        name = request.form.get('name')
        ip = request.form.get('ip')
        port = request.form.get('port', 4449)
        password = request.form.get('password')
        
        # Validate form data
        if not name or not ip:
            flash('Name and IP are required fields', 'danger')
            return redirect(url_for('index'))
        
        # Check if node name already exists
        if node_name_exists(name):
            flash(f'A node with the name "{name}" already exists. Please use a unique name.', 'danger')
            return redirect(url_for('index'))
        
        # Check connection and authenticate
        try:
            node_api = NodeAPI(ip, port)
            token = node_api.authenticate(password)
            
            nodes = get_nodes()
            new_node = {
                'id': get_lowest_available_id(nodes),  # Use lowest available ID
                'name': name,
                'ip': ip,
                'port': port,
                'token': token,
                'created_at': datetime.now().isoformat()
            }
            nodes.append(new_node)
            save_nodes(nodes)
            
            flash(f'Node {name} added successfully', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error connecting to node: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    return render_template('dashboard/add_node.html', title='Add Node')

@app.route('/node/<int:node_id>')
def node_details(node_id):
    node = get_node_by_id(node_id)
    if not node:
        flash('Node not found', 'danger')
        return redirect(url_for('index'))
    
    return render_template('node/details.html', title=f'Node: {node["name"]}', node=node)

@app.route('/node/<int:node_id>/data')
def node_data(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    
    try:
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        # Get node data
        health = node_api.health_check()
        stats = node_api.session_stats()
        stats_daily = node_api.session_stats_daily()
        services = node_api.service_list()
        identities = node_api.identity_list()
        
        # Get session data with increased limit (get more history for charts)
        # Default is 50, let's request as many as needed for 30+ days of data
        sessions = node_api.sessions({"page_size": 1000})
        
        # Get NAT status info
        nat_info = node_api.nat_status()
        print("\n=== NAT Status Info ===")
        if nat_info:
            print(f"Raw NAT status: {json.dumps(nat_info, indent=2)}")
        else:
            # If we don't have NAT info, create a placeholder
            print("NAT status unavailable, creating placeholder")
            nat_info = {
                'type': 'unknown',
                'status': 'unavailable'
            }
        print("=====================\n")
        
        # Get node monitoring status
        monitoring_status = node_api.node_monitoring_status()
        print("\n=== Node Monitoring Status ===")
        if monitoring_status:
            print(f"Monitoring status: {json.dumps(monitoring_status, indent=2)}")
        else:
            print("Node monitoring status unavailable")
            monitoring_status = {"status": "unknown"}
        print("==========================\n")
        
        # Fetch quality metrics from Mysterium discovery API if identities are available
        quality_metrics = None
        location_info = None
        if identities and 'identities' in identities and len(identities['identities']) > 0:
            provider_id = identities['identities'][0]['id']  # Use the first identity
            try:
                import requests
                print(f"Fetching quality metrics from discovery API for provider {provider_id}")
                discovery_url = f"https://discovery.mysterium.network/api/v4/proposals?access_policy=all&provider_id={provider_id}"
                discovery_response = requests.get(discovery_url, timeout=5)
                if discovery_response.status_code == 200:
                    discovery_data = discovery_response.json()
                    if discovery_data and len(discovery_data) > 0:
                        # Extract quality metrics and location from the first proposal
                        quality_metrics = discovery_data[0].get('quality', {})
                        location_info = discovery_data[0].get('location', {})
                        print(f"Found quality metrics for provider {provider_id}: {quality_metrics}")
                        print(f"Found location info for provider {provider_id}: {location_info}")
            except Exception as e:
                print(f"Error fetching discovery data: {str(e)}")
        
        # Debug: Log raw stats data to terminal
        print("\n=== Session Stats Data ===")
        print(f"Raw stats response: {json.dumps(stats, indent=2)}")
        if 'stats' in stats:
            print(f"Stats object keys: {list(stats['stats'].keys())}")
            for key, value in stats['stats'].items():
                print(f"  {key}: {value}")
        else:
            print("No 'stats' key in stats response")
        print("===========================\n")
        
        # Log only session count instead of detailed data
        if sessions and 'items' in sessions:
            print(f"\nSession count for node {node_id}: {len(sessions['items'])}")
        else:
            print(f"\nNo sessions data available for node {node_id}")
        
        return jsonify({
            'health': health,
            'stats': stats,
            'stats_daily': stats_daily,
            'services': services,
            'identities': identities,
            'sessions': sessions,
            'quality_metrics': quality_metrics,
            'location_info': location_info,
            'nat_info': nat_info,
            'monitoring_status': monitoring_status
        })
    except Exception as e:
        print(f"Error getting node data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/node/<int:node_id>/start_service', methods=['POST'])
def start_service(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    
    # Detailed request logging
    print(f"\n=== Service Start Request for Node {node_id} ===")
    print(f"Request Content-Type: {request.headers.get('Content-Type')}")
    print(f"Request method: {request.method}")
    
    try:
        # Parse request data
        if request.is_json:
            data = request.json
            print(f"Received JSON data: {data}")
        else:
            data = request.form.to_dict()
            print(f"Received form data: {data}")
        
        # Extract service type and provider ID
        service_type = data.get('type')
        provider_id = data.get('provider_id')
        
        print(f"Extracted: service_type={service_type}, provider_id={provider_id}")
        
        if not service_type:
            return jsonify({"error": "Service type is required"}), 400
        
        if not provider_id:
            print("No provider_id in request, getting from identities API")
            # Get identities to find a provider ID if not provided
            node_api = NodeAPI(node['ip'], node['port'], node['token'])
            identities = node_api.identity_list()
            
            if not identities or 'identities' not in identities or not identities['identities']:
                return jsonify({"error": "No identities found on node"}), 400
            
            provider_id = identities['identities'][0]['id']
            print(f"Using provider_id from identity: {provider_id}")
        
        # Create service request with exact format required by API
        service_request = {
            "provider_id": provider_id,
            "type": service_type
        }
        
        print(f"Final service request payload: {service_request}")
        
        # Initialize node API
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        # Add headers logging to NodeAPI
        node_api.headers['Content-Type'] = 'application/json'
        print(f"Request headers: {node_api.headers}")
        
        # Direct HTTP request with detailed logging
        import json
        url = f"{node_api.base_url}/services"
        print(f"Making POST request to: {url}")
        
        response = requests.post(
            url,
            headers=node_api.headers,
            data=json.dumps(service_request)
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        try:
            response_text = response.text
            print(f"Response text: {response_text}")
            response_json = response.json()
            print(f"Response JSON: {response_json}")
        except Exception as e:
            print(f"Could not parse response as JSON: {e}")
            response_json = None
        
        # Handle response appropriately
        if response.status_code == 200 or response.status_code == 201:
            # Success - return service data
            if response_json:
                return jsonify({"success": True, "service": response_json})
            else:
                return jsonify({"success": True})
        else:
            error_msg = response_json.get('error', {}).get('message') if response_json else response.text
            print(f"Error starting service: {error_msg}")
            return jsonify({"error": f"Failed to start service: {error_msg}"}), response.status_code
                 
    except Exception as e:
        print(f"Exception starting service: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/node/<int:node_id>/stop_service', methods=['POST'])
def stop_service(node_id):
    node = get_node_by_id(node_id)
    if not node:
        flash('Node not found', 'danger')
        return redirect(url_for('index'))
    
    service_id = request.form.get('service_id')
    
    try:
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        node_api.stop_service(service_id)
        flash('Service stopped successfully', 'success')
    except Exception as e:
        flash(f'Error stopping service: {str(e)}', 'danger')
    
    return redirect(url_for('node_details', node_id=node_id))

# Add new route to handle service creation via POST request to /services
@app.route('/node/<int:node_id>/services', methods=['POST'])
def create_service(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    
    # Detailed request logging
    print(f"\n=== Service Create Request for Node {node_id} ===")
    print(f"Request Content-Type: {request.headers.get('Content-Type')}")
    print(f"Request method: {request.method}")
    
    try:
        # Parse request data
        if request.is_json:
            data = request.json
            print(f"Received JSON data: {data}")
        else:
            data = request.form.to_dict()
            print(f"Received form data: {data}")
        
        # Extract service type and provider ID (different field names from JavaScript)
        service_type = data.get('service_type')
        provider_id = data.get('provider_id')
        
        print(f"Extracted: service_type={service_type}, provider_id={provider_id}")
        
        if not service_type:
            return jsonify({"error": "Service type is required"}), 400
        
        if not provider_id:
            print("No provider_id in request, getting from identities API")
            # Get identities to find a provider ID if not provided
            node_api = NodeAPI(node['ip'], node['port'], node['token'])
            identities = node_api.identity_list()
            
            if not identities or 'identities' not in identities or not identities['identities']:
                return jsonify({"error": "No identities found on node"}), 400
            
            provider_id = identities['identities'][0]['id']
            print(f"Using provider_id from identity: {provider_id}")
        
        # Create service request with exact format required by API
        service_request = {
            "provider_id": provider_id,
            "type": service_type  # Note: API expects "type", not "service_type"
        }
        
        print(f"Final service request payload: {service_request}")
        
        # Initialize node API
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        # Try to start the service
        result = node_api.start_service(service_request)
        return jsonify({"success": True, "service": result})
                 
    except Exception as e:
        print(f"Exception starting service: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/remove_node/<int:node_id>', methods=['POST'])
def remove_node(node_id):
    nodes = get_nodes()
    for i, node in enumerate(nodes):
        if node.get('id') == node_id:
            del nodes[i]
            save_nodes(nodes)
            flash(f'Node {node["name"]} removed successfully', 'success')
            break
    return redirect(url_for('index'))

# Global variable to cache CoinMarketCap data
cmc_cache = {
    'data': None,
    'last_updated': None
}

@app.route('/api/myst-price')
def myst_price():
    # Check if we have cached data that's less than 10 minutes old
    if cmc_cache['data'] and cmc_cache['last_updated'] and \
       datetime.now() - cmc_cache['last_updated'] < timedelta(minutes=10):
        return jsonify(cmc_cache['data'])
    
    # Fetch new data from CoinMarketCap
    api_key = request.args.get('api_key', '')
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    
    try:
        headers = {
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json'
        }
        
        response = requests.get(
            'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?slug=mysterium',
            headers=headers
        )
        
        if response.status_code != 200:
            return jsonify({"error": f"CoinMarketCap API error: {response.text}"}), response.status_code
        
        data = response.json()
        
        # Process the data to extract just what we need
        if 'data' in data and data['data']:
            coin_data = list(data['data'].values())[0]  # Get the first (and only) item
            processed_data = {
                'name': coin_data['name'],
                'symbol': coin_data['symbol'],
                'price': coin_data['quote']['USD']['price'],
                'percent_change_1h': coin_data['quote']['USD']['percent_change_1h'],
                'percent_change_24h': coin_data['quote']['USD']['percent_change_24h'],
                'percent_change_7d': coin_data['quote']['USD']['percent_change_7d'],
                'percent_change_30d': coin_data['quote']['USD']['percent_change_30d'],
                'volume_24h': coin_data['quote']['USD']['volume_24h'],
                'volume_change_24h': coin_data['quote']['USD']['volume_change_24h'],
                'market_cap': coin_data['quote']['USD']['market_cap'],
                'fully_diluted_market_cap': coin_data['quote']['USD']['fully_diluted_market_cap'],
                'max_supply': coin_data['max_supply'],
                'circulating_supply': coin_data['circulating_supply'],
                'total_supply': coin_data['total_supply'],
                'last_updated': coin_data['quote']['USD']['last_updated']
            }
            
            # Update cache
            cmc_cache['data'] = processed_data
            cmc_cache['last_updated'] = datetime.now()
            
            return jsonify(processed_data)
        else:
            return jsonify({"error": "No data found for Mysterium token"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/node/<int:node_id>/connection_stats')
def connection_stats(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    
    try:
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        stats = node_api.connection_statistics()
        
        # Log connection statistics for debugging
        print(f"\n=== Connection Statistics for node {node_id} ===")
        print(f"Stats: {json.dumps(stats, indent=2)}")
        print("=========================================\n")
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting connection stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/node/<int:node_id>/session_stats/<string:session_id>')
def session_stats(node_id, session_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    
    try:
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        session_data = node_api.session_by_id(session_id)
        
        # Log session data for debugging
        print(f"\n=== Session Stats for node {node_id}, session {session_id} ===")
        print(f"Data: {json.dumps(session_data, indent=2)}")
        print("=========================================\n")
        
        return jsonify(session_data)
    except Exception as e:
        print(f"Error getting session stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/node/<int:node_id>/active_sessions')
def node_active_sessions(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    
    try:
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        # Only get sessions data, avoid quality API calls
        sessions = node_api.sessions({"page_size": 100})  # Smaller page size for active sessions
        
        print(f"Fetching active sessions for node {node_id} without quality metrics")
        
        return jsonify({
            'sessions': sessions
        })
    except Exception as e:
        print(f"Error getting active sessions data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add this route to handle DELETE requests for stopping services
@app.route('/node/<int:node_id>/services/<string:service_id>', methods=['DELETE'])
def delete_service(node_id, service_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    
    try:
        # Print debug information
        print(f"\n=== Service Stop Request for Node {node_id} ===")
        print(f"Stopping service with ID: {service_id}")
        
        # Initialize node API
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        # Try to stop the service
        result = node_api.stop_service(service_id)
        
        # Return success response
        print(f"Service {service_id} stopped successfully")
        return jsonify({"success": True}), 200
    except Exception as e:
        print(f"Exception stopping service: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
