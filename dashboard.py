import os
import json
from datetime import datetime, timedelta
import requests
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
import yaml
import markdown
import re
import logging

templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
static_dir = os.path.join(os.path.dirname(__file__), 'static')

if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
    os.makedirs(os.path.join(templates_dir, 'dashboard'))
    os.makedirs(os.path.join(templates_dir, 'node'))
    os.makedirs(os.path.join(templates_dir, 'help'))

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

class NodeAPI:
    def __init__(self, ip, port, token=None):
        self.base_url = f"http://{ip}:{port}/tequilapi"
        self.token = token
        self.headers = {'Accept': 'application/json'}
        if token:
            self.headers['Authorization'] = f'Bearer {token}'
    
    def authenticate(self, password):
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
    
    def health_check(self):
        try:
            response = requests.get(f"{self.base_url}/healthcheck", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Health check failed: {str(e)}")
    
    def session_stats(self):
        try:
            response = requests.get(f"{self.base_url}/sessions/stats-aggregated", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get session stats: {str(e)}")
    
    def session_stats_daily(self, query=None):
        try:
            response = requests.get(f"{self.base_url}/sessions/stats-daily", headers=self.headers, params=query)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get daily session stats: {str(e)}")
    
    def sessions(self, query=None):
        try:
            response = requests.get(f"{self.base_url}/sessions", headers=self.headers, params=query)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get sessions: {str(e)}")
    
    def identity_list(self):
        try:
            response = requests.get(f"{self.base_url}/identities", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get identities: {str(e)}")
    
    def service_list(self):
        try:
            response = requests.get(f"{self.base_url}/services", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to get services: {str(e)}")
    
    def start_service(self, request):
        try:
            print(f"Starting service with request: {request}")
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

    def stop_service(self, service_id):
        try:
            response = requests.delete(f"{self.base_url}/services/{service_id}", headers=self.headers)
            response.raise_for_status()
            return True
        except Exception as e:
            raise Exception(f"Failed to stop service: {str(e)}")
    
    def connection_statistics(self):
        try:
            response = requests.get(f"{self.base_url}/connection/statistics", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get connection statistics: {str(e)}")
            return {"bytesReceived": 0, "bytesSent": 0, "duration": 0, "tokensSpent": 0}
    
    def session_by_id(self, session_id):
        try:
            response = requests.get(f"{self.base_url}/sessions/{session_id}", headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to get session by ID: {str(e)}")
            return None
    
    def nat_status(self):
        try:
            nat_info = {}
            
            try:
                response = requests.get(f"{self.base_url}/nat/type", headers=self.headers)
                if response.status_code == 200:
                    nat_type_info = response.json()
                    if nat_type_info:
                        print("NAT type obtained from /nat/type endpoint")
                        
                        if 'type' in nat_type_info:
                            nat_info['type'] = nat_type_info['type']
                        
                        for key in ['status', 'error']:
                            if key in nat_type_info:
                                nat_info[key] = nat_type_info[key]
                else:
                    print(f"The /nat/type endpoint returned status code {response.status_code}")
            except Exception as e:
                print(f"Failed to get NAT type from nat/type endpoint: {str(e)}")
            
            if nat_info and 'type' in nat_info and 'status' not in nat_info:
                nat_info['status'] = 'finished'
            
            if nat_info:
                return nat_info
                
            try:
                response = requests.get(f"{self.base_url}/proposals", headers=self.headers)
                response.raise_for_status()
                proposals = response.json()
                
                if proposals and len(proposals) > 0:
                    nat_type = proposals[0].get('nat_compatibility')
                    if nat_type:
                        print(f"NAT information extracted from proposals: {nat_type}")
                        return {
                            'type': nat_type,
                            'status': 'finished'
                        }
            except Exception as e:
                print(f"Failed to get NAT info from proposals: {str(e)}")
                
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

    def node_monitoring_status(self):
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        
        if not name or not ip:
            flash('Name and IP are required fields', 'danger')
            return redirect(url_for('index'))
        
        if node_name_exists(name):
            flash(f'A node with the name "{name}" already exists. Please use a unique name.', 'danger')
            return redirect(url_for('index'))
        
        try:
            node_api = NodeAPI(ip, port)
            token = node_api.authenticate(password)
            
            nodes = get_nodes()
            new_node = {
                'id': get_lowest_available_id(nodes),
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
        
        health = node_api.health_check()
        stats = node_api.session_stats()
        stats_daily = node_api.session_stats_daily()
        services = node_api.service_list()
        identities = node_api.identity_list()
        
        sessions = node_api.sessions({"page_size": 1000})
        
        nat_info = node_api.nat_status()
        logger.info("\n=== NAT Status Info ===")
        if nat_info:
            logger.info(f"Raw NAT status: {json.dumps(nat_info, indent=2)}")
        else:
            logger.info("NAT status unavailable, creating placeholder")
            nat_info = {
                'type': 'unknown',
                'status': 'unavailable'
            }
        logger.info("=====================\n")
        
        monitoring_status = node_api.node_monitoring_status()
        logger.info("\n=== Node Monitoring Status ===")
        if monitoring_status:
            logger.info(f"Monitoring status: {json.dumps(monitoring_status, indent=2)}")
        else:
            logger.info("Node monitoring status unavailable")
            monitoring_status = {"status": "unknown"}
        logger.info("==========================\n")
        
        quality_metrics = None
        location_info = None
        if identities and 'identities' in identities and len(identities['identities']) > 0:
            provider_id = identities['identities'][0]['id']
            try:
                import requests
                logger.info(f"Fetching quality metrics from discovery API for provider {provider_id}")
                discovery_url = f"https://discovery.mysterium.network/api/v4/proposals?access_policy=all&provider_id={provider_id}"
                discovery_response = requests.get(discovery_url, timeout=5)
                if discovery_response.status_code == 200:
                    discovery_data = discovery_response.json()
                    if discovery_data and len(discovery_data) > 0:
                        quality_metrics = discovery_data[0].get('quality', {})
                        location_info = discovery_data[0].get('location', {})
                        logger.info(f"Found quality metrics for provider {provider_id}: {quality_metrics}")
                        logger.info(f"Found location info for provider {provider_id}: {location_info}")
            except Exception as e:
                logger.warning(f"Error fetching discovery data: {str(e)}")
        
        logger.info("\n=== Session Stats Data ===")
        logger.info(f"Raw stats response: {json.dumps(stats, indent=2)}")
        if 'stats' in stats:
            logger.info(f"Stats object keys: {list(stats['stats'].keys())}")
            for key, value in stats['stats'].items():
                logger.info(f"  {key}: {value}")
        else:
            logger.info("No 'stats' key in stats response")
        logger.info("===========================\n")
        
        if sessions and 'items' in sessions:
            logger.info(f"\nSession count for node {node_id}: {len(sessions['items'])}")
        else:
            logger.info(f"\nNo sessions data available for node {node_id}")
        
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
        logger.error(f"Error getting node data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/node/<int:node_id>/start_service', methods=['POST'])
def start_service(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    
    logger.info(f"\n=== Service Start Request for Node {node_id} ===")
    logger.info(f"Request Content-Type: {request.headers.get('Content-Type')}")
    logger.info(f"Request method: {request.method}")
    
    try:
        if request.is_json:
            data = request.json
            logger.info(f"Received JSON data: {data}")
        else:
            data = request.form.to_dict()
            logger.info(f"Received form data: {data}")
        
        service_type = data.get('type')
        provider_id = data.get('provider_id')
        
        logger.info(f"Extracted: service_type={service_type}, provider_id={provider_id}")
        
        if not service_type:
            return jsonify({"error": "Service type is required"}), 400
        
        if not provider_id:
            logger.info("No provider_id in request, getting from identities API")
            node_api = NodeAPI(node['ip'], node['port'], node['token'])
            identities = node_api.identity_list()
            
            if not identities or 'identities' not in identities or not identities['identities']:
                return jsonify({"error": "No identities found on node"}), 400
            
            provider_id = identities['identities'][0]['id']
            logger.info(f"Using provider_id from identity: {provider_id}")
        
        service_request = {
            "provider_id": provider_id,
            "type": service_type
        }
        
        logger.info(f"Final service request payload: {service_request}")
        
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        node_api.headers['Content-Type'] = 'application/json'
        logger.info(f"Request headers: {node_api.headers}")
        
        import json
        url = f"{node_api.base_url}/services"
        logger.info(f"Making POST request to: {url}")
        
        response = requests.post(
            url,
            headers=node_api.headers,
            data=json.dumps(service_request)
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
        try:
            response_text = response.text
            logger.info(f"Response text: {response_text}")
            response_json = response.json()
            logger.info(f"Response JSON: {response_json}")
        except Exception as e:
            logger.warning(f"Could not parse response as JSON: {e}")
            response_json = None
        
        if response.status_code == 200 or response.status_code == 201:
            if response_json:
                return jsonify({"success": True, "service": response_json})
            else:
                return jsonify({"success": True})
        else:
            error_msg = response_json.get('error', {}).get('message') if response_json else response.text
            logger.error(f"Error starting service: {error_msg}")
            return jsonify({"error": f"Failed to start service: {error_msg}"}), response.status_code
                 
    except Exception as e:
        logger.error(f"Exception starting service: {str(e)}")
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

@app.route('/node/<int:node_id>/services', methods=['POST'])
def create_service(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    
    logger.info(f"\n=== Service Create Request for Node {node_id} ===")
    logger.info(f"Request Content-Type: {request.headers.get('Content-Type')}")
    logger.info(f"Request method: {request.method}")
    
    try:
        if request.is_json:
            data = request.json
            logger.info(f"Received JSON data: {data}")
        else:
            data = request.form.to_dict()
            logger.info(f"Received form data: {data}")
        
        service_type = data.get('service_type')
        provider_id = data.get('provider_id')
        
        logger.info(f"Extracted: service_type={service_type}, provider_id={provider_id}")
        
        if not service_type:
            return jsonify({"error": "Service type is required"}), 400
        
        if not provider_id:
            logger.info("No provider_id in request, getting from identities API")
            node_api = NodeAPI(node['ip'], node['port'], node['token'])
            identities = node_api.identity_list()
            
            if not identities or 'identities' not in identities or not identities['identities']:
                return jsonify({"error": "No identities found on node"}), 400
            
            provider_id = identities['identities'][0]['id']
            logger.info(f"Using provider_id from identity: {provider_id}")
        
        service_request = {
            "provider_id": provider_id,
            "type": service_type
        }
        
        logger.info(f"Final service request payload: {service_request}")
        
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        result = node_api.start_service(service_request)
        return jsonify({"success": True, "service": result})
                 
    except Exception as e:
        logger.error(f"Exception starting service: {str(e)}")
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

cmc_cache = {
    'data': None,
    'last_updated': None
}

@app.route('/api/myst-price')
def myst_price():
    if cmc_cache['data'] and cmc_cache['last_updated'] and \
       datetime.now() - cmc_cache['last_updated'] < timedelta(minutes=10):
        return jsonify(cmc_cache['data'])
    
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
        
        if 'data' in data and data['data']:
            coin_data = list(data['data'].values())[0]
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
        
        logger.info(f"\n=== Connection Statistics for node {node_id} ===")
        logger.info(f"Stats: {json.dumps(stats, indent=2)}")
        logger.info("=========================================\n")
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting connection stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/node/<int:node_id>/session_stats/<string:session_id>')
def session_stats(node_id, session_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    
    try:
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        session_data = node_api.session_by_id(session_id)
        
        logger.info(f"\n=== Session Stats for node {node_id}, session {session_id} ===")
        logger.info(f"Data: {json.dumps(session_data, indent=2)}")
        logger.info("=========================================\n")
        
        return jsonify(session_data)
    except Exception as e:
        logger.error(f"Error getting session stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/node/<int:node_id>/active_sessions')
def node_active_sessions(node_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({'error': 'Node not found'}), 404
    
    try:
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        sessions = node_api.sessions({"page_size": 100})
        
        logger.info(f"Fetching active sessions for node {node_id} without quality metrics")
        
        return jsonify({
            'sessions': sessions
        })
    except Exception as e:
        logger.error(f"Error getting active sessions data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/node/<int:node_id>/services/<string:service_id>', methods=['DELETE'])
def delete_service(node_id, service_id):
    node = get_node_by_id(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    
    try:
        logger.info(f"\n=== Service Stop Request for Node {node_id} ===")
        logger.info(f"Stopping service with ID: {service_id}")
        
        node_api = NodeAPI(node['ip'], node['port'], node['token'])
        
        result = node_api.stop_service(service_id)
        
        logger.info(f"Service {service_id} stopped successfully")
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Exception stopping service: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_node_password', methods=['POST'])
def update_node_password():
    node_id = request.form.get('node_id')
    new_password = request.form.get('password')
    
    if not node_id or not new_password:
        flash('Node ID and password are required', 'danger')
        return redirect(url_for('index'))
    
    try:
        node_id = int(node_id)
    except ValueError:
        flash('Invalid node ID', 'danger')
        return redirect(url_for('index'))
        
    node = get_node_by_id(node_id)
    
    if not node:
        flash('Node not found', 'danger')
        return redirect(url_for('index'))
    
    try:
        node_api = NodeAPI(node['ip'], node['port'])
        token = node_api.authenticate(new_password)
        
        nodes = get_nodes()
        for n in nodes:
            if n.get('id') == node_id:
                n['token'] = token
                break
                
        save_nodes(nodes)
        
        if 'node_tokens' in session:
            node_tokens = session.get('node_tokens', {})
            if str(node_id) in node_tokens:
                del node_tokens[str(node_id)]
                session['node_tokens'] = node_tokens
        
        flash(f'Password updated for node {node["name"]}', 'success')
    except Exception as e:
        flash(f'Error updating password: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

def get_help_topics():
    """Get a list of all available help topics."""
    help_dir = os.path.join(os.path.dirname(__file__), 'help_content')
    topics = []
    
    logger.info(f"\n=== Searching for help topics in: {help_dir} ===")
    
    if not os.path.exists(help_dir):
        logger.warning(f"Help content directory not found at: {help_dir}")
        try:
            os.makedirs(help_dir)
            logger.info(f"Created help_content directory at: {help_dir}")
        except Exception as e:
            logger.error(f"Error creating help_content directory: {e}")
        return topics
    
    try:
        all_files = os.listdir(help_dir)
        logger.info(f"Found {len(all_files)} files in help_content directory:")
        for file in all_files:
            logger.info(f"  - {file}")
    except Exception as e:
        logger.error(f"Error listing help content directory: {e}")
        return topics
    
    for filename in all_files:
        if filename.endswith('.yaml'):
            topic_id = filename[:-5]
            
            try:
                with open(os.path.join(help_dir, filename), 'r') as file:
                    topic_data = yaml.safe_load(file)
                    
                if not topic_data:
                    logger.warning(f"Error: Empty or invalid YAML in {filename}")
                    continue
                
                if 'color' not in topic_data or not topic_data['color']:
                    topic_data['color'] = 'primary'
                    
                topics.append({
                    'id': topic_id,
                    'title': topic_data.get('title', topic_id),
                    'description': topic_data.get('description', ''),
                    'color': topic_data.get('color', 'primary'),
                    'thumbnail_url': topic_data.get('thumbnail_url', '')
                })
                logger.info(f"Successfully loaded help topic: {topic_id} - {topic_data.get('title')} with color {topic_data.get('color', 'primary')}")
            except Exception as e:
                logger.error(f"Error loading help topic {filename}: {e}")
    
    logger.info(f"Total help topics loaded: {len(topics)}")
    return topics

def get_help_topic(topic_id):
    """Get content for a specific help topic."""
    help_file = os.path.join(os.path.dirname(__file__), 'help_content', f"{topic_id}.yaml")
    
    if not os.path.exists(help_file):
        return None
    
    try:
        with open(help_file, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading help topic {topic_id}: {e}")
        return None

@app.route('/help')    
def help_index():
    topics = get_help_topics()
    return render_template('help/index.html', title='Help Center', topics=topics)

@app.route('/help/<topic_id>')
def help_topic(topic_id):
    topic_data = get_help_topic(topic_id)
    if not topic_data:
        flash('Help topic not found', 'danger')
        return redirect(url_for('help_index'))
    
    if topic_data and 'content_sections' in topic_data:
        for section in topic_data['content_sections']:
            if 'content' in section:
                section['content'] = markdown.markdown(
                    section['content'], 
                    extensions=['tables', 'fenced_code', 'nl2br']
                )
    
    return render_template('help/topic.html', title=f'Help: {topic_data.get("title")}', topic=topic_data)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)