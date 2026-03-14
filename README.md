# epubArena3 - EPUB Processing and Translation Pipeline

epubArena3 is a EPUB processing and translation pipeline that uses Large Language Models (LLMs) to transform EPUB files through customizable workflows including summarization, translation, and content analysis. The system provides both command-line and web-based GUI interfaces for managing EPUB processing tasks.

**Note:** This project is functional but actively evolving. The `main` branch now tracks the FastAPI GUI and async flow; the previous synchronous/Flask implementation lives in the `synchronous` branch for comparison or fallback.

## Overview

This project enables automated processing of EPUB files through a multi-step pipeline:
1. **EPUB Extraction** - Parse EPUB files to extract chapters, metadata, and images
2. **Content Chunking** - Split content into manageable chunks (configurable by paragraphs and word count)
3. **LLM Processing** - Apply customizable LLM transformations using configurable prompts
4. **Publication** - Generate side-by-side HTML comparisons and regenerate EPUB files

## Key Features

### Multi-Step Processing Pipeline
- **Step 1 (Prompt1)**: Typically used for summarization or initial processing
- **Step 2 (Prompt2)**: Typically used for translation or further refinement
- **Flexible Source Selection**: Can process from original source or from Step 1 output
- **Multi-Source Processing**: Compare and combine multiple translations

### LLM Integration
- **OpenAI-Compatible APIs**: Support for local LLM servers (LM Studio, llama.cpp)
- **Local Model Support**: Load models via `llama-cpp-python`
- **Configurable Parameters**: Temperature, top_p, max tokens, system prompts
- **Customizable Prompts**: JSON-based prompt management system

### Publication & Output
- **Side-by-Side HTML Comparison**: Original vs. processed text with toggleable columns
- **EPUB Regeneration**: Create new EPUB files from processed content
- **Batch Processing**: Process multiple EPUB files sequentially
- **Resume Capability**: Save progress as pickle files for continuation

### User Interfaces
- **Web GUI**: FastAPI interface (`gui3.py`) is the primary entry point
- **Command-Line Interface**: Script-based processing for automation
- **Real-time Monitoring**: Live log viewing and progress tracking inside the FastAPI GUI

### Deployment Options
- **Local Development**: Python virtual environment
- **Docker Container**: Pre-configured container for easy deployment
- **Docker Compose**: Simplified multi-container deployment with data persistence

## Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `epubArena3.py` | Main orchestration script |
| `collect.py` | EPUB extraction, cleaning, and chunking |
| `process.py` | LLM processing with configurable prompts |
| `store.py` | Data persistence and Publication (HTML/EPUB generation) |
| `call.py` | LLM API communication layer |
| `config.py` | Configuration management |
| `gui3.py` | FastAPI-based GUI entry point (current primary UI) |
| `prompts.py` | Prompt management system |
| `jaccard.py` | Text similarity/comparison (quality checking) |
| `errorLog.py` | Comprehensive logging system |

### Data Flow
```
EPUB File → extractor → cleaner → chunker → processor → store → Publication
                                   ↓
                               LLM API/Local LLM
```

## Project Structure

```
├── data/                    # Application data (created automatically)
│   ├── cfg/                # Configuration files (prompts.json, api_configs.json)
│   ├── input/              # EPUB files to process
│   ├── output/             # Generated HTML and EPUB files
│   └── pkl/                # Progress persistence (pickle files)
├── static/                 # Web GUI assets (CSS, JavaScript)
├── templates/              # HTML templates for web interface
├── sample_api_configs.json # Sample API endpoint configurations, actually use them in data/cfg
├── sample_prompts.json     # Sample prompt configurations, actually use them in data/cfg
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker container definition
├── docker-compose.yml     # Docker Compose configuration
├── _start_epubArena3.bat  # Windows batch startup script
├── config.py              # Application configuration
└── *.py                   # Core Python modules
```

## Installation & Setup

### Prerequisites
- Python 3.12+ (for local development)
- Docker and Docker Compose (for containerized deployment) - optional
- Virtual environment recommended for local development

### Option 1: Local Development Installation

```bash
# Clone the repository
git clone https://github.com/sschmitt78mtk/epubArena3.git
cd epubArena3

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Docker Installation

```bash
# Build the Docker image
docker build -t epubarena3-20260309:latest .

