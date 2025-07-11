#!/usr/bin/env python3
import libtmux
import configparser
import os
import argparse
import time

SESSION_NAME = "BICSession"
PYTHON_EXECUTABLE = "python3"
ROOT_EXECUTABLE = "root -l -q"
PRODUCER_SCRIPT = "ASTROPIXv3Producer.py"
DECODER_SCRIPT = "decode_online.cpp"

def parse_ini_for_producers(ini_path):
    config = configparser.ConfigParser()
    config.read(ini_path)

    producers = config.get('RunControl', 'dataproducers').split(',')
    outdir = config.get('RunControl', 'outdir', fallback='.')
    #runno = "test"
    #runno = config.get('RunControl', 'RunNumber', fallback=runno)

    parsed = []
    last_config = {}

    for prod in producers:
        section = f"Producer.{prod.strip()}"
        options = dict(config.items(section))

        full_config = {}
        for key, val in options.items():
            val = val.strip()
            if val.upper() == "SAME":
                full_config[key] = last_config.get(key)
            else:
                full_config[key] = val

        last_config = full_config
        parsed.append((prod.strip(), full_config))

    return parsed, outdir

def build_args(config_dict, outdir):
    args = []
    for key, val in config_dict.items():
        if key in ["fpga_index", "plane"]:
            continue
        elif key in ["serial"]:
            args.append(val)
        elif key in ["saveascsv"]:
            if val.lower() == "true":
                args.append(" -c")
        else:
            args.extend([f"--{key}", val])
    
    args.append(f"--outdir {outdir}")
    return " ".join(args)

def start_tmux_producers(ini_file):
    server = libtmux.Server()
    if server.has_session(SESSION_NAME):
        server.kill_session(SESSION_NAME)

    session = server.new_session(session_name=SESSION_NAME, window_name="placeholder", kill_session=True)

    producers, outdir = parse_ini_for_producers(ini_file)
    if os.path.exists(outdir):
        #print(f"Output directory '{outdir}' already exists. Modify \'outdir\' at {ini_file}.")
        #exit(1)
        new_outdir = f"{outdir}_{time.strftime('%Y%m%d-%H%M%S')}"
        print(f"Output directory '{outdir}' already exists. Saving to '{new_outdir}' instead.")
        os.makedirs(new_outdir, exist_ok=True)
        outdir = new_outdir
    else:
        os.makedirs(outdir, exist_ok=True)
        print(f"Output directory '{outdir}' created.")

    for i, (name, config) in enumerate(producers):
        args = build_args(config, outdir)
        win = session.new_window(attach=False, window_name=name)
        win.active_pane.send_keys(f"{PYTHON_EXECUTABLE} {PRODUCER_SCRIPT} {args}")

    """

    win = session.new_window(attach=False, window_name="Decoder")

    top_pane = win.active_pane
    pane_list = [top_pane]

    # 상단 나머지 pane 분할 (수직)
    for i, (name, config) in enumerate(producers):
        new_pane = pane_list[-1].split()
        filename = os.path.join(outdir, f"{config['name']}.log")
        new_pane.send_keys(f"{ROOT_EXECUTABLE} '{DECODER_SCRIPT}(\"{filename}\")'")
        pane_list.append(new_pane)

    # 상단 전체를 기준으로 수평 분할 → 아래 pane 생성
    #bottom_pane = top_pane.split_window(attach=False, vertical=True)
    #bottom_pane.send_keys("echo 'Bottom pane ready'")

    
    """

    # Remove the placeholder window
    placeholder = session.find_where({"window_name": "placeholder"})
    if placeholder:
        placeholder.kill()

    print(f"tmux session '{SESSION_NAME}' created with {len(producers)} windows.")
    os.system(f"tmux attach -t {SESSION_NAME}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Astropix Driver Code')
    parser.add_argument('ini', type=str, help='Path to the INI file for configuration.')
    args = parser.parse_args()
    start_tmux_producers(args.ini)


