# GraphLang is AI-native

The language is not the regex parser, the canvas, or Cypher.

```
human speech / draw / import / LLM
              ↓
         Intent JSON
              ↓
     engine + projections
     (graph, Cypher, GQL, HTML, voice)
```

Human features exist so people can *drive* the same IR an AI already speaks.

- Adding a node by voice is `create_node`.
- “It’s for secure auth to the db” is `set_purpose` plus, if needed, `connect_with_auth`.
- Drawing a line while talking still emits those intents; the words become `purpose`.
- When an API key is present, the LLM compiles first. Rules only cover the offline case.
- Do not special-case humans in a way that the model cannot emit.
