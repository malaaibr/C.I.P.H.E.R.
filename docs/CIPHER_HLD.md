---
doc_version: 3.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# CIPHER — Cognitive Intelligent Platform for Holistic Embedded R&D Automation
## High-Level Design: Layered Software Architecture
### Local MVP Edition · Document ID: CIPHER-HLD-001 · Release R1.1 · 10 May 2026

---

> **Document Purpose.** This document describes the layered software architecture of the CIPHER platform for its Local MVP deployment. It is modeled after the AUTOSAR Layered Software Architecture document structure (AUTOSAR_EXP_LayeredSoftwareArchitecture R22-11) and the Agentic OS architectural pattern. It provides a top-down hierarchical view of the platform's seven software layers, maps every agent and platform component to exactly one layer, and defines the interaction rules between layers. The foundational Layer 1 — the **Deployment & Runtime Substrate (DRS)** — replaces the AUTOSAR "Microcontroller" concept with a software-owned, deployment-topology-independent contract that makes the entire stack portable across Docker Compose, Kubernetes, Nomad, and bare metal without changing any agent code. This document is informative and focused on static structural views. Dynamic interface specifications are provided in the individual agent LLD documents.

---

## Document Metadata

| Field | Value |
|---|---|
| Document Title | CIPHER Layered Software Architecture — High-Level Design |
| Document Owner | CIPHER Platform Team |
| Document Status | Release Candidate |
| Part of Standard | CIPHER Platform Specification |
| Release | R1.0 — Local MVP |
| Date | May 2026 |
| Companion Document | CIPHER_Architecture_v3.md (full architectural reference) |
| Reference Standard | AUTOSAR EXP LayeredSoftwareArchitecture R22-11 |
| Reference Pattern | Agentic OS Architecture (datasciencedojo.com) |

---

## Table of Contents

```
1.  Introduction
    1.1  Purpose and Inputs
    1.2  Scope and Extensibility
    1.3  Relationship to AUTOSAR Architecture

2.  Architecture — Overview of Software Layers
    2.1  Top View: The Three Master Layers
    2.2  Coarse View: Expanded Layer Stack
    2.3  Detailed View: Full CIPHER Layer Hierarchy
    2.4  Layer Interaction Matrix

3.  Architecture — Layer Definitions
    3.1  Layer 1 — Deployment & Runtime Substrate (DRS)
    3.2  Layer 2 — Platform Kernel (PKL)
    3.3  Layer 3 — Agent Runtime Environment (ARE)
    3.4  Layer 4 — Tool & Resource Fabric (TRF)
    3.5  Layer 5 — Memory & Knowledge Fabric (MKF)
    3.6  Layer 6 — Governance & Compliance Layer (GCL)
    3.7  Layer 7 — Application / Agent Layer (AAL)

4.  Architecture — Module Type Definitions
    4.1  Driver
    4.2  Interface
    4.3  Handler
    4.4  Manager
    4.5  Library

5.  Architecture — Whole-System HLD
    5.1  System Boundary and External Actors
    5.2  Full Layered Component Diagram
    5.3  Request Lifecycle — Normative Flow

6.  Architecture — Individual Agent HLDs
    6.1  Orchestrator Agent (AGT-000)
    6.2  DevNex Domain Agent (AGT-001)
    6.3  Planning Agent (AGT-002)
    6.4  ASIL Review Agent (AGT-003)
    6.5  Compliance Agent (AGT-004)
    6.6  Research Agent (AGT-005)
    6.7  Garvis Voice/UX Agent (AGT-006)
    6.8  Memory / Context Agent (AGT-007)
    6.9  Tool Broker Agent (AGT-008)

7.  Architecture — Interfaces: General Rules
    7.1  Layer Boundary Rules
    7.2  Upward Interface Rules
    7.3  Downward Interface Rules
    7.4  Lateral Interface Rules (A2A Escapes)

8.  Architecture — Interfaces: Interaction of Layers
    8.1  How the Application Layer communicates with ARE
    8.2  How ARE communicates with TRF and MKF
    8.3  How GCL cross-cuts all layers

9.  Configuration
    9.1  Domain Pack Configuration
    9.2  Agent Scope Configuration
    9.3  LLM Gateway Configuration

10. Integration and Runtime Aspects
    10.1  Startup Sequence (docker-compose)
    10.2  Shutdown and Graceful Drain
    10.3  Checkpoint and Resume
    10.4  Human-in-the-Loop Gate Runtime
```

---

## 1. Introduction

### 1.1 Purpose and Inputs

This document describes the software architecture of CIPHER using a layered approach modeled after the AUTOSAR Classic Platform Layered Software Architecture. Specifically it does three things: it describes in a top-down approach the hierarchical structure of CIPHER software, maps every platform component and agent to one of seven defined software layers, and shows the interaction relationships between those layers.

Just as AUTOSAR separates hardware-dependent code (MCAL) from hardware-independent application code through well-defined vertical layers and strictly controlled cross-layer interfaces, CIPHER separates deployment-topology-dependent code (the DRS) from domain-specific agent logic (the Application/Agent Layer) through seven vertical layers with equally strict interface rules. The critical distinction is that AUTOSAR's bottom layer is physical silicon that the software must adapt to, while CIPHER's bottom layer is a *software contract* that CIPHER owns and any deployment topology must satisfy.

This document focuses on static structural views. It does not specify a detailed software design with full dynamic interface descriptions — those are contained in the individual agent LLD documents. Examples given are representative, not exhaustive.

**Inputs.** This document is based on the CIPHER Architecture Reference Document v3.0, the DevNex Assistant HLD and LLD documents (`devnex_assistant/docs/HLD.md` and `LLD.md`), the AUTOSAR EXP LayeredSoftwareArchitecture R22-11, and the Agentic OS Architecture pattern.

### 1.2 Scope and Extensibility

**Application scope.** CIPHER is designed for embedded and automotive software R&D automation. The Local MVP targets a single developer workstation running a Docker Compose stack, with all agents, stores, and tool servers on localhost. The architecture is extensible to cloud-native multi-node deployments without changing agent contracts.

**CIPHER extensibility.** The CIPHER Software Architecture is a generic approach. Standard agents can be extended in functionality while remaining compliant with the Agent Card and A2A task contract. Non-standard domain agents can be integrated as long as they implement the `CIPHERAgent` base interface. Additional domain packs (new regulatory profiles) can be added without modifying the platform kernel layers. New software layers cannot be added — the seven-layer stack is fixed for MVP, mirroring AUTOSAR's constraint that further layers cannot be added.

### 1.3 Relationship to AUTOSAR Architecture

Understanding the mapping between AUTOSAR and CIPHER layers is the fastest way to internalize the CIPHER architecture for engineers already familiar with AUTOSAR. The table below establishes this conceptual bridge.

| AUTOSAR Layer | CIPHER Analog | Rationale |
|---|---|---|
| Microcontroller | Deployment & Runtime Substrate (DRS) | The lowest CIPHER-owned layer — the deployment topology contract. Exposes four typed primitives (compute, network, storage, secret fabric) upward through `cipher.core.substrate`, making all higher layers completely independent of whether they run on a developer laptop, an on-prem server, or a Kubernetes cluster |
| Microcontroller Abstraction Layer (MCAL) | Platform Kernel (PKL) | Direct interaction with the substrate; provides a deployment-independent interface upward |
| ECU Abstraction Layer | Tool & Resource Fabric (TRF) | Abstracts the specific tool (VectorCAST, DOORS, Git) from the agents that use them, just as ECU Abstraction abstracts the specific peripheral |
| Complex Drivers | Memory & Knowledge Fabric (MKF) | Spans from the DRS up to the Agent Layer; provides specialized cross-cutting capabilities (temporal knowledge graph, four-tier memory, hybrid retrieval) that don't fit the normal sequential layered path |
| Services Layer | Governance & Compliance Layer (GCL) | Highest layer of the "Basic Software" — provides cross-cutting services (policy, audit, identity) to all other layers |
| Runtime Environment (RTE) | Agent Runtime Environment (ARE) | The crucial decoupling layer — above it the architecture style changes from layered to component/agent style |
| Application Layer | Application / Agent Layer (AAL) | Domain-specialized agents that implement actual SDLC work |

The single most important insight from this mapping is the role of the **Agent Runtime Environment (ARE)**, which mirrors AUTOSAR's RTE exactly: above the ARE, the architecture style changes from layered to component style. Above the ARE, agents communicate with each other through typed A2A task contracts and are completely independent of which tool servers, storage backends, or deployment substrates are running underneath them.

---

## 2. Architecture — Overview of Software Layers

### 2.1 Top View: The Three Master Layers

At the highest abstraction level, CIPHER distinguishes three master software layers that run on any supported deployment target. This is the direct analog of AUTOSAR's three-layer top view (Application / RTE / Basic Software running on Microcontroller), with the Deployment & Runtime Substrate (DRS) replacing the Microcontroller as the foundational, topology-independent substrate contract.

```
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION / AGENT LAYER                  │
│           (Domain Agents: DevNex, Planner, Reviewer...)      │
├─────────────────────────────────────────────────────────────┤
│              AGENT RUNTIME ENVIRONMENT (ARE)                 │
│         (A2A Server, Task Contracts, OTel Spans)             │
├─────────────────────────────────────────────────────────────┤
│                    PLATFORM KERNEL (PKL)                     │
│   (Orchestrator, Memory, Tool Broker, Policy, Audit)         │
├─────────────────────────────────────────────────────────────┤
│           DEPLOYMENT & RUNTIME SUBSTRATE (DRS)               │
│  (Compute Fabric · Network Fabric · Storage Fabric ·         │
│   Secret Fabric — topology-independent contracts)            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Coarse View: Expanded Layer Stack

The Platform Kernel is further divided into the Governance & Compliance Layer, the Tool & Resource Fabric, the Memory & Knowledge Fabric, and the core Platform Kernel services. This mirrors AUTOSAR's coarse view that divides Basic Software into Services, ECU Abstraction, MCAL, and Complex Drivers. The Deployment & Runtime Substrate (DRS) sits beneath all of these, providing the topology-independent substrate contract the entire stack depends on.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       APPLICATION / AGENT LAYER  (AAL)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                    AGENT RUNTIME ENVIRONMENT  (ARE)                      │
├──────────────────────────────────────────────────┬──────────────────────┤
│          GOVERNANCE & COMPLIANCE LAYER  (GCL)    │                      │
├──────────────────────────────────────────────────┤  MEMORY &            │
│            TOOL & RESOURCE FABRIC  (TRF)         │  KNOWLEDGE           │
├──────────────────────────────────────────────────┤  FABRIC  (MKF)       │
│               PLATFORM KERNEL  (PKL)             │                      │
├──────────────────────────────────────────────────┴──────────────────────┤
│                 DEPLOYMENT & RUNTIME SUBSTRATE  (DRS)                    │
└─────────────────────────────────────────────────────────────────────────┘
```

The Memory & Knowledge Fabric (MKF) spans vertically from the DRS up to the Agent Layer — just as AUTOSAR's Complex Drivers span from the microcontroller directly up to the RTE. This reflects the fact that agents at every layer need access to memory services without routing through multiple intermediate abstractions for every read or write.

### 2.3 Detailed View: Full CIPHER Layer Hierarchy

The following diagram shows the complete seven-layer stack with its key modules at each level. This is the CIPHER equivalent of AUTOSAR's detailed view showing Communication Services, Memory Services, I/O Hardware Abstraction, MCAL modules, and so on.

