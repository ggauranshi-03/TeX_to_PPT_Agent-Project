# Agent for PPT Generation from TeX Tar Archives

## Overview

This project implements a multi-agent system to automatically generate Beamer (LaTeX-based) presentation PDFs from academic papers provided as compressed tar archives (e.g., .tar or .tar.gz files from arXiv). The system extracts the LaTeX content and images, uses LLMs to plan a 10-12 slide structure, generates compilable Beamer code, compiles it to PDF, and supports iterative refinements via user feedback.

The core logic is built using [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration, [OpenRouter](https://openrouter.ai/) for LLM access (e.g., Google's Gemini model), and `pdflatex` for PDF compilation. There are two variants in the notebook (`Agent_for_PPT_generation_using_TeX_tar.ipynb`):

- **Code 1**: A console-based runner with human-in-the-loop feedback via command-line inputs.
- **Code 2**: An enhanced version with a web-based UI using [Gradio](https://www.gradio.app/) for file uploads, feedback, and PDF downloads.


## Features

- **Extraction**: Unpacks tar archives, identifies the main .tex file, and lists available images.
- **Planning Agent**: Uses an LLM to create a structured 10-12 slide outline based on the paper's content, suggesting visuals from extracted images.
- **Developer Agent**: Generates compilable Beamer LaTeX code from the plan, with error-handling retries (up to 3 attempts).
- **Compilation**: Uses `pdflatex` to produce the PDF, with automatic retries on failures.
- **Feedback Loop**: Incorporates user critiques to refine the plan and regenerate the presentation.
- **UI (Code 2)**: Gradio interface for uploading archives, providing feedback, and downloading PDFs without re-uploading files.
- **Validation**: Checks for valid tar files and handles extraction/compilation errors gracefully.

## Requirements

- Python 3.8+
- Libraries: `langgraph`, `langchain-openai`, `gradio` (for Code 2), `tarfile`, `subprocess`, `shutil`, `typing`
- TeX distribution: `pdflatex` (install via `apt install texlive texlive-latex-extra texlive-fonts-recommended` on Linux/Colab)
- OpenRouter API Key: Replace the placeholder in the code with your own key (sign up at [OpenRouter](https://openrouter.ai/)).
- Supported Models: Google Gemini Flash (default), Claude 3.5 Sonnet, or GPT-4o.

No additional package installations are needed beyond the above (use `pip install langgraph langchain-openai gradio`).

## Usage

### Code 1: Console-Based Runner

This version runs in a terminal or notebook cell with interactive prompts.

1. Prepare a .tar or .tar.gz file containing a LaTeX paper (e.g., from arXiv).
2. Call the runner function with the file path:
   ```python
   run_multi_agent_system('/path/to/your/archive.tar.gz')
   ```
3. The system processes the file, generates the PDF, and prompts for feedback:
   - If happy, enter "yes" to exit.
   - If not, enter feedback (e.g., "Add more details to methods") and it regenerates.
4. Output PDF is saved in the working directory (e.g., `archive_work/presentation.pdf`).

### Code 2: Gradio Web UI

This version provides a browser-based interface.

1. Run the code in a notebook (e.g., Colab) or script.
2. The Gradio app launches automatically (use `share=True` for a public link).
3. In the UI:
   - Upload a compressed archive (.tar, .tar.gz, etc.).
   - (Optional) Enter initial feedback.
   - Click "Generate PDF".
   - Download the PDF if successful.
   - For refinements, enter feedback and click again (no re-upload needed).
4. Status messages show progress, plans, and errors.

**Note**: The UI validates tar files and persists state for feedback loops.

## Demo

A live demo is made available on running the gradlio code.

Upload your tar archive and generate presentations interactively.

## Limitations

- LLM Context: Truncates .tex content to ~15k characters; may miss details in very long papers.
- Images: Only supports .png, .jpg, .jpeg, .pdf; paths must match exactly.
- Compilation: Relies on standard TeX packages; complex papers with custom .sty may fail.
- API Costs: OpenRouter usage incurs fees based on model and tokens.
