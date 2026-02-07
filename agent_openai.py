import os
import re
import tarfile
import subprocess
import time
from openai import OpenAI  # Switched to OpenAI

# --- CONFIG ---
# Replace with your OpenAI API Key
client = OpenAI(api_key="")

class ArchiveTool:
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
    def __init__(self, directory):
        self.directory = directory
        self.images = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                    self.images.append(file)

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
    """Tool 2: Now using OpenAI GPT-4o-mini for reliable distillation."""
    @staticmethod
    def process_section(title, content, available_images):
        prompt = f"""
        Convert this research section into a LaTeX Beamer frame.
        Title: {title}
        Content: {content}
        Images: {available_images}

        Rules:
        1. Return ONLY the LaTeX code: \\begin{{frame}}{{Title}} ... \\end{{frame}}.
        2. Use \\begin{{itemize}} for bullets.
        3. Keep all math in $...$.
        4. If an image matches the context, use \\includegraphics[width=0.4\\textwidth]{{filename}}.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Cost-effective and very capable for TeX
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  AI Error on {title}: {e}")
            return f"\\begin{{frame}}{{{title}}}\n\\item Summary unavailable.\n\\end{{frame}}"

class BeamerGenerator:
    def __init__(self, directory):
        self.directory = directory

    def assemble(self, frames, title="Research Presentation"):
        preamble = [
            "\\documentclass{beamer}",
            "\\usetheme{metropolis}",
            "\\usepackage{graphicx}",
            f"\\title{{{title}}}",
            "\\begin{document}",
            "\\maketitle"
        ]
        full_code = "\n".join(preamble) + "\n" + "\n".join(frames) + "\n\\end{document}"
        output_path = os.path.join(self.directory, "presentation.tex")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_code)
        return output_path

def run_agent(archive_file):
    work_dir = ArchiveTool.extract(archive_file)
    ws = WorkspaceTool(work_dir)
    main_tex = ws.find_main_tex()
    
    if not main_tex:
        print("Main TeX file not found.")
        return

    with open(main_tex, 'r', encoding='utf-8', errors='ignore') as f:
        content = re.sub(r'%.*', '', f.read())
    
    sections = re.findall(r'\\section\{(.+?)\}(.*?)(?=\\section|\\end\{document\}|\\bibliography)', content, re.DOTALL)
    
    distiller = DistillerTool()
    frames = []
    print(f"Distilling {len(sections)} sections...")
    
    for sec_title, sec_content in sections[:10]:
        clean_title = re.sub(r'\\.*\{.*\}', '', sec_title).strip()
        print(f"-> Processing: {clean_title}")
        frame = distiller.process_section(clean_title, sec_content.strip()[:2000], ws.images)
        frames.append(frame.replace("```latex", "").replace("```", ""))

    gen = BeamerGenerator(work_dir)
    tex_path = gen.assemble(frames)
    
    # Compilation
    print("Compiling PDF...")
    old_cwd = os.getcwd()
    os.chdir(work_dir)
    try:
        # We use shell=True on Windows to help find the pdflatex executable
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "presentation.tex"], 
                       check=True, shell=True)
        print(f"DONE! File created: {work_dir}/presentation.pdf")
    except Exception as e:
        print(f"Compilation failed. Make sure pdflatex is in your PATH. Error: {e}")
    finally:
        os.chdir(old_cwd)

if __name__ == "__main__":
    run_agent("./arXiv-2601.07654v1.tar.gz")