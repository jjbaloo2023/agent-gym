#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg bzip2 python3-venv gmsh python3-gmsh
curl -fsSL https://dl.openfoam.org/gpg.key -o /usr/share/keyrings/openfoam.asc
printf '%s\n' 'deb [arch=amd64 signed-by=/usr/share/keyrings/openfoam.asc] http://dl.openfoam.org/ubuntu noble main' > /etc/apt/sources.list.d/openfoam.list
apt-get update
apt-get install -y --no-install-recommends openfoam14=20261008
if ! id gym >/dev/null 2>&1; then useradd --create-home --shell /bin/bash gym; fi
install -d -o gym -g gym /home/gym/agent-gym /home/gym/agent-gym-runs
if ! test -x /usr/local/bin/micromamba; then
    curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/latest -o /tmp/micromamba.tar.bz2
    tar -xjf /tmp/micromamba.tar.bz2 -C /tmp bin/micromamba
    install /tmp/bin/micromamba /usr/local/bin/micromamba
fi
MAMBA_ROOT_PREFIX=/opt/micromamba micromamba create -y -p /opt/agent-gym-cad -c conda-forge --strict-channel-priority python=3.11 freecad=2026.09.16=py311hb8dae88_0
python3 -m venv /opt/agent-gym-mcp
/opt/agent-gym-mcp/bin/pip install 'mcp==1.30.0'