# Or use Docker Compose
docker-compose up -d
```

### Option 3: Windows Quick Start
Run `_start_epubArena3.bat` to start the application with a pre-configured virtual environment.

## Configuration System

### Prompt Management
Prompts are stored in JSON format (`sample_prompts.json`, `data/cfg/prompts.json`) with each prompt containing:
- System message
- Pre/Post prompts
- Temperature, top_p, max token limits
- Target language and processing flags

### API Configuration
Multiple API endpoint configurations in `sample_api_configs.json` supporting:
- Local LLM servers (LM Studio)
- Remote OpenAI-compatible APIs
- Custom model configurations

### Configuration Migration
On first run, sample configuration files are automatically copied to `data/cfg/`:
- `sample_api_configs.json` → `data/cfg/api_configs.json`
- `sample_prompts.json` → `data/cfg/prompts.json`

## Running the Application

### FastAPI Web GUI (default)
```bash
# Local development GUI
python gui3.py
# Access at http://127.0.0.1:8083
```

### Command Line
```bash
python epubArena3.py
```

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Batch Processing
- Configure `config.py` or use web interface
- Place EPUB files in `data/input/` directory
- Enable batch processing mode

## Usage Examples

### 1. EPUB Translation
1. Upload EPUB file via web interface
2. Configure translation prompts
3. Process through summarization → translation pipeline
4. Download side-by-side comparison or translated EPUB

### 2. Content Summarization
1. Configure summarization prompt (Prompt1)
2. Process EPUB to create condensed version
3. Generate HTML comparison with original

### 3. Comparative Analysis
1. Process same EPUB with multiple prompts/models
2. Compare outputs side-by-side
3. Analyze differences in translation quality

### 4. Docker-based Processing
```bash
# Start the Docker container
docker-compose up -d

# Upload EPUB files to data/input directory
cp your-book.epub data/input/

# Access web interface at http://localhost:8083
# Configure and process through the GUI
```

## Configuration Options

### Processing Settings
- **Chunk Size**: Control paragraph and word limits per chunk (recently improved for better handling)
- **LLM Parameters**: Temperature, top_p, max tokens
- **Model Selection**: Different models for each processing step
- **Batch Processing**: Process multiple files sequentially

### Publication Settings
- **HTML Output**: Side-by-side or single-column views
- **EPUB Generation**: Include images, preserve formatting (recently improved with better HTML handling)
- **Jaccard Clean**: Text similarity filtering (experimental)

## Recent Improvements

The project has seen significant recent development including:

- **FastAPI Migration**: Modern web interface with async support and automatic OpenAPI documentation
- **Enhanced Chunking System**: Improved paragraph and word-based chunking with duplicate prevention
- **EPUB Output Fixes**: Better handling of HTML tags in EPUB regeneration
- **Docker Support**: Full containerization with Dockerfile and docker-compose.yml
- **Configuration Persistence**: Automatic saving and loading of processing state
- **Path Management**: Improved cross-platform file path handling

## Technology Stack

- **Python 3.12+** with extensive typing annotations
- **FastAPI** for modern web interface with async support and OpenAPI documentation
- **OpenAI SDK** for LLM communication
- **EbookLib** for EPUB manipulation
- **BeautifulSoup4** for HTML processing
- **Markdown** support for content conversion
- **Docker** for containerization

## Development Status

The project is actively maintained and under continuous development with:
- Comprehensive error handling and logging
- Configuration persistence
- Support for both CLI and GUI operation
- Batch processing capabilities
- Docker support for easy deployment

## Code Quality
- Type hints throughout the codebase
- Pylint configuration for style checking
- Clear module separation and responsibilities
- Comprehensive logging for debugging

## Use Cases

1. **EPUB Translation**: Translating books between languages using LLMs
2. **Content Summarization**: Creating condensed versions of books/articles
3. **Educational Tools**: Side-by-side comparison for language learning
4. **Content Analysis**: Comparing multiple translations/summaries
5. **Content Transformation**: Applying various text transformations via LLM prompts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Submit a pull request

## License

See `LICENSE` file for details.

## Support

For issues and feature requests, please use the GitHub issue tracker.

---

*Note: This project is designed for processing EPUB files for educational and research purposes. Always ensure you have the appropriate rights to process and modify any EPUB files.*

*Development Status: This project is functional and actively used, but is still under active development with regular improvements and updates.*
