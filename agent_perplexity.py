import os
import re
import tarfile
import subprocess
from openai import OpenAI

# --- CONFIG ---

client = OpenAI(api_key="", base_url="https://api.perplexity.ai")

# Perplexity model options: "sonar-reasoning", "sonar", "sonar-pro"
MODEL_NAME = "sonar" 

class ArchiveTool:
    """Extracts the arXiv source bundle."""
    @staticmethod
    def extract(archive_path):
        extract_path = archive_path.replace(".tar.gz", "_extracted").replace(".tar", "_extracted")
        if not os.path.exists(extract_path):
            os.makedirs(extract_path)
        print(f"Extracting {archive_path}...")
        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=extract_path)
        return extract_path

class WorkspaceTool:
    """Finds images and the main TeX file."""
    def __init__(self, directory):
        self.directory = directory
        self.images = [f for root, _, files in os.walk(directory) 
                       for f in files if f.lower().endswith(('.png', '.jpg', '.pdf'))]

    def find_main_tex(self):
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".tex"):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        if "\\begin{document}" in f.read():
                            return path
        return None

class DistillerTool:
    """Uses Perplexity to summarize LaTeX sections."""
    @staticmethod
    def process_section(title, content, available_images):
        prompt = f"""
        Task: Create a LaTeX Beamer frame.
        Section Title: {title}
        Content: {content[:2500]}
        Available Graphics: {available_images}

        Rules:
        1. Output ONLY LaTeX code starting with \\begin{{frame}} and ending with \\end{{frame}}.
        2. Use \\begin{{itemize}} for bullets.
        3. If a graphic name matches the context, include it via \\includegraphics[width=0.6\\textwidth]{{filename}}.
        4. Keep all math in $...$.
        """
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  API Error: {e}")
            return f"\\begin{{frame}}{{{title}}}\\item Content summary failed.\\end{{frame}}"

def run_agent(archive_file):
    # 1. Setup
    work_dir = ArchiveTool.extract(archive_file)
    ws = WorkspaceTool(work_dir)
    main_tex = ws.find_main_tex()
    
    if not main_tex:
        print("Error: Main .tex file not found.")
        return

    # 2. Parse Sections
    with open(main_tex, 'r', encoding='utf-8', errors='ignore') as f:
        content = re.sub(r'%.*', '', f.read()) # Strip comments
    
    sections = re.findall(r'\\section\{(.+?)\}(.*?)(?=\\section|\\end\{document\})', content, re.DOTALL)
    
    # 3. Generate Slides
    distiller = DistillerTool()
    frames = []
    print(f"Processing {len(sections)} sections using Perplexity...")
    
    for title, body in sections[:8]:
        clean_title = re.sub(r'\\.*\{.*\}', '', title).strip()
        print(f"-> Distilling: {clean_title}")
        frame = distiller.process_section(clean_title, body.strip(), ws.images)
        frames.append(frame.replace("```latex", "").replace("```", "").strip())

    # 4. Assemble TeX
    output_tex = os.path.join(work_dir, "presentation.tex")
    preamble = "\\documentclass{beamer}\n\\usetheme{metropolis}\n\\usepackage{graphicx}\n\\begin{document}\n"
    with open(output_tex, 'w', encoding='utf-8') as f:
        f.write(preamble + "\n".join(frames) + "\n\\end{document}")

    # 5. Compile PDF
    print("Attempting LaTeX compilation...")
    old_dir = os.getcwd()
    os.chdir(work_dir)
    try:
        # shell=True is vital for Windows to find pdflatex
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "presentation.tex"], shell=True, check=True)
        print(f"SUCCESS! Created: {work_dir}\\presentation.pdf")
    except Exception as e:
        print(f"FAILED to compile. Is MiKTeX installed and in PATH? Error: {e}")
    finally:
        os.chdir(old_dir)

if __name__ == "__main__":
    run_agent("./arXiv-2601.07654v1.tar.gz")