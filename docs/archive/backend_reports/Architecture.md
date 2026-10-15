# Architecture Overview
The Building Knowledge Intelligence System employs a Hybrid Retrieval-Augmented Generation (RAG) architecture powered by an Agentic AI workflow.

## 1. Overall System Architecture
The system consists of a Vite/React frontend, a FastAPI Python backend, and a tripartite database layer (MongoDB for metadata, ChromaDB for vectors, Neo4j for graphs).

## 2. Hybrid RAG Pipeline
Combines dense vector similarity search (ChromaDB) with topological graph traversal (Neo4j) to inject highly contextualized engineering knowledge into the LLM context window.

## 3. Agentic AI Workflow
Utilizes LangGraph to parse user queries, determine if external search, document retrieval, or direct answering is required, and orchestrates the final response.
