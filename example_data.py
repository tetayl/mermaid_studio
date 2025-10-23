# example_data.py
# Ready-made Mermaid examples for many diagram types.
# Import in your app and use EXAMPLES[name] to get a code snippet.
# Some diagrams are experimental in newer Mermaid versions. Those entries
# include a note in comments and may require mermaid-cli v10+.

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
    x-axis Low risk -> High risk
    y-axis Low reward -> High reward
    quadrant-1 Invest
    quadrant-2 Evaluate
    quadrant-3 Avoid
    quadrant-4 Maintain
    A[Refactor core]        : [0.3, 0.7]
    B[New feature X]        : [0.65, 0.6]
    C[Prototype idea]       : [0.8, 0.3]
    D[Reduce costs]         : [0.2, 0.4]
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
      title Web shop - System Context
      Person(customer, "Customer", "A shopper")
      System_Boundary(c1, "Shop") {
        Container(web, "Web App", "React", "User interface")
        Container(api, "API", "Python", "Business logic")
        ContainerDb(db, "Database", "PostgreSQL", "Orders and products")
      }
      Rel(customer, web, "Uses")
      Rel(web, api, "Calls")
      Rel(api, db, "Reads and writes")
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
    @startuml
    title Sign in flow
    User -> App: Open
    App -> API: POST /login
    API --> App: 200 OK + token
    App --> User: Navigate to dashboard
    @enduml
    """,

    "Sankey": r"""sankey-beta
      title Traffic sources
      Home[Home] -> Product[Product] : 600
      Home -> Docs[Docs] : 150
      Product -> Checkout[Checkout] : 250
      Docs -> Checkout : 30
      Product -> Exit[Exit] : 200
      Docs -> Exit : 120
    """,

    "XY Chart": r"""xychart-beta
      title Response times
      x-axis label Time (s) type linear
      y-axis label ms type linear
      series Backend: [ [0,120], [1,110], [2,130], [3,95] ]
      series Frontend: [ [0,200], [1,180], [2,150], [3,140] ]
    """,

    "Block Diagram": r"""blockDiagram
      title Payment pipeline
      block Ingress
        Web
        Mobile
      end
      block Core
        Auth
        Payments
        Ledger
      end
      block Storage
        DB[(Postgres)]
        Cache[(Redis)]
      end
      Web -> Auth -> Payments -> Ledger
      Mobile -> Auth
      Payments -> DB
      Auth -> Cache
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
      144-...: "Payload"
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

    "Architecture": r"""architecture
      title Simple web app
      component Browser
      component CDN
      component WebApp
      component API
      database DB
      queue Queue
      Browser -> CDN
      CDN -> WebApp
      WebApp -> API
      API -> DB
      API -> Queue
    """,

    "Radar": r"""radar
      title Tech radar
      categories Languages, Frameworks, Infra, Data
      series Adopt: 80, 60, 70, 50
      series Trial: 40, 45, 35, 30
      series Assess: 20, 25, 30, 15
    """,

    "Treemap": r"""treemap
      title Storage usage
      section Home
        Docs: 3
        Photos: 7
        Videos: 12
      section Work
        Reports: 5
        Assets: 8
    """,
}

def list_examples() -> List[str]:
    """Return the available example names."""
    return sorted(EXAMPLES.keys())

def get_example(name: str) -> str:
    """Return a Mermaid source by name. Raises KeyError if not found."""
    return EXAMPLES[name]
