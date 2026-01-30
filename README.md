# epubArena3 - EPUB Processing and Translation Pipeline

epubArena3 is a EPUB processing and translation pipeline that uses Large Language Models (LLMs) to transform EPUB files through customizable workflows including summarization, translation, and content analysis. The system provides both command-line and web-based GUI interfaces for managing EPUB processing tasks.

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
- **Web GUI**: Flask-based interface for configuration and monitoring
- **Command-Line Interface**: Script-based processing for automation
- **Real-time Monitoring**: Live log viewing and progress tracking

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
| `gui3.py` | Web interface (Flask) |
| `prompts.py` | Prompt management system |
| `jaccard.py` | Text similarity/comparison (quality checking) |
| `ErrorLog.py` | Comprehensive logging system |

### Data Flow
```
EPUB File → extractor → cleaner → chunker → processor → store → Publication
                                   ↓
                               LLM API/Local LLM
```

## Project Structure

```
├── input/          # EPUB files to process
├── output/         # Generated HTML and EPUB files
├── pkl/           # Progress persistence (pickle files)
├── logs/          # Processing logs
├── static/        # Web GUI assets (CSS, JavaScript)
├── templates/     # HTML templates for web interface
├── api_configs_sample.json  # API endpoint configurations
├── prompts_sample.json      # Default prompt configurations
├── requirements.txt         # Python dependencies
├── config.py               # Application configuration
└── *.py                    # Core Python modules
```

## Configuration System

### Prompt Management
Prompts are stored in JSON format (`prompts_sample.json`, `prompts.json`) with each prompt containing:
- System message
- Pre/Post prompts
- Temperature, top_p, max token limits
- Target language and processing flags

### API Configuration
Multiple API endpoint configurations in `api_configs_sample.json` supporting:
- Local LLM servers (LM Studio)
- Remote OpenAI-compatible APIs
- Custom model configurations

## Installation & Setup

### Prerequisites
- Python 3.12+
- Virtual environment recommended

### Installation
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

### Running the Application

**Web GUI:**
```bash
python gui3.py
# Access at http://127.0.0.1:8080
```

**Command Line:**
```bash
python epubArena3.py
```

**Batch Processing:**
- Configure `config.py` or use web interface
- Place EPUB files in `input/` directory
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

## Configuration Options

### Processing Settings
- **Chunk Size**: Control paragraph and word limits per chunk
- **LLM Parameters**: Temperature, top_p, max tokens
- **Model Selection**: Different models for each processing step
- **Batch Processing**: Process multiple files sequentially

### Publication Settings
- **HTML Output**: Side-by-side or single-column views
- **EPUB Generation**: Include images, preserve formatting
- **Jaccard Clean**: Text similarity filtering

## Technology Stack

- **Python 3.12+** with extensive typing annotations
- **Flask** for web interface
- **OpenAI SDK** for LLM communication
- **EbookLib** for EPUB manipulation
- **BeautifulSoup4** for HTML processing
- **Spacy** (optional) for text analysis via Jaccard similarity
- **Markdown** support for content conversion

## Development Status

The project is actively maintained with:
- Comprehensive error handling and logging
- Configuration persistence
- Support for both CLI and GUI operation
- Batch processing capabilities
- Regular updates and improvements

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