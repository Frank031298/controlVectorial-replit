# Overview

This is a comprehensive Streamlit-based epidemiological surveillance system designed for public health institutions. The application processes and visualizes large CSV files (up to 200MB, 150,000+ records) containing 91 columns of surveillance information. It provides three main analysis modules: Vigilancia (Surveillance), Control Larvario (Larval Control), and Cerco (Epidemiological Fence). The system calculates Aedic Index, coverage percentages, container statistics, larvicide consumption, and febril cases analysis with interactive visualizations and comprehensive filtering capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit web framework for rapid data application development
- **Component Structure**: Modular tab-based interface with separate components for each analysis module
- **Layout**: Wide layout with expandable sidebar for file upload and filters
- **State Management**: Streamlit session state for data persistence across user interactions

## Data Processing Architecture
- **Data Input**: CSV file upload through Streamlit file uploader with UTF-8 encoding
- **Data Validation**: 91-column structure validation for epidemiological inspection data
- **Processing Pipeline**: DataProcessor class handles data cleaning, transformation, and filtering
- **Memory Management**: Data stored in session state to avoid reprocessing on each interaction

## Analysis Modules
- **Vigilancia Tab**: Surveillance data analysis with Aedic Index calculations, container statistics, larvicide consumption, monthly trends, and geographic mapping
- **Control Larvario Tab**: Enhanced larval control analysis including coverage percentages, container treatment analysis, febril cases tracking, and comprehensive larvicide consumption metrics
- **Cerco Tab**: Epidemiological fence analysis with coverage analysis, container statistics, larvicide tracking, febril cases, and trend analysis
- **Shared Components**: Common filter component with dynamic filtering, date range selection, and search functionality

## Calculation Engine
- **EpidemiologicalCalculations**: Specialized class for computing Aedic Index and container statistics
- **Health Facilities Registry**: Hardcoded reference data for 35+ health facilities with house counts
- **Container Analysis**: Support for multiple container types with status tracking (Inspected, Positive, Treated Chemically, Treated Physically)

## Visualization Layer
- **Library**: Plotly for interactive charts and graphs
- **Chart Types**: Bar charts, stacked charts, and geographic visualizations
- **Color Schemes**: Consistent color palette across all visualizations
- **Responsive Design**: Charts adapt to data size and screen dimensions

## Data Model
- **Geographic Hierarchy**: Department > Province > District structure
- **Health Facilities**: RENIPRESS code-based facility identification
- **Container Types**: 6 main categories (tanks, barrels, buckets, tires, flower pots, etc.)
- **Inspection Data**: Date-time stamped records with inspector information and GPS coordinates

# External Dependencies

## Core Libraries
- **Streamlit**: Web application framework for the user interface
- **Pandas**: Data manipulation and analysis library
- **NumPy**: Numerical computing support
- **Plotly**: Interactive visualization library (plotly.express and plotly.graph_objects)

## Data Processing
- **CSV Processing**: Built-in pandas CSV reader with UTF-8 encoding support
- **DateTime Handling**: Python datetime module for date filtering and processing

## No External Services
- **Database**: None - application operates on uploaded CSV files only
- **APIs**: No external API integrations
- **Authentication**: No authentication system implemented
- **Cloud Services**: No cloud service dependencies