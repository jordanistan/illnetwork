#!/usr/bin/env bash
#
# ill.network Security Scanner
#
# v3.0 - 2025-11-11
#
# A comprehensive security and health scanner for Linux systems.
# Designed to be run locally or inside a Docker container to scan remote hosts.
#

set -uo pipefail
IFS=




$'\n\t'

# ---------- styling ----------
NC="\033[0m"; B="\033[1m"
G="\033[32m"; Y="\033[33m"; R="\033[31m"; C="\033[36m"; M="\033[35m"
ok(){ printf "${G}[GOOD]${NC} %s\n" "$*"; }
warn(){ printf "${Y}[WARN]${NC} %s\n" "$*"; }
bad(){ printf "${R}[BAD] ${NC} %s\n" "$*"; }
info(){ printf "${C}[-]${NC} %s\n" "$*"; }
head(){ printf "\n${B}${M}=== %s ===${NC}\n" "$*"; }

TS="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
HOST="$(hostname)"
REMDOC="/root/hardening_recommendations.sh"
: > "$REMDOC" || true

append_fix () {
  printf "%s\n" "$*" >> "$REMDOC"
}

require_cmd () {
  command -v "$1" >/dev/null 2>&1
}

# allowlist for listeners publicly exposed (edit if you know you need others)
ALLOW_WAN_TCP_PORTS_DEFAULT="22 80 443 51413"   # ssh, http, https, transmission peer
ALLOW_WAN_UDP_PORTS_DEFAULT="51413"             # transmission peer
WAN_IF="$(ip -o -4 route show to default | awk '{print $5}' | head -n1 || true)"

head "Context"
printf "%s\n" "Time: $TS"
printf "Host: %s | Kernel: %s | Distro: " "$HOST" "$(uname -r)"
[ -f /etc/os-release ] && . /etc/os-release && printf "%s %s\n" "$NAME" "$VERSION" || echo "unknown"

# ---------- APT repo sanity & updates ----------
head "APT sources & updates"
grep -Rni 'kali' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null | sed -n '1,12p' || true
if grep -Rqi 'kali' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null; then
  bad "Kali repo detected alongside Debian. This causes libaudit/auditd conflicts."
  append_fix "# Disable Kali repos (comment lines), then repair and upgrade"
  append_fix "sudo sed -i.bak 's/^\\s*deb .*kali/# &/I' /etc/apt/sources.list"
  append_fix "sudo find /etc/apt/sources.list.d -maxdepth 1 -type f -exec sudo sed -i.bak 's/^\\s*deb .*kali/# &/I' {} \\;"
  append_fix "sudo apt update && sudo apt -f install && sudo apt full-upgrade -y"
else
  ok "No Kali sources detected (good)."
fi

UPG=$(apt-get -s upgrade 2>/dev/null | grep -c '^Inst' || echo 0)
if [ "$UPG" -gt 0 ]; then
  warn "$UPG packages can be upgraded."
  append_fix "# Apply security/bugfix updates"
  append_fix "sudo apt update && sudo apt full-upgrade -y"
else
  ok "No pending package upgrades."
fi

# ---------- Second opinions & preload tricks ----------
head "Rootkit second opinions & preload tricks"

if require_cmd rkhunter; then
  info "rkhunter present – running terse check..."
  sudo rkhunter --update >/dev/null 2>&1 || true
  RKH=$(sudo rkhunter --check --sk --rwo 2>/dev/null | sed -n '1,120p')
  if [ -n "$RKH" ]; then
    printf "%s\n" "$RKH"
    if echo "$RKH" | grep -qi "warning"; then
      warn "rkhunter reported warnings above (review)."
    else
      ok "rkhunter: no warnings in snippet above."
    fi
  else
    ok "rkhunter: no noteworthy output."
  fi
else
  warn "rkhunter not installed."
  append_fix "sudo apt install -y rkhunter && sudo rkhunter --update && sudo rkhunter --propupd"
fi

if require_cmd chkrootkit; then
  info "chkrootkit present – scanning..."
  CHKRAW="$(sudo chkrootkit 2>/dev/null || true)"
  # count only real 'INFECTED' not 'not infected'
  CHK_HITS=$(printf "%s\n" "$CHKRAW" | awk 'toupper($0) ~ /INFECTED/ && tolower($0) !~ /not infected/' | wc -l)
  printf "%s\n" "$CHKRAW" | sed -n '1,120p'
  if [ "$CHK_HITS" -eq 0 ]; then
    ok "chkrootkit: no hits."
  else
    bad "chkrootkit: $CHK_HITS suspicious hits."
  fi
