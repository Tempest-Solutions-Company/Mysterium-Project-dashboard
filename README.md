# Mysterium Node Dashboard

A web-based dashboard for monitoring and managing multiple Mysterium Network nodes with detailed statistics, service management, and token information.

<img src="https://i.imgur.com/tNs7WPV.png" alt="Mysterium Node Dashboard" width="500" />
<img src="https://i.imgur.com/nHBnf6p.png" alt="Mysterium Node Dashboard" width="500" />
<img src="https://i.imgur.com/fZ9d74K.png" alt="Mysterium Node Dashboard" width="500" />

## Features

- **Multi-Node Management**: Monitor and control multiple Mysterium nodes from a single interface
- **Service Control**: Start/stop different service types (VPN, B2B VPN, Public, etc.)
- **Detailed Statistics**: View session stats, earnings, traffic data, and more
- **Node Quality Metrics**: Monitor node performance, latency, and market position
- **MYST Token Information**: Real-time token price, market data, and trends
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

- Python 3.7+ installed on your system
- Access to one or more Mysterium nodes with the Tequila API exposed (port 4449)
- For token information: a CoinMarketCap API key (optional)

## Installation

### Method 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/Tempest-Solutions-Company/Mysterium-Project-dashboard.git
cd Mysterium-Project-dashboard

# Install required dependencies
pip install -r requirements.txt
```

### Method 2: Download ZIP

1. Visit https://github.com/Tempest-Solutions-Company/Mysterium-Project-dashboard
2. Click the green "Code" button and select "Download ZIP"
3. Extract the ZIP file to your preferred location
4. Open a terminal/command prompt in the extracted folder
5. Run `pip install -r requirements.txt`

## Running the Dashboard

Start the dashboard server with:

```bash
python dashboard.py
```

The dashboard will be available at http://localhost:5000

## Adding Nodes

1. Click the "Add Node" button on the dashboard
2. Enter the following details:
   - **Name**: A friendly name for your node
   - **IP**: The IP address of your Mysterium node
   - **Port**: The API port (usually 4449)
   - **Password**: Your node's API password
3. Click "Add Node"

> **Port Forwarding Note**: Ensure port 4449 is forwarded to your node if accessing it remotely

## Viewing Node Details

Click "View Details" on any node card to access:

- Node health information
- Session statistics (all-time and today)
- Service management
- Quality metrics

## Managing Services

On the node details page:

1. Scroll to the "Services" section
2. Use the "Start" button to begin a service:
   - **B2B VPN/Data Transfer**: For business connectivity
   - **Public**: Standard Wireguard service
   - **VPN**: VPN service
   - **B2B Scraping**: For business web scraping
3. Use the "Stop" button to terminate active services

## MYST Token Information

To view MYST token market data:

1. Obtain a free API key from [CoinMarketCap](https://coinmarketcap.com/api/)
2. On the dashboard, click the "API Key" button in the token info section
3. Enter your API key and click "Save & Fetch Data"

The dashboard will display:
- Current MYST price
- Price changes (1h, 24h, 7d, 30d)
- Volume information
- Market cap data
- Supply metrics

## Troubleshooting

### Connection Issues

If you can't connect to your node:
- Verify the node is running
- Check that port 4449 is accessible (try accessing http://YOUR_NODE_IP:4449/tequilapi/healthcheck in a browser)
- For remote access, ensure proper port forwarding is configured
- Check your firewall settings

### Authentication Errors

If you receive authentication errors:
- Verify the correct password is being used
- Try accessing the Mysterium UI directly to confirm credentials

## Security Notes

- This dashboard stores node connection details locally
- The CoinMarketCap API key is stored in your browser's localStorage
- Consider running this application only on trusted or local networks

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Mysterium Network](https://mysterium.network/) for the node software
- Contributors to the Mysterium Project Dashboard
