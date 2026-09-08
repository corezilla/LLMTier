# LLMTier V0.4 Data Plane deferred scope

Status: Future / not implemented

Slinky scope decision `S-20260906-2f9539048493` defers the following capabilities from V0.3:

- `POST /v1/chat/completions`;
- Responses SSE and Chat SSE;
- all streaming event, disconnect, replay and reattach contracts.

These paths and schemas are not part of the V0.3 authoritative OpenAPI. V0.3 must return the typed
`unsupported_endpoint` error for the Chat path and `unsupported_feature` when `POST /v1/responses`
requests `stream=true`. There is no alias, normalization route, inactive parallel endpoint, provider
passthrough or runtime fallback. A future V0.4 contract requires a separate review and activation gate.
