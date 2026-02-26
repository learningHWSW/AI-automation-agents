import os
import sys
import subprocess
import siliconcompiler
import vcdvcd
from openai import OpenAI

# Connect to local Ollama instance (Qwen 2.5 Coder 7B)
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama', 
)

SYSTEM_PROMPT = """
You are an expert hardware design agent. 
1. Output Verilog code strictly inside /// VERILOG START and /// VERILOG END tags.
2. Output Cocotb (Python) testbench strictly inside /// PYTHON START and /// PYTHON END tags.
3. The top module MUST be named 'my_module'.
4. Do not include markdown formatting (like ```verilog) inside the tags.
"""

def extract_failing_waveform(vcd_file="dump.vcd", num_ticks=10):
    """Reads the VCD and creates an ASCII table of the final clock cycles."""
    if not os.path.exists(vcd_file):
        return "[Waveform dump not found. Ensure WAVES=1 is set.]"

    try:
        vcd = vcdvcd.VCDVCD(vcd_file)

        # Get all signal names
        signals = vcd.signals

        # Find the maximum timestamp (where the simulation crashed/stopped)
        max_time = vcd.endtime
        start_time = max(0, max_time - num_ticks * 10) # Roughly last N ticks

        # Format as a Markdown Table for the LLM
        wave_text = "\n### Waveform State Prior to Failure (Last few ticks):\n"
        wave_text += "| Time | " + " | ".join([sig.replace('TOP.my_module.', '') for sig in signals]) + " |\n"
        wave_text += "|" + "---|" * (len(signals) + 1) + "\n"

        # Sample the signals at integer time steps at the end of the simulation
        for t in range(int(start_time), int(max_time) + 1, 5): # Step by 5 time units
            row = [str(t)]
            for sig in signals:
                # vcdvcd allows querying the value of a signal at a specific time
                val = vcd[sig][t]
                row.append(str(val))
            wave_text += "| " + " | ".join(row) + " |\n"

        return wave_text

    except Exception as e:
        return f"[Failed to parse waveform: {e}]"

def generate_code(prompt, history=[]):
    """Sends the prompt and error history to the local LLM."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model="qwen2.5-coder:7b",
        messages=messages,
        temperature=0.1
    )
    return response.choices[0].message.content

def extract_and_save(text):
    """Parses the LLM output and writes dut.v and testbench.py."""
    if "/// VERILOG START" in text:
        v_code = text.split("/// VERILOG START")[1].split("/// VERILOG END")[0]
        with open("dut.v", "w") as f: f.write(v_code.strip())
        print("[*] Saved dut.v")
        
    if "/// PYTHON START" in text:
        p_code = text.split("/// PYTHON START")[1].split("/// PYTHON END")[0]
        with open("testbench.py", "w") as f: f.write(p_code.strip())
        print("[*] Saved testbench.py")

def run_verification():
    """Compiles the Verilog and runs the Cocotb testbench using Verilator."""
    print("[*] Compiling and running simulation via Verilator...")
    subprocess.run(["make", "clean"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = subprocess.run(["make", "WAVES=1"], capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr

def run_silicon_compiler(module_name='my_module', source_file='dut.v'):
    """Native execution of the ASAP7 physical design flow."""
    print("\n===================================================")
    print("  Starting SiliconCompiler Backend Flow (ASAP7)  ")
    print("===================================================")
    
    try:
        # 1. Initialize the chip object
        chip = siliconcompiler.Chip(module_name)
        
        # 2. Add the verified Verilog file
        chip.input(source_file)
        
        # 3. Configure for the ASAP7 7nm predictive PDK
        chip.load_target('asap7_demo')
        
        # 4. Set design constraints
        chip.clock('clk', period=1.0) # 1GHz target
        chip.set('constraint', 'density', 50) # 50% core utilization
        
        # 5. Execute the automated ASIC flow natively
        print("[*] Running 7nm physical design flow (Synthesis -> GDSII)...")
        chip.run()
        
        print("\n[*] ASAP7 7nm Layout Complete!")
        chip.summary()
        return True
        
    except Exception as e:
        print(f"\n[FAIL] SiliconCompiler encountered an error: {e}")
        return False

def main():
    print("===================================================")
    print("  Open-Source Chip Agent (Unified Flow Edition)  ")
    print("===================================================")
    
    prompt_file = "design_spec.txt"
    
    try:
        with open(prompt_file, "r") as f:
            task = f.read().strip()
            
        if not task:
            print(f"[FAIL] {prompt_file} is empty. Please add your hardware spec.")
            sys.exit(1)
            
        print(f"[*] Successfully loaded specification from {prompt_file}")
        print(f"[*] Prompt length: {len(task)} characters\n")
        
    except FileNotFoundError:
        print(f"[FAIL] Could not find '{prompt_file}' in the current directory.")
        sys.exit(1)

    history = []
    
    for iteration in range(5):
        print(f"\n--- Iteration {iteration+1} ---")
        print("Agent is reading the spec and writing code...")
        
        response = generate_code(task, history)
        extract_and_save(response)
        
        ret_code, log = run_verification()
        
        if ret_code == 0 and "TESTS=1 PASS=1" in log:
            print("[SUCCESS] Verilator compiled successfully and Cocotb tests passed!")
            run_silicon_compiler()
            break
        else:
            print("[FAIL] Bug detected. Extracting waveforms and feeding back to agent...")

            # 1. Parse the waveform
            wave_data = extract_failing_waveform()

            # 2. Combine the console error with the visual waveform data
            error_msg = f"The simulation failed with these assertions/errors:\n\n{log[-1000:]}\n\n"
            error_msg += f"Here is the waveform data leading up to the failure:\n{wave_data}\n\n"
            error_msg += "Analyze the timing diagram. Did a signal change on the wrong clock edge? Please fix the Verilog code."

            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": error_msg})
    else:
        print("\n[STOP] Reached 5 iterations without a fix.")

if __name__ == "__main__":
    main()
