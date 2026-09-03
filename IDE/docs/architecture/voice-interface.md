# Voice interface (GraphLang syntax)

People never write GraphLang. They talk. The voice answers in this shape:

1. **Notice** — “Oh, this is reading like a storefront.”
2. **Offer a pack** — “Want a database, a secure checkout, a picture store, and an LLM for design ideas?”
3. **Wait** — Yes / add those / not now.
4. **Do it as intents** — still AI-native. A pack is several `create_node` + handshake intents.
5. **Then lint the lines** — missing secure path, missing includes.

## Scenes the voice can see

| It notices | It offers |
|---|---|
| shop / cart / product / checkout | MainDB, secure Checkout, PictureStore, DesignLLM |
| fan / band / artist / club | Forum, MailingList, Login, FansDB |
| blog / post / article | PostsDB, Comments, AuthorLogin |
| photo / gallery / portfolio | PictureStore, Grid, private Upload |
| dashboard / settings / app | Users, secure Settings, Audit |
| pages and no database | MainDB + a first handshake |

## Turns

```
You: add a shop page
GL:  Shop is on the canvas. Oh — this is reading like a storefront.
     Want nodes for a database, a secure checkout, a picture store,
     and an LLM we can call for design ideas?
You: add those
GL:  Okay — I added that.
```

```
You: this is a fan site for the band
GL:  Hey — this looks like a fan site.
     Want nodes for a forum, a mailing list, and user logins?
You: yes
```

Drawing a line while talking still names that one line.
Scene offers are for when the *whole picture* has a genre.
