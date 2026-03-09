# AutonomousRacer
Converting a AWS Deepracer into and autonomous navigator using VIO of an iphone 

Docker DevContainer Setup:

Prereqs:
* Docker Desktop
* VScode
* Github

Clone the repo
Install Docker Desktop (verify docker is running using docker ps)
Open Vscode
Install Vscode DevContainer Extension -> Use prerelease version!! 
Hit reopen in container!

## DeepRacer Linux Access via Docker

This repo now includes a dedicated Docker access container so you can manage the DeepRacer Linux host from your local Linux environment.

### 1) Configure target connection

```bash
cp .env.deepracer.example .env.deepracer
```

Edit `.env.deepracer`:
- `DEEPRACER_HOST`: IP address of your car
- `DEEPRACER_USER`: SSH user (default `ubuntu`)
- `DEEPRACER_PORT`: SSH port (default `22`)
- `DEEPRACER_KEY`: optional key path inside container (example `/home/druser/.ssh/id_rsa`)

### 2) Build + run access container

```bash
./scripts/deepracerAccess/up.sh
```

### 3) Open Linux shell in access container

```bash
./scripts/deepracerAccess/shell.sh
```

### 4) SSH directly to DeepRacer from container

```bash
./scripts/deepracerAccess/ssh.sh
```

### 5) Copy files to/from DeepRacer

```bash
./scripts/deepracerAccess/scp_to_car.sh <local_path> <remote_path>
./scripts/deepracerAccess/scp_from_car.sh <remote_path> <local_path>
```

### 6) Stop the access container

```bash
./scripts/deepracerAccess/down.sh
```

### Notes
- Compose file: `docker-compose.deepracer.yml`
- Image Dockerfile: `docker/deepracer-access/Dockerfile`
- Your host `~/.ssh` is mounted read-only into the container at `/home/druser/.ssh`

