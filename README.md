# Data Center News Clipper

A Python-based pipeline that automatically collects, classifies, summarizes, and generates beautifully formatted PDF reports of data center industry news.

## Overview

This tool automates the process of gathering and organizing news about the data center industry. It:
1. Collects news from various sources using RSS feeds
2. Classifies articles into relevant categories (clients, competitors, government, innovation, others)
3. Filters out irrelevant content
4. Scrapes and summarizes articles
5. Generates a professionally formatted PDF report

## Features

- **Automated News Collection**: Configurable RSS feed queries
- **Smart Classification**: AI-powered categorization of articles
- **Content Summarization**: Automatic article summarization using LLMs
- **Professional PDF Generation**: 
  - Clean, modern design with Montserrat font
  - Organized table of contents
  - Articles grouped by categories
  - Page headers with logo and date range
  - Page footers with section names and page numbers
  - Empty section handling
  - Automatic page breaks between sections

## Project Structure

```
├── configs/
│   ├── queries.json         # RSS feed search configurations
│   ├── clipping_template.html  # PDF report template
│   └── test_queries.json    # Test configuration
├── services/
│   ├── classifier.py        # Article classification logic
│   ├── scraper.py          # Web scraping functionality
│   ├── summarizer.py       # Article summarization
│   ├── build_pdf.py        # PDF generation
│   └── utils/              # Utility functions
├── output/
│   └── clippings.json      # Processed articles data
├── run_pipeline.py         # Main execution script
└── requirements.txt        # Python dependencies
```

## Pipeline Steps

1. **Query Configuration Loading**
   - Loads search parameters from `configs/queries.json`

2. **RSS Feed Processing**
   - Fetches articles based on configured queries
   - Deduplicates by URL

3. **Classification**
   - Adds category labels to articles
   - Filters out irrelevant content

4. **Content Processing**
   - Scrapes full article content
   - Generates concise summaries

5. **Report Generation**
   - Stores processed data in JSON format
   - Creates formatted PDF report using HTML template

## Categories

Articles are automatically classified into the following categories:
- **Clientes**: Client-related news
- **Competidores**: Competitor news
- **Governo**: Government and regulatory news
- **Inovação**: Innovation and technology news
- **Outros**: Other relevant industry news

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   OPENAI_API_KEY=your_key_here
   ```
4. Configure search queries in `configs/queries.json`

## Usage

Run the complete pipeline:
```bash
python run_pipeline.py
```

This will:
1. Collect and process news articles
2. Save data to `output/clippings.json`
3. Generate a PDF report

## Configuration

### Query Configuration
Edit `configs/queries.json` to modify:
- Search terms
- Time range
- Geographic focus

### Report Styling
Modify `configs/clipping_template.html` to customize:
- Layout
- Typography
- Colors
- Section formatting

## Dependencies

- Python 3.x
- OpenAI API (for classification and summarization)
- WeasyPrint (for PDF generation)
- Beautiful Soup (for web scraping)
- Jinja2 (for HTML templating)

## Contributing

See `TODO.md` for planned features and improvements.

## License

[Add your license information here] 