import os
import re
import tarfile
import subprocess
from google import genai
import time # Added for rate-limit safety
# --- CONFIG ---
# Security Note: Your previous key was visible; I recommend rotating it.

client = genai.Client(api_key="")

class ArchiveTool:
    """Tool 0: Extracts the compressed arXiv source bundle."""
    @staticmethod
    def extract(archive_path):
        extract_path = archive_path.replace(".tar.gz", "_extracted")
        if not os.path.exists(extract_path):
            os.makedirs(extract_path)
        
        print(f"Extracting {archive_path}...")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=extract_path)
        return extract_path

class WorkspaceTool:
    """Tool 1: Navigates the extracted folder to find the main entry point."""
    def __init__(self, directory):
        self.directory = directory
        # Find all images in the extracted folder (recursively if needed)
        self.images = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.pdf')):
                    self.images.append(file)

    def find_main_tex(self):
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".tex"):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if "\\begin{document}" in content:
                            return path
        return None



class DistillerTool:
    """Tool 2: Updated Semantic compression with Error Handling."""
    @staticmethod
    def process_section(title, content, available_images):
        prompt = f"""
        You are a Beamer Slide Expert. Convert this section into a Beamer frame.
        Section: {title}
        Content: {content}
        Images available: {available_images}

        Rules:
        1. Output ONLY LaTeX code (\\begin{{frame}}...\\end{{frame}}).
        2. Keep math formulas exactly as written ($...$).
        3. Use \\begin{{itemize}} and \\item for bullets.
        4. Use \\includegraphics[width=0.5\\textwidth]{{filename}} if an image matches.
        """
        
        try:
            # Change: Try 'gemini-1.5-flash' or 'gemini-1.5-flash-latest'
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt
            )
            # Add a small sleep to prevent hitting rate limits (0.5s)
            time.sleep(0.5) 
            return response.text
        except Exception as e:
            print(f"  Warning: LLM failed for section '{title}'. Error: {e}")
            # Fallback: Create a simple slide so the compilation doesn't break
            return f"\\begin{{frame}}{{{title}}}\n\\item Content distillation failed for this section.\n\\end{{frame}}"

class BeamerGenerator:
    """Tool 3: The Synthesizer."""
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

# --- THE ORCHESTRATOR ---
def run_agent(archive_file):
    # 1. Extract Archive
    if archive_file.endswith(".tar.gz"):
        work_dir = ArchiveTool.extract(archive_file)
    else:
        work_dir = archive_file

    # 2. Setup Workspace
    ws = WorkspaceTool(work_dir)
    main_tex = ws.find_main_tex()
    
    if not main_tex:
        print("Error: Could not find main LaTeX file.")
        return

    # 3. Read Content
    with open(main_tex, 'r', encoding='utf-8', errors='ignore') as f:
        raw_content = f.read()
    
    # Strip common problematic LaTeX commands
    clean_content = re.sub(r'%.*', '', raw_content) # Remove comments
    
    # Improved regex to find sections more reliably
    sections = re.findall(r'\\section\{(.+?)\}(.*?)(?=\\section|\\end\{document\}|\\bibliography)', clean_content, re.DOTALL)
    
    distiller = DistillerTool()
    generated_frames = []
    
    # 4. Process Slides (The Distillation Step)
    print(f"Found {len(sections)} sections. Processing...")
    for sec_title, sec_content in sections[:10]:
        # Clean title of LaTeX commands like \label or \cite
        display_title = re.sub(r'\\.*\{.*\}', '', sec_title).strip()
        print(f"Working on slide: {display_title}")
        
        frame_code = distiller.process_section(display_title, sec_content.strip(), ws.images)
        
        # Basic cleanup: if LLM returns markdown code blocks, strip them
        frame_code = frame_code.replace("```latex", "").replace("```", "").strip()
        generated_frames.append(frame_code)

    # 5. Synthesis
    gen = BeamerGenerator(work_dir)
    final_tex_path = gen.assemble(generated_frames)
    
    # 6. Compilation
    original_dir = os.getcwd()
    os.chdir(os.path.dirname(final_tex_path))
    
    try:
        print("Starting LaTeX Compilation (pdflatex)...")
        # interaction=batchmode makes it quieter and faster
        subprocess.run(["pdflatex", "-interaction=batchmode", "presentation.tex"], check=True)
        print(f"\nSUCCESS! Your presentation is at: {os.path.join(os.getcwd(), 'presentation.pdf')}")
    except Exception as e:
        print(f"\nCompilation issue: {e}")
        print("Check 'presentation.log' in the extracted folder for details.")
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    # Now it takes the archive file directly
    run_agent("./arXiv-2601.07654v1.tar.gz")