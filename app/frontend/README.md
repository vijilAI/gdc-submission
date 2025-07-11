# Virtual User Testing Frontend

This directory contains the Streamlit-based frontend for the Virtual User Testing application.

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
