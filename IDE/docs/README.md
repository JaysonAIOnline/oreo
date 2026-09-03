# OREO Documentation

## Overview

This directory contains documentation for the OREO programming language and IDE.

## Documents

| Document | Description |
|----------|-------------|
| [language_guide.md](language_guide.md) | Language tutorial and guide |
| [api_reference.md](api_reference.md) | API reference for all modules |
| [visual_editor_guide.md](visual_editor_guide.md) | Visual editor user guide |
| [ai_integration_guide.md](ai_integration_guide.md) | AI integration guide |
| [contributing.md](contributing.md) | Contribution guidelines |

## Architecture Subsystem (merged from GraphLang)

The OREO Architecture package (`parser/architecture/`) is the NL+visual layer for
modeling application architecture. Its docs are under [docs/architecture/](architecture/).

| Document | Description |
|----------|-------------|
| [ai-native.md](architecture/ai-native.md) | Intents are the language; Cypher/GQL/HTML are projections |
| [end-user.md](architecture/end-user.md) | End-user pathway (talk + draw) |
| [graph-query-languages.md](architecture/graph-query-languages.md) | Same intents in Cypher, GQL, Gremlin, SPARQL |
| [microservices-and-state.md](architecture/microservices-and-state.md) | State, handshakes, service mesh |
| [neo4j-vs-memgraph-gql.md](architecture/neo4j-vs-memgraph-gql.md) | Store comparison and Bolt adapter |
| [voice-interface.md](architecture/voice-interface.md) | Ears + voice UI in the editor |
| [../spec/NL_CYPHER_SPEC.md](../spec/NL_CYPHER_SPEC.md) | NL layer + Cypher specification |

## Quick Links

- [Language Specification](../spec/OREO_LANGUAGE_SPEC.md)
- [Project Structure](../PROJECT_STRUCTURE.md)
- [Agent Onboarding](../ALL%20AGENTS%20READ%20FIRST.md)

## Building Documentation

```bash
# Generate API docs from source
python -m docs.generate_api_docs

# Build HTML docs (if using Sphinx/MkDocs)
mkdocs build
```