```mermaid
flowchart TB
    subgraph AAL["Layer 7 — Application / Agent Layer (AAL)"]
        direction LR
        AGT000["Orchestrator\nAGT-000"]
        AGT001["DevNex\nAGT-001"]
        AGT002["Planning\nAGT-002"]
        AGT003["ASIL Review\nAGT-003"]
        AGT004["Compliance\nAGT-004"]
        AGT005["Research\nAGT-005"]
        AGT006["Garvis Voice\nAGT-006"]
        AGT011["Doc Agent\nAGT-011"]
    end

    subgraph ARE["Layer 6 — Agent Runtime Environment (ARE)"]
        direction LR
        A2ASRV["A2A Server\n(FastAPI)"]
        TASKCTRL["Task Contract\nValidator"]
        OTELSPAN["OTel Span\nEmitter"]
        AGTREG["Agent Registry\n(.well-known)"]
        BUDGET["Budget\nEnforcer"]
    end

    subgraph GCL["Layer 5 — Governance & Compliance Layer (GCL)"]
        direction LR
        OPA["Policy Engine\n(OPA / Rego)"]
        AUDIT["Audit Journal\n(append-only SQLite)"]
        HITL["HITL Gate\nManager"]
        IDENT["Identity\n(JWT / Ed25519)"]
        DOMPACK["Domain Pack\nLoader"]
    end

    subgraph TRF["Layer 4 — Tool & Resource Fabric (TRF)"]
        direction LR
        TOOLAGT["Tool Broker\nAGT-008"]
        MCPSRV["MCP Gateway\n(JSON-RPC)"]
        subgraph MCPTOOLS["MCP Tool Servers"]
            GIT_MCP["Git MCP\n:7211"]
            VC_MCP["VectorCAST MCP\n:7210"]
            DOORS_MCP["DOORS/ReqIF MCP\n:7212"]
            FS_MCP["Filesystem MCP\n:7214"]
            LLM_GW["LLM Gateway\n(LiteLLM / GCA)\n:7215"]
        end
    end

    subgraph MKF["Layer 3 — Memory & Knowledge Fabric (MKF)"]
        direction LR
        MEMAGT["Memory Agent\nAGT-007"]
        KG["Knowledge Graph\n(Memgraph)"]
        VEC["Vector Store\n(Qdrant embedded)"]
        WKMEM["Working Memory\n(Redis)"]
        DOCST["Document Store\n(SQLite)"]
        OBJST["Artifact Store\n(MinIO)"]
    end

    subgraph PKL["Layer 2 — Platform Kernel (PKL)"]
        direction LR
        NATS["Event Bus\n(NATS)"]
        LANGRAPH["Workflow Runtime\n(LangGraph)"]
        CKPT["Checkpoint Store\n(SQLite)"]
        LANGFUSE["Observability\n(Langfuse + OTel)"]
        ADAPTERS["Storage Adapters\ncipher.core.adapters"]
    end

    subgraph DRS["Layer 1 — Deployment & Runtime Substrate (DRS)"]
        direction LR
        COMPFAB["Compute Fabric\n(cipher.substrate.compute)"]
        NETFAB["Network Fabric\n(cipher.substrate.network)"]
        STORFAB["Storage Fabric\n(cipher.substrate.storage)"]
        SECFAB["Secret Fabric\n(cipher.substrate.secrets)"]
    end

    DRS --> PKL --> MKF --> TRF --> GCL --> ARE --> AAL
    MKF -. "cross-cuts" .-> AAL
    GCL -. "governs all" .-> TRF
    GCL -. "governs all" .-> ARE
    GCL -. "governs all" .-> AAL
```

### 2.4 Layer Interaction Matrix

This matrix defines which layers are permitted to communicate directly with which other layers. An "X" means direct communication is allowed; a blank means the layer must go through an intermediate layer. This is the CIPHER equivalent of AUTOSAR's Layer Interaction Matrix.

| From ↓  To → | DRS | PKL | MKF | TRF | GCL | ARE | AAL |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **DRS** | — | X | X | — | — | — | — |
| **PKL** | X | — | X | X | X | — | — |
| **MKF** | X | X | — | X | X | X | X |
| **TRF** | — | X | X | — | X | — | — |
| **GCL** | — | X | X | X | — | X | X |
| **ARE** | — | — | X | X | X | — | X |
| **AAL** | — | — | X | — | X | X | — |

The key rules encoded in this matrix are that no agent (AAL) may communicate directly with the Tool & Resource Fabric (TRF) — all tool calls must be mediated by the Tool Broker (TRF) through the ARE boundary. Agents communicate with memory services (MKF) directly because MKF is a cross-cutting fabric, just as AUTOSAR Complex Drivers span the full stack. The Governance & Compliance Layer (GCL) governs all layers that contain executable actions — this is what makes compliance enforcement architectural rather than optional.

---

## 3. Architecture — Layer Definitions

### 3.1 Layer 1 — Deployment & Runtime Substrate (DRS)

**The Deployment & Runtime Substrate is the lowest and most architecturally creative layer in CIPHER.** Unlike AUTOSAR's Microcontroller layer — which is fixed silicon that the software must adapt to — the DRS is a *software-owned contract layer* that CIPHER defines, implements, and controls. It abstracts the deployment topology entirely from every layer above it, exposing four typed primitive interfaces upward through `cipher.core.substrate` regardless of whether the platform is running on a developer laptop, an on-prem server, or a multi-region Kubernetes cluster.

This distinction is profound. Where AUTOSAR says "you depend on this silicon, now abstract it," CIPHER says "you define this contract, and any deployment topology must satisfy it." Every higher layer in the stack calls the DRS, not the other way around. The DRS is what makes CIPHER genuinely deployment-topology-independent rather than merely "cloud-compatible."

**Task.** Provide four stable, typed, deployment-topology-independent primitive interfaces — Compute Fabric, Network Fabric, Storage Fabric, and Secret Fabric — through which the Platform Kernel and all higher layers can spawn workloads, resolve service addresses, bind durable storage, and inject credentials without ever knowing whether the underlying runtime is Docker Compose, bare metal, Nomad, or Kubernetes.

**Properties.**
- Implementation: topology-specific. The DRS has a *driver* for each supported deployment target. The **Docker Compose Driver** (`cipher.substrate.drivers.compose`) implements all four fabric interfaces using the Docker SDK, host-local DNS, bind-mount volumes, and Docker secrets. The **Kubernetes Driver** (`cipher.substrate.drivers.k8s`) implements them using the Kubernetes API, CoreDNS + service mesh, PersistentVolumeClaims, and Vault or Kubernetes Secrets. A new deployment target is a new DRS driver — no other layer changes.
- Upper Interface: standardized, topology-independent. All four fabric interfaces are defined in `cipher.core.substrate` as abstract Python protocols. The Platform Kernel calls `substrate.compute.spawn_unit(image, env, resources)` — it does not know whether this creates a Docker container or a Kubernetes Pod.
- Lower Interface: topology-specific drivers that call Docker SDK, `kubectl`/client-go, or cloud provider APIs.

**The Four Fabric Primitives.** Each fabric is a typed abstract interface with a concrete driver registered at startup via `cipher.substrate.registry.register(driver)`.

```python
# cipher/core/substrate/__init__.py
# The four fabric protocols — the complete DRS public API.
# Every higher layer depends ONLY on these four interfaces.
# No higher layer ever imports a driver directly.

from typing import Protocol, runtime_checkable

@runtime_checkable
class ComputeFabric(Protocol):
    """
    Spawns, monitors, and terminates isolated execution units.
    A unit is a container in Docker Compose, a Pod in Kubernetes,
    or a process group on bare metal. The caller never knows which.
    """
    def spawn_unit(self, image: str, name: str, env: dict,
                   resources: "ResourceSpec", ports: dict) -> "UnitHandle": ...
    def terminate_unit(self, handle: "UnitHandle", graceful: bool = True): ...
    def health_check(self, handle: "UnitHandle") -> "HealthStatus": ...
    def list_units(self, label_selector: dict) -> list["UnitHandle"]: ...

@runtime_checkable
class NetworkFabric(Protocol):
    """
    Resolves service addresses and manages inter-unit connectivity.
    Returns a routable address for a named service, regardless of
    whether that is 'localhost:7001', a Kubernetes ClusterIP, or
    a service mesh virtual IP.
    """
    def resolve(self, service_name: str, port: int) -> str: ...
    def register_service(self, name: str, unit: "UnitHandle", port: int): ...
    def deregister_service(self, name: str): ...

@runtime_checkable
class StorageFabric(Protocol):
    """
    Binds durable storage volumes to execution units and provides
    object store access. A 'volume' is a bind-mount locally and a
    PersistentVolumeClaim in Kubernetes. An 'object bucket' is
    a MinIO bucket locally and S3 in production.
    """
    def bind_volume(self, unit: "UnitHandle", volume_name: str,
                    mount_path: str, read_only: bool = False): ...
    def create_volume(self, name: str, size_gb: int): ...
    def get_object_store_url(self, bucket: str) -> str: ...
    def ensure_bucket(self, bucket: str): ...

@runtime_checkable
class SecretFabric(Protocol):
    """
    Injects credentials into execution units at spawn time.
    Secrets are never stored in environment variables or config files
    by the caller — they are resolved and injected by the DRS driver.
    Locally: Docker secrets or age-encrypted files.
    In production: Vault dynamic secrets or Kubernetes Secrets.
    """
    def inject_secret(self, unit: "UnitHandle", secret_name: str,
                      mount_path: str): ...
    def get_secret_value(self, secret_name: str) -> str: ...
    def rotate_secret(self, secret_name: str): ...
```

**Topology Portability.** The DRS is the mechanism that makes CIPHER's "Local ≡ Cloud" principle structurally enforced rather than aspirationally stated. The Platform Kernel's startup sequence calls `substrate.compute.spawn_unit("cipher/memory-agent:1.0", ...)` — whether that creates a Docker container on localhost or a Kubernetes Deployment is entirely determined by which DRS driver was registered at boot, set through the single configuration variable `CIPHER_SUBSTRATE_DRIVER=compose|k8s|nomad`. Migrating from MVP to production requires changing that one variable and providing a `k8s` driver implementation — nothing in PKL, MKF, TRF, GCL, ARE, or AAL changes.

**DRS Driver Implementations for MVP.**

The *Docker Compose Driver* (`cipher.substrate.drivers.compose`) implements all four fabrics for local single-machine deployment. Its `ComputeFabric` wraps the Docker SDK (`docker.from_env()`) to spawn and monitor containers. Its `NetworkFabric` uses Docker's built-in DNS resolver on the Compose network (container names become routable hostnames). Its `StorageFabric` maps volume names to `./data/{name}` bind-mount paths and provides MinIO as the object store. Its `SecretFabric` reads `age`-encrypted files from `./secrets/` and injects them as environment variables at container creation time — the calling code never touches the raw secret.

**DRS Driver Implementation Sketch.**

```python
# cipher/substrate/drivers/compose.py
# The Docker Compose DRS driver — implements all four fabric interfaces
# using Docker SDK. Registered at startup in MVP.

import docker
from cipher.core.substrate import ComputeFabric, NetworkFabric, StorageFabric, SecretFabric

class ComposeComputeFabric:
    """Wraps Docker SDK. spawn_unit → docker.containers.run()"""
    def __init__(self):
        self._client = docker.from_env()
        self._network = "cipher_net"      # defined in docker-compose.yml

    def spawn_unit(self, image, name, env, resources, ports):
        container = self._client.containers.run(
            image=image,
            name=name,
            environment=env,
            network=self._network,
            detach=True,
            mem_limit=resources.memory_mb * 1024 * 1024 if resources else None,
            labels={"cipher.managed": "true"},
            ports=ports or {},
        )
        return UnitHandle(id=container.id, name=name, driver="compose")

    def terminate_unit(self, handle, graceful=True):
        c = self._client.containers.get(handle.id)
        c.stop(timeout=30) if graceful else c.kill()
        c.remove()

    def health_check(self, handle):
        c = self._client.containers.get(handle.id)
        return HealthStatus(running=(c.status == "running"), detail=c.status)

class ComposeNetworkFabric:
    """Uses Docker's built-in Compose DNS: service_name → routable hostname"""
    def resolve(self, service_name, port):
        # Docker Compose DNS makes every container reachable by name on the network
        return f"http://{service_name}:{port}"

class ComposeStorageFabric:
    """Maps volume names to ./data/ bind mounts; uses MinIO for object store"""
    def __init__(self, data_root="./data"):
        self._data_root = data_root

    def get_object_store_url(self, bucket):
        return f"http://minio:9000/{bucket}"

    def ensure_bucket(self, bucket):
        # Called at startup to ensure MinIO bucket exists
        import boto3, botocore
        s3 = boto3.client("s3", endpoint_url="http://localhost:9000",
                          aws_access_key_id="cipher", aws_secret_access_key="cipher")
        try:
            s3.create_bucket(Bucket=bucket)
        except botocore.exceptions.ClientError:
            pass   # bucket already exists

class ComposeSecretFabric:
    """Reads age-encrypted secrets from ./secrets/ and injects at unit spawn"""
    def get_secret_value(self, secret_name):
        import subprocess, os
        result = subprocess.run(
            ["age", "--decrypt", f"./secrets/{secret_name}.age"],
            capture_output=True, env={**os.environ, "AGE_KEY_FILE": "./secrets/key.txt"}
        )
        return result.stdout.decode().strip()
```

**Extensibility via Driver Registration.** Adding a Kubernetes deployment target requires implementing the four fabric interfaces with Kubernetes client calls and registering them at boot:

```python
# deploy/production/substrate_init.py
from cipher.core.substrate.registry import register
from cipher.substrate.drivers.k8s import (
    K8sComputeFabric, K8sNetworkFabric, K8sStorageFabric, K8sSecretFabric
)

# One line to swap the entire deployment topology:
register(compute=K8sComputeFabric(), network=K8sNetworkFabric(),
         storage=K8sStorageFabric(), secret=K8sSecretFabric())
```