else
  warn "chkrootkit not installed (Debian: apt install chkrootkit)."
  append_fix "sudo apt install -y chkrootkit"
fi

if require_cmd debsums; then
  info "debsums (silent missing files only)..."
  DS="$(sudo debsums -s 2>/dev/null || true)"
  if [ -z "$DS" ]; then
    ok "debsums: all files present."
  else
    warn "debsums reported missing files (first 20 shown):"
    printf "%s\n" "$DS" | sed -n '1,20p'
    append_fix "# Reinstall or purge noisy packages reported by debsums (example for LibreOffice)"
    append_fix "sudo apt install --reinstall -y libreoffice-draw libreoffice-impress libreoffice-math libreoffice-writer || true"
    append_fix "# If not needed:"
    append_fix "sudo apt purge -y 'libreoffice-*' && sudo apt autoremove -y"
  fi
else
  warn "debsums not installed."
  append_fix "sudo apt install -y debsums && sudo debsums -s"
fi

# unhide
if require_cmd unhide; then
  info "unhide quick (hidden procs/ports)..."
  UH="$(sudo unhide quick 2>/dev/null || true)"
  if echo "$UH" | grep -qi "Found"; then
    bad "unhide found anomalies:"
    printf "%s\n" "$UH" | sed -n '1,120p'
  else
    ok "unhide: no hidden procs/ports reported."
  fi
else
  warn "unhide not installed."
  append_fix "sudo apt install -y unhide"
fi

# preload tricks
if [ -f /etc/ld.so.preload ]; then
  PL=$(sudo grep -vE '^\s*(#|$)' /etc/ld.so.preload || true)
  if [ -z "$PL" ]; then
    ok "/etc/ld.so.preload exists but is empty (ok)."
  else
    bad "/etc/ld.so.preload contains entries:"
    printf "%s\n" "$PL"
    append_fix "# Investigate and clear suspicious preload entries"
    append_fix "sudo cp /etc/ld.so.preload{,.bak} && echo > /etc/ld.so.preload"
  fi
else
  ok "/etc/ld.so.preload not present (good)."
fi

# suspicious dot-dirs
info "Suspicious hidden dot-dirs (depth<=2) under /dev /etc /usr:"
sudo find /dev /etc /usr -maxdepth 2 -type d -name '.*' -printf '%p\n' 2>/dev/null | sort | sed -n '1,60p' || true

# ---------- Process & sockets cross-check ----------
head "Process & sockets"
info "Top 25 via coreutils ps:"
ps axwwo pid,ppid,user,stat,etime,command | sed -n '1,25p'
if require_cmd busybox; then
  info "Top 25 via busybox ps:"
  busybox ps w | sed -n '1,25p'
else
  warn "busybox not installed; skipping ps cross-check."
  append_fix "sudo apt install -y busybox"
fi

# Listening sockets
info "Listening sockets (first 80):"
sudo ss -lptn 2>/dev/null | sed -n '1,80p'

# Flag public listeners (0.0.0.0 or :::) not in allowlist
ALLOW_TCP="${ALLOW_WAN_TCP_PORTS_DEFAULT}"
ALLOW_UDP="${ALLOW_WAN_UDP_PORTS_DEFAULT}"

PUB=$(sudo ss -ltnpH 2>/dev/null | awk '$4 ~ /(^0\.0\.0\.0:|^\[::\]:)/{print}' || true)
if [ -n "$PUB" ]; then
  head "Public TCP listeners"
  printf "%s\n" "$PUB"
  # extract disallowed ports
  DIS=$(printf "%s\n" "$PUB" | awk '{split($4,a,":"); p=a[length(a)]; print p}' \
      | grep -v -E "(^$(echo "$ALLOW_TCP" | sed 's/ /$|^/g')$)" || true)
  if [ -n "$DIS" ]; then
    bad "These TCP ports are publicly listening and NOT in allowlist: $(echo "$DIS" | sort -u | xargs)"
    append_fix "# If you do not intend public access, rebind these to 127.0.0.1 and proxy via NPM"
    for P in $(echo "$DIS" | sort -u); do
      append_fix "# Example: docker run ... -p 127.0.0.1:${P}:${P} ..."
    done
  else
    ok "All public TCP listeners match the allowlist ($ALLOW_TCP)."
  fi
