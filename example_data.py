# example_data.py

# All examples in this file are original works created for Mermaid Studio
# and released under the MIT license.

from __future__ import annotations
from typing import Dict, List

EXAMPLES: Dict[str, str] = {
    "Flowchart": r"""flowchart LR
    %% Basic flow with a subgraph and styles
    A[Start] --> B{Authenticated?}
    B -- Yes --> C[Show dashboard]
    B -- No --> D[Show login]
    C --> E[Load profile]
    subgraph Services
      E --> S1[(DB)]
      E --> S2[(Cache)]
    end
    S1 -. fallback .- S2
    classDef success fill:#eaffea,stroke:#5cb85c,color:#2d662d
    class C,E success
    """,

    "Sequence Diagram": r"""sequenceDiagram
    autonumber
    participant U as User
    participant W as WebApp
    participant S as Service
    U->>W: Open page
    activate W
    W->>S: GET /api/items
    activate S
    S-->>W: 200 OK + data
    deactivate S
    W-->>U: Render list
    opt User clicks item
      U->>W: Show details
      W->>S: GET /api/item/:id
      S-->>W: 200 OK + detail
      W-->>U: Render detail view
    end
    deactivate W
    """,

    "Class Diagram": r"""classDiagram
    class User {
      +id: UUID
      +name: string
      +email: string
      +login(): bool
    }
    class Session {
      +token: string
      +createdAt: Date
      +isValid(): bool
    }
    class Cart {
      +addItem(p: Product, qty: int)
      +total(): number
    }
    class Product {
      +sku: string
      +price: number
    }

    User "1" o-- "0..1" Session : creates
    User "1" --> "0..*" Cart : owns
    Cart "1" --> "0..*" Product : contains
    """,

    "State Diagram": r"""stateDiagram-v2
    [*] --> Idle
    Idle --> Loading : fetch()
    Loading --> Error : fail
    Loading --> Ready : success
    Ready --> Editing : edit()
    Editing --> Ready : save()
    Error --> Idle : retry()
    """,

    "Entity Relationship Diagram": r"""erDiagram
      USER ||--o{ ORDER : places
      ORDER ||--|{ ORDER_LINE : has
      PRODUCT ||--o{ ORDER_LINE : referenced
      USER {
        UUID id PK
        string email
        string name
      }
      PRODUCT {
        string sku PK
        string title
        float price
      }
      ORDER {
        UUID id PK
        date created_at
        UUID user_id FK
      }
      ORDER_LINE {
        int id PK
        UUID order_id FK
        string product_sku FK
        int qty
      }
    """,

    "User Journey": r"""journey
    title Checkout funnel
    section Visit
      Landing -> Browse : 80
    section Product
      View -> Add to cart : 60
    section Payment
      Checkout -> Pay : 30
    section Post
      Confirmation -> Email receipt : 25
    """,

    "Gantt": r"""gantt
    dateFormat  YYYY-MM-DD
    title Release v1.0
    excludes weekends
    section Planning
    Spec             :a1, 2025-02-01, 7d
    Estimates        :after a1, 3d
    section Build
    Backend          :b1, 2025-02-10, 10d
    Frontend         :b2, after b1, 8d
    section QA
    Tests            :c1, after b2, 6d
    section Launch
    Release          :milestone, m1, after c1, 1d
    """,

    "Pie Chart": r"""pie title Browser share
      "Chrome" : 63
      "Safari" : 20
      "Edge"   : 8
      "Firefox": 6
      "Other"  : 3
    """,

    "Quadrant Chart": r"""quadrantChart
    title Product strategy
    x-axis Low risk --> High risk
    y-axis Low reward --> High reward
    quadrant-1 Invest
    quadrant-2 Evaluate
    quadrant-3 Avoid
    quadrant-4 Maintain
    Refactor core A : [0.3, 0.7]  radius: 12
    New feature X B : [0.65, 0.6] color: #ff5500
    Prototype idea C : [0.8, 0.3]
    Reduce costs D : [0.2, 0.4] stroke-color: #005500, stroke-width: 5px ,color: #55ffff
    """,

    "Requirement Diagram": r"""requirementDiagram
    requirement R1 {
      id: R1
      text: User must login
      risk: high
      verifymethod: test
    }
    requirement R2 {
      id: R2
      text: Cart persists
      risk: medium
      verifymethod: analysis
    }
    element FE {
      type: component
      docRef: FE.md
    }
    element API {
      type: component
      docRef: API.md
    }
    FE - satisfies -> R1
    API - satisfies -> R2
    R1 - traces -> R2
    """,

    "Gitgraph (Git) Diagram": r"""gitGraph
      commit id: "init"
      branch feature
      commit tag: "v0.1"
      checkout feature
      commit
      commit type: HIGHLIGHT
      checkout main
      merge feature tag: "merge-feature"
      commit id: "release"
    """,

    "C4 Diagram": r"""C4Context
      title Observability Platform - System Context
      Person(sre, "On-call SRE", "Monitors production health")
      System_Boundary(obs, "Observability Platform") {
        Container(agent, "Collector Agent", "Go", "Scrapes metrics & logs")
        Container(api, "Ingestion API", "Rust", "Accepts telemetry from agents")
        ContainerDb(store, "Time-series DB", "ClickHouse", "Stores metrics/events")
        Container(ui, "Status Dashboard", "React", "Live graphs and alerts")
      }
      Rel(sre, ui, "Views incidents / dashboards")
      Rel(agent, api, "Push metrics")
      Rel(api, store, "Writes telemetry")
      Rel(ui, api, "Queries alert summaries")
    """,

    "Mindmaps": r"""mindmap
    root((Project))
      Planning
        Scope
        Budget
      Build
        Backend
        Frontend
      Launch
        Marketing
        Ops
    """,

    "Timeline": r"""timeline
      title Migration plan
      2025-01 : Design complete
      2025-02 : Alpha build
      2025-03 : Beta rollout
      2025-04 : Public release
    """,

    "ZenUML": r"""zenuml
        title Scaled Agile Feature Delivery
        @Actor BusinessOwner #FFE8CC
        @Boundary ProductManager #0747A6
        @EC2 <<RTE>> ReleaseTrain #E3FCEF
        group AgileTeams {
          @Lambda TeamA
          @Lambda TeamB
        }
        @Boundary DevOps #CDEBFF

        @Starter(BusinessOwner)
        ProductManager.defineFeature(feature) {
          ReleaseTrain.planPI(feature) {
            // Teams work in parallel during the PI
            par {
              TeamA.implement(feature)
              TeamB.implement(feature)
            }
            ReleaseTrain.integrate(feature) {
              DevOps.deployToProd(feature)
            }
          }
        }
    """,

    "Sankey": r"""sankey-beta

    %% Global electricity generation: 2023
    %% Units are approximate TWh-equivalent flows for illustrative purposes

    Electricity grid,Coal (2023),4800
    Electricity grid,Nuclear (2023),2700
    Electricity grid,Hydro (2023),4200
    Electricity grid,Wind (2023),2000
    Electricity grid,Solar (2023),1500
    Electricity grid,Other renewables (2023),900
    """,

    "XY Chart": r"""xychart-beta
        title "Support Tickets per Month"
        x-axis [jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec]
        y-axis "Tickets opened" 0 --> 400
        bar [320, 340, 360, 310, 290, 280, 260, 270, 300, 330, 350, 370]
        line [320, 340, 360, 310, 290, 280, 260, 270, 300, 330, 350, 370]
    """,

    "Block Diagram": r"""block-beta
    columns 1
      metaLayer(("meta-yocto\n(layer)"))
      blockArrowId1<["fetch\n&\nparse"]>(down)
      block:BuildPipeline
        Recipe["linux-yocto.bb"]
        Tasks["do_configure\ndo_compile\ndo_install"]
        RootFS["rootfs"]
      end
      space
      ImageOut["bootable image\n.wic/.sdimg"]

      BuildPipeline --> ImageOut
      Tasks --> RootFS
      Recipe --> Tasks
      metaLayer --> Recipe

      style Recipe fill:#b3cde3,stroke:#225,stroke-width:2px
      style Tasks fill:#ccebc5,stroke:#252,stroke-width:2px
      style RootFS fill:#fff2ae,stroke:#664,stroke-width:2px
      style ImageOut fill:#decbe4,stroke:#424,stroke-width:2px
    """,


    "Packet": r"""packet
      title HTTP request packet
      0-15: "Src Port"
      16-31: "Dst Port"
      32-63: "Sequence Number"
      64-95: "Ack Number"
      96-99: "Data Offset"
      100-105: "Flags"
      106-111: "Window"
      112-127: "Checksum"
      128-143: "Urgent Ptr"
      144-191: "Payload"
    """,

    "Kanban": r"""kanban
      title Engineering board
      column Todo
        - Setup CI
        - Write docs
      column Doing
        - Implement auth
      column Review
        - API tests
      column Done
        - Project skeleton
    """,

    "Architecture": r"""architecture-beta
    group be(cloud)[BACKEND]

    service db(database)[Database] in be
    service disk(disk)[Storage] in be
    service server(server)[Server] in be

    group fe(cloud)[FRONTEND]

    service ux(internet)[Frontend] in fe


    db:L -- R:server
    disk:T -- B:db
    ux:T -- B:server
    """,

    "Radar": r"""radar-beta
      axis l["Languages"], f["Frameworks"], i["Infra"], d["Data"], e["Connectivity"]
      curve a["Adopt"]{ 80, 60, 70, 50,80}
      curve b["Trial"]{ 40, 45, 35, 30,20}
      curve c["Assess"]{ 20, 25, 30, 15,50}
    """,

    # "Treemap": r"""treemap
    #   title Storage usage
    #   section Home
    #     Docs: 3
    #     Photos: 7
    #     Videos: 12
    #   section Work
    #     Reports: 5
    #     Assets: 8
    # """,
}

def list_examples() -> List[str]:
    """Return the available example names."""
    return sorted(EXAMPLES.keys())

def get_example(name: str) -> str:
    """Return a Mermaid source by name. Raises KeyError if not found."""
    return EXAMPLES[name]
