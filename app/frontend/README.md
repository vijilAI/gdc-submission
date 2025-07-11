# Virtual User Testing Frontend

This directory contains the Streamlit-based frontend for the Virtual User Testing application.

## Features

- **📱 Interactive Web Interface**: Clean, modern Streamlit interface
- **👥 Virtual User Browser**: Browse and select from available virtual users in the database
- **🎯 Session Configuration**: Configure testing sessions with custom parameters
- **📊 Results Visualization**: View conversation results with formatted output
- **💾 Export Functionality**: Download session results as JSON files

## Setup and Usage

### Prerequisites

Make sure you have the required dependencies installed:

```bash
# From the repository root
pip install streamlit requests pandas
```

### Running the Frontend

1. **Start the API Server** (required):
   ```bash
   cd /path/to/gdc-submission
   python app/api/run_api.py
   ```
   The API will be available at `http://localhost:8000`

2. **Start the Streamlit Frontend**:
   ```bash
   cd app/frontend
   python run_streamlit.py
   ```
   
   Or directly with Streamlit:
   ```bash
   streamlit run streamlit_app.py --server.port=8501
   ```

3. **Access the Application**:
   Open your browser and go to `http://localhost:8501`

## Application Structure

### Pages

1. **👥 Browse Virtual Users**
   - View all virtual users in the database
   - Select a virtual user for testing sessions
   - View detailed virtual user information

2. **🎯 Run Session**
   - Configure session parameters (goals, turns, verbosity)
   - Run testing sessions with selected virtual users
   - Real-time progress tracking

3. **📊 Session Results**
   - View conversation results organized by goal type
   - Download results in JSON format
   - Formatted display of virtual user vs agent conversations

### Key Features

- **Real-time API Communication**: Direct integration with the FastAPI backend
- **Progress Tracking**: Visual progress bars during session execution
- **Error Handling**: Comprehensive error messages and status indicators
- **Responsive Design**: Works on desktop and mobile devices
- **Export Functionality**: Download session results for further analysis

## Configuration

The frontend is configured to connect to:
- **API Server**: `http://localhost:8000`
- **Streamlit Port**: `8501`

You can modify these settings in `streamlit_app.py` if needed.

## Troubleshooting

### Common Issues

1. **"API server is not responding"**
   - Make sure the API server is running: `python app/api/run_api.py`
   - Check that the API is accessible at `http://localhost:8000/health`

2. **"No personas found"**
   - Populate the database: `python scripts/populate_db.py`
   - Or use the API endpoint: `curl -X POST http://localhost:8000/load-personas`

3. **Session fails to run**
   - Check API server logs for errors
   - Ensure all required environment variables are set (API keys, etc.)
   - Verify the selected persona exists in the database

### Logs and Debugging

- Streamlit logs appear in the terminal where you started the app
- API logs appear in the API server terminal
- Use the browser's developer tools to debug frontend issues

## Development

### File Structure

```
app/frontend/
├── streamlit_app.py      # Main Streamlit application
├── run_streamlit.py      # Script to start the app
└── README.md            # This file
```

### Extending the Frontend

To add new features:

1. **New Pages**: Add new page options in the sidebar radio button
2. **API Endpoints**: Add new functions to communicate with additional API endpoints
3. **Visualizations**: Use Streamlit's built-in charting for data visualization
4. **Styling**: Modify the CSS in the `st.markdown()` calls for custom styling

## Dependencies

- `streamlit`: Web application framework
- `requests`: HTTP client for API communication
- `pandas`: Data manipulation (if needed for future features)
- `json`: JSON handling for API responses

## Performance Notes

- The app caches API responses where possible
- Session state maintains user selections across page navigation
- Progress bars provide user feedback during long-running operations

---

For issues or feature requests, please check the main project documentation.
