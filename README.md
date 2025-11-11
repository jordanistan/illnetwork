<div align="center" id="top"> 
  <img src="https://raw.githubusercontent.com/jordanistan/ill.network/main/assets/img/logo.png" alt="illnet.ai" />

  &#xa0;

  <h1 align="center">illnet.ai Security Scanner</h1>
</div>

<p align="center">
  <img alt="Github top language" src="https://img.shields.io/github/languages/top/jordanistan/illnetwork?color=00ffff">
  <img alt="Repository size" src="https://img.shields.io/github/repo-size/jordanistan/illnetwork?color=00ffff">
  <img alt="License"
src="https://img.shields.io/github/license/jordanistan/illnetwork?color=00ffff">
</p>

<p align="center">
  <a href="#dart-about">About</a> &#xa0; | &#xa0; 
  <a href="#sparkles-features">Features</a> &#xa0; | &#xa0;
  <a href="#rocket-technologies">Technologies</a> &#xa0; | &#xa0;
  <a href="#checkered_flag-starting">Starting</a> &#xa0; | &#xa0;
  <a href="#memo-license">License</a> &#xa0; | &#xa0;
  <a href="https://github.com/jordanistan" target="_blank">Author</a>
</p>

<br>

## :dart: About ##

**illnet.ai Security Scanner** is a comprehensive security and health audit tool for Linux systems. It's designed to be run from a Docker container, allowing you to scan local or remote hosts for a wide range of vulnerabilities and misconfigurations. The scanner provides a detailed report with remediation suggestions to help you secure your systems.

The web interface provides a user-friendly way to view scan reports and manage the scanner.

## :sparkles: Features ##

:heavy_check_mark: **Comprehensive System Audit:** Checks for out-of-date packages, kernel security parameters, world-writable files, and risky sudo configurations.
:heavy_check_mark: **Network Exposure Scanning:** Uses `nmap` to scan for open ports and identify running services.
:heavy_check_mark: **Docker Security Analysis:**
    - Scans Docker images for known vulnerabilities using `Trivy`.
    - Detects containers running with `--privileged` or `--net=host` flags.
:heavy_check_mark: **Web Server Audits:** Checks for missing security headers on detected web servers.
:heavy_check_mark: **Automated Remediation Plan:** Generates a shell script with recommended commands to fix identified issues.
:heavy_check_mark: **Web Interface:** A modern, responsive web interface to view and manage scan results.

## :rocket: Technologies ##

The following tools were used in this project:

- **Frontend:** HTML, CSS (SASS), JavaScript
- **Backend/Scanner:** Bash, Docker
- **Security Tools:** `nmap`, `trivy`, `rkhunter`, `chkrootkit`, and more.

## :white_check_mark: Requirements ##

Before starting :checkered_flag:, you need to have [Git](https://git-scm.com) and [Docker](https://www.docker.com) installed.

## :checkered_flag: Starting ##

```bash
# Clone this project
$ git clone https://github.com/jordanistan/illnetwork

# Access
$ cd illnetwork

# Build and run the application
$ docker compose up --build

# The web interface will be available at http://localhost:8080
# The scanner can be run by executing the healthcheck.sh script inside the container.
```

To run a scan on a remote host, you can use `docker compose exec`:

```bash
# Run a scan on a remote host (replace <remote_host> with the IP or hostname)
$ docker compose exec app ./healthcheck.sh -t <remote_host>
```

Scan reports and remediation plans will be saved in the `reports` directory.

## :memo: License ##

This project is under the MIT License. For more details, see the [LICENSE](LICENSE) file.

Made with :heart: by <a href="https://github.com/jordanistan" target="_blank">Jordanistan</a>

&#xa0;

<a href="#top">Back to top</a>