Adding a Nomad driver, a bare-metal process supervisor driver, or a serverless driver follows the exact same pattern. The rest of CIPHER is unchanged.

### 3.2 Layer 2 — Platform Kernel (PKL)

**The Platform Kernel is the first fully CIPHER-owned orchestration layer.** It sits directly above the DRS and depends exclusively on the DRS's four fabric primitives — never on Docker, Kubernetes, or any other topology-specific API. It contains the foundational runtime services that every agent and every higher layer depends on: the event bus, the durable workflow runtime, the checkpoint store, and the storage adapter library that further abstracts concrete storage technologies from all higher layers.

**Analogy to AUTOSAR MCAL.** Just as AUTOSAR's Microcontroller Abstraction Layer exposes a standardized, hardware-independent interface upward while depending on the microcontroller's specific registers downward, the Platform Kernel exposes a standardized, deployment-independent interface upward while depending on the DRS's topology-independent fabric primitives downward.

**Task.** Make all higher software layers independent of the specific storage technology (SQLite vs. PostgreSQL, NATS vs. Kafka) and the specific workflow runtime (LangGraph in MVP, Temporal in production). Provide the event bus backbone for all asynchronous platform events.

**Properties.**
- Implementation: deployment-independent by design. The PKL calls `substrate.storage.get_object_store_url()` to find where to store checkpoints — it never hard-codes a filesystem path or a cloud storage URL.
- Upper Interface: standardized and deployment-independent. Any higher-layer component that needs to write to the document store calls `cipher.core.adapters.document_store.upsert()` — it does not care whether the backing store is SQLite or Aurora PostgreSQL.

**Modules at this layer.**

The *Event Bus (NATS)* provides the publish/subscribe backbone for all CloudEvents-enveloped platform events. Its service address is resolved through `substrate.network.resolve("nats", 4222)` at startup — the PKL never has a hard-coded `localhost:4222`. The *Workflow Runtime (LangGraph)* provides the checkpointed state machine execution environment for all agent task graphs. The *Checkpoint Store* persists LangGraph workflow state after every node, using the storage path resolved from the DRS Storage Fabric. The *Observability Backend (Langfuse + OTel Collector)* receives OpenTelemetry OTLP traces from all agents and tool servers. The *Storage Adapters (`cipher.core.adapters`)* are the thin abstraction modules that translate standardized storage API calls into concrete database operations, swappable between MVP and cloud deployments through DRS driver registration, not through configuration files.

### 3.3 Layer 3 — Memory & Knowledge Fabric (MKF)

**The Memory & Knowledge Fabric is the cross-cutting memory subsystem.** It spans from the Deployment & Runtime Substrate (DRS) up to the Application/Agent Layer — just as AUTOSAR's Complex Drivers span from the microcontroller directly up to the RTE — because memory access is needed at every layer without routing through multiple intermediate abstractions.

**Analogy to AUTOSAR Complex Drivers.** AUTOSAR's Complex Drivers exist because some modules have special requirements that don't fit cleanly into the normal MCAL → ECU Abstraction → Services path. They access the hardware directly and provide a result directly to the application. Similarly, the Memory & Knowledge Fabric accesses the storage substrate (DRS Storage Fabric) directly and provides memory services directly to any layer that needs them.

**Task.** Provide four-tier memory services — working memory, episodic memory, semantic memory, and procedural memory — to all agents and platform components through a single, typed `MemoryAPI` interface. Own the Knowledge Graph schema and enforce the ArtifactRelation data model.

**Properties.**
- Implementation: deployment-independent at the API level. Memgraph Community is used in MVP and Neo4j Aura Enterprise in production — both are resolved through the DRS Network Fabric by name. No higher layer ever contains a hard-coded connection string.
- Upper Interface: standardized `MemoryAPI` — completely storage-technology-independent. An agent calling `memory.retrieve()` does not know whether the backing store is Memgraph + Qdrant embedded or Neo4j Aura + Qdrant Cloud.

**Modules at this layer.**

The *Memory Agent (AGT-007)* is the manager module that owns all reads and writes to the memory subsystem. It performs episodic-to-semantic consolidation on a schedule, enforces retention policies, and maintains the temporal validity of Knowledge Graph edges. The *Knowledge Graph (Memgraph Community)* stores the full artifact relation model — every Requirement, Design, Code, Test, Run, Agent, Person, Decision, and ChangeRequest node, connected by typed `ArtifactRelation` edges with `valid_from`, `valid_to`, and `confidence` properties. The *Vector Store (Qdrant embedded)* stores BGE-M3 embeddings for all artifact chunks, organized into four collections: `requirements`, `design_docs`, `source_code`, and `test_cases`. The *Working Memory (Redis)* provides per-agent-per-task key-value storage with TTL, used as the ephemeral task scratchpad. The *Document Store (SQLite)* stores structured metadata — TaskContracts, project configurations, agent registrations, and plan objects. The *Artifact Object Store (MinIO)* stores the actual binary content of artifacts — LLD CSV files, annotated source files, UTD documents, coverage reports — with its bucket URL resolved from `substrate.storage.get_object_store_url("cipher-artifacts")`.

### 3.4 Layer 4 — Tool & Resource Fabric (TRF)

**The Tool & Resource Fabric abstracts every external tool and resource from the agents that use them.** Just as AUTOSAR's ECU Abstraction Layer interfaces the drivers of the MCAL and provides an API for peripheral access regardless of whether a device is on-chip or external, the Tool & Resource Fabric provides a uniform MCP JSON-RPC interface to every tool (VectorCAST, Git, DOORS, JIRA, LLM providers) regardless of whether that tool is a local CLI, a remote REST API, or an external SaaS service.

**Task.** Provide equal mechanisms to access any development tool, build system, requirements management system, test bench, or LLM provider, regardless of its location (local Docker container, remote server, cloud API) and its interface type (CLI, REST, gRPC, proprietary protocol).

**Properties.**
- Implementation: deployment-independent at the API level. The VectorCAST MCP Server is spawned as a compute unit through `substrate.compute.spawn_unit()` regardless of whether that means a Docker container or a Kubernetes Job. All tool server addresses are resolved through `substrate.network.resolve()` — no hard-coded host ports appear in TRF code.
- Upper Interface: standardized MCP JSON-RPC 2.0. All tool calls from any agent go through the same `POST /mcp/tools/{name}/invoke` interface regardless of the underlying tool.

**Modules at this layer.**

The *Tool Broker Agent (AGT-008)* is the MCP Gateway — the single entry point for all tool calls from all agents. It enforces per-agent scope policies (read from `cipher/governance/agent_scopes.yaml`), injects secrets at call time from the secret store, logs every invocation to the Audit Journal (GCL), and spawns sandboxed execution containers for tools requiring code execution. The *MCP Gateway (JSON-RPC server)* is the HTTP server implementing the MCP protocol that routes validated, policy-checked tool calls to the appropriate MCP tool server. The *Git MCP Server* wraps libgit2 to provide read access to all branches and scoped write access to development branches. The *VectorCAST MCP Server* wraps the VectorCAST CLI in a Docker sandbox to create test environments and parse coverage reports. The *DOORS/ReqIF MCP Server* provides both a read path (ReqIF export file parsing) and a write path (DOORS REST API), with the write path requiring human approval from the HITL Gate Manager (GCL). The *Filesystem MCP Server* enforces directory boundary policies using a Linux seccomp profile, preventing any agent from reading or writing outside its configured project directory. The *LLM Gateway (LiteLLM + GCA bridge)* routes all LLM completion calls to the appropriate provider, implements prompt caching keyed on `(model, messages_hash)`, applies model tiering, and records every token cost against the calling agent's budget.

### 3.5 Layer 5 — Governance & Compliance Layer (GCL)

**The Governance & Compliance Layer provides cross-cutting services to all other layers.** It is the highest layer of the Platform infrastructure. Just as AUTOSAR's Services Layer provides operating system functionality, network management, memory services, and diagnostic services to both the application and lower BSW modules, the Governance & Compliance Layer provides policy enforcement, human approval routing, identity verification, and audit logging to every layer.

**The key architectural property of GCL is that it cross-cuts all layers.** A tool call in TRF, a task submission in ARE, a graph write in MKF, and an agent action in AAL all route through GCL for policy evaluation before execution. This is encoded in the Layer Interaction Matrix — GCL has write access to the audit journal and read access to every layer it governs.

**Task.** Provide policy-as-code enforcement, auditable human approval workflows, cryptographic agent identity, and domain pack management to all platform layers. Ensure that no irreversible action can execute without passing an authorization check and, where required, a human approval gate.

**Properties.**
- Implementation: largely host and technology independent. OPA evaluates Rego policies in memory; the Audit Journal is SQLite in MVP.
- Upper Interface: all layers interact with GCL through two interfaces — the `policy.evaluate(input)` call (synchronous, before any action) and the `audit.record(event)` call (asynchronous, after any action).

**Modules at this layer.**

The *Policy Engine (OPA with Rego)* evaluates every consequential action against the applicable domain pack's policy profile before execution. Every OPA decision is signed with the acting agent's identity and logged. The *Audit Journal (append-only SQLite)* records every platform action — tool invocations, LLM calls, graph writes, human approvals — as an immutable AuditRecord with Ed25519 signature. The *HITL Gate Manager* owns the human-in-the-loop approval workflow: it suspends the calling LangGraph task, emits a `cipher.gate.pending` CloudEvent, delivers the approval request to the web dashboard, and resumes the workflow on receipt of a signed approval. The *Identity Manager (JWT + Ed25519 keypairs)* issues, validates, and rotates agent identities and user JWTs. In MVP, agent keypairs are generated at container startup and stored in the Docker secret mount. The *Domain Pack Loader* reads the active domain pack from `cipher/governance/domain_packs/{pack_id}/` at platform startup and registers its OPA policies, evidence schemas, approval matrices, and evaluation rubrics with the appropriate consumers.

### 3.6 Layer 6 — Agent Runtime Environment (ARE)

**The Agent Runtime Environment is the crucial decoupling layer.** Above the ARE, the architecture style changes from layered to component/agent style — exactly as AUTOSAR specifies for the RTE. Above the ARE, agents communicate with each other through typed A2A task contracts and are completely independent of which specific tool servers, storage backends, or compute substrates are running underneath.

**Analogy to AUTOSAR RTE.** AUTOSAR's Runtime Environment makes Software Components independent from their mapping to a specific ECU. CIPHER's ARE makes agents independent from their mapping to a specific deployment (local laptop vs. cloud cluster, SQLite vs. PostgreSQL, NATS vs. Kafka). An agent that was developed and tested on a local laptop runs without modification in a Kubernetes cluster because the ARE provides the same `tasks/send`, `tasks/get`, and `tasks/stream` interfaces in both environments.

**Task.** Make CIPHER agents independent of their specific deployment environment. Provide the standardized A2A protocol endpoints, task contract validation, OTel span creation, and agent discovery that all agents depend on at their north interface.

**Properties.**
- Implementation: ECU (deployment) and application specific — generated individually for each agent deployment from the `a2a-python SDK` and the agent's Agent Card.
- Upper Interface: completely deployment-independent. Every agent sees the same `tasks/send` method whether it is running locally or in a Kubernetes pod.

**Modules at this layer.**

The *A2A Server (FastAPI)* is the HTTP server implementing the A2A protocol endpoints for each agent: `/.well-known/agent-card.json` for discovery, `POST /a2a` for JSON-RPC task operations, `GET /a2a/tasks/{id}/stream` for SSE streaming. The *Task Contract Validator* schema-validates every incoming TaskContract JSON against the `cipher.taskcontract.v1` JSON Schema before the task is accepted, rejecting malformed tasks with a `400 Bad Request` before they ever reach the agent's plan logic. The *OTel Span Emitter* creates OpenTelemetry root spans for every agent task and child spans for every tool call and LLM call, recording the `trace_id` on every AuditRecord for full correlated observability. The *Agent Registry (`.well-known` server)* maintains the list of registered agents and their Agent Cards, serves the `GET /v1/agents` endpoint, and provides the capability discovery interface that the Orchestrator uses to find which agent has the `vcycle_s3n1` skill for a given task. The *Budget Enforcer* tracks cumulative token spend, wall-clock time, and LLM call count against the `ResourceBudget` declared in the TaskContract's `constraints` field and terminates the agent task with a `BUDGET_EXCEEDED` hard failure if any limit is crossed.

### 3.7 Layer 7 — Application / Agent Layer (AAL)

**The Application / Agent Layer contains all domain-specialized agents.** These agents implement the actual SDLC work — LLD generation, requirement decomposition, code review, static analysis, traceability maintenance, documentation rendering, and voice interaction. They are completely independent of the deployment substrate below the ARE boundary.

