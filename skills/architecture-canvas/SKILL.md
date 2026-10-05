---
name: architecture-canvas
description: Trace how events flow through a codebase and render the result as a zoomable, pannable interactive canvas. Use when the user wants to visualize or map their architecture, has lost the overview of how components connect, or asks what happens end to end when some event occurs (a message arrives, a webhook fires, a user clicks pay).
license: MIT
---

# Architecture canvas

The deliverable is a canvas the user can drag, zoom, and step through flow by flow. What makes it worth trusting is the **trace**: every arrow is a hop you found in code, with its `file:line`. If you could not see a hop, flag it as `inferred` so it draws dashed.

## 1. Scope the flows

A **flow** is one trigger event followed to its end, for example "customer sends a WhatsApp message" or "agent replies from the helpdesk". Use the user's words. If they only name a system, list its entry points (webhook routes, HTTP handlers, CLI commands, cron jobs, queue consumers) and pick the 3–6 that carry the core business. Include the return paths. The reply path is usually the part the user has lost track of.

**Done when** you have a list of flows, each with a concrete trigger and the `file:line` of its entry point.

**Refresh branch:** a canvas may already exist, either under `docs/architecture/` or at a path the user gives. If so, read its `#canvas-data` block first and treat this run as a refresh. Re-trace every flow against current code, keep existing ids stable, and add, change, or remove steps where the code has moved.

## 2. Trace each flow

Start at the entry point and follow the path hop by hop. Cover calls across modules, outbound HTTP/SDK calls, database reads and writes, background tasks and queues, and third-party webhooks that call back in. Also cover the **branches** that change where things go, such as state checks ("human handoff active?"), feature flags, and error or fallback paths. For each hop, record from, to, what crosses (method + path, event name, table, essential payload fields), and `file:line`.

To find which external systems exist and how they connect, read the wiring files: `.env.example`, docker-compose, route tables, and SDK client setup. Some hops happen in a system you cannot see, like a webhook URL configured in a vendor dashboard or third-party server behaviour. Mark those `inferred` and write in `detail` what the inference rests on.

In many stacks the wiring sits in config or editor files rather than code. A hop declared there is **not** inferred: cite the config file and line.

- **Java / JSP:** `web.xml` (servlets, filters, listeners), `struts-config.xml`, Spring bean XML or `@Controller`/`@RequestMapping`/`@Autowired`, JNDI datasources in `context.xml`. JSPs call into beans through `<jsp:useBean>` and taglibs.
- **.NET:** `Program.cs`/`Startup.cs` (DI registrations and middleware order), route attributes, `Global.asax` and `RouteConfig` in older apps, `web.config`/`appsettings.json` for connection strings and endpoints, and EF `DbContext` for which tables are touched.
- **Stored procedures:** when a step calls one, look for its SQL in the repo (migrations, `.sql`, a database project). If the SQL isn't there, mark the hop `inferred`.
- **Godot:** signals connected in the editor are `[connection signal=… from=… to=… method=…]` lines in `.tscn`. Also check autoload singletons in `project.godot`, plus `connect()`/`emit_signal()` and groups (`add_to_group`, `call_group`) in `.gd`/`.cs`.
- **Unity:** Inspector-wired `UnityEvent`s and component references are stored in `.unity`/`.prefab` YAML (`m_PersistentCalls`, `m_MethodName`) and point to scripts by GUID. Find the script by grepping `.meta` files for that GUID. If the assets are saved in binary format, mark those hops `inferred`. Also check ScriptableObject event channels, `SendMessage`, and static event buses.

**Done when** every flow reaches a terminal (response sent, message delivered, state persisted). Every external boundary on the path (inbound webhook, outbound API call, data store, queue) must be a step with a `file:line` or an `inferred` flag. A branch that changes the destination is either its own step or its own flow.

## 3. Model

Fill the data block of [canvas-template.html](canvas-template.html). Its header comment holds the schema.

- **Nodes:** use one per deployable, external system, and data store, plus one per module that owns a distinct responsibility in the flows (router, state machine, integration client). Fold helpers into their owner. Keep labels to 24 characters or fewer. A monolith is one deployable, so its nodes are its layers or modules (controller → service → DAO → database) plus the external systems. In a game, nodes are subsystems (input, player/state, physics, AI, UI, audio, save, networking) and autoloads or managers.
- **Layout:** columns run left→right in the order a message travels: outside actors → your services → third parties and stores. Group columns into `zones` (for example "Meta", "Our bot", "Chatwoot stack"). Put nodes that talk often in adjacent columns. When an arrow skips a column within one row, the renderer arcs it over the nodes in between. In games, flows are event chains inside the frame loop (for example "player presses jump → physics → animation → HUD"), and a flow ends when state is updated or something is shown. Lay the columns out as input → game logic → physics/world → presentation (UI, audio) → persistence/network.
- **Steps:** keep `label` short; it sits on the arrow. Write `detail` in 1–3 sentences in the user's domain language. It is what they read while stepping through, so say what happens and why it matters.

## 4. Render and validate

Copy the template to the destination, replace the data block, and set `<title>` to a 2–4 word name. Then run:

```
python <this skill's directory>/validate.py <canvas.html> --root <repo root>
```

The validator fails on unknown node ids, two nodes in one grid cell, and refs whose file or line does not exist. Run it until it prints `OK`. When no repo is available (for example on claude.ai with pasted code), leave out `--root`.

## 5. Deliver

- **Claude Code:** save to `docs/architecture/<slug>.html` in the repo so the next refresh finds it. If the Artifact tool is available, also publish the file as an artifact and give the link.
- **claude.ai:** publish it as an HTML artifact.

In the reply, include the flows drawn, the 2–3 non-obvious things the trace turned up (unexpected coupling, a path with no error handling, an important hop that is only inferred), and the controls: drag to pan, scroll or pinch to zoom, pick a flow, ←/→ to step, `F` to fit.
