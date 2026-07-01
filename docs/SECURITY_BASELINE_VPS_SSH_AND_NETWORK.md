# 🔐 VPS Security Baseline

## SSH, Firewall, Access Model

### Scope

This document describes the **baseline security configuration** applied to all VPS nodes in the project.
Its purpose is to make it **explicit, reproducible, and auditable** what security controls are enabled on each node.

This is **architecture documentation**, not an incident report.

---

## 🧱 Security Principles

The VPS security model is built on the following principles:

1. **No password-based SSH access**
2. **No direct root access**
3. **Minimal exposed network surface**
4. **Explicit access paths**
5. **Defense-in-depth (SSH + UFW + Fail2Ban)**

---

## 👤 User & Privilege Model

### Dedicated administrative user

Each VPS has a **dedicated administrative user** instead of using `root`:

Example:

```
okx-hft-timescaledb
okx-hft-ops
```

Properties:

* member of `sudo` group
* SSH access via **public key only**
* no password-based remote access

Root account:

* **SSH login disabled**
* used only indirectly via `sudo`

---

## 🔑 SSH Authentication Model

### Authentication rules

SSH access is restricted to **public key authentication only**.

Password-based mechanisms are explicitly disabled:

* password authentication
* keyboard-interactive authentication
* PAM-based password fallbacks

---

### Canonical SSH configuration

All nodes include a dedicated hardening file:

```
/etc/ssh/sshd_config.d/99-hardening.conf
```

#### Content

```ini
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM yes

AuthenticationMethods publickey
```

> `AuthenticationMethods publickey` enforces key-only access regardless of other SSH/PAM defaults.

---

### Validation

Effective SSH configuration is validated using:

```bash
sshd -T
```

Expected properties:

* root login disabled
* only `publickey` authentication method allowed
* password-based access impossible

---

## 🛡 Brute-force Protection (Fail2Ban)

### Purpose

Fail2Ban is used as a **secondary control** to automatically block IPs attempting repeated SSH authentication failures.

### Configuration

* Enabled system-wide
* SSH jail active
* Default ban thresholds used

Commands:

```bash
systemctl enable --now fail2ban
fail2ban-client status
fail2ban-client status sshd
```

Fail2Ban is not relied upon as the primary defense;
it complements the key-only SSH model.

---

## 🔥 Network Security (UFW)

### Default firewall policy

```bash
Incoming: deny
Outgoing: allow
Routed: deny
```

### Allowed traffic

Only explicitly required ports are opened.

Typical pattern:

* SSH (`22/tcp`)
* Monitoring ports restricted by source IP
* Application ports exposed only when necessary

Firewall state is verified via:

```bash
ufw status numbered
```

---

## 🐳 Docker & Service Exposure

### Principles

* Databases are **not exposed directly**
* Access via internal Docker networks or local loopback
* Exporters and metrics endpoints restricted via firewall rules
* External exposure only through controlled entry points

---

## 🔄 Change Management

Any security-related changes must satisfy:

* SSH config validation via `sshd -t`
* Successful key-based login test
* No password-based login possible
* Services remain operational after restart

---

## ✅ Security Baseline Summary

Each VPS following this baseline guarantees:

* 🔒 Root account not accessible via SSH
* 🔑 SSH access only via public key
* 🚫 Password-based login impossible
* 🛡 Automated brute-force blocking
* 🔥 Minimal exposed network surface
* 🐳 Controlled service exposure

This document serves as the **source of truth** for VPS security configuration.

---

## 📌 Notes on Public Repositories

This document is safe for **public repositories** because it:

* does **not** expose IP addresses
* does **not** describe vulnerabilities
* does **not** include credentials or secrets
* documents *what is enforced*, not *what was broken*

---

**Owner:** Dmitrii Soroka
**Status:** Active security baseline
**Last updated:** January 2026

---