**Above the ARE, the architecture style changes from layered to component style** — exactly as AUTOSAR specifies. Agents are opaque components that communicate with each other exclusively through typed A2A task messages. No agent shares Python memory with another. No agent calls another agent's internal methods. Every cross-agent interaction is a network call through the ARE.

**Task.** Implement domain-specific SDLC intelligence as interoperable, independently deployable, opaque agent components. Conform to the `CIPHERAgent` base interface. Declare capabilities through Agent Cards. Accept tasks through the ARE's A2A endpoints. Use the MKF for all memory access. Use the TRF (through the Tool Broker) for all external tool access.

**Properties.**
- Implementation: ECU (deployment) and application specific. DevNex's LLD generation logic is specific to automotive embedded SDLC. The ASIL Review Agent's rubrics are specific to ISO 26262. These implementation specifics are encapsulated and invisible to other agents.
- Upper Interface: the agent's Agent Card and its A2A skills — completely deployment and implementation independent. Any orchestrator can call `vcycle_s3n1` on DevNex without knowing that DevNex is implemented in Python using GCA as its LLM backend.

---

## 4. Architecture — Module Type Definitions

Just as AUTOSAR defines specific module types (Driver, Interface, Handler, Manager, Library) that clarify the role and behavioral contract of every BSW module, CIPHER defines the same five module types. Every component at every layer is one of these types.

### 4.1 Driver

A driver contains the functionality to directly access a specific backend technology or external system. It is the lowest-level module that has direct dependencies on a specific technology. Drivers are located in the Platform Kernel (PKL) or Tool & Resource Fabric (TRF).

Examples in CIPHER: the *SQLite Checkpoint Driver* in PKL directly calls SQLite APIs to read and write LangGraph checkpoint state. The *Memgraph Driver* in MKF directly calls the Memgraph Bolt protocol to execute Cypher queries. The *VectorCAST CLI Driver* in TRF directly spawns the VectorCAST process and parses its stdout output.

### 4.2 Interface

An interface module contains the functionality to abstract from modules placed below it. It provides a generic API to access a specific type of resource, independent of how many instances of that resource exist and independent of the hardware realization. Interfaces do not change the content of the data.

Examples in CIPHER: the *Storage Adapter Interface (`cipher.core.adapters`)* in PKL provides `document_store.upsert()`, `document_store.query()` — the same API whether the backing store is SQLite or Aurora PostgreSQL. The *Memory API Interface (`cipher.core.memory.MemoryAPI`)* in MKF provides `retrieve()`, `upsert_node()`, `upsert_edge()` — the same API whether the backing graph is Memgraph or Neo4j Aura.

### 4.3 Handler

A handler is a specific interface that controls concurrent, multiple, and asynchronous access of one or multiple clients to one or more drivers. It performs buffering, queuing, arbitration, and multiplexing. The handler does not change the content of the data.

Examples in CIPHER: the *MCP Gateway (Tool Broker)* in TRF is a handler — it accepts concurrent tool call requests from multiple agents, queues them against per-agent rate limits, arbitrates scope conflicts, and routes them to the appropriate MCP tool server. The *NATS Event Bus* in PKL is a handler — it accepts concurrent `publish()` calls from all agents, queues messages, and delivers them to all subscribed consumers.

### 4.4 Manager

A manager offers specific services for multiple clients. Unlike a handler, a manager can evaluate and change or adapt the content of the data. Managers are generally located in the Services/Governance layers.

Examples in CIPHER: the *Memory Agent (AGT-007)* in MKF is a manager — it doesn't just route memory requests, it evaluates which episodic records to consolidate into semantic memory, prunes expired working memory, and assigns confidence scores to newly created ArtifactRelation edges. The *Policy Engine (OPA)* in GCL is a manager — it evaluates and adapts authorization decisions based on runtime input context, trust tier, and domain pack policy profile. The *HITL Gate Manager* in GCL is a manager — it evaluates whether a pending action is genuinely irreversible and routes the approval request to the correct human reviewer based on the ASIL level and the active domain pack's approval matrix.

### 4.5 Library

Libraries are collections of functions for related purposes. They run in the context of the caller, are re-entrant, have no internal state, require no initialization, and are synchronous.

Examples in CIPHER: the *`cipher.core.schemas` library* provides schema validation functions (validate TaskContract, validate ArtifactRelation, validate Agent Card) that run in any caller's context with no side effects. The *`cipher.core.otel` library* provides the `@traced()` decorator and span helper functions used by all agents. The *`cipher.core.cloudevents` library* provides envelope construction and parsing for CloudEvents 1.0 messages.

---

## 5. Architecture — Whole-System HLD

### 5.1 System Boundary and External Actors

The system boundary for the CIPHER Local MVP encompasses all software running inside the platform stack, managed through the Docker Compose DRS driver. External actors are the human users (Developer, Technical Lead, QA Engineer), the CI/CD pipeline (GitHub Actions / GitLab CI), and the external tool services (IBM DOORS/DOORS Next, Git remote, VectorCAST license server, LLM API providers).

```mermaid
C4Context
    title CIPHER Local MVP — System Context

    Person(dev,   "Developer",       "Submits intents via PyQt6 GUI or CLI")
    Person(lead,  "Technical Lead",  "Approves HITL gates via web dashboard")
    Person(qa,    "QA Engineer",     "Queries traceability, exports evidence")

    System(cipher, "CIPHER Platform\n(Docker Compose DRS driver, Local MVP)", "7-layer agentic platform")

    System_Ext(doors,  "DOORS / ReqIF files",      "Requirements source")
    System_Ext(git,    "Git repository",            "Source code, artifact history")
    System_Ext(vc,     "VectorCAST installation",   "Unit test execution")
    System_Ext(llm,    "LLM APIs (GCA / Ollama)",   "LLM inference")

    Rel(dev,   cipher, "A2A + HTTP tasks")
    Rel(lead,  cipher, "Approval via web dashboard")
    Rel(qa,    cipher, "Traceability queries, evidence export")
    Rel(cipher, doors, "ReqIF read/write (DOORS MCP)")
    Rel(cipher, git,   "Git read/write (Git MCP)")
    Rel(cipher, vc,    "Test execution (VectorCAST MCP)")
    Rel(cipher, llm,   "LLM completions (LLM Gateway)")
```

### 5.2 Full Layered Component Diagram

The component diagram below maps every concrete component to its layer and shows the inter-layer communication paths for the MVP deployment. Port numbers are the actual localhost ports used in the Docker Compose stack.

```mermaid
flowchart TB
    subgraph EXT["External Systems"]
        DEV_GUI["PyQt6 GUI\n(DevNex)"]
        DEV_CLI["Click CLI\n(DevNex)"]
        WEB_DB["Web Dashboard\n(HITL / Compliance)"]
        DOORS_EXT["DOORS / ReqIF\n(external)"]
        GIT_EXT["Git Remote\n(external)"]
        LLM_EXT["GCA / Ollama\n(external or local)"]
    end

    subgraph L7_AAL["Layer 7 — Application / Agent Layer"]
        ORCH["Orchestrator\nAGT-000 :8000"]
        DEVNEX["DevNex\nAGT-001 :7001"]
        PLANNER["Planning\nAGT-002 :7002"]
        REVIEWER["ASIL Review\nAGT-003 :7003"]
        COMPLIANCE["Compliance\nAGT-004 :7004"]
        RESEARCH["Research\nAGT-005 :7005"]
        GARVIS["Garvis\nAGT-006 :7006"]
    end

    subgraph L6_ARE["Layer 6 — Agent Runtime Environment"]
        A2A_GW["A2A Gateway\n(FastAPI, per agent)"]
        TASK_VAL["Task Contract\nValidator"]
        OTEL_EM["OTel Span Emitter\n(OTLP → :4317)"]
        REG["Agent Registry\n(.well-known)"]
    end

    subgraph L5_GCL["Layer 5 — Governance & Compliance Layer"]
        OPA_S["OPA Sidecar\n:8181"]
        AUDIT_S["Audit Journal\nSQLite append-only"]
        HITL_MGR["HITL Gate Manager\n(suspends LangGraph)"]
        DOMPACK_L["Domain Pack Loader\n(iso26262-asil-b)"]
        ID_MGR["Identity Manager\n(JWT + Ed25519)"]
    end

    subgraph L4_TRF["Layer 4 — Tool & Resource Fabric"]
        TOOLBROKER["Tool Broker\nAGT-008 :7200"]
        MCP_GW["MCP Gateway\n(JSON-RPC server)"]
        GIT_MCP_S["Git MCP\n:7211 (Docker)"]
        VC_MCP_S["VectorCAST MCP\n:7210 (Docker)"]
        DOORS_MCP_S["DOORS/ReqIF MCP\n:7212 (Docker)"]
        FS_MCP_S["FS MCP\n:7214 (Docker)"]
        LLM_GW_S["LLM Gateway\n:7215 (LiteLLM)"]
    end

    subgraph L3_MKF["Layer 3 — Memory & Knowledge Fabric"]
        MEM_AGT["Memory Agent\nAGT-007 :7100"]
        MEMGRAPH_S["Memgraph\n:7687 (Bolt)"]
        QDRANT_S["Qdrant embedded\n:6333"]
        REDIS_S["Redis\n:6379"]
        SQLITE_DOC["SQLite\n(document store)"]
        MINIO_S["MinIO\n:9000"]
    end

    subgraph L2_PKL["Layer 2 — Platform Kernel"]
        NATS_S["NATS\n:4222"]
        LANGGRAPH_RT["LangGraph\n(in-process)"]
        CKPT_DB["Checkpoint SQLite\n(./data/checkpoints)"]
        LANGFUSE_S["Langfuse\n:3000"]
        ADAPTERS_LIB["cipher.core.adapters\n(storage abstraction)"]
    end

    subgraph L1_DRS["Layer 1 — Deployment & Runtime Substrate (DRS)"]
        DRS_COMP["Compute Fabric\ncipher.substrate.compute\n(ComposeComputeFabric — MVP)"]
        DRS_NET["Network Fabric\ncipher.substrate.network\n(ComposeNetworkFabric — MVP)"]
        DRS_STOR["Storage Fabric\ncipher.substrate.storage\n(ComposeStorageFabric — MVP)"]
        DRS_SEC["Secret Fabric\ncipher.substrate.secrets\n(ComposeSecretFabric — MVP)"]
    end

    %% External → ARE (entry point)
    DEV_GUI & DEV_CLI -->|"HTTP / A2A"| A2A_GW
    WEB_DB -->|"HTTP"| HITL_MGR

    %% ARE → AAL
    A2A_GW --> TASK_VAL --> ORCH
    A2A_GW --> DEVNEX
    A2A_GW --> PLANNER & REVIEWER & COMPLIANCE & RESEARCH & GARVIS

    %% AAL ↔ AAL (lateral A2A)
    ORCH <-->|"A2A"| DEVNEX
    ORCH <-->|"A2A"| PLANNER & REVIEWER & RESEARCH
    DEVNEX <-->|"A2A lateral"| REVIEWER
    REVIEWER <-->|"A2A lateral"| COMPLIANCE

    %% AAL → GCL
    ORCH & DEVNEX & REVIEWER -->|"policy.evaluate()"| OPA_S
    ORCH & DEVNEX -->|"audit.record()"| AUDIT_S

    %% AAL → MKF (direct — cross-cutting)
    ORCH & DEVNEX & REVIEWER & COMPLIANCE --> MEM_AGT

    %% AAL → TRF (via Tool Broker only)
    DEVNEX & COMPLIANCE & RESEARCH -->|"MCP tasks/call"| TOOLBROKER

    %% TRF internals
    TOOLBROKER --> MCP_GW
    MCP_GW --> GIT_MCP_S & VC_MCP_S & DOORS_MCP_S & FS_MCP_S & LLM_GW_S
    GIT_MCP_S --> GIT_EXT
    VC_MCP_S --> LLM_EXT
    DOORS_MCP_S --> DOORS_EXT
    LLM_GW_S --> LLM_EXT

    %% GCL cross-cuts TRF
    OPA_S -.->|"governs"| TOOLBROKER
    HITL_MGR -.->|"suspends"| LANGGRAPH_RT

    %% MKF → PKL
    MEM_AGT --> MEMGRAPH_S & QDRANT_S & REDIS_S & SQLITE_DOC & MINIO_S
    MEMGRAPH_S & QDRANT_S & REDIS_S & SQLITE_DOC & MINIO_S --> ADAPTERS_LIB

    %% PKL internals
    ADAPTERS_LIB --> CKPT_DB
    LANGGRAPH_RT --> CKPT_DB
    OTEL_EM -->|"OTLP"| LANGFUSE_S
    NATS_S -->|"CloudEvents"| MEM_AGT & ORCH

    %% PKL → DRS
    ADAPTERS_LIB --> DRS_STOR
    NATS_S --> DRS_STOR
    LANGGRAPH_RT --> DRS_COMP
    DRS_COMP & DRS_NET & DRS_STOR & DRS_SEC -.->|"substrate contract"| L2_PKL
```

### 5.3 Request Lifecycle — Normative Flow

The following sequence diagram defines the normative platform behavior for any V-cycle task execution, showing exactly which layer handles which step. The layer name appears in brackets before each action.

```mermaid
sequenceDiagram
    actor DEV as Developer
    participant ARE as L6: ARE
    participant GCL as L5: GCL
    participant AAL as L7: Orchestrator
    participant AAL_DN as L7: DevNex
    participant AAL_RV as L7: ASIL Review
    participant MKF as L3: Memory Agent
    participant TRF as L4: Tool Broker
    participant PKL as L2: LangGraph + NATS

    DEV->>ARE: POST /v1/tasks (TaskContract JSON)
    ARE->>ARE: Schema-validate TaskContract
    ARE->>GCL: Identity check (JWT validation)
    GCL->>GCL: policy.evaluate(intent, tenant, policyProfile)
    GCL-->>ARE: ALLOW + signed policy decision
    ARE->>AAL: Create LangGraph workflow from TaskContract
    PKL->>PKL: Checkpoint workflow state (step=0)

    AAL->>MKF: memory.materialize(contextHandle)
    MKF-->>AAL: Assembled context string (≤20k tokens)

    AAL->>AAL_DN: A2A tasks/send (skill=vcycle_s3n1)
    ARE->>GCL: policy.evaluate(devnex, lld:write, asil=B)
    GCL-->>ARE: ALLOW
    AAL_DN->>TRF: MCP: llm.complete(lld_gen prompt + context)
    TRF->>GCL: scope check (devnex has llm:complete scope)
    GCL-->>TRF: ALLOW + audit record
    TRF-->>AAL_DN: LLD CSV draft
    AAL_DN->>MKF: memory.upsert_node(LLD_Module) + upsert_edge(GENERATED_BY)
    PKL->>PKL: Checkpoint (step=lld_generated) + emit artifact.created CloudEvent

    AAL->>AAL_RV: A2A tasks/send (skill=review_lld, asil=B)
    AAL_RV->>MKF: memory.retrieve(lld_context, budget=12k)
    AAL_RV-->>AAL: verdict=APPROVED, confidence=0.93

    Note over AAL,GCL: Irreversible action — HITL gate required
    AAL->>GCL: HITL gate request (action=doors.write)
    GCL->>GCL: HITL Gate Manager — suspend LangGraph
    PKL->>PKL: Checkpoint (step=awaiting_hitl) + emit gate.pending CloudEvent
    DEV->>GCL: POST /v1/approvals/{id} (signed approval)
    GCL->>GCL: Resume LangGraph from checkpoint

    AAL->>TRF: MCP: doors.write(lld_artifact)
    TRF->>GCL: audit.record(doors.write, approved=true)
    GCL->>GCL: Append AuditRecord with Ed25519 signature
    TRF-->>AAL: doors.write success

    AAL->>MKF: memory.upsert_edge(LLD_Module DERIVES_FROM SwReq)
    PKL->>PKL: emit task.completed CloudEvent
    ARE-->>DEV: 200 OK + artifact_uri + trace_id
```

---

## 6. Architecture — Individual Agent HLDs

This section follows the AUTOSAR pattern of defining each individual module's layer position, task, properties, upper interface, lower interface, and internal structure. Each agent HLD is one "page" in the AUTOSAR sense — a self-contained architectural definition.

---

### 6.1 Orchestrator Agent (AGT-000)

**Layer.** Application / Agent Layer (AAL) — Trust Tier T0 (System).

**Purpose.** The Orchestrator is the Supervisor agent that decomposes user intent into an execution plan, assigns tasks to specialist agents, enforces the sequential/parallel/iterative/recursive execution patterns, maintains the overall task lifecycle state, and routes human approval gates. It is the "OS scheduler" of the CIPHER agentic system.

**Task.** Decompose every incoming TaskContract into an ordered ExecutionPlan, spawn child tasks on specialist agents through the ARE's A2A interface, monitor child task completion and failures, invoke the HITL Gate Manager (GCL) for irreversible actions, and persist full audit trails to GCL for every state transition.

**Properties.**
- Implementation: deployment-independent. The Orchestrator is backed by a LangGraph Supervisor graph with SQLite checkpointing (MVP). No agent-specific SDLC domain knowledge is encoded in the Orchestrator — it depends on Agent Cards and the Planning Agent for domain knowledge.
- Upper Interface: `POST /v1/tasks` (REST, north-south) and `POST /orchestration/v1/intents` for intent submission. Exposes `GET /orchestration/v1/plans/{id}` for plan inspection.
- Lower Interface: calls the ARE's `A2A tasks/send` method to delegate to specialist agents. Calls GCL for policy evaluation and HITL gating. Calls MKF's `memory.materialize()` to assemble context before delegation.

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT000["Orchestrator Agent (AGT-000)"]
        INTENT_RECV["Intent Receiver\n(FastAPI)"]
        PLAN_EXEC["Plan Executor\n(LangGraph Supervisor)"]
        ROUTER["Topology Router\n(sequential / parallel / iterative / recursive)"]
        GATE_CLIENT["Gate Client\n(calls GCL HITL Manager)"]
        RETRY_MGR["Retry Manager\n(soft/hard failure classifier)"]
        CKPT_MGR["Checkpoint Manager\n(LangGraph checkpointer)"]
    end

    INTENT_RECV --> PLAN_EXEC
    PLAN_EXEC --> ROUTER
    ROUTER --> GATE_CLIENT
    ROUTER --> RETRY_MGR
    PLAN_EXEC --> CKPT_MGR
```

**Interaction Diagram.**

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant M as Memory Agent (MKF)
    participant P as Planning Agent (AAL)
    participant D as DevNex (AAL)
    participant G as GCL

    U->>O: TaskContract
    O->>M: materialize(contextHandle)
    M-->>O: context
    O->>P: A2A: plan(goal, context)
    P-->>O: ExecutionPlan
    loop For each step in plan
        O->>G: policy.evaluate(step)
        G-->>O: ALLOW
        O->>D: A2A: tasks/send(step)
        D-->>O: StepResult
        O->>G: audit.record(step)
    end
    O-->>U: TaskComplete + artifact_refs
```

---

### 6.2 DevNex Domain Agent (AGT-001)

**Layer.** Application / Agent Layer (AAL) — Trust Tier T2 (Gated).

**Purpose.** DevNex is the V-cycle domain execution agent. It is the reference implementation of a CIPHER domain agent and the seed agent for the MVP. It encapsulates thirteen V-cycle workflow nodes (S1N1 through S9N1) as individually callable A2A skills and has no knowledge of the agents that call it or the platform layers beneath the ARE.

**Task.** Given an A2A task with a specific skill ID (e.g., `vcycle_s3n1` for LLD generation), load the relevant project context from MKF, construct a domain-specific LLM prompt, call the LLM Gateway through the Tool Broker (TRF), process the result, persist the output artifact to MKF with full ArtifactRelation provenance edges, and return the artifact reference to the calling orchestrator.

**Properties.**
- Implementation: specific to automotive embedded SDLC. The LLD generation prompts (`lld_gen_v1.md`), code annotation prompts (`code_link_v1.md`), and traceability prompts (`full_trace_v1.md`) are AUTOSAR/MISRA-C-aware and stored in the Procedural Memory tier (MKF). The LLM backend is GCA (Google Code Assist) accessed through the LLM Gateway.
- Upper Interface: thirteen A2A skills declared in the Agent Card. Input is a TaskContract with `inputArtifacts` referencing graph URIs. Output is a `StepResult` with `outputArtifacts` as graph URIs + MinIO object URIs.
- Lower Interface: calls Tool Broker (TRF) for all LLM completions, file reads, Git operations, and VectorCAST runs. Calls Memory Agent (MKF) for context materialization and artifact persistence. Never calls the Platform Kernel or DRS layers directly.

**The Adapter Pattern (wrapping existing DevNex code without modification).**

```python
# cipher/agents/devnex/adapter.py
# This adapter wraps the existing DevNex package at its I/O boundary.
# The DevNex package internals (S1N1..S9N1 node logic, prompt templates,
# GCA invocation) are completely unchanged.

class DevNexAdapter:
    """
    Intercepts DevNex's I/O calls at startup by monkey-patching
    the three boundary points: LLM calls, file reads/writes, and
    VectorCAST invocations. All three are redirected to the
    CIPHER Tool Broker (TRF) so they are audited, scoped, and
    sandboxed by the GCL policy engine.
    """
    def __init__(self, tool_client: ToolClient, memory_client: MemoryClient):
        # Redirect LLM calls through the audited LLM Gateway
        devnex.llm.complete = lambda prompt, **kw: tool_client.call(
            "llm.complete", {"prompt": prompt, **kw}
        )
        # Redirect file I/O through the sandboxed Filesystem MCP
        devnex.io.read_file  = lambda p: tool_client.call("fs.read",  {"path": p})
        devnex.io.write_file = lambda p, c: tool_client.call("fs.write", {"path": p, "content": c})
        # Redirect VectorCAST through the scoped VectorCAST MCP
        devnex.tools.run_vectorcast = lambda env: tool_client.call(
            "vectorcast.run_unit_tests", {"env_path": env, "coverage": "mcdc"}
        )
```

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT001["DevNex Agent (AGT-001)"]
        A2ASRV001["A2A Server\n(FastAPI :7001)"]
        EXEC001["DevNex Executor\n(routes to node)"]
        ADAPTER["DevNex Adapter\n(monkey-patches I/O)"]
        subgraph NODES["V-Cycle Nodes (unchanged internals)"]
            S1N1["S1N1 LLD Gen"]
            S2N1["S2N1 Code Annotate"]
            S3N1["S3N1 Trace Report"]
            S4N1["S4N1 HLD Link"]
            S5N1["S5N1 Full DS Trace"]
            S6N1["S6N1 Test Gen"]
            S7N1["S7N1 UTD Gen"]
            S8N1["S8N1 UTD Link"]
            S9N1["S9N1 Full Matrix"]
        end
        ART_PERSIST["Artifact Persister\n(writes to MKF)"]
    end

    A2ASRV001 --> EXEC001 --> ADAPTER --> NODES --> ART_PERSIST
```

**V-Cycle Node to A2A Skill Mapping.**

| Node | A2A Skill ID | ASPICE Process | Output Artifact |
|---|---|---|---|
| S1N1 | `vcycle_s1n1` | SWE.3 | `LLD_Module` nodes in graph + CSV in MinIO |
| S1N2 | `vcycle_s1n2` | SWE.3 (HITL) | Human approval record |
| S1N3 | `vcycle_s1n3` | SWE.3 (HITL) | Human approval record |
| S1N4 | `vcycle_s1n4` | SWE.3 | `LLD_Functional_Req` CSV |
| S2N1 | `vcycle_s2n1` | SWE.4 | Annotated `SourceFile` nodes + `.c` in MinIO |
| S2N2 | `vcycle_s2n2` | SWE.4 (HITL) | Human approval record |
| S3N1 | `vcycle_s3n1` | SWE.5 | `ArtifactRelation(IMPLEMENTS)` edges |
| S4N1 | `vcycle_s4n1` | SWE.3 | `ArtifactRelation(DERIVES_FROM)` edges |
| S5N1 | `vcycle_s5n1` | SWE.5 | Full downstream trace subgraph |
| S6N1 | `vcycle_s6n1` | SWE.4 (HITL) | `UnitTest` nodes + `test.bat` in MinIO |
| S7N1 | `vcycle_s7n1` | SWE.4 | `UTD` document in MinIO |
| S8N1 | `vcycle_s8n1` | SWE.5 | `ArtifactRelation(VERIFIES)` edges |
| S9N1 | `vcycle_s9n1` | SWE.6 | Full traceability matrix + CSV in MinIO |

---

### 6.3 Planning Agent (AGT-002)

**Layer.** Application / Agent Layer (AAL) — Trust Tier T1 (Advisory).

**Purpose.** The Planning Agent receives a high-level goal from the Orchestrator and decomposes it into a concrete ExecutionPlan — a typed data structure listing the ordered sequence of sub-tasks, the skills and agents needed for each, the estimated token budgets, and the dependency graph between sub-tasks.

**Task.** Given a goal string and a context handle, use the ReAct (Reason + Act) loop to query the Agent Registry for available skills, load the active domain pack's workflow templates (from Procedural Memory in MKF), and produce a well-formed ExecutionPlan with a workflow type (sequential / parallel / iterative / recursive), assigned agent for each step, estimated cost, and ASPICE process mapping.

**Properties.**
- Implementation: uses a medium-capability LLM (Claude Sonnet or GCA standard) for complex planning reasoning. ASPICE workflow templates stored in Procedural Memory (MKF) constrain the plans it generates.
- Upper Interface: single A2A skill `plan_goal`. Returns a structured `ExecutionPlan` JSON.
- Lower Interface: queries the Agent Registry (ARE) for available agent skills. Reads ASPICE workflow templates from MKF procedural memory. Reads project context from MKF semantic memory.

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT002["Planning Agent (AGT-002)"]
        REACT["ReAct Loop\n(Reason then Act)"]
        SKILL_QUERY["Skill Query\n(Agent Registry via ARE)"]
        TEMPLATE_LOAD["Template Loader\n(ASPICE workflow templates\nfrom MKF procedural memory)"]
        PLAN_BUILDER["Plan Builder\n(assembles ExecutionPlan JSON)"]
        BUDGET_EST["Budget Estimator\n(estimates token cost per step)"]
    end

    REACT --> SKILL_QUERY & TEMPLATE_LOAD
    SKILL_QUERY & TEMPLATE_LOAD --> PLAN_BUILDER --> BUDGET_EST
```

---

### 6.4 ASIL Review Agent (AGT-003)

**Layer.** Application / Agent Layer (AAL) — Trust Tier T2 (Gated).

**Purpose.** The ASIL Review Agent evaluates any CIPHER artifact against the ASIL-level-specific rubric defined in the active domain pack. It applies ISO 26262-6 clauses to design artifacts, checks coverage requirements for code artifacts, and verifies test completeness for verification artifacts. It produces a structured verdict (APPROVED / PASS WITH DEVIATIONS / FAIL) with per-finding severity, location, and remediation suggestion.

**Task.** Given an artifact reference (graph URI) and an ASIL level, retrieve the artifact content and its traceability context from MKF, load the applicable ISO 26262 rubric from Procedural Memory, evaluate each rubric criterion against the artifact, and return a structured `ReviewVerdict` with overall recommendation and a finding list.

**Properties.**
- Implementation: uses a constitutional AI rubric-based evaluation pattern. The rubric files in `cipher/governance/domain_packs/iso26262-asil-b/rubrics/` define each ISO 26262-6 clause as a checkable criterion with a mandatory/advisory classification. A MISRA Required violation always produces FAIL regardless of overall rubric score.
- Upper Interface: A2A skill `review_artifact`. Accepts artifact URI + ASIL level. Returns `ReviewVerdict` JSON.
- Lower Interface: calls MKF for artifact retrieval and rubric loading. May call Compliance Agent (TRF → cppcheck) through a lateral A2A escape when code artifacts require static analysis evidence.

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT003["ASIL Review Agent (AGT-003)"]
        ART_FETCH["Artifact Fetcher\n(from MKF)"]
        RUBRIC_LOAD["Rubric Loader\n(from MKF procedural memory)"]
        CRITERION_EVAL["Criterion Evaluator\n(LLM + deterministic checks)"]
        VERDICT_BUILDER["Verdict Builder\n(APPROVED / DEVIATIONS / FAIL)"]
        CONFID_SCORE["Confidence Scorer\n(0.0–1.0 per criterion)"]
    end

    ART_FETCH & RUBRIC_LOAD --> CRITERION_EVAL --> CONFID_SCORE --> VERDICT_BUILDER
```

**ReviewVerdict Schema.**

```json
{
  "artifactId": "lld-IndicatorLamp-v3",
  "asilLevel": "B",
  "recommendation": "PASS_WITH_DEVIATIONS",
  "overallConfidence": 0.87,
  "findings": [
    {
      "findingId": "RVW-001",
      "severity": "MAJOR",
      "clause": "ISO26262-6:8.4.4",
      "description": "Timing budget missing for IndicatorLamp_MainFunction",
      "location": "LLD_Module:IndicatorLamp:timing_constraints",
      "remediation": "Add worst-case execution time estimate and jitter bound",
      "blocked": false
    }
  ],
  "evidenceRefs": ["run:rev-0042"],
  "reviewedBy": "AGT-003",
  "timestamp": "2026-05-09T15:30:00Z"
}
```

---

### 6.5 Compliance Agent (AGT-004)

**Layer.** Application / Agent Layer (AAL) — Trust Tier T0 (System).

**Purpose.** The Compliance Agent is the deterministic static analysis gate. It wraps PC-lint Plus, cppcheck, and Polyspace as MCP tools and evaluates source code artifacts against MISRA-C:2025 rules, AUTOSAR coding guidelines, and ASPICE BP/GP coverage requirements. Unlike the ASIL Review Agent (which uses LLM-based rubric evaluation), the Compliance Agent relies primarily on deterministic rule engines — its findings are reproducible and can be used as formal compliance evidence.

**Task.** Given a source file reference (graph URI), retrieve the file content from MKF, call the appropriate static analysis tools through TRF, parse the tool results, create `ArtifactRelation(VIOLATES)` edges in MKF for any violations found, and return a structured `ComplianceReport` with violation count by severity and rule category.

**Properties.**
- Implementation: hybrid LLM + deterministic rule engine. MISRA Required violations are always detected deterministically by cppcheck/PC-lint. MISRA Advisory violations may use LLM-based heuristics when the static analyzer is unavailable (fallback mode, labeled as non-deterministic in the audit trail).
- Upper Interface: A2A skill `compliance_check`. Returns `ComplianceReport` JSON.
- Lower Interface: calls TRF for `cppcheck.run`, `pclint.run`. Calls MKF for file content retrieval and violation edge persistence.

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT004["Compliance Agent (AGT-004)"]
        FILE_FETCH["File Fetcher\n(from MKF object store)"]
        STATIC_DISPATCH["Static Analyzer Dispatcher\n(cppcheck / pclint / polyspace)"]
        RESULT_PARSER["Result Parser\n(MISRA rule, severity, location)"]
        VIOLATION_WRITER["Violation Writer\n(VIOLATES edges to MKF graph)"]
        REPORT_BUILD["Report Builder\n(ComplianceReport JSON)"]
    end

    FILE_FETCH --> STATIC_DISPATCH --> RESULT_PARSER --> VIOLATION_WRITER & REPORT_BUILD
```

---

### 6.6 Research Agent (AGT-005)

**Layer.** Application / Agent Layer (AAL) — Trust Tier T1 (Advisory).

**Purpose.** The Research Agent retrieves external and internal context that other agents need but do not have in their immediate working memory. It indexes and retrieves from internal wikis, AUTOSAR specification documents, datasheets, prior project artifacts, and internet sources (when permitted by policy). It is the RAG specialist of the CIPHER system.

**Task.** Given a research query and a context handle, perform a hybrid retrieval operation (vector search + graph expansion + rerank) through MKF, assemble the retrieved chunks into a structured context pack sized to the caller's token budget, and return the pack as a context handle that the caller can materialize on demand.

**Properties.**
- Implementation: uses Qdrant vector search + Memgraph PageRank expansion + bge-reranker-large cross-encoder. Document corpus is indexed at project setup time from the team's wiki and AUTOSAR specification PDFs.
- Upper Interface: A2A skill `research_query`. Returns a `ContextHandle` pointing to the assembled retrieval result.
- Lower Interface: calls MKF `memory.retrieve()` for hybrid retrieval. May call TRF LLM Gateway for query expansion and reranking.

---

### 6.7 Garvis Voice/UX Agent (AGT-006)

**Layer.** Application / Agent Layer (AAL) — Trust Tier T1 (Advisory).

**Purpose.** Garvis is the voice and natural-language interaction front-end for CIPHER. It translates engineer voice commands into structured CIPHER task intents that the Orchestrator can act on, and reads out status updates, gate notifications, and brief artifact summaries in natural language.

**Task.** Listen for the wake word, convert the engineer's spoken command to text using Whisper, classify the intent using a small local LLM (7B GGUF model), construct a TaskContract from the classified intent, submit it to the Orchestrator through the ARE, and read out the response using Piper TTS.

**Properties.**
- Implementation: latency-critical path. Wake-word detection (Porcupine or openWakeWord) runs on-device continuously. STT (Whisper-large-v3 via faster-whisper) processes the command locally. Intent classification uses Llama-3.1-8B-Instruct GGUF via llama.cpp — this avoids LLM Gateway latency for simple intents. Only complex intents that require full Orchestrator planning are forwarded through the normal A2A path.
- Upper Interface: LiveKit room endpoint for audio streaming. HTTP REST endpoint for text-only interaction from the web dashboard.
- Lower Interface: calls the Orchestrator (AAL via A2A) to submit task intents. Reads task status updates from the event bus (PKL NATS subscription to `cipher.task.completed`).

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT006["Garvis Voice Agent (AGT-006)"]
        WAKEWORD["Wake Word Detector\n(openWakeWord, on-device)"]
        STT["STT Engine\n(Whisper-large-v3)"]
        INTENT_CLS["Intent Classifier\n(Llama-3.1-8B GGUF)"]
        TASK_BUILD["Task Builder\n(TaskContract from intent)"]
        TTS["TTS Engine\n(Piper TTS)"]
        STATUS_SUB["Status Subscriber\n(NATS cipher.task.*)"]
    end

    WAKEWORD --> STT --> INTENT_CLS --> TASK_BUILD
    STATUS_SUB --> TTS
```

---

### 6.8 Memory / Context Agent (AGT-007)

**Layer.** Memory & Knowledge Fabric (MKF) — Trust Tier T0 (System).

**Purpose.** The Memory Agent is the manager module that owns all reads and writes to the CIPHER memory subsystem. No other agent writes directly to Memgraph, Qdrant, Redis, or MinIO — all memory operations go through the Memory Agent's API. It performs episodic-to-semantic consolidation on a schedule, enforces retention policies, and maintains the temporal validity of Knowledge Graph edges.

**Task.** Expose the full `MemoryAPI` interface to all agents. On `upsert_node()` and `upsert_edge()` calls, enforce the ArtifactRelation schema and set `valid_from` timestamps. On `consolidate()` calls, move approved episodic records to the semantic tier by creating permanent graph nodes from ephemeral run records. On `retrieve()` calls, execute the four-stage hybrid retrieval pipeline (vector search → graph expansion → rerank → context assembly).

**Properties.**
- Implementation: the Memory Agent is the only component with direct driver-level access to Memgraph (Bolt protocol), Qdrant (gRPC), Redis (RESP protocol), SQLite, and MinIO (S3 API). All other agents access these through the Memory Agent's abstraction.
- Upper Interface: `MemoryAPI` (REST at `/memory/v1/`) — `search`, `cypher`, `upsert_node`, `upsert_edge`, `assert_relation`, `retrieve`, `materialize`, `create_handle`, `get_prompt`, `get_rubric`, `consolidate`.
- Lower Interface: direct driver calls to Memgraph, Qdrant, Redis, SQLite, and MinIO through `cipher.core.adapters`.

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT007["Memory / Context Agent (AGT-007)"]
        MEM_API_SRV["MemoryAPI Server\n(FastAPI :7100)"]
        RETRIEVAL_PIPE["Retrieval Pipeline\n(vector→graph→rerank→assemble)"]
        RELATION_VALIDATOR["Relation Validator\n(ArtifactRelation schema)"]
        TEMPORAL_MGR["Temporal Manager\n(valid_from / valid_to lifecycle)"]
        CONSOLIDATOR["Consolidator\n(episodic→semantic on schedule)"]
        PROC_MEM_STORE["Procedural Memory Store\n(prompts, rubrics from ./prompts/)"]
    end

    MEM_API_SRV --> RETRIEVAL_PIPE & RELATION_VALIDATOR & TEMPORAL_MGR & PROC_MEM_STORE
    TEMPORAL_MGR --> CONSOLIDATOR
```

---

### 6.9 Tool Broker Agent (AGT-008)

**Layer.** Tool & Resource Fabric (TRF) — Trust Tier T0 (System).

**Purpose.** The Tool Broker is the façade between all agents in the AAL and all MCP tool servers in the TRF. It is the single chokepoint through which every external tool call must pass. Its architectural role is identical to AUTOSAR's ECU Abstraction Layer: it abstracts the specific tool implementation (VectorCAST 2025 vs. 2026 API change, DOORS REST API version) from the agents that use the tools.

**Task.** Receive all incoming MCP `tools/call` requests from AAL agents. Validate the calling agent's JWT and scope. Evaluate the call against OPA policy. Inject the appropriate secret credentials. Log the invocation to the Audit Journal. Route the call to the appropriate MCP tool server. Return the normalized result to the calling agent.

**Properties.**
- Implementation: the Tool Broker is a stateless routing and policy enforcement layer. It spawns Docker containers for execution-capable tools (cppcheck, VectorCAST) on demand and destroys them after result collection. It never stores tool state between calls.
- Upper Interface: `POST /mcp/tools/{name}/invoke` — standardized for all tools. Every response includes `x-cipher-audit-ref` header with the AuditRecord ID.
- Lower Interface: HTTP JSON-RPC calls to individual MCP tool server containers on their assigned ports.

**Internal Structure.**

```mermaid
flowchart LR
    subgraph AGT008["Tool Broker Agent (AGT-008)"]
        TOOL_RECV["Request Receiver\n(MCP JSON-RPC server)"]
        SCOPE_CHK["Scope Checker\n(JWT → agent_scopes.yaml)"]
        OPA_CALL["OPA Policy Call\n(authorize before execution)"]
        SECRET_INJ["Secret Injector\n(from pass/age store)"]
        AUDIT_EMIT["Audit Emitter\n(→ GCL Audit Journal)"]
        SANDBOX_CTL["Sandbox Controller\n(Docker spawn/destroy)"]
        TOOL_ROUTER["Tool Router\n(→ correct MCP server)"]
    end

    TOOL_RECV --> SCOPE_CHK --> OPA_CALL --> SECRET_INJ --> AUDIT_EMIT --> SANDBOX_CTL --> TOOL_ROUTER
```

---

## 7. Architecture — Interfaces: General Rules

### 7.1 Layer Boundary Rules

These rules are derived from the AUTOSAR interface rules and adapted to the CIPHER context. Every CIPHER engineer must know them.

**Rule 1 — Upward only through defined interfaces.** No layer may call a layer above it directly. The DRS cannot call the Platform Kernel's public API — information flows upward only when the PKL explicitly calls the DRS's substrate primitives. The PKL cannot call agents in the AAL — information flows upward when agents are invoked through the ARE.

**Rule 2 — Skip-layer calls are forbidden except for MKF.** A component in the Application/Agent Layer (AAL) may not call the Platform Kernel (PKL) directly, bypassing ARE, GCL, and TRF. The sole exception is the Memory & Knowledge Fabric (MKF), which is explicitly designated as a cross-cutting layer that AAL agents may call directly.

**Rule 3 — The ARE boundary is the key decoupling point.** Above the ARE, all communication is component-style (typed A2A messages between opaque agents). Below the ARE, all communication is layered (typed API calls through defined interfaces). This boundary is the CIPHER equivalent of the AUTOSAR RTE boundary — the most important architectural constraint in the entire system.

**Rule 4 — GCL is a cross-cutting governance layer, not a sequential layer.** The Governance & Compliance Layer does not sit in the sequential call stack — it is invoked by all layers as a side channel for authorization checks (`policy.evaluate()`) and audit recording (`audit.record()`). A tool call in TRF invokes GCL; an agent task submission in ARE invokes GCL; an artifact write in MKF invokes GCL. GCL is never the primary execution path.

**Rule 5 — No agent shares memory with another agent.** Two agents in the AAL may not share a Python object, a global variable, or a direct function call. All inter-agent communication goes through typed A2A task messages through the ARE. This rule is what makes every agent independently deployable and what gives the audit trail its completeness — there are no "side channel" communications.

### 7.2 Upward Interface Rules

A layer's *upward interface* is the API it exposes to the layer above it. Upward interfaces in CIPHER follow three rules borrowed from AUTOSAR: they are standardized (defined by a published schema, not by the implementing module), they are technology-independent (they do not expose implementation details), and they are versioned (a version number appears in every API path or message schema ID).

The most important upward interfaces in the MVP are: the Platform Kernel's `cipher.core.adapters` upward interface (standardized storage API, technology-independent, version in the adapter class name); the MKF's `MemoryAPI` upward interface (standardized, technology-independent — the same API against Memgraph and Neo4j); the TRF's MCP `/tools/{name}/invoke` upward interface (standardized MCP protocol, technology-independent); and the ARE's A2A `/a2a` upward interface (standardized A2A protocol, deployment-independent).

### 7.3 Downward Interface Rules

A layer's *downward interface* is how it accesses the layer below it. Downward interfaces in CIPHER are always less stable than upward interfaces — the MKF's downward calls to Memgraph's Bolt protocol are more likely to change (e.g., when migrating to Neo4j in production) than the MKF's upward MemoryAPI. For this reason, all downward calls from any layer to the layer below it are encapsulated in the `cipher.core.adapters` abstraction, making the downward interface a private implementation detail rather than a published contract.

### 7.4 Lateral Interface Rules (A2A Escapes)

Lateral A2A escapes are direct agent-to-agent communications that bypass the Orchestrator hub. They are permitted only when all of the following conditions hold: both agents are in the same layer (both in AAL); the Orchestrator has explicitly authorized the lateral connection as part of a plan step; the communication is still through the ARE's A2A endpoints (not through shared Python memory); and the lateral communication is recorded in the audit trail with a `parent_task_id` linking it to the orchestrator's task that authorized it.

Permitted lateral pairs in the MVP are: DevNex (AGT-001) ↔ ASIL Review (AGT-003), and ASIL Review (AGT-003) ↔ Compliance (AGT-004). No other lateral pairs are permitted without an explicit domain pack configuration entry authorizing them.

---

## 8. Architecture — Interfaces: Interaction of Layers

### 8.1 How the Application Layer communicates with ARE

Every agent in the AAL is also an A2A server — it exposes the same A2A endpoints that it uses to receive tasks. When the Orchestrator (AAL) delegates a subtask to DevNex (AAL), it does so by calling DevNex's ARE endpoint (`POST /a2a`, `method: tasks/send`), not by calling DevNex's Python methods directly. This means the Orchestrator's A2A client goes through its own ARE boundary outbound (task submission through its own A2A client library) and DevNex's ARE boundary inbound (task validation, OTel span creation, budget enforcement).

The round-trip of a delegated subtask therefore touches the ARE twice — once when the Orchestrator submits it, and once when DevNex receives it. Both touches create OTel spans and both touches invoke GCL for authorization. This is what makes the inter-agent interaction fully observable and auditable.

### 8.2 How ARE communicates with TRF and MKF

Agents in the AAL do not call TRF or MKF directly from within their LangGraph nodes. Instead, they call `self.tools.call("llm.complete", ...)` (TRF, through the ToolClient library) and `self.memory.retrieve(query, ...)` (MKF, through the MemoryClient library). These client libraries are thin wrappers that add the calling agent's JWT and trace ID to every request, ensuring every tool and memory call is traceable to the specific agent task that initiated it.

The ToolClient and MemoryClient are ARE-layer libraries — they are provided by the ARE, they understand A2A task context, and they are injected into the agent at construction time by the ARE framework. Agents never instantiate storage connections themselves.

### 8.3 How GCL Cross-Cuts All Layers

The Governance & Compliance Layer does not sit in the sequential call path — it is invoked as a side channel from every layer at two specific points: before any consequential action (`policy.evaluate()`), and after any completed action (`audit.record()`). The following diagram shows these cross-cutting invocations for a single tool call.

```mermaid
flowchart LR
    subgraph "Full cross-cutting GCL invocation for one tool call"
        AGT["Agent (AAL)"]
        ARE_C["ARE Client\n(ToolClient)"]
        GCL_PE["GCL: policy.evaluate()\n(OPA Rego evaluation)"]
        TRF_BRK["TRF: Tool Broker\n(scope + secret injection)"]
        GCL_AR["GCL: audit.record()\n(AuditRecord + signature)"]
        TOOL["MCP Tool Server"]
    end

    AGT -->|"tools.call()"| ARE_C
    ARE_C -->|"JWT + trace_id"| GCL_PE
    GCL_PE -->|"ALLOW + policy_rule"| TRF_BRK
    TRF_BRK -->|"invoke()"| TOOL
    TOOL -->|"result"| TRF_BRK
    TRF_BRK -->|"result + policy_decision"| GCL_AR
    GCL_AR -->|"signed audit record"| ARE_C
    ARE_C -->|"result + audit_ref"| AGT
```

---

## 9. Configuration

### 9.1 Domain Pack Configuration

Domain packs are loaded at platform startup by the Domain Pack Loader (GCL). The active pack is set in `deploy/local/.env`:

```bash
# deploy/local/.env
CIPHER_DOMAIN_PACK=iso26262-asil-b
CIPHER_TENANT_ID=devteam-local
CIPHER_PROJECT_ID=BC-ECU-Sprint01
```

The domain pack directory structure mirrors the AUTOSAR configuration approach — all regulatory behavior is data, not code:

```
cipher/governance/domain_packs/
└── iso26262-asil-b/
    ├── pack.yaml               # Pack ID, version, base standard
    ├── policies/
    │   ├── hitl_gates.rego     # Which actions require human approval
    │   ├── asil_thresholds.rego # Minimum confidence for ASIL-B approval
    │   └── tool_access.rego    # Tool scope rules for this ASIL level
    ├── evidence_schema.yaml    # Required artifact types for ASPICE SWE
    ├── approval_matrix.yaml    # Who can approve what (role → ASIL level)
    └── rubrics/
        ├── lld_review.yaml     # ISO 26262-6 LLD review criteria
        ├── code_review.yaml    # Coding standard + MISRA severity mapping
        └── test_coverage.yaml  # MC/DC and branch coverage thresholds
```

### 9.2 Agent Scope Configuration

Per-agent tool access permissions are defined in a single YAML file that is version-controlled alongside the codebase:

```yaml
# cipher/governance/agent_scopes.yaml
DevNex:
  read:  [git:project/**, doors:read, vectorcast:read, fs:project/**]
  write: [fs:project/src/**, fs:project/tests/**, vectorcast:env/**]
  exec:  [vectorcast:run, gcc:compile]
  deny:  [git:push:main, git:push:release/**, jira:delete, doors:write]

ASIL_Reviewer:
  read:  [fs:project/**, kg:read, doors:read]
  write: [kg:write:review_node]
  deny:  [fs:write, git:write, doors:write, vectorcast:write]

Compliance_Agent:
  read:  [fs:project/src/**, fs:project/tests/**, kg:read]
  write: [kg:write:violation_node]
  exec:  [pclint:run, cppcheck:run]
  deny:  [fs:write:project/src/**, git:write, doors:write]
```

### 9.3 LLM Gateway Configuration

The LLM Gateway (LiteLLM) is configured through `cipher/tools/llm_gateway/config.yaml`, which defines the model tiering strategy:

```yaml
# Model tiering — determines which model handles which task class
model_routing:
  triage:        "gca-flash"     # Orchestrator routing, intent classification
  planning:      "gca-standard"  # Planning Agent, context assembly
  generation:    "gca-standard"  # DevNex LLD / code generation
  review:        "gca-standard"  # ASIL Review Agent rubric evaluation
  compliance:    "gca-flash"     # Compliance Agent (mostly deterministic)
  voice_local:   "llama-3.1-8b" # Garvis intent classification (on-device)

# Prompt caching — avoid re-billing identical prompts within TTL
cache:
  enabled: true
  ttl_hours: 24
  key_fields: [model, messages_hash]

# Cost limits — hard cap per task class
cost_limits:
  per_task_usd: 5.00
  per_agent_per_hour_usd: 50.00
```

---

## 10. Integration and Runtime Aspects

### 10.1 Startup Sequence (docker-compose)

The MVP platform starts with `docker compose up` from `deploy/local/`. The startup order is enforced by Docker Compose `depends_on` health checks to ensure each layer's services are ready before the layer above starts.

```
Phase 1 — Deployment & Runtime Substrate (DRS):
  DRS driver registered: cipher.substrate.drivers.compose.ComposeDriver
  Compute Fabric: Docker Engine verified reachable (docker info)
  Network Fabric: cipher_net Docker network created
  Storage Fabric: ./data/ volumes created — memgraph, qdrant, audit.db,
                  checkpoints, artifacts; MinIO bucket cipher-artifacts ensured
  Secret Fabric:  ./secrets/ directory scanned; age-encrypted secrets verified

Phase 2 — Platform Kernel (PKL) services start:
  1. NATS server (:4222) — health: TCP connect
  2. Redis (:6379) — health: PING
  3. Langfuse (:3000) — health: HTTP GET /health
  → All PKL services healthy before MKF starts

Phase 3 — Memory & Knowledge Fabric (MKF) services start:
  4. Memgraph (:7687) — health: Bolt connect
  5. Qdrant embedded (:6333) — health: HTTP GET /health
  6. MinIO (:9000) — health: HTTP GET /minio/health/live
  7. Memory Agent (:7100) — health: HTTP GET /health
  → All MKF services healthy before TRF starts

Phase 4 — Tool & Resource Fabric (TRF) and GCL services start:
  8. OPA sidecar (:8181) — health: HTTP GET /health
  9. Tool Broker / MCP Gateway (:7200) — health: HTTP GET /mcp/tools
  → TRF and GCL services healthy before ARE / AAL starts

Phase 5 — Agent Runtime Environment (ARE) and Agents (AAL) start:
  10. Orchestrator (:8000) — health: HTTP GET /health
  11. DevNex Agent (:7001) — health: GET /.well-known/agent-card.json
  12. Planning Agent (:7002) — health: GET /.well-known/agent-card.json
  13. ASIL Review Agent (:7003) — health: GET /.well-known/agent-card.json
  14. Compliance Agent (:7004) — health: GET /.well-known/agent-card.json
  15. Research Agent (:7005) — health: GET /.well-known/agent-card.json
  16. Garvis Voice Agent (:7006) — health: HTTP GET /health
  → Platform fully operational
```

### 10.2 Shutdown and Graceful Drain

On `docker compose stop`, a `SIGTERM` is sent to each container. Each agent's FastAPI server catches `SIGTERM`, stops accepting new task submissions through the ARE, allows currently executing LangGraph nodes to complete, checkpoints any in-flight workflow state to the PKL Checkpoint Store, and then exits. The Memory Agent is the last to stop because all other agents may need to write final ArtifactRelation edges during their shutdown sequence. The Platform Kernel services (NATS, Redis, Langfuse) stop after all agents have exited.

### 10.3 Checkpoint and Resume

Every LangGraph workflow state is checkpointed to the PKL Checkpoint Store after each completed node. If any agent container is killed unexpectedly (OOM kill, host restart), the workflow state survives in the Checkpoint Store. On next platform startup, the Orchestrator queries the Checkpoint Store for any workflows in `RUNNING` or `WAITING` state and resumes them from their last committed checkpoint. This is what makes the MVP resilient to the most common failure modes on a developer workstation.

The resume mechanism works because CIPHER enforces the **stateless execution + durable external state** principle: no agent holds meaningful state in Python memory. All state is either in the LangGraph checkpoint, the Knowledge Graph, or the Working Memory store. Any agent container can resume any workflow because it reconstructs all necessary context from these external stores, not from its own in-memory state.

### 10.4 Human-in-the-Loop Gate Runtime

When an agent reaches a step that requires human approval (e.g., writing to DOORS, pushing an artifact to a release branch), the following runtime sequence occurs at the LangGraph level:

The LangGraph workflow hits an `interrupt()` node — a special LangGraph construct that suspends the workflow at that exact point without terminating it. The HITL Gate Manager (GCL) serializes the approval request (the action to be approved, the artifact URI, the ASIL level, and the domain pack's approval matrix) as a CloudEvent and emits it on the NATS bus as `cipher.gate.pending`. The web dashboard subscribes to this topic and displays the pending approval with all relevant artifact context. The human reviewer inspects the artifact using the traceability graph view and approves or rejects through `POST /v1/approvals/{id}`. The HITL Gate Manager receives the signed approval, verifies the reviewer's JWT and ASIL authorization level, records the `APPROVED_BY` ArtifactRelation edge in MKF, and calls LangGraph's `resume()` to continue the workflow from the exact interrupted state.

This mechanism means that a workflow can be approved hours or days after it was initiated — the LangGraph checkpoint persists indefinitely in the PKL Checkpoint Store.

---

## Appendix A: Module Inventory

This table provides a complete inventory of all software modules in the CIPHER Local MVP, their layer assignment, their module type (Driver/Interface/Handler/Manager/Library), and their implementation reference.

| Module | Layer | Type | Implementation | Port |
|---|---|---|---|---|
| Compute Fabric (ComposeComputeFabric) | DRS | Driver | `cipher/substrate/drivers/compose.py` | — |
| Network Fabric (ComposeNetworkFabric) | DRS | Interface | `cipher/substrate/drivers/compose.py` | — |
| Storage Fabric (ComposeStorageFabric) | DRS | Driver | `cipher/substrate/drivers/compose.py` | — |
| Secret Fabric (ComposeSecretFabric) | DRS | Driver | `cipher/substrate/drivers/compose.py` | — |
| `cipher.core.substrate` (protocol definitions) | DRS | Interface | `cipher/core/substrate/__init__.py` | — |
| NATS Server | PKL | Handler | `nats-server:2.10` | :4222 |
| LangGraph Runtime | PKL | Manager | `langgraph>=0.4` (in-process) | — |
| Checkpoint SQLite | PKL | Driver | `sqlite3` (stdlib) | — |
| Langfuse | PKL | Manager | `langfuse/langfuse:latest` | :3000 |
| `cipher.core.adapters` | PKL | Interface | Python module | — |
| Memory Agent (AGT-007) | MKF | Manager | `cipher/agents/memory/` | :7100 |
| Memgraph | MKF | Driver | `memgraph/memgraph:2.x` | :7687 |
| Qdrant (embedded) | MKF | Driver | `qdrant-client>=1.9` | :6333 |
| Redis | MKF | Handler | `redis:7-alpine` | :6379 |
| Document Store SQLite | MKF | Driver | `sqlite3` (stdlib) | — |
| MinIO | MKF | Driver | `minio/minio:RELEASE.*` | :9000 |
| Tool Broker (AGT-008) | TRF | Handler | `cipher/agents/tool_broker/` | :7200 |
| MCP Gateway | TRF | Interface | `mcp-python` + FastAPI | :7200 |
| Git MCP Server | TRF | Driver | `cipher/tools/git_mcp/` | :7211 |
| VectorCAST MCP Server | TRF | Driver | `cipher/tools/vectorcast_mcp/` | :7210 |
| DOORS/ReqIF MCP Server | TRF | Driver | `cipher/tools/doors_mcp/` | :7212 |
| Filesystem MCP Server | TRF | Driver | `cipher/tools/fs_mcp/` | :7214 |
| LLM Gateway (LiteLLM) | TRF | Handler | `litellm>=1.40` | :7215 |
| OPA Sidecar | GCL | Manager | `openpolicyagent/opa:latest` | :8181 |
| Audit Journal SQLite | GCL | Driver | `sqlite3` append-only | — |
| HITL Gate Manager | GCL | Manager | `cipher/governance/hitl/` | — |
| Domain Pack Loader | GCL | Manager | `cipher/governance/domain_packs/` | — |
| Identity Manager | GCL | Manager | `cipher/governance/identity/` | — |
| A2A Server | ARE | Interface | `a2a-python SDK` + FastAPI | per agent |
| Task Contract Validator | ARE | Interface | `cipher.core.schemas` | — |
| OTel Span Emitter | ARE | Library | `opentelemetry-sdk` | :4317 |
| Agent Registry | ARE | Manager | `cipher/orchestrator/registry/` | — |
| Budget Enforcer | ARE | Manager | `cipher.core.budget` | — |
| Orchestrator (AGT-000) | AAL | Manager | `cipher/agents/orchestrator/` | :8000 |
| DevNex Agent (AGT-001) | AAL | Manager | `cipher/agents/devnex/` | :7001 |
| Planning Agent (AGT-002) | AAL | Manager | `cipher/agents/planner/` | :7002 |
| ASIL Review Agent (AGT-003) | AAL | Manager | `cipher/agents/asil_reviewer/` | :7003 |
| Compliance Agent (AGT-004) | AAL | Manager | `cipher/agents/compliance/` | :7004 |
| Research Agent (AGT-005) | AAL | Manager | `cipher/agents/research/` | :7005 |
| Garvis Voice Agent (AGT-006) | AAL | Manager | `cipher/agents/garvis/` | :7006 |
| `cipher.core.schemas` | ARE | Library | Python module | — |
| `cipher.core.otel` | ARE | Library | Python module | — |
| `cipher.core.cloudevents` | ARE | Library | Python module | — |

---

## Appendix B: Layer Dependency Rules Summary

This summary table defines what each layer is allowed to depend on directly. It is the CIPHER equivalent of the AUTOSAR Layer Interaction Matrix distilled into plain-language dependency rules.

| Layer | May depend on | May NOT depend on |
|---|---|---|
| **DRS** (Layer 1) | Topology-specific drivers only (Docker SDK, k8s client-go, Nomad API) | Nothing in CIPHER layers above |
| **PKL** (Layer 2) | DRS (all four fabric primitives), MKF (storage only) | TRF, GCL, ARE, AAL |
| **MKF** (Layer 3) | DRS (storage and network fabric), PKL (adapters) | TRF, GCL, ARE, AAL |
| **TRF** (Layer 4) | PKL, MKF, GCL | DRS directly, ARE, AAL |
| **GCL** (Layer 5) | PKL, MKF (audit writes) | TRF internals, ARE, AAL |
| **ARE** (Layer 6) | PKL (event bus), MKF, TRF, GCL | DRS directly |
| **AAL** (Layer 7) | ARE (A2A), MKF (direct memory), GCL (policy/audit) | PKL directly, TRF directly, DRS directly |

---

*This document describes the static structural architecture of the CIPHER Local MVP. For dynamic interface specifications, see individual agent LLD documents. For deployment configuration, see `deploy/local/docker-compose.yml`. For the full architectural reference including cloud production deployment, see `CIPHER_Architecture_v3.md`.*

---

## Documentation Index

> Added 2026-05-17. The CIPHER platform's design is now decomposed into per-layer HLDs and per-agent docs. This master document remains the canonical platform-level architecture; the linked files provide layer-by-layer and agent-by-agent depth.

### Per-Layer HLDs

| Layer | Doc | Coverage |
|-------|-----|----------|
| DRS | [DRS_HLD](layers/DRS_HLD.md) | Docker stack, infra ports, volume layout |
| GCL | [GCL_HLD](layers/GCL_HLD.md) | OPA policy, audit journal, gate enforcement |
| PKL | [PKL_HLD](layers/PKL_HLD.md) | NATS event bus, LangGraph workflow engine |
| MKF | [MKF_HLD](layers/MKF_HLD.md) | Hybrid RAG (Qdrant + BM25), long-term memory |
| TRF | [TRF_HLD](layers/TRF_HLD.md) | LLM Gateway, MCP servers, TaskClass routing |
| ARE | [ARE_HLD](layers/ARE_HLD.md) | A2A server, SkillLoader, AgentCard registry |
| AAL | [AAL_HLD](layers/AAL_HLD.md) | Agent application layer (hosts agent plugins) |
| GUI | [GUI_HLD](layers/GUI_HLD.md) | PyQt6 desktop app, HUD + DevNex workspace |
| Core | [Core_HLD](layers/Core_HLD.md) | Schemas, adapters, OTel, mother CipherOrchestrator |

### Per-Agent Docs

| Agent | Status | Doc |
|-------|--------|-----|
| devnex_assistant | Implemented | [devnex_assistant](agents/devnex_assistant.md) |
| devnex (adapter) | Implemented | [devnex](agents/devnex.md) |
| asil_reviewer | Stub | [asil_reviewer](agents/asil_reviewer.md) |
| compliance | Stub | [compliance](agents/compliance.md) |
| memory_agent | Stub | [memory_agent](agents/memory_agent.md) |
| planner | Stub | [planner](agents/planner.md) |
| research | Stub | [research](agents/research.md) |
| test_agent | Stub | [test_agent](agents/test_agent.md) |
| tool_agent | Stub | [tool_agent](agents/tool_agent.md) |
| traceability | Stub | [traceability](agents/traceability.md) |

### Demo Trial Artifacts

| Artifact | Doc |
|----------|-----|
| AUTOSAR Dio SWS extract | [CAR-004](car/CAR-004-autosar-dio-sws.md) |
| AUTOSAR Port SWS extract | [CAR-005](car/CAR-005-autosar-port-sws.md) |
| AUTOSAR DET SWS extract | [CAR-006](car/CAR-006-autosar-det-sws.md) |
| IoHwAb references (no SWS) | [CAR-007](car/CAR-007-autosar-iohwab-reference.md) |
| SWC Template references (no SWS) | [CAR-008](car/CAR-008-autosar-swc-template-reference.md) |
| Dio-only demo plan | [WBS-0002](wbs/WBS-0002-dio-demo-trial.md) |
| Full Demo (5-component) plan | [WBS-0003](wbs/WBS-0003-full-demo-trial.md) |
| Presenter runbook | [DEMO_RUNBOOK_DIO](DEMO_RUNBOOK_DIO.md) |

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 3.0.0 | 2026-05-18 | CIPHER team | Versioning frontmatter added; body unchanged. |
