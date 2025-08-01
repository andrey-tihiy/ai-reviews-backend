# Review Analysis Application

This Django application provides a configurable multi-step pipeline for analyzing app reviews.

## Features

- **Tone Detection**: Analyzes emotional tone using VADER and TextBlob
- **Issue Detection**: Identifies problems and feature requests  
- **Complexity Check**: Determines if reviews need manual attention
- **GPT Analysis**: Advanced analysis for complex reviews using OpenAI
- **Automatic Ticketing**: Creates tickets for problematic reviews
- **Admin Interface**: Full control over pipeline configuration

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt

# For NLP features, also install spaCy model:
python -m spacy download en_core_web_sm
```

2. Run migrations:
```bash
python manage.py migrate review_analysis
```

3. Initialize pipeline steps:
```bash
python manage.py init_pipeline_steps --with-config
python manage.py init_prompt_templates
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key for GPT analysis (optional)

### Celery Queue

The application uses a separate Celery queue called 'analysis':

```bash
# Start worker for analysis queue
celery -A django_app worker -Q analysis -l info

# Or start worker for all queues
celery -A django_app worker -Q default,analysis -l info
```

## Usage

### Automatic Analysis

Reviews are automatically analyzed when created through the `post_save` signal.

### Manual Analysis

In Django Admin:
1. Go to Reviews
2. Select reviews to analyze
3. Choose "Run analysis on selected reviews" action

### Pipeline Configuration

In Django Admin → Review Analysis:

1. **Pipeline Step Types**: Read-only reference of available steps
2. **Pipeline Step Configurations**: Enable/disable steps, set order, configure parameters
3. **Prompt Templates**: Manage GPT prompts
4. **Analysis Results**: View all analysis results
5. **Review Tickets**: Manage tickets for problematic reviews

### Pipeline Step Parameters

- **tone_detection**: No parameters needed
- **issue_detection**: No parameters needed  
- **complexity_check**: No parameters needed
- **gpt_analysis**:
  - `api_key`: OpenAI API key (optional, uses settings if not provided)
  - `model`: GPT model to use (default: "gpt-4o-mini")
  - `prompt_id`: Prompt template ID
- **persistence**:
  - `auto_ticket_for_problems`: Create tickets for problems (default: true)
  - `auto_ticket_for_complex`: Create tickets for complex reviews (default: true)
  - `min_severity_for_ticket`: Minimum severity level (default: "medium")

## Models

### PipelineStepType
Predefined pipeline step types (tone_detection, issue_detection, etc.)

### PipelineStepConfig
Configuration for each pipeline step (enabled, order, parameters)

### PromptTemplate
Templates for GPT analysis prompts

### AnalysisResult
Stores analysis results for each review (OneToOne with Review)

### ReviewTicket
Tickets for reviews requiring attention

## API

No REST API endpoints are currently exposed. All functionality is available through Django Admin and Celery tasks.

## Development

### Adding New Pipeline Steps

1. Create a new class inheriting from `BaseAnalysisStep`
2. Register it with `@StepRegistry.register('your_step_key')`
3. Add the step type to `PIPELINE_STEP_TYPES` in the management command
4. Run `python manage.py init_pipeline_steps --reset`

### Running Tests

```bash
python manage.py test apps.review_analysis
```

## Troubleshooting

### Missing NLP Libraries

The application gracefully handles missing NLP libraries. Install them for full functionality:

```bash
pip install spacy spacytextblob vaderSentiment
python -m spacy download en_core_web_sm
```

### GPT Analysis Not Working

1. Check that `OPENAI_API_KEY` is set
2. Verify the API key in pipeline step config
3. Check Celery worker logs for errors

### Tickets Not Being Created

1. Verify persistence step is enabled
2. Check `auto_ticket_for_problems` parameter
3. Review minimum severity settings