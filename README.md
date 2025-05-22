# SmartKBEngine Overview

**SmartKBEngine** is a comprehensive solution for sourcing, managing, and cataloging content to build a robust knowledgebase thats supports semantic search and retrieval of information. The product organizes content by topics and allows access restrictions based on predefined groups and users.

---

## Key Features

### 0. Topics Management

**Dynamic Topic Management:**
Administrators can effortlessly create, modify, or delete topics, ensuring that content is always organized within the most relevant categories. New content is systematically uploaded to one or more topics, maintaining a structured repository that evolves with the organization.

**Controlled Access and Permissions:**
Access to topics and the corresponding content is secured through a robust access control management system. This system governs who can view or modify topics and content, ensuring that sensitive information remains protected while allowing collaboration among authorized users.

### 1. Content Sourcing

**Multi-Source Integration:**  
Import documents from websites (via scraping), Google Drive, Dropbox, or your local machine.

---

### 2. Cataloging

**Metadata Enrichment:**  
Once sourced, content is enriched with metadata, validated, and approved before being added to a catalog.

---

### 3. Knowledge Base Creation

This process is divided into three key stages:

#### Parsing & Chunking
- Documents are split into logical nodes and converted into markdown.
- Currently, page-level chunking is supported via **LlamaParse**, with potential expansion to include parsers like **Docling**.

#### Metadata Extraction
Each markdown page is processed by a lightweight LLM to extract essential metadata, including:
- A summary of the page content
- Topics covered on the page
- Types of questions the page can answer

#### Embedding Creation
- An embedding is generated for each page, incorporating the rich metadata extracted by the LLM.

---

### 4. Search & Retrieval

**Advanced Retrieval Techniques:**  
The knowledge base supports both **semantic** and **hybrid search**, enabling fine-grained document retrieval based on user queries.  
Retrieved documents are processed by the LLM alongside the query to generate precise answers.

---

### 5. Conversational AI
Engine maintains chat history, allowing users to ask follow-up questions without re-entering full context.  
The LLM reconstructs queries using historical data to ensure accurate document retrieval.

---

### 6. Chat Threads

**Personalized Experience:**  
Each user has personalized chat threads, facilitating:
- Easy access to past interactions
- The ability to delete threads as needed
- Search specific content from history
- Recommend question based on user's past interaction and question or as a following in the current session.

---

### 7. Up coming features
- **Support for Document Images:**  
  Enables extraction and indexing of content from embedded images (e.g., charts, scanned documents, or infographics) within uploaded files. This extends the knowledge base to include visual data, making the system more comprehensive and accessible.

- **Internet Search Capability:**  
  Augments internal knowledge base results with real-time information sourced directly from the internet. This ensures users receive the most current and relevant answers, even when the internal content may be outdated or incomplete.

- **MCP server based sourcing:**
  Sourcing content from differenct data sources using a standard interface based on MCP  