else
  ok "No public TCP listeners detected."
fi

PUBU=$(sudo ss -lunpH 2>/dev/null | awk '$4 ~ /(^0\.0\.0\.0:|^\[::\]:)/{print}' || true)
if [ -n "$PUBU" ]; then
  head "Public UDP listeners"
  printf "%s\n" "$PUBU"
  DISU=$(printf "%s\n" "$PUBU" | awk '{split($4,a,":"); p=a[length(a)]; print p}' \
      | grep -v -E "(^$(echo "$ALLOW_UDP" | sed 's/ /$|^/g')$)" || true)
  if [ -n "$DISU" ]; then
    bad "These UDP ports are public and NOT in allowlist: $(echo "$DISU" | sort -u | xargs)"
    append_fix "# If you do not intend public access, restrict these UDP services or bind to LAN only."
  else
    ok "All public UDP listeners match the allowlist ($ALLOW_UDP)."
  fi
else
  ok "No public UDP listeners detected."
fi

# ---------- Docker / CasaOS exposure & secrets ----------
head "Docker exposure & secrets"

if require_cmd docker; then
  info "Containers using host networking:"
  while read -r line; do
    [ -z "$line" ] && continue
    nm=$(echo "$line" | awk '{print $2}')
    echo "$line"
    bad "Host network container detected: $nm"
    append_fix "# Recreate ${nm} without --network host; bind to 127.0.0.1 and front with NPM if needed."
  done < <(for c in $(sudo docker ps -q); do
              m=$(sudo docker inspect -f '{{.HostConfig.NetworkMode}} {{.Name}}' "$c" 2>/dev/null)
              [ "${m%% *}" = "host" ] && echo "$m"
           done)

  info "Containers exposing 0.0.0.0 (public):"
  sudo docker ps --format '{{.Names}} {{.Ports}}' \
    | awk '/0\.0\.0\.0/ {print}' || true

  # Secret-like envs (do not print values)
  info "Containers with envs named key/token/secret/password (names only):"
  for c in $(sudo docker ps -q); do
    name=$(sudo docker inspect -f '{{.Name}}' "$c" | sed 's#^/##')
    envs=$(sudo docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$c" | egrep -i '(^[^=]*(key|token|secret|password)[^=]*=)' | cut -d= -f1 | sort -u)
    [ -n "$envs" ] && printf "%-25s -> %s\n" "$name" "$envs"
  done

  # Specific scan for OPENAI_API_KEY placeholders that look like 'sk-xxxxxx'
  info "OPENAI_API_KEY length check (9 chars indicates placeholder):"
  for c in $(sudo docker ps -q); do
    name=$(sudo docker inspect -f '{{.Name}}' "$c" | sed 's#^/##')
    val=$(sudo docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$c" | awk -F= '$1=="OPENAI_API_KEY"{print $2}')
    [ -n "$val" ] && echo "$name: ${#val} chars"
  done

  # Known bad image we removed before
  if sudo docker images --format '{{.Repository}}:{{.Tag}}' | grep -q '^wisdomsky/cloudflared-web:'; then
    bad "wisdomsky/cloudflared-web image still present."
    append_fix "sudo docker image rm wisdomsky/cloudflared-web:latest || true"
  else
    ok "wisdomsky/cloudflared-web image not present."
  fi
else
  warn "Docker not installed or not accessible; skipping container checks."
fi

# ---------- Firewall posture for Docker (DOCKER-USER) ----------
head "Firewall posture (DOCKER-USER chain)"

if require_cmd iptables; then
  if sudo iptables -S DOCKER-USER >/dev/null 2>&1; then
    ok "DOCKER-USER chain exists. Rules:"
    sudo iptables -S DOCKER-USER | sed -n '1,40p'
  else
    warn "DOCKER-USER chain empty/missing (Docker can bypass UFW)."
    append_fix "# Tighten WAN -> containers; allow 80/443 (+ any ports you need), drop the rest"
    append_fix 'WAN_IF=$(ip -o -4 route show to default | awk '"'"'{print $5}'"'"' | head -n1)'
    append_fix 'sudo iptables -I DOCKER-USER -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT'
    append_fix 'sudo iptables -I DOCKER-USER -s 10.0.0.0/8 -j ACCEPT'
    append_fix 'sudo iptables -I DOCKER-USER -s 172.16.0.0/12 -j ACCEPT'
    append_fix 'sudo iptables -I DOCKER-USER -s 192.168.0.0/16 -j ACCEPT'
    append_fix 'sudo iptables -I DOCKER-USER -i "$WAN_IF" -p tcp --dport 80  -j ACCEPT'
    append_fix 'sudo iptables -I DOCKER-USER -i "$WAN_IF" -p tcp --dport 443 -j ACCEPT'
    append_fix '# Optional: Transmission peer if you need WAN peers'
    append_fix 'sudo iptables -I DOCKER-USER -i "$WAN_IF" -p tcp --dport 51413 -j ACCEPT'
    append_fix 'sudo iptables -I DOCKER-USER -i "$WAN_IF" -p udp --dport 51413 -j ACCEPT'
    append_fix 'sudo iptables -I DOCKER-USER -i "$WAN_IF" -j DROP'
  fi
else
  warn "iptables not present; skipping DOCKER-USER checks."
fi

# ---------- Auditd feasibility ----------
head "auditd feasibility"
AUDV_DEB=$(apt-cache policy libaudit1 2>/dev/null | sed -n '1,12p')
printf "%s\n" "$AUDV_DEB"
if grep -Rqi 'kali' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null; then
  warn "auditd install will fail until Kali is removed or pinned low."
  append_fix "# After disabling/pinning Kali, install auditd and add node exec watch"
  append_fix "sudo apt install -y auditd audispd-plugins"
  append_fix "echo '-w /usr/local/bin/node -p x -k node_exec' | sudo tee /etc/audit/rules.d/node.rules"
  append_fix "sudo augenrules --load && sudo systemctl enable --now auditd"
else
  ok "Repository set likely supports auditd. To install:"
  append_fix "sudo apt install -y auditd audispd-plugins"
  append_fix "echo '-w /usr/local/bin/node -p x -k node_exec' | sudo tee /etc/audit/rules.d/node.rules"
  append_fix "sudo augenrules --load && sudo systemctl enable --now auditd"
fi

# ---------- Final summary ----------
head "Summary (Good / Bad / Ugly)"

echo
echo "${B}Good:${NC}"
[ ! -f /etc/ld.so.preload ] && echo " - No ld.so.preload abuse."
[ -z "${DS:-}" ] && echo " - debsums OK or not installed."
[ "$UPG" -eq 0 ] && echo " - No pending upgrades."
require_cmd docker && echo " - Docker inspection completed."
require_cmd iptables && sudo iptables -S DOCKER-USER >/dev/null 2>&1 && echo " - DOCKER-USER chain exists."

echo
echo "${B}Bad:${NC}"
grep -Rqi 'kali' /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null && echo " - Mixed Debian+Kali repos (breaks auditd & stability)."
[ -n "${DS:-}" ] && echo " - debsums missing files (see above)."
[ -n "$PUB" ] && [ -n "$DIS" ] && echo " - Public TCP listeners beyond allowlist."
[ -n "$PUBU" ] && [ -n "$DISU" ] && echo " - Public UDP listeners beyond allowlist."
require_cmd docker && sudo docker ps --format '{{.Names}} {{.Ports}}' | grep -q '0.0.0.0' && echo " - Containers published to 0.0.0.0 (consider binding to 127.0.0.1 + NPM)."

echo
echo "${B}Ugly (needs attention):${NC}"
if require_cmd docker; then
  if sudo docker images --format '{{.Repository}}' | grep -q '^wisdomsky/cloudflared-web$'; then
    echo " - Untrusted image wisdomsky/cloudflared-web still present."
  fi
  # host network containers printed earlier; recheck count
  HN_COUNT=$(for c in $(sudo docker ps -q); do sudo docker inspect -f '{{.HostConfig.NetworkMode}}' "$c"; done | grep -c '^host$' || true)
  [ "$HN_COUNT" -gt 0 ] && echo " - $HN_COUNT container(s) using --network host."
fi

head "Remediation plan (written to $REMDOC)"
if [ -s "$REMDOC" ]; then
  nl -ba "$REMDOC" | sed -n '1,200p'
else
  ok "No critical remediation necessary. Keep monitoring and good hygiene."
fi

echo
info "Done. Review output above. Apply fixes found in: $REMDOC"
