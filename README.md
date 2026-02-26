# AI Automation Agents: Autonomous Open-Source Silicon Compiler

An open-source, fully local autonomous AI-EDA workflow that translates natural language hardware specifications into verified RTL and physical layouts (GDSII). 

This project mimics proprietary AI-EDA tools by utilizing a local Large Language Model (LLM) orchestrated in a self-correcting loop with industry-standard open-source verification and physical design tools. It is highly optimized to run locally on consumer hardware with 8GB VRAM limits (e.g., NVIDIA RTX 5060).

## System Architecture

The agent loop operates in five continuous phases:
1. **Ingestion:** Reads hardware requirements from a standard text specification file.
2. **Generation:** A local LLM (Qwen 2.5 Coder) generates the synthesizable Verilog code (`dut.v`) and a robust Python-based Cocotb testbench (`testbench.py`).
3. **Verification:** The Makefile triggers Verilator to compile the C++ simulation and run the Cocotb assertions.
4. **Self-Correction (Agentic Debugging):** If the simulation fails, PyVCD extracts the exact failing clock cycles from the `.vcd` waveform dump, formats them as a timing table, and feeds the error log back to the LLM for autonomous bug fixing.
5. **Physical Design:** Upon passing all testbench assertions, SiliconCompiler natively synthesizes the RTL, performs place-and-route targeting the ASAP7 7nm predictive PDK, and outputs a final `.gds` layout file.

## Repository Structure

```text
AI-automation-agents/
├── agents/                  # Python AI orchestrators
│   └── agent.py             # Main unified agent loop
├── specs/                   # Hardware requirement prompts (RAG sources)
│   ├── aes_128_spec.txt     # Example: Iterative AES-128 core
│   └── cxl_serdes_spec.txt  # Example: CXL serialize/deserialize accelerator
├── workspace/               # Active sandbox for AI generation
│   ├── Makefile             # Cocotb/Verilator compilation rules
│   └── design_spec.txt      # The active prompt file read by the agent
├── requirements.txt         # Python dependencies
└── .gitignore               # Ignores large EDA build artifacts




Prerequisites
Ensure your Linux environment has the following installed:

Python 3.12+ (with venv module)

Ollama (for local LLM serving)

Verilator (Built from source, v5.020+ recommended)

System dependencies: make, g++, git, python3-dev

Installation
Clone the repository:

Bash
git clone [https://github.com/YourUsername/AI-automation-agents.git](https://github.com/YourUsername/AI-automation-agents.git)
cd AI-automation-agents
Pull the local LLM model:
We use Qwen 2.5 Coder 7B due to its exceptional performance in Verilog/Python generation while remaining within an 8GB VRAM footprint.

Bash
ollama run qwen2.5-coder:7b
# Type /bye to exit once downloaded
Set up the Python environment:

Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Note: SiliconCompiler will automatically download the ASAP7 PDK and backend EDA tools (OpenROAD, Yosys) during its first successful run.

Usage
Always run the agent from within the workspace/ directory to contain build artifacts.

Start the Ollama server in the background (if not already running):

Bash
ollama serve
Define your hardware specification. Copy your target architecture (e.g., a serialize/deserialize accelerator for a CXL platform) into the active workspace prompt:

Bash
cd workspace
cp ../specs/cxl_serdes_spec.txt design_spec.txt
Activate your environment and execute the agent loop:

Bash
source ../venv/bin/activate
python3 ../agents/agent.py
Output Artifacts
Upon a successful iteration, the agent will populate the workspace/ directory with:

dut.v: The verified Verilog source code.

testbench.py: The Cocotb verification suite.

dump.vcd: The waveform trace of the simulation.

build/my_module/job0/export/0/outputs/my_module.gds: The final physical layout geometry.